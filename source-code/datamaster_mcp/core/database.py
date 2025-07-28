#!/usr/bin/env python3
"""
DataMaster MCP - 数据库核心模块

这个模块包含所有数据库相关的工具函数：
- connect_data_source: 数据源连接路由器
- execute_sql: 本地数据库查询
- query_external_database: 外部数据库查询
- list_data_sources: 数据源列表
- manage_database_config: 数据库配置管理

以及相关的辅助函数和数据库操作。
"""

import json
import sqlite3
import pandas as pd
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import numpy as np

# 设置日志
logger = logging.getLogger("DataMaster_MCP.Database")

# SQLAlchemy imports for pandas to_sql compatibility
try:
    from sqlalchemy import create_engine
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy not available. External database import may not work properly.")

# 导入配置管理器
try:
    from ..config.database_manager import database_manager
    from ..config.config_manager import config_manager
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent.parent.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from datamaster_mcp.config.database_manager import database_manager
    from datamaster_mcp.config.config_manager import config_manager

# ================================
# 数据库配置和初始化
# ================================

DB_PATH = "data/analysis.db"
DATA_DIR = "data"
EXPORTS_DIR = "exports"

# 确保目录存在
for directory in [DATA_DIR, EXPORTS_DIR]:
    Path(directory).mkdir(exist_ok=True)

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
    return conn

def init_database():
    """初始化数据库"""
    try:
        with get_db_connection() as conn:
            # 创建元数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _metadata (
                    table_name TEXT PRIMARY KEY,
                    created_at TEXT,
                    source_type TEXT,
                    source_path TEXT,
                    row_count INTEGER
                )
            """)
            
            # 创建数据处理元数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_metadata (
                    table_name TEXT PRIMARY KEY,
                    source_type TEXT,
                    source_path TEXT,
                    created_at TEXT,
                    metadata TEXT
                )
            """)
            
            conn.commit()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

# ================================
# 数据库工具函数
# ================================

def _escape_identifier(identifier: str) -> str:
    """转义SQL标识符（表名、列名等）"""
    # 使用双引号包围标识符，并转义内部的双引号
    return '"' + identifier.replace('"', '""') + '"'

def _safe_table_query(table_name: str, query_template: str) -> str:
    """安全地构建包含表名的查询"""
    escaped_table = _escape_identifier(table_name)
    return query_template.format(table=escaped_table)

def _table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return cursor.fetchone() is not None
    except Exception:
        return False

def _preprocess_sql(query: str) -> str:
    """预处理SQL语句"""
    # 移除多余的空白字符
    query = ' '.join(query.split())
    
    # 基本的SQL注入防护
    dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
    query_upper = query.upper()
    
    for keyword in dangerous_keywords:
        if keyword in query_upper and not query_upper.strip().startswith('SELECT'):
            raise ValueError(f"不允许执行 {keyword} 操作，仅支持 SELECT 查询")
    
    return query

def _format_sql_error(error: Exception, query: str) -> dict:
    """格式化SQL错误信息"""
    error_msg = str(error)
    
    # 常见错误类型识别
    if "no such table" in error_msg.lower():
        error_type = "表不存在"
        suggestion = "请使用 get_data_info() 查看可用的表"
    elif "no such column" in error_msg.lower():
        error_type = "列不存在"
        suggestion = "请使用 get_data_info(info_type='schema', table_name='表名') 查看表结构"
    elif "syntax error" in error_msg.lower():
        error_type = "SQL语法错误"
        suggestion = "请检查SQL语法是否正确"
    else:
        error_type = "未知错误"
        suggestion = "请检查查询语句和数据库连接"
    
    return {
        "status": "error",
        "message": f"SQL执行失败: {error_msg}",
        "error_type": error_type,
        "suggestion": suggestion,
        "query": query
    }

# ================================
# 数据导入辅助函数
# ================================

def _import_excel(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入Excel文件到本地SQLite或外部数据库"""
    try:
        # 获取配置参数
        file_path = config.get('file_path')
        sheet_name = config.get('sheet_name', 0)  # 默认第一个sheet
        
        if not file_path:
            raise ValueError("缺少file_path参数")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取Excel文件
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # 生成表名
        if not target_table:
            file_name = Path(file_path).stem
            target_table = f"excel_{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 清理列名（移除特殊字符）
        df.columns = [col.replace(' ', '_').replace('-', '_').replace('.', '_') for col in df.columns]
        
        # 导入到数据库
        if target_database:
            # 导入到外部数据库
            return _import_to_external_database(df, target_table, target_database, 'excel', file_path, sheet_name)
        else:
            # 导入到本地SQLite数据库
            with get_db_connection() as conn:
                df.to_sql(target_table, conn, if_exists='replace', index=False)
                
                # 更新元数据
                conn.execute("""
                    INSERT OR REPLACE INTO _metadata 
                    (table_name, created_at, source_type, source_path, row_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    target_table,
                    datetime.now().isoformat(),
                    'excel',
                    file_path,
                    len(df)
                ))
                conn.commit()
            
            result = {
                "status": "success",
                "message": "Excel文件已导入到本地SQLite数据库",
                "data": {
                    "table_name": target_table,
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                    "file_path": file_path,
                    "sheet_name": sheet_name,
                    "connection_type": "本地数据导入",
                    "data_location": f"本地SQLite数据库 ({DB_PATH})",
                    "usage_note": f"使用execute_sql('SELECT * FROM \"{target_table}\"')查询此表数据"
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "source_type": "excel"
                }
            }
        
        return f"✅ Excel文件已导入到本地SQLite数据库\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"Excel导入失败: {e}")
        raise

def _import_csv(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入CSV文件到本地SQLite或外部数据库"""
    try:
        file_path = config.get('file_path')
        encoding = config.get('encoding', 'utf-8')
        separator = config.get('separator', ',')
        
        if not file_path:
            raise ValueError("缺少file_path参数")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取CSV文件
        df = pd.read_csv(file_path, encoding=encoding, sep=separator)
        
        # 生成表名
        if not target_table:
            file_name = Path(file_path).stem
            target_table = f"csv_{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 清理列名
        df.columns = [col.replace(' ', '_').replace('-', '_').replace('.', '_') for col in df.columns]
        
        # 导入到数据库
        if target_database:
            # 导入到外部数据库
            return _import_to_external_database(df, target_table, target_database, 'csv', file_path, {'encoding': encoding, 'separator': separator})
        else:
            # 导入到本地SQLite数据库
            with get_db_connection() as conn:
                df.to_sql(target_table, conn, if_exists='replace', index=False)
                
                # 更新元数据
                conn.execute("""
                    INSERT OR REPLACE INTO _metadata 
                    (table_name, created_at, source_type, source_path, row_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    target_table,
                    datetime.now().isoformat(),
                    'csv',
                    file_path,
                    len(df)
                ))
                conn.commit()
            
            result = {
                "status": "success",
                "message": "CSV文件已导入到本地SQLite数据库",
                "data": {
                    "table_name": target_table,
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                    "file_path": file_path,
                    "encoding": encoding,
                    "separator": separator,
                    "connection_type": "本地数据导入",
                    "data_location": f"本地SQLite数据库 ({DB_PATH})",
                    "usage_note": f"使用execute_sql('SELECT * FROM \"{target_table}\"')查询此表数据"
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "source_type": "csv"
                }
            }
        
        return f"✅ CSV文件已导入到本地SQLite数据库\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"CSV导入失败: {e}")
        raise

def _import_json(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入JSON文件到本地SQLite或外部数据库"""
    try:
        file_path = config.get('file_path')
        encoding = config.get('encoding', 'utf-8')
        
        if not file_path:
            raise ValueError("缺少file_path参数")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding=encoding) as f:
            data = json.load(f)
        
        # 转换为DataFrame
        if isinstance(data, list):
            df = pd.json_normalize(data)
        elif isinstance(data, dict):
            df = pd.json_normalize([data])
        else:
            raise ValueError("JSON文件格式不支持，需要是对象或对象数组")
        
        # 生成表名
        if not target_table:
            file_name = Path(file_path).stem
            target_table = f"json_{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 清理列名
        df.columns = [col.replace(' ', '_').replace('-', '_').replace('.', '_') for col in df.columns]
        
        # 导入到数据库
        if target_database:
            # 导入到外部数据库
            return _import_to_external_database(df, target_table, target_database, 'json', file_path, {'encoding': encoding})
        else:
            # 导入到本地SQLite数据库
            with get_db_connection() as conn:
                df.to_sql(target_table, conn, if_exists='replace', index=False)
                
                # 更新元数据
                conn.execute("""
                    INSERT OR REPLACE INTO _metadata 
                    (table_name, created_at, source_type, source_path, row_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    target_table,
                    datetime.now().isoformat(),
                    'json',
                    file_path,
                    len(df)
                ))
                conn.commit()
            
            result = {
                "status": "success",
                "message": "JSON文件已导入到本地SQLite数据库",
                "data": {
                    "table_name": target_table,
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                    "file_path": file_path,
                    "encoding": encoding,
                    "connection_type": "本地数据导入",
                    "data_location": f"本地SQLite数据库 ({DB_PATH})",
                    "usage_note": f"使用execute_sql('SELECT * FROM \"{target_table}\"')查询此表数据"
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "source_type": "json"
                }
            }
        
        return f"✅ JSON文件已导入到本地SQLite数据库\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"JSON导入失败: {e}")
        raise

def _import_to_external_database(df: pd.DataFrame, target_table: str, target_database: str, source_type: str, source_path: str, source_config: any) -> str:
    """导入数据到外部数据库"""
    try:
        # 使用数据库管理器导入数据
        result = database_manager.import_dataframe(target_database, target_table, df)
        
        if result["success"]:
            response_data = {
                "status": "success",
                "message": f"{source_type.upper()}文件已导入到外部数据库",
                "data": {
                    "table_name": target_table,
                    "database_name": target_database,
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                    "source_path": source_path,
                    "source_config": source_config,
                    "connection_type": "外部数据库导入",
                    "data_location": f"外部数据库 ({target_database})",
                    "usage_note": f"使用query_external_database(database_name='{target_database}', query='SELECT * FROM {target_table}')查询此表数据"
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "source_type": source_type
                }
            }
            return f"✅ {source_type.upper()}文件已导入到外部数据库\n\n{json.dumps(response_data, indent=2, ensure_ascii=False)}"
        else:
            raise Exception(result["error"])
            
    except Exception as e:
        logger.error(f"外部数据库导入失败: {e}")
        raise

def _import_csv(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入CSV文件到本地SQLite或外部数据库"""
    try:
        # 获取配置参数
        file_path = config.get('file_path')
        encoding = config.get('encoding', 'utf-8')
        separator = config.get('separator', ',')
        
        if not file_path:
            raise ValueError("缺少file_path参数")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取CSV文件
        df = pd.read_csv(file_path, encoding=encoding, sep=separator)
        
        # 生成表名
        if not target_table:
            file_name = Path(file_path).stem
            target_table = f"csv_{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 清理列名（移除特殊字符）
        df.columns = [col.replace(' ', '_').replace('-', '_').replace('.', '_') for col in df.columns]
        
        # 导入到数据库
        if target_database:
            # 导入到外部数据库
            return _import_to_external_database(df, target_table, target_database, 'csv', file_path, config)
        else:
            # 导入到本地SQLite
            return _import_to_local_database(df, target_table, 'csv', file_path, config)
            
    except Exception as e:
        logger.error(f"CSV导入失败: {e}")
        raise

def _import_json(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入JSON文件到本地SQLite或外部数据库"""
    try:
        # 获取配置参数
        file_path = config.get('file_path')
        encoding = config.get('encoding', 'utf-8')
        
        if not file_path:
            raise ValueError("缺少file_path参数")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding=encoding) as f:
            json_data = json.load(f)
        
        # 转换为DataFrame
        if isinstance(json_data, list):
            df = pd.json_normalize(json_data)
        elif isinstance(json_data, dict):
            df = pd.json_normalize([json_data])
        else:
            raise ValueError("JSON文件格式不支持，需要是对象或对象数组")
        
        # 生成表名
        if not target_table:
            file_name = Path(file_path).stem
            target_table = f"json_{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 清理列名（移除特殊字符）
        df.columns = [col.replace(' ', '_').replace('-', '_').replace('.', '_') for col in df.columns]
        
        # 导入到数据库
        if target_database:
            # 导入到外部数据库
            return _import_to_external_database(df, target_table, target_database, 'json', file_path, config)
        else:
            # 导入到本地SQLite
            return _import_to_local_database(df, target_table, 'json', file_path, config)
            
    except Exception as e:
        logger.error(f"JSON导入失败: {e}")
        raise

# ================================
# 数据库连接函数
# ================================

def _connect_sqlite(config: dict, target_table: str = None) -> str:
    """连接SQLite数据库文件"""
    try:
        db_path = config.get('db_path') or config.get('file_path')
        
        if not db_path:
            raise ValueError("缺少db_path或file_path参数")
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"SQLite文件不存在: {db_path}")
        
        # 测试连接
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        result = {
            "status": "success",
            "message": "SQLite数据库连接成功",
            "data": {
                "db_path": db_path,
                "table_count": len(tables),
                "tables": tables,
                "connection_type": "SQLite文件连接",
                "usage_note": "使用execute_sql()查询此数据库，或使用get_data_info()查看详细信息"
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_type": "sqlite"
            }
        }
        
        return f"✅ SQLite数据库连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"SQLite连接失败: {e}")
        raise

def _connect_external_database(db_type: str, config: dict, target_table: str = None) -> str:
    """连接外部数据库（第一步：创建临时配置）"""
    try:
        # 生成临时配置名称
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_config_name = f"temp_{db_type}_{timestamp}"
        
        # 标准化配置参数
        standardized_config = _standardize_db_config(db_type, config)
        
        # 创建临时配置
        result = database_manager.create_temp_config(temp_config_name, db_type, standardized_config)
        
        if result["success"]:
            response_data = {
                "status": "success",
                "message": f"{db_type.upper()}数据库临时配置已创建",
                "data": {
                    "config_name": temp_config_name,
                    "database_type": db_type,
                    "host": standardized_config.get('host'),
                    "port": standardized_config.get('port'),
                    "database": standardized_config.get('database'),
                    "connection_type": "临时配置创建",
                    "next_step": f"使用connect_data_source(source_type='database_config', config={{'database_name': '{temp_config_name}'}})建立连接"
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "source_type": db_type,
                    "step": "第一步：配置创建"
                }
            }
            return f"✅ {db_type.upper()}数据库临时配置已创建\n\n{json.dumps(response_data, indent=2, ensure_ascii=False)}"
        else:
            raise Exception(result["error"])
            
    except Exception as e:
        logger.error(f"{db_type}配置创建失败: {e}")
        raise

def _connect_from_config(config: dict, target_table: str = None) -> str:
    """使用已有配置连接数据库（第二步：实际连接）"""
    try:
        database_name = config.get('database_name')
        
        if not database_name:
            raise ValueError("缺少database_name参数")
        
        # 建立数据库连接
        result = database_manager.connect_database(database_name)
        
        if result["success"]:
            # 获取数据库信息
            tables = database_manager.get_table_list(database_name)
            db_info = database_manager.get_database_info(database_name)
            
            response_data = {
                "status": "success",
                "message": "数据库连接已建立",
                "data": {
                    "database_name": database_name,
                    "database_type": db_info.get('type', 'unknown'),
                    "host": db_info.get('host'),
                    "port": db_info.get('port'),
                    "database": db_info.get('database'),
                    "table_count": len(tables),
                    "tables": tables[:10] if len(tables) > 10 else tables,  # 只显示前10个表
                    "connection_type": "外部数据库连接",
                    "usage_note": f"使用query_external_database(database_name='{database_name}', query='SQL')查询此数据库"
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "source_type": "database_config",
                    "step": "第二步：连接建立"
                }
            }
            
            if len(tables) > 10:
                response_data["data"]["note"] = f"共有{len(tables)}个表，仅显示前10个"
            
            return f"✅ 数据库连接已建立\n\n{json.dumps(response_data, indent=2, ensure_ascii=False)}"
        else:
            raise Exception(result["error"])
            
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def _standardize_db_config(db_type: str, config: dict) -> dict:
    """标准化数据库配置参数"""
    standardized = config.copy()
    
    # 统一用户名参数
    if 'username' in standardized and 'user' not in standardized:
        standardized['user'] = standardized['username']
    
    # 确保端口号是整数
    if 'port' in standardized:
        try:
            standardized['port'] = int(standardized['port'])
        except (ValueError, TypeError):
            # 使用默认端口
            default_ports = {
                'mysql': 3306,
                'postgresql': 5432,
                'mongodb': 27017
            }
            standardized['port'] = default_ports.get(db_type, 3306)
    
    # 确保密码是字符串
    if 'password' in standardized:
        standardized['password'] = str(standardized['password'])
    
    return standardized

# ================================
# 主要工具函数实现
# ================================

def connect_data_source_impl(
    source_type: str,
    config: dict,
    target_table: str = None,
    target_database: str = None
) -> str:
    """数据源连接路由器实现"""
    try:
        if source_type == "excel":
            return _import_excel(config, target_table, target_database)
        elif source_type == "csv":
            return _import_csv(config, target_table, target_database)
        elif source_type == "json":
            return _import_json(config, target_table, target_database)
        elif source_type == "sqlite":
            return _connect_sqlite(config, target_table)
        elif source_type in ["mysql", "postgresql", "mongodb"]:
            return _connect_external_database(source_type, config, target_table)
        elif source_type == "database_config":
            return _connect_from_config(config, target_table)
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")
    except Exception as e:
        logger.error(f"数据源连接失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"数据源连接失败: {str(e)}",
            "source_type": source_type,
            "timestamp": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)

def execute_sql_impl(
    query: str,
    params: dict = None,
    limit: int = 1000,
    data_source: str = None
) -> str:
    """本地数据库查询实现"""
    try:
        # 预处理SQL语句
        query = _preprocess_sql(query)
        
        # 添加LIMIT限制
        if limit and limit > 0 and "LIMIT" not in query.upper():
            query += f" LIMIT {limit}"
        
        with get_db_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            
            # 获取列名
            columns = [description[0] for description in cursor.description]
            
            # 获取数据
            rows = cursor.fetchall()
            
            # 转换为字典列表
            data = [dict(zip(columns, row)) for row in rows]
            
            result = {
                "status": "success",
                "data": data,
                "columns": columns,
                "row_count": len(data),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
            
    except Exception as e:
        logger.error(f"SQL执行失败: {e}")
        error_info = _format_sql_error(e, query)
        return json.dumps(error_info, indent=2, ensure_ascii=False)

def query_external_database_impl(
    database_name: str,
    query: str,
    limit: int = 1000
) -> str:
    """外部数据库查询实现"""
    try:
        # 执行查询
        result = database_manager.execute_query(database_name, query, limit)
        
        if result["success"]:
            response_data = {
                "status": "success",
                "data": result["data"],
                "columns": result.get("columns", []),
                "row_count": result.get("row_count", 0),
                "database_name": database_name,
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(response_data, indent=2, ensure_ascii=False, default=str)
        else:
            raise Exception(result["error"])
            
    except Exception as e:
        logger.error(f"外部数据库查询失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"外部数据库查询失败: {str(e)}",
            "database_name": database_name,
            "query": query,
            "timestamp": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)

def list_data_sources_impl() -> str:
    """数据源列表实现"""
    try:
        # 获取本地SQLite信息
        local_info = {
            "name": "local_sqlite",
            "type": "sqlite",
            "status": "available",
            "path": DB_PATH,
            "is_default": True
        }
        
        # 获取外部数据库配置
        external_configs = database_manager.list_all_configs()
        
        result = {
            "status": "success",
            "data": {
                "local_database": local_info,
                "external_databases": external_configs,
                "total_count": 1 + len(external_configs)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"获取数据源列表失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)

def manage_database_config_impl(
    action: str,
    config: dict = None
) -> str:
    """数据库配置管理实现"""
    try:
        if action == "list":
            configs = database_manager.list_all_configs()
            result = {
                "status": "success",
                "action": "list",
                "data": configs,
                "count": len(configs)
            }
        elif action == "test":
            if not config or "database_name" not in config:
                raise ValueError("测试连接需要database_name参数")
            test_result = database_manager.test_connection(config["database_name"])
            result = {
                "status": "success",
                "action": "test",
                "data": test_result
            }
        elif action == "add":
            if not config:
                raise ValueError("添加配置需要config参数")
            add_result = database_manager.add_permanent_config(
                config["database_name"],
                config["database_config"]
            )
            result = {
                "status": "success",
                "action": "add",
                "data": add_result
            }
        elif action == "remove":
            if not config or "database_name" not in config:
                raise ValueError("删除配置需要database_name参数")
            remove_result = database_manager.remove_config(config["database_name"])
            result = {
                "status": "success",
                "action": "remove",
                "data": remove_result
            }
        elif action == "reload":
            reload_result = database_manager.reload_configs()
            result = {
                "status": "success",
                "action": "reload",
                "data": reload_result
            }
        elif action == "list_temp":
            temp_configs = database_manager.list_temp_configs()
            result = {
                "status": "success",
                "action": "list_temp",
                "data": temp_configs,
                "count": len(temp_configs)
            }
        elif action == "cleanup_temp":
            cleanup_result = database_manager.cleanup_temp_configs()
            result = {
                "status": "success",
                "action": "cleanup_temp",
                "data": cleanup_result
            }
        else:
            raise ValueError(f"不支持的操作类型: {action}")
        
        result["timestamp"] = datetime.now().isoformat()
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"数据库配置管理失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"数据库配置管理失败: {str(e)}",
            "action": action,
            "timestamp": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)

# ================================
# 模块初始化函数
# ================================

def init_database_module():
    """初始化数据库模块"""
    try:
        init_database()
        logger.info("数据库模块初始化完成")
        return True
    except Exception as e:
        logger.error(f"数据库模块初始化失败: {e}")
        return False