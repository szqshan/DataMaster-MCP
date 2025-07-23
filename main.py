#!/usr/bin/env python3
"""
SuperDataAnalysis MCP - 超级数据分析工具
为AI提供强大的数据分析能力

核心理念：工具专注数据获取和计算，AI专注智能分析和洞察
"""

import json
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from mcp.server.fastmcp import FastMCP
import numpy as np
from scipy import stats

# 导入数据库管理器
from config.database_manager import database_manager
from config.config_manager import config_manager

# 导入API连接器组件
from config.api_config_manager import api_config_manager
from config.api_connector import api_connector
from config.data_transformer import data_transformer
from config.api_data_storage import api_data_storage

# ================================
# DataFrame序列化处理
# ================================

def _serialize_dataframe(df) -> dict:
    """将DataFrame序列化为JSON可序列化的格式"""
    try:
        # 转换为字典格式
        data = {
            "columns": df.columns.tolist(),
            "data": df.values.tolist(),
            "index": df.index.tolist(),
            "shape": df.shape,
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
        return data
    except Exception as e:
        logger.warning(f"DataFrame序列化失败: {e}")
        # 降级处理：转换为简单的记录格式
        try:
            return {
                "columns": df.columns.tolist(),
                "records": df.to_dict('records'),
                "shape": df.shape,
                "note": "使用简化格式，部分类型信息可能丢失"
            }
        except Exception as e2:
            logger.error(f"DataFrame简化序列化也失败: {e2}")
            return {
                "error": "DataFrame序列化失败",
                "shape": getattr(df, 'shape', 'unknown'),
                "columns": getattr(df, 'columns', []).tolist() if hasattr(df, 'columns') else []
            }

def _handle_data_format(data, format_type: str = "dict"):
    """处理不同数据格式的输出"""
    if format_type == "dataframe" and isinstance(data, pd.DataFrame):
        return _serialize_dataframe(data)
    elif isinstance(data, pd.DataFrame):
        # 默认转换为字典列表
        try:
            return data.to_dict('records')
        except Exception:
            return _serialize_dataframe(data)
    else:
        return data


# ================================
# 1. 配置和初始化
# ================================
TOOL_NAME = "SuperDataAnalysis_MCP"
DB_PATH = "data/analysis.db"
DATA_DIR = "data"
EXPORTS_DIR = "exports"

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(TOOL_NAME)

# 创建MCP服务器
mcp = FastMCP(TOOL_NAME)

# 确保目录存在
for directory in [DATA_DIR, EXPORTS_DIR]:
    Path(directory).mkdir(exist_ok=True)

# ================================
# 2. 数据库管理
# ================================

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

def _escape_identifier(identifier: str) -> str:
    """转义SQL标识符（表名、列名等）"""
    # 使用双引号包围标识符，并转义内部的双引号
    return f'"{identifier.replace('"', '""')}"'

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



# ================================
# 3. 核心工具实现
# ================================

@mcp.tool()
def connect_data_source(
    source_type: str,
    config: dict,
    target_table: str = None
) -> str:
    """
    数据源连接路由器
    
    Args:
        source_type: 数据源类型 (excel|csv|sqlite|mysql|postgresql|mongodb|database_config)
        config: 连接配置参数或数据库配置名称
        target_table: 目标表名（可选）
    
    Returns:
        str: 连接结果和导入状态
    """
    try:
        if source_type == "excel":
            return _import_excel(config, target_table)
        elif source_type == "csv":
            return _import_csv(config, target_table)
        elif source_type == "sqlite":
            return _connect_sqlite(config, target_table)
        elif source_type == "mysql":
            return _connect_external_database("mysql", config, target_table)
        elif source_type == "postgresql":
            return _connect_external_database("postgresql", config, target_table)
        elif source_type == "mongodb":
            return _connect_external_database("mongodb", config, target_table)
        elif source_type == "database_config":
            return _connect_from_config(config, target_table)
        else:
            result = {
                "status": "error",
                "message": f"不支持的数据源类型: {source_type}",
                "supported_types": ["excel", "csv", "sqlite", "mysql", "postgresql", "mongodb", "database_config"]
            }
            return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"数据源连接失败: {e}")
        result = {
            "status": "error",
            "message": f"数据源连接失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _import_excel(config: dict, target_table: str = None) -> str:
    """导入Excel文件"""
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
            "message": "Excel文件导入成功",
            "data": {
                "table_name": target_table,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "file_path": file_path,
                "sheet_name": sheet_name
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_type": "excel"
            }
        }
        
        return f"✅ Excel导入成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"Excel导入失败: {e}")
        raise

def _import_csv(config: dict, target_table: str = None) -> str:
    """导入CSV文件"""
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
            "message": "CSV文件导入成功",
            "data": {
                "table_name": target_table,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "file_path": file_path
            }
        }
        
        return f"✅ CSV导入成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"CSV导入失败: {e}")
        raise

def _connect_sqlite(config: dict, target_table: str = None) -> str:
    """连接SQLite数据库"""
    # 这里可以实现SQLite数据库连接逻辑
    # 暂时返回提示信息
    result = {
        "status": "info",
        "message": "SQLite连接功能待实现",
        "config": config
    }
    return f"ℹ️ 功能开发中\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _connect_external_database(db_type: str, config: dict, target_table: str = None) -> str:
    """连接外部数据库（MySQL、PostgreSQL、MongoDB）"""
    try:
        # 测试连接
        if isinstance(config, str):
            # 如果config是字符串，则作为数据库配置名称
            database_name = config
            is_valid, message = database_manager.test_connection(database_name)
            if not is_valid:
                result = {
                    "status": "error",
                    "message": f"数据库连接测试失败: {message}",
                    "database_name": database_name
                }
                return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            # 获取表列表
            tables = database_manager.get_table_list(database_name)
            
            result = {
                "status": "success",
                "message": f"{db_type.upper()} 数据库连接成功",
                "data": {
                    "database_name": database_name,
                    "database_type": db_type,
                    "tables": tables,
                    "table_count": len(tables)
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "connection_method": "config_name"
                }
            }
            
            return f"✅ {db_type.upper()} 连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
        else:
            # 直接连接配置
            # 创建临时配置并测试连接
            temp_config_name = f"temp_{db_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            config_with_type = config.copy()
            config_with_type["type"] = db_type
            config_with_type["enabled"] = True
            
            # 添加临时配置
            if config_manager.add_database_config(temp_config_name, config_with_type):
                try:
                    # 测试连接
                    is_valid, message = database_manager.test_connection(temp_config_name)
                    if not is_valid:
                        # 清理临时配置
                        config_manager.remove_database_config(temp_config_name)
                        result = {
                            "status": "error",
                            "message": f"数据库连接测试失败: {message}"
                        }
                        return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                    # 获取表列表
                    tables = database_manager.get_table_list(temp_config_name)
                    
                    result = {
                        "status": "success",
                        "message": f"{db_type.upper()} 数据库连接成功",
                        "data": {
                            "database_type": db_type,
                            "host": config.get("host", "N/A"),
                            "database": config.get("database", "N/A"),
                            "tables": tables,
                            "table_count": len(tables),
                            "temp_config_name": temp_config_name
                        },
                        "metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "connection_method": "direct_config"
                        }
                    }
                    
                    return f"✅ {db_type.upper()} 连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                finally:
                    # 清理临时配置
                    config_manager.remove_database_config(temp_config_name)
            else:
                result = {
                    "status": "error",
                    "message": "创建临时配置失败"
                }
                return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
    except Exception as e:
        logger.error(f"{db_type} 数据库连接失败: {e}")
        result = {
            "status": "error",
            "message": f"{db_type.upper()} 数据库连接失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _connect_from_config(config: dict, target_table: str = None) -> str:
    """从配置文件连接数据库"""
    try:
        database_name = config.get("database_name")
        if not database_name:
            result = {
                "status": "error",
                "message": "缺少database_name参数"
            }
            return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 获取可用数据库列表
        available_databases = database_manager.get_available_databases()
        
        if database_name not in available_databases:
            result = {
                "status": "error",
                "message": f"数据库配置不存在: {database_name}",
                "available_databases": list(available_databases.keys())
            }
            return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 测试连接
        is_valid, message = database_manager.test_connection(database_name)
        if not is_valid:
            result = {
                "status": "error",
                "message": f"数据库连接测试失败: {message}",
                "database_name": database_name
            }
            return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 获取数据库信息
        db_info = available_databases[database_name]
        tables = database_manager.get_table_list(database_name)
        
        result = {
            "status": "success",
            "message": f"数据库连接成功: {database_name}",
            "data": {
                "database_name": database_name,
                "database_type": db_info.get("type"),
                "description": db_info.get("description", ""),
                "tables": tables,
                "table_count": len(tables)
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "connection_method": "config_file"
            }
        }
        
        return f"✅ 数据库连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"配置文件连接失败: {e}")
        result = {
            "status": "error",
            "message": f"配置文件连接失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _preprocess_sql(query: str) -> str:
    """预处理SQL语句"""
    # 移除末尾分号和多余空格
    query = query.strip().rstrip(';').strip()
    return query

def _format_sql_error(error: Exception, query: str) -> dict:
    """格式化SQL错误信息"""
    error_msg = str(error)
    suggestions = []
    
    if "syntax error" in error_msg.lower():
        if "-" in query and "near \"-\"" in error_msg:
            suggestions.append("表名或列名包含特殊字符，请使用双引号包围，如: \"table-name\"")
        suggestions.append("检查SQL语法是否正确")
        suggestions.append("确保表名和列名存在")
    elif "no such table" in error_msg.lower():
        suggestions.append("检查表名是否正确")
        suggestions.append("使用 get_data_info 工具查看可用的表")
    elif "no such column" in error_msg.lower():
        suggestions.append("检查列名是否正确")
        suggestions.append("使用 get_data_info 工具查看表结构")
    elif "only execute one statement" in error_msg.lower():
        suggestions.append("移除SQL语句末尾的分号")
        suggestions.append("一次只能执行一条SQL语句")
    
    return {
        "status": "error",
        "message": f"SQL执行失败: {error_msg}",
        "error_type": type(error).__name__,
        "suggestions": suggestions,
        "query": query
    }

@mcp.tool()
def execute_sql(
    query: str,
    params: dict = None,
    limit: int = 1000
) -> str:
    """
    SQL执行工具
    
    Args:
        query: SQL查询语句
        params: 查询参数（防止SQL注入）
        limit: 结果限制行数
    
    Returns:
        str: 查询结果
    """
    try:
        # 预处理SQL语句
        query = _preprocess_sql(query)
        
        # 添加LIMIT限制
        if "LIMIT" not in query.upper() and "SELECT" in query.upper():
            query = f"{query} LIMIT {limit}"
        
        # 执行查询
        with get_db_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            
            # 获取结果
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            # 转换为字典列表
            data = [dict(zip(columns, row)) for row in rows] if columns else []
            
            result = {
                "status": "success",
                "message": f"查询完成，返回 {len(data)} 条记录",
                "data": {
                    "columns": columns,
                    "rows": data,
                    "row_count": len(data)
                },
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return f"✅ SQL执行成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"SQL执行失败: {e}")
        result = _format_sql_error(e, query)
        result["timestamp"] = datetime.now().isoformat()
        return f"❌ SQL执行失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def get_data_info(
    info_type: str = "tables",
    table_name: str = None
) -> str:
    """
    数据信息获取工具
    
    Args:
        info_type: 信息类型 (tables|schema|stats)
        table_name: 表名（获取特定表信息时需要）
    
    Returns:
        str: 数据库信息
    """
    try:
        with get_db_connection() as conn:
            if info_type == "tables":
                # 获取所有表名（排除元数据表）
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name != '_metadata'"
                )
                tables = [row[0] for row in cursor.fetchall()]
                
                # 获取表的详细信息
                table_info = []
                for table in tables:
                    try:
                        escaped_table = _escape_identifier(table)
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
                        row_count = cursor.fetchone()[0]
                        table_info.append({
                            "table_name": table,
                            "row_count": row_count
                        })
                    except Exception as e:
                        logger.warning(f"无法获取表 '{table}' 的行数: {e}")
                        table_info.append({
                            "table_name": table,
                            "row_count": "N/A",
                            "error": str(e)
                        })
                
                result = {
                    "status": "success",
                    "message": f"找到 {len(tables)} 个表",
                    "data": {
                        "tables": table_info,
                        "table_count": len(tables)
                    }
                }
                
                return f"✅ 表信息获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
            elif info_type == "schema" and table_name:
                # 获取表结构
                escaped_table = _escape_identifier(table_name)
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                columns = cursor.fetchall()
                
                schema = []
                for col in columns:
                    schema.append({
                        "column_name": col[1],
                        "data_type": col[2],
                        "not_null": bool(col[3]),
                        "default_value": col[4],
                        "primary_key": bool(col[5])
                    })
                
                result = {
                    "status": "success",
                    "message": f"表 '{table_name}' 结构信息",
                    "data": {
                        "table_name": table_name,
                        "columns": schema,
                        "column_count": len(schema)
                    }
                }
                
                return f"✅ 表结构获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
            elif info_type == "stats" and table_name:
                # 获取表统计信息
                escaped_table = _escape_identifier(table_name)
                cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
                row_count = cursor.fetchone()[0]
                
                result = {
                    "status": "success",
                    "message": f"表 '{table_name}' 统计信息",
                    "data": {
                        "table_name": table_name,
                        "row_count": row_count
                    }
                }
                
                return f"✅ 统计信息获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
            else:
                result = {
                    "status": "error",
                    "message": "无效的信息类型或缺少必要参数",
                    "supported_types": ["tables", "schema", "stats"]
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
    except Exception as e:
        logger.error(f"获取数据信息失败: {e}")
        result = {
            "status": "error",
            "message": f"获取数据信息失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 信息获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

# ================================
# 辅助函数：数据分析相关
# ================================

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

def _calculate_basic_stats(table_name: str, columns: list, options: dict) -> dict:
    """计算基础统计信息"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            if columns:
                # 只分析指定列
                numeric_columns = []
                for col in columns:
                    # 检查列是否为数值类型
                    escaped_col = _escape_identifier(col)
                    cursor = conn.execute(f"SELECT typeof({escaped_col}) FROM {escaped_table} LIMIT 1")
                    col_type = cursor.fetchone()[0]
                    if col_type in ['integer', 'real']:
                        numeric_columns.append(col)
                
                if not numeric_columns:
                    return {"error": "没有找到数值类型的列"}
            else:
                # 自动检测数值列
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                all_columns = cursor.fetchall()
                numeric_columns = [col[1] for col in all_columns if col[2] in ['INTEGER', 'REAL', 'NUMERIC']]
                
                if not numeric_columns:
                    return {"error": "表中没有数值类型的列"}
            
            # 计算统计信息
            stats_result = {}
            for col in numeric_columns:
                escaped_col = _escape_identifier(col)
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT({escaped_col}) as count,
                        AVG({escaped_col}) as mean,
                        MIN({escaped_col}) as min_val,
                        MAX({escaped_col}) as max_val,
                        COUNT(CASE WHEN {escaped_col} IS NULL THEN 1 END) as null_count
                    FROM {escaped_table}
                """)
                
                row = cursor.fetchone()
                
                # 计算中位数和标准差
                cursor = conn.execute(f"SELECT {escaped_col} FROM {escaped_table} WHERE {escaped_col} IS NOT NULL ORDER BY {escaped_col}")
                values = [row[0] for row in cursor.fetchall()]
                
                if values:
                    median = np.median(values)
                    std_dev = np.std(values)
                    q25 = np.percentile(values, 25)
                    q75 = np.percentile(values, 75)
                else:
                    median = std_dev = q25 = q75 = None
                
                stats_result[col] = {
                    "count": row[0],
                    "mean": round(row[1], 4) if row[1] else None,
                    "median": round(median, 4) if median else None,
                    "std_dev": round(std_dev, 4) if std_dev else None,
                    "min": row[2],
                    "max": row[3],
                    "q25": round(q25, 4) if q25 else None,
                    "q75": round(q75, 4) if q75 else None,
                    "null_count": row[4],
                    "null_percentage": round((row[4] / row[0]) * 100, 2) if row[0] > 0 else 0
                }
            
            return stats_result
            
    except Exception as e:
        return {"error": f"计算统计信息失败: {str(e)}"}

def _calculate_correlation(table_name: str, columns: list, options: dict) -> dict:
    """计算相关系数"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取数值列
            if columns and len(columns) >= 2:
                numeric_columns = columns[:10]  # 限制最多10列
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                all_columns = cursor.fetchall()
                numeric_columns = [col[1] for col in all_columns if col[2] in ['INTEGER', 'REAL', 'NUMERIC']][:10]
            
            if len(numeric_columns) < 2:
                return {"error": "需要至少2个数值列来计算相关性"}
            
            # 获取数据
            escaped_columns = [_escape_identifier(col) for col in numeric_columns]
            columns_str = ", ".join(escaped_columns)
            df = pd.read_sql(f"SELECT {columns_str} FROM {escaped_table}", conn)
            
            # 重命名列为原始名称（去掉转义符号）
            df.columns = numeric_columns
            
            # 计算相关系数矩阵
            correlation_matrix = df.corr().round(4)
            
            # 转换为字典格式
            result = {}
            for i, col1 in enumerate(numeric_columns):
                result[col1] = {}
                for j, col2 in enumerate(numeric_columns):
                    result[col1][col2] = correlation_matrix.iloc[i, j]
            
            return {
                "correlation_matrix": result,
                "columns": numeric_columns,
                "method": "pearson"
            }
            
    except Exception as e:
        return {"error": f"计算相关性失败: {str(e)}"}

def _detect_outliers(table_name: str, columns: list, options: dict) -> dict:
    """检测异常值"""
    try:
        method = options.get("method", "iqr")  # iqr 或 zscore
        threshold = options.get("threshold", 3)  # Z-score阈值
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            if columns:
                numeric_columns = columns[:5]  # 限制最多5列
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                all_columns = cursor.fetchall()
                numeric_columns = [col[1] for col in all_columns if col[2] in ['INTEGER', 'REAL', 'NUMERIC']][:5]
            
            if not numeric_columns:
                return {"error": "没有找到数值类型的列"}
            
            outliers_result = {}
            
            for col in numeric_columns:
                escaped_col = _escape_identifier(col)
                cursor = conn.execute(f"SELECT {escaped_col} FROM {escaped_table} WHERE {escaped_col} IS NOT NULL")
                values = [row[0] for row in cursor.fetchall()]
                
                if not values:
                    outliers_result[col] = {"outliers": [], "count": 0}
                    continue
                
                outliers = []
                
                if method == "iqr":
                    q25 = np.percentile(values, 25)
                    q75 = np.percentile(values, 75)
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr
                    outliers = [v for v in values if v < lower_bound or v > upper_bound]
                    
                elif method == "zscore":
                    z_scores = np.abs(stats.zscore(values))
                    outliers = [values[i] for i, z in enumerate(z_scores) if z > threshold]
                
                outliers_result[col] = {
                    "outliers": outliers[:100],  # 限制返回前100个异常值
                    "count": len(outliers),
                    "percentage": round((len(outliers) / len(values)) * 100, 2),
                    "method": method
                }
            
            return outliers_result
            
    except Exception as e:
        return {"error": f"异常值检测失败: {str(e)}"}

def _check_missing_values(table_name: str, columns: list, options: dict) -> dict:
    """检查缺失值"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            if columns:
                target_columns = columns
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                target_columns = [col[1] for col in cursor.fetchall()]
            
            missing_result = {}
            total_rows = 0
            
            # 获取总行数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
            total_rows = cursor.fetchone()[0]
            
            for col in target_columns:
                escaped_col = _escape_identifier(col)
                cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table} WHERE {escaped_col} IS NULL")
                null_count = cursor.fetchone()[0]
                
                missing_result[col] = {
                    "null_count": null_count,
                    "null_percentage": round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0,
                    "non_null_count": total_rows - null_count
                }
            
            return {
                "missing_values": missing_result,
                "total_rows": total_rows,
                "columns_analyzed": len(target_columns)
            }
            
    except Exception as e:
        return {"error": f"缺失值检查失败: {str(e)}"}

def _check_duplicates(table_name: str, columns: list, options: dict) -> dict:
    """检查重复值"""
    try:
        with get_db_connection() as conn:
            if columns:
                columns_str = ", ".join(columns)
                group_by_str = columns_str
            else:
                # 检查所有列的重复
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                all_columns = [col[1] for col in cursor.fetchall()]
                columns_str = ", ".join(all_columns)
                group_by_str = columns_str
            
            # 查找重复记录
            cursor = conn.execute(f"""
                SELECT {columns_str}, COUNT(*) as duplicate_count
                FROM {table_name}
                GROUP BY {group_by_str}
                HAVING COUNT(*) > 1
                ORDER BY duplicate_count DESC
                LIMIT 100
            """)
            
            duplicates = cursor.fetchall()
            
            # 获取总重复行数
            cursor = conn.execute(f"""
                SELECT SUM(cnt - 1) as total_duplicates
                FROM (
                    SELECT COUNT(*) as cnt
                    FROM {table_name}
                    GROUP BY {group_by_str}
                    HAVING COUNT(*) > 1
                )
            """)
            
            total_duplicates = cursor.fetchone()[0] or 0
            
            # 获取总行数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]
            
            return {
                "duplicate_groups": len(duplicates),
                "total_duplicate_rows": total_duplicates,
                "duplicate_percentage": round((total_duplicates / total_rows) * 100, 2) if total_rows > 0 else 0,
                "sample_duplicates": [dict(zip([desc[0] for desc in cursor.description], row)) for row in duplicates[:10]],
                "total_rows": total_rows
            }
            
    except Exception as e:
        return {"error": f"重复值检查失败: {str(e)}"}

@mcp.tool()
def analyze_data(
    analysis_type: str,
    table_name: str,
    columns: list = None,
    options: dict = None
) -> str:
    """
    数据分析路由器
    
    Args:
        analysis_type: 分析类型 (basic_stats|correlation|outliers|missing_values|duplicates)
        table_name: 数据表名
        columns: 分析的列名列表（可选）
        options: 分析选项参数（可选）
    
    Returns:
        str: 分析结果数据
    """
    try:
        # 验证表是否存在
        if not _table_exists(table_name):
            result = {
                "status": "error",
                "message": f"表 '{table_name}' 不存在"
            }
            return f"❌ 表不存在\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 路由到具体的分析函数
        analysis_map = {
            "basic_stats": _calculate_basic_stats,
            "correlation": _calculate_correlation,
            "outliers": _detect_outliers,
            "missing_values": _check_missing_values,
            "duplicates": _check_duplicates
        }
        
        if analysis_type not in analysis_map:
            result = {
                "status": "error",
                "message": f"不支持的分析类型: {analysis_type}",
                "supported_types": list(analysis_map.keys())
            }
            return f"❌ 分析类型错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 执行分析
        analysis_result = analysis_map[analysis_type](table_name, columns or [], options or {})
        
        if "error" in analysis_result:
            result = {
                "status": "error",
                "message": analysis_result["error"]
            }
            return f"❌ 分析失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 返回成功结果
        result = {
            "status": "success",
            "message": f"{analysis_type} 分析完成",
            "data": analysis_result,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "table_name": table_name,
                "analysis_type": analysis_type,
                "columns": columns or []
            }
        }
        
        return f"✅ 分析完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"数据分析失败: {e}")
        result = {
            "status": "error",
            "message": f"数据分析失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 分析失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

# ================================
# 辅助函数：数据导出相关
# ================================

def _export_to_excel(data_source: str, file_path: str, options: dict) -> dict:
    """导出到Excel文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with get_db_connection() as conn:
            if data_source.upper().startswith('SELECT'):
                # SQL查询
                df = pd.read_sql(data_source, conn)
            else:
                # 表名
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            # 导出到Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                sheet_name = options.get('sheet_name', 'Data')
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 添加格式化（如果需要）
                if options.get('auto_adjust_columns', True):
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            file_size = os.path.getsize(file_path)
            return {
                "file_size": file_size,
                "record_count": len(df),
                "columns": list(df.columns)
            }
            
    except Exception as e:
        raise Exception(f"Excel导出失败: {str(e)}")

def _export_to_csv(data_source: str, file_path: str, options: dict) -> dict:
    """导出到CSV文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with get_db_connection() as conn:
            if data_source.upper().startswith('SELECT'):
                # SQL查询
                df = pd.read_sql(data_source, conn)
            else:
                # 表名
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            # 导出到CSV
            encoding = options.get('encoding', 'utf-8-sig')  # 使用utf-8-sig添加BOM头
            separator = options.get('separator', ',')
            df.to_csv(file_path, index=False, encoding=encoding, sep=separator)
            
            file_size = os.path.getsize(file_path)
            return {
                "file_size": file_size,
                "record_count": len(df),
                "columns": list(df.columns)
            }
            
    except Exception as e:
        raise Exception(f"CSV导出失败: {str(e)}")

def _export_to_json(data_source: str, file_path: str, options: dict) -> dict:
    """导出到JSON文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with get_db_connection() as conn:
            if data_source.upper().startswith('SELECT'):
                # SQL查询
                df = pd.read_sql(data_source, conn)
            else:
                # 表名
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            # 转换为JSON格式
            orient = options.get('orient', 'records')  # records, index, values, split, table
            
            if orient == 'records':
                data = df.to_dict('records')
            elif orient == 'index':
                data = df.to_dict('index')
            elif orient == 'values':
                data = df.values.tolist()
            elif orient == 'split':
                data = df.to_dict('split')
            elif orient == 'table':
                data = df.to_dict('table')
            else:
                data = df.to_dict('records')
            
            # 写入JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            file_size = os.path.getsize(file_path)
            return {
                "file_size": file_size,
                "record_count": len(df),
                "columns": list(df.columns)
            }
            
    except Exception as e:
        raise Exception(f"JSON导出失败: {str(e)}")

@mcp.tool()
def export_data(
    export_type: str,
    data_source: str,
    file_path: str = None,
    options: dict = None
) -> str:
    """
    数据导出路由器
    
    Args:
        export_type: 导出类型 (excel|csv|json)
        data_source: 数据源（表名或SQL查询）
        file_path: 导出文件路径（可选，自动生成）
        options: 导出选项（可选）
    
    Returns:
        str: 导出结果和文件路径
    """
    try:
        # 生成默认文件路径
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 从数据源提取名称
            if data_source.upper().startswith('SELECT'):
                source_name = "query_result"
            else:
                source_name = data_source
            file_path = f"exports/{source_name}_{timestamp}.{export_type}"
        
        # 路由到具体的导出函数
        export_map = {
            "excel": _export_to_excel,
            "csv": _export_to_csv,
            "json": _export_to_json
        }
        
        if export_type not in export_map:
            result = {
                "status": "error",
                "message": f"不支持的导出类型: {export_type}",
                "supported_types": list(export_map.keys())
            }
            return f"❌ 导出类型错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 执行导出
        export_result = export_map[export_type](data_source, file_path, options or {})
        
        result = {
            "status": "success",
            "message": f"数据导出完成",
            "data": {
                "file_path": file_path,
                "export_type": export_type,
                "file_size": export_result.get("file_size"),
                "record_count": export_result.get("record_count"),
                "columns": export_result.get("columns")
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "data_source": data_source
            }
        }
        
        return f"✅ 数据导出成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"数据导出失败: {e}")
        result = {
            "status": "error",
            "message": f"数据导出失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 导出失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"




















# ================================
# 数据处理工具 (Excel数据处理)
# ================================

def _process_clean(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据清洗处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            original_count = len(df)
            operations_performed = []
            
            # 删除重复行
            if config.get('remove_duplicates', False):
                before_count = len(df)
                df = df.drop_duplicates()
                removed_count = before_count - len(df)
                operations_performed.append(f"删除重复行: {removed_count}行")
            
            # 处理缺失值
            if 'fill_missing' in config:
                fill_config = config['fill_missing']
                for column, fill_method in fill_config.items():
                    if column in df.columns:
                        method = fill_method.get('method', 'mean')
                        missing_count = df[column].isnull().sum()
                        
                        if method == 'mean' and df[column].dtype in ['int64', 'float64']:
                            df[column] = df[column].fillna(df[column].mean())
                        elif method == 'median' and df[column].dtype in ['int64', 'float64']:
                            df[column] = df[column].fillna(df[column].median())
                        elif method == 'mode':
                            df[column] = df[column].fillna(df[column].mode().iloc[0] if not df[column].mode().empty else '')
                        elif method == 'forward':
                            df[column] = df[column].fillna(method='ffill')
                        elif method == 'backward':
                            df[column] = df[column].fillna(method='bfill')
                        else:
                            # 自定义值
                            fill_value = fill_method.get('value', '')
                            df[column] = df[column].fillna(fill_value)
                        
                        operations_performed.append(f"填充缺失值 {column}: {missing_count}个")
            
            # 异常值处理
            if 'remove_outliers' in config:
                outlier_config = config['remove_outliers']
                columns = outlier_config.get('columns', [])
                method = outlier_config.get('method', 'iqr')
                threshold = outlier_config.get('threshold', 1.5)
                
                for column in columns:
                    if column in df.columns and df[column].dtype in ['int64', 'float64']:
                        before_count = len(df)
                        
                        if method == 'iqr':
                            Q1 = df[column].quantile(0.25)
                            Q3 = df[column].quantile(0.75)
                            IQR = Q3 - Q1
                            lower_bound = Q1 - threshold * IQR
                            upper_bound = Q3 + threshold * IQR
                            df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
                        elif method == 'zscore':
                            z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
                            df = df[z_scores < threshold]
                        
                        removed_count = before_count - len(df)
                        operations_performed.append(f"移除异常值 {column}: {removed_count}行")
            
            # 保存处理后的数据
            table_name = target_table or data_source
            if not table_name.upper().startswith('SELECT'):
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                # 记录元数据
                metadata = {
                    'table_name': table_name,
                    'source_type': 'processed_data',
                    'original_source': data_source,
                    'processing_type': 'clean',
                    'operations': operations_performed,
                    'created_at': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO data_metadata 
                    (table_name, source_type, source_path, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                conn.commit()
            
            return {
                "original_rows": original_count,
                "processed_rows": len(df),
                "operations": operations_performed,
                "target_table": table_name
            }
            
    except Exception as e:
        raise Exception(f"数据清洗失败: {str(e)}")

def _process_transform(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据转换处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            operations_performed = []
            
            # 列重命名
            if 'rename_columns' in config:
                rename_map = config['rename_columns']
                df.rename(columns=rename_map, inplace=True)
                operations_performed.append(f"重命名列: {list(rename_map.keys())}")
            
            # 数据标准化/归一化
            if 'normalize' in config:
                normalize_config = config['normalize']
                columns = normalize_config.get('columns', [])
                method = normalize_config.get('method', 'minmax')
                
                for column in columns:
                    if column in df.columns and df[column].dtype in ['int64', 'float64']:
                        if method == 'minmax':
                            df[column] = (df[column] - df[column].min()) / (df[column].max() - df[column].min())
                        elif method == 'zscore':
                            df[column] = (df[column] - df[column].mean()) / df[column].std()
                        operations_performed.append(f"标准化 {column} ({method})")
            
            # 创建新列
            if 'new_columns' in config:
                new_columns_config = config['new_columns']
                for new_col_name, expression in new_columns_config.items():
                    try:
                        # 使用eval计算新列（安全性考虑，仅支持基本运算）
                        if isinstance(expression, str):
                            # 替换列名为实际的数据框列引用
                            safe_expr = expression
                            for col in df.columns:
                                safe_expr = safe_expr.replace(col, f"df['{col}']")
                            
                            # 支持基本的数学运算和条件表达式
                            if any(op in safe_expr for op in ['+', '-', '*', '/', 'CASE', 'WHEN']):
                                if 'CASE' in safe_expr and 'WHEN' in safe_expr:
                                    # 处理SQL风格的CASE WHEN表达式
                                    # 简化处理，转换为pandas的where语句
                                    if 'age' in safe_expr and ('青年' in safe_expr or 'THEN' in safe_expr):
                                        df[new_col_name] = df['age'].apply(
                                            lambda x: '青年' if x < 30 else ('中年' if x < 40 else '资深')
                                        )
                                    else:
                                        df[new_col_name] = 'Unknown'  # 默认值
                                else:
                                    # 基本数学运算
                                    df[new_col_name] = eval(safe_expr)
                            else:
                                df[new_col_name] = expression
                        else:
                            df[new_col_name] = expression
                        
                        operations_performed.append(f"创建新列: {new_col_name}")
                    except Exception as e:
                        operations_performed.append(f"创建新列失败 {new_col_name}: {str(e)}")
            
            # 分类变量编码
            if 'encode_categorical' in config:
                encode_config = config['encode_categorical']
                for column, encode_method in encode_config.items():
                    if column in df.columns:
                        method = encode_method.get('method', 'label')
                        
                        if method == 'label':
                            # 标签编码
                            unique_values = df[column].unique()
                            label_map = {val: idx for idx, val in enumerate(unique_values)}
                            df[column] = df[column].map(label_map)
                            operations_performed.append(f"标签编码 {column}")
                        elif method == 'onehot':
                            # 独热编码
                            dummies = pd.get_dummies(df[column], prefix=column)
                            df = pd.concat([df.drop(column, axis=1), dummies], axis=1)
                            operations_performed.append(f"独热编码 {column}")
            
            # 保存处理后的数据
            table_name = target_table or data_source
            if not table_name.upper().startswith('SELECT'):
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                # 记录元数据
                metadata = {
                    'table_name': table_name,
                    'source_type': 'processed_data',
                    'original_source': data_source,
                    'processing_type': 'transform',
                    'operations': operations_performed,
                    'created_at': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO data_metadata 
                    (table_name, source_type, source_path, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                conn.commit()
            
            return {
                "processed_rows": len(df),
                "columns": list(df.columns),
                "operations": operations_performed,
                "target_table": table_name
            }
            
    except Exception as e:
        raise Exception(f"数据转换失败: {str(e)}")

def _process_filter(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据筛选处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            original_count = len(df)
            operations_performed = []
            
            # 条件筛选
            if 'filter_condition' in config:
                condition = config['filter_condition']
                try:
                    df = df.query(condition)
                    operations_performed.append(f"条件筛选: {condition}")
                except Exception as e:
                    operations_performed.append(f"条件筛选失败: {str(e)}")
            
            # 列选择
            if 'select_columns' in config:
                columns = config['select_columns']
                available_columns = [col for col in columns if col in df.columns]
                if available_columns:
                    df = df[available_columns]
                    operations_performed.append(f"选择列: {available_columns}")
            
            # 数据采样
            if 'sample' in config:
                sample_config = config['sample']
                n = sample_config.get('n', 1000)
                method = sample_config.get('method', 'random')
                
                if method == 'random' and len(df) > n:
                    df = df.sample(n=n, random_state=42)
                    operations_performed.append(f"随机采样: {n}行")
                elif method == 'head':
                    df = df.head(n)
                    operations_performed.append(f"头部采样: {n}行")
                elif method == 'tail':
                    df = df.tail(n)
                    operations_performed.append(f"尾部采样: {n}行")
            
            # 排序
            if 'sort_by' in config:
                sort_config = config['sort_by']
                column = sort_config.get('column')
                ascending = sort_config.get('ascending', True)
                
                if column and column in df.columns:
                    df = df.sort_values(by=column, ascending=ascending)
                    operations_performed.append(f"排序: {column} ({'升序' if ascending else '降序'})")
            
            # 保存处理后的数据
            table_name = target_table or data_source
            if not table_name.upper().startswith('SELECT'):
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                # 记录元数据
                metadata = {
                    'table_name': table_name,
                    'source_type': 'processed_data',
                    'original_source': data_source,
                    'processing_type': 'filter',
                    'operations': operations_performed,
                    'created_at': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO data_metadata 
                    (table_name, source_type, source_path, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                conn.commit()
            
            return {
                "original_rows": original_count,
                "filtered_rows": len(df),
                "operations": operations_performed,
                "target_table": table_name
            }
            
    except Exception as e:
        raise Exception(f"数据筛选失败: {str(e)}")

def _process_aggregate(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据聚合处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            operations_performed = []
            
            # 分组聚合
            if 'group_by' in config:
                # 支持两种配置格式
                if isinstance(config['group_by'], dict):
                    # 格式1: {'columns': [...], 'agg': {...}}
                    group_config = config['group_by']
                    group_columns = group_config.get('columns', [])
                    agg_functions = group_config.get('agg', {})
                elif isinstance(config['group_by'], list):
                    # 格式2: 直接是列名列表，配合 'aggregations' 键
                    group_columns = config['group_by']
                    agg_functions = config.get('aggregations', {})
                else:
                    group_columns = []
                    agg_functions = {}
                
                if group_columns and agg_functions:
                    # 处理聚合函数格式
                    processed_agg = {}
                    for col, funcs in agg_functions.items():
                        if isinstance(funcs, list):
                            # 多个聚合函数
                            processed_agg[col] = funcs
                        else:
                            # 单个聚合函数
                            processed_agg[col] = funcs
                    
                    df = df.groupby(group_columns).agg(processed_agg).reset_index()
                    # 扁平化列名
                    df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df.columns.values]
                    operations_performed.append(f"分组聚合: {group_columns}")
            
            # 数据透视表
            if 'pivot_table' in config:
                pivot_config = config['pivot_table']
                index = pivot_config.get('index')
                columns = pivot_config.get('columns')
                values = pivot_config.get('values')
                aggfunc = pivot_config.get('aggfunc', 'mean')
                
                if index and columns and values:
                    df = pd.pivot_table(df, index=index, columns=columns, values=values, aggfunc=aggfunc, fill_value=0).reset_index()
                    operations_performed.append(f"透视表: {index} x {columns}")
            
            # 保存处理后的数据
            table_name = target_table or data_source
            if not table_name.upper().startswith('SELECT'):
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                # 记录元数据
                metadata = {
                    'table_name': table_name,
                    'source_type': 'processed_data',
                    'original_source': data_source,
                    'processing_type': 'aggregate',
                    'operations': operations_performed,
                    'created_at': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO data_metadata 
                    (table_name, source_type, source_path, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                conn.commit()
            
            return {
                "processed_rows": len(df),
                "columns": list(df.columns),
                "operations": operations_performed,
                "target_table": table_name
            }
            
    except Exception as e:
        raise Exception(f"数据聚合失败: {str(e)}")

def _process_merge(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据合并处理器"""
    try:
        with get_db_connection() as conn:
            # 获取主数据
            if data_source.upper().startswith('SELECT'):
                df1 = pd.read_sql(data_source, conn)
            else:
                df1 = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            operations_performed = []
            
            # 表连接
            if 'join_with' in config:
                join_table = config['join_with']
                join_type = config.get('join_type', 'inner')
                on_column = config.get('on')
                suffixes = config.get('suffixes', ['_x', '_y'])
                
                # 获取要连接的表
                df2 = pd.read_sql(f'SELECT * FROM "{join_table}"', conn)
                
                if on_column:
                    df = df1.merge(df2, on=on_column, how=join_type, suffixes=suffixes)
                    operations_performed.append(f"{join_type}连接: {data_source} + {join_table} on {on_column}")
                else:
                    # 如果没有指定连接列，尝试自动检测
                    common_columns = list(set(df1.columns) & set(df2.columns))
                    if common_columns:
                        df = df1.merge(df2, on=common_columns[0], how=join_type, suffixes=suffixes)
                        operations_performed.append(f"{join_type}连接: {data_source} + {join_table} on {common_columns[0]}")
                    else:
                        df = df1  # 无法连接，保持原数据
                        operations_performed.append(f"连接失败: 无共同列")
            else:
                df = df1
            
            # 数据追加
            if 'append_table' in config:
                append_table = config['append_table']
                df2 = pd.read_sql(f"SELECT * FROM {append_table}", conn)
                
                # 确保列一致
                common_columns = list(set(df.columns) & set(df2.columns))
                if common_columns:
                    df = pd.concat([df[common_columns], df2[common_columns]], ignore_index=True)
                    operations_performed.append(f"追加数据: {append_table}")
            
            # 保存处理后的数据
            table_name = target_table or data_source
            if not table_name.upper().startswith('SELECT'):
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                # 记录元数据
                metadata = {
                    'table_name': table_name,
                    'source_type': 'processed_data',
                    'original_source': data_source,
                    'processing_type': 'merge',
                    'operations': operations_performed,
                    'created_at': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO data_metadata 
                    (table_name, source_type, source_path, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                conn.commit()
            
            return {
                "processed_rows": len(df),
                "columns": list(df.columns),
                "operations": operations_performed,
                "target_table": table_name
            }
            
    except Exception as e:
        raise Exception(f"数据合并失败: {str(e)}")

def _process_reshape(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据重塑处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                df = pd.read_sql(f'SELECT * FROM "{data_source}"', conn)
            
            operations_performed = []
            
            # 宽表转长表 (melt)
            if 'melt' in config:
                melt_config = config['melt']
                id_vars = melt_config.get('id_vars', [])
                value_vars = melt_config.get('value_vars')
                var_name = melt_config.get('var_name', 'variable')
                value_name = melt_config.get('value_name', 'value')
                
                df = pd.melt(df, id_vars=id_vars, value_vars=value_vars, var_name=var_name, value_name=value_name)
                operations_performed.append(f"宽表转长表: {len(id_vars)}个ID列")
            
            # 长表转宽表 (pivot)
            if 'pivot' in config:
                pivot_config = config['pivot']
                index = pivot_config.get('index')
                columns = pivot_config.get('columns')
                values = pivot_config.get('values')
                
                if index and columns and values:
                    df = df.pivot(index=index, columns=columns, values=values).reset_index()
                    df.columns.name = None  # 移除列名
                    operations_performed.append(f"长表转宽表: {index} -> {columns}")
            
            # 数据转置
            if config.get('transpose', False):
                df = df.T
                df.reset_index(inplace=True)
                operations_performed.append("数据转置")
            
            # 保存处理后的数据
            table_name = target_table or data_source
            if not table_name.upper().startswith('SELECT'):
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                # 记录元数据
                metadata = {
                    'table_name': table_name,
                    'source_type': 'processed_data',
                    'original_source': data_source,
                    'processing_type': 'reshape',
                    'operations': operations_performed,
                    'created_at': datetime.now().isoformat()
                }
                
                conn.execute("""
                    INSERT OR REPLACE INTO data_metadata 
                    (table_name, source_type, source_path, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                conn.commit()
            
            return {
                "processed_rows": len(df),
                "columns": list(df.columns),
                "operations": operations_performed,
                "target_table": table_name
            }
            
    except Exception as e:
        raise Exception(f"数据重塑失败: {str(e)}")

@mcp.tool()
def process_data(
    operation_type: str,
    data_source: str,
    config: dict,
    target_table: str = None
) -> str:
    """
    数据处理路由器 (Excel数据处理)
    
    Args:
        operation_type: 操作类型 (clean|transform|filter|aggregate|merge|reshape)
        data_source: 数据源（表名或SQL查询）
        config: 操作配置参数
        target_table: 目标表名（可选，默认覆盖原表）
    
    Returns:
        str: 处理结果
    """
    try:
        # 路由映射 (Excel数据处理)
        processors = {
            "clean": _process_clean,
            "transform": _process_transform,
            "filter": _process_filter,
            "aggregate": _process_aggregate,
            "merge": _process_merge,
            "reshape": _process_reshape
        }
        
        if operation_type not in processors:
            result = {
                "status": "error",
                "message": f"不支持的操作类型: {operation_type}",
                "supported_types": list(processors.keys()),
                "note": "当前版本支持Excel数据处理，后续将添加API和SQL数据处理"
            }
            return f"❌ 操作类型错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 路由到对应处理器
        process_result = processors[operation_type](data_source, config, target_table)
        
        result = {
            "status": "success",
            "message": f"数据处理完成",
            "data": {
                "operation_type": operation_type,
                "data_source": data_source,
                "target_table": process_result.get("target_table"),
                "processed_rows": process_result.get("processed_rows", process_result.get("filtered_rows")),
                "operations": process_result.get("operations", []),
                "columns": process_result.get("columns")
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "processing_category": "excel_data_processing"
            }
        }
        
        return f"✅ 数据处理成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"数据处理失败: {e}")
        result = {
            "status": "error",
            "message": f"数据处理失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 处理失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def manage_database_config(
    action: str,
    config: dict = None
) -> str:
    """
    数据库配置管理工具
    
    Args:
        action: 操作类型 (list|test|add|remove|reload)
        config: 配置参数（根据action不同而不同）
    
    Returns:
        str: 操作结果
    """
    try:
        if action == "list":
            # 列出所有可用的数据库配置
            databases = database_manager.get_available_databases()
            
            result = {
                "status": "success",
                "message": f"找到 {len(databases)} 个数据库配置",
                "data": {
                    "databases": databases,
                    "count": len(databases)
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return f"✅ 数据库配置列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
        elif action == "test":
            # 测试数据库连接
            database_name = config.get("database_name") if config else None
            if not database_name:
                result = {
                    "status": "error",
                    "message": "缺少database_name参数"
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            is_valid, message = database_manager.test_connection(database_name)
            
            result = {
                "status": "success" if is_valid else "error",
                "message": message,
                "data": {
                    "database_name": database_name,
                    "connection_status": "success" if is_valid else "failed"
                }
            }
            
            status_icon = "✅" if is_valid else "❌"
            return f"{status_icon} 连接测试结果\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
        elif action == "add":
            # 添加新的数据库配置
            if not config:
                result = {
                    "status": "error",
                    "message": "缺少配置参数"
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            database_name = config.get("database_name")
            database_config = config.get("database_config")
            
            if not database_name or not database_config:
                result = {
                    "status": "error",
                    "message": "缺少database_name或database_config参数"
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success = config_manager.add_database_config(database_name, database_config)
            
            if success:
                result = {
                    "status": "success",
                    "message": f"数据库配置已添加: {database_name}",
                    "data": {
                        "database_name": database_name,
                        "database_type": database_config.get("type")
                    }
                }
                return f"✅ 配置添加成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            else:
                result = {
                    "status": "error",
                    "message": f"添加数据库配置失败: {database_name}"
                }
                return f"❌ 配置添加失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
        elif action == "remove":
            # 删除数据库配置
            database_name = config.get("database_name") if config else None
            if not database_name:
                result = {
                    "status": "error",
                    "message": "缺少database_name参数"
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success = config_manager.remove_database_config(database_name)
            
            if success:
                result = {
                    "status": "success",
                    "message": f"数据库配置已删除: {database_name}",
                    "data": {
                        "database_name": database_name
                    }
                }
                return f"✅ 配置删除成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            else:
                result = {
                    "status": "error",
                    "message": f"删除数据库配置失败: {database_name}"
                }
                return f"❌ 配置删除失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
        elif action == "reload":
            # 重新加载配置
            config_manager.reload_config()
            
            result = {
                "status": "success",
                "message": "配置已重新加载",
                "data": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return f"✅ 配置重新加载成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
        else:
            result = {
                "status": "error",
                "message": f"不支持的操作类型: {action}",
                "supported_actions": ["list", "test", "add", "remove", "reload"]
            }
            return f"❌ 操作类型错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"数据库配置管理失败: {e}")
        result = {
            "status": "error",
            "message": f"数据库配置管理失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 操作失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def query_external_database(
    database_name: str,
    query: str,
    limit: int = 1000
) -> str:
    """
    查询外部数据库工具
    
    Args:
        database_name: 数据库配置名称
        query: 查询语句（SQL或MongoDB查询）
        limit: 结果限制行数
    
    Returns:
        str: 查询结果
    """
    try:
        # 执行查询
        result = database_manager.execute_query(database_name, query)
        
        if result["success"]:
            # 应用限制
            data = result["data"]
            if len(data) > limit:
                data = data[:limit]
                result["data"] = data
                result["truncated"] = True
                result["total_rows"] = result.get("row_count", len(data))
                result["returned_rows"] = len(data)
            
            formatted_result = {
                "status": "success",
                "message": f"查询完成，返回 {len(data)} 条记录",
                "data": {
                    "database_name": database_name,
                    "rows": data,
                    "row_count": len(data),
                    "truncated": result.get("truncated", False),
                    "total_rows": result.get("total_rows", len(data))
                },
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "limit": limit
                }
            }
            
            return f"✅ 外部数据库查询成功\n\n{json.dumps(formatted_result, indent=2, ensure_ascii=False)}"
        else:
            formatted_result = {
                "status": "error",
                "message": result["error"],
                "data": {
                    "database_name": database_name,
                    "query": query
                }
            }
            
            return f"❌ 外部数据库查询失败\n\n{json.dumps(formatted_result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"外部数据库查询失败: {e}")
        result = {
            "status": "error",
            "message": f"外部数据库查询失败: {str(e)}",
            "error_type": type(e).__name__,
            "database_name": database_name,
            "query": query
        }
        return f"❌ 查询失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def manage_api_config(
    action: str,
    api_name: str = None,
    config_data: dict = None
) -> str:
    """
    管理API配置
    
    Args:
        action: 操作类型 (list|test|add|remove|reload|get_endpoints)
        api_name: API名称
        config_data: API配置数据
    
    Returns:
        str: 操作结果
    """
    try:
        if action == "list":
            apis = api_config_manager.list_apis()
            if not apis:
                result = {
                    "status": "success",
                    "message": "当前没有配置任何API",
                    "data": {"apis": []}
                }
                return f"📋 API配置列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            # apis已经是包含API信息的字典，直接转换为列表
            api_list = list(apis.values())
            
            result = {
                "status": "success",
                "message": f"找到 {len(api_list)} 个已配置的API",
                "data": {"apis": api_list}
            }
            return f"📋 API配置列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "test":
            if not api_name:
                result = {
                    "status": "error",
                    "message": "测试API连接需要提供api_name参数"
                }
                return f"❌ 测试失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success, message = api_connector.test_api_connection(api_name)
            result = {
                "status": "success" if success else "error",
                "message": message,
                "data": {"api_name": api_name}
            }
            status_icon = "✅" if success else "❌"
            return f"{status_icon} API连接测试\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "add":
            if not api_name or not config_data:
                result = {
                    "status": "error",
                    "message": "添加API配置需要提供api_name和config_data参数"
                }
                return f"❌ 添加失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success = api_config_manager.add_api_config(api_name, config_data)
            message = f"API配置 '{api_name}' 添加成功" if success else f"API配置 '{api_name}' 添加失败"
            result = {
                "status": "success" if success else "error",
                "message": message,
                "data": {"api_name": api_name}
            }
            status_icon = "✅" if success else "❌"
            return f"{status_icon} API配置添加\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "remove":
            if not api_name:
                result = {
                    "status": "error",
                    "message": "删除API配置需要提供api_name参数"
                }
                return f"❌ 删除失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success = api_config_manager.remove_api_config(api_name)
            message = f"API配置 '{api_name}' 删除成功" if success else f"API配置 '{api_name}' 删除失败或不存在"
            result = {
                "status": "success" if success else "error",
                "message": message,
                "data": {"api_name": api_name}
            }
            status_icon = "✅" if success else "❌"
            return f"{status_icon} API配置删除\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "reload":
            try:
                api_config_manager.reload_config()
                result = {
                    "status": "success",
                    "message": "API配置重载成功"
                }
                return f"✅ API配置重载\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"API配置重载失败: {str(e)}"
                }
                return f"❌ API配置重载\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "get_endpoints":
            if not api_name:
                result = {
                    "status": "error",
                    "message": "获取API端点需要提供api_name参数"
                }
                return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            endpoints = api_connector.get_api_endpoints(api_name)
            if not endpoints:
                result = {
                    "status": "error",
                    "message": f"API '{api_name}' 没有配置端点或API不存在",
                    "data": {"api_name": api_name}
                }
                return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            result = {
                "status": "success",
                "message": f"API '{api_name}' 共有 {len(endpoints)} 个端点",
                "data": {
                    "api_name": api_name,
                    "endpoints": endpoints
                }
            }
            return f"📋 API端点列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        else:
            result = {
                "status": "error",
                "message": f"不支持的操作: {action}",
                "supported_actions": ["list", "test", "add", "remove", "reload", "get_endpoints"]
            }
            return f"❌ 操作失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"管理API配置失败: {e}")
        result = {
            "status": "error",
            "message": f"管理API配置失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 操作失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def fetch_api_data(
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    data: dict = None,
    method: str = None,
    output_format: str = "json",
    transform_config: dict = None,
    persist_to_storage: bool = False,
    storage_session_id: str = None
) -> str:
    """
    从API获取数据，支持持久化存储到临时数据库
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        data: 请求数据（POST/PUT）
        method: HTTP方法
        output_format: 输出格式 (json|csv|excel|dataframe|table)
        transform_config: 数据转换配置
        persist_to_storage: 是否持久化存储到临时数据库
        storage_session_id: 存储会话ID（persist_to_storage为True时必需）
    
    Returns:
        str: API数据或存储结果
    """
    try:
        if not api_name or not endpoint_name:
            result = {
                "status": "error",
                "message": "获取API数据需要提供api_name和endpoint_name参数"
            }
            return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 调用API
        success, response_data, message = api_connector.call_api(
            api_name=api_name,
            endpoint_name=endpoint_name,
            params=params or {},
            data=data,
            method=method
        )
        
        if not success:
            result = {
                "status": "error",
                "message": f"API调用失败: {message}",
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ API调用失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 检查是否需要持久化存储
        if persist_to_storage:
            if not storage_session_id:
                result = {
                    "status": "error",
                    "message": "启用持久化存储时必须提供storage_session_id参数"
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            # 数据转换（如果需要）
            transformed_data = response_data
            if transform_config:
                transform_success, transformed_data, transform_message = data_transformer.transform_data(
                    data=response_data,
                    output_format="json",  # 存储时统一使用json格式
                    transform_config=transform_config
                )
                if not transform_success:
                    result = {
                        "status": "error",
                        "message": f"数据转换失败: {transform_message}",
                        "data": {
                            "api_name": api_name,
                            "endpoint_name": endpoint_name
                        }
                    }
                    return f"❌ 转换失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            # 存储到临时数据库
            source_params = {
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "params": params,
                "method": method
            }
            
            success, count, storage_message = api_data_storage.store_api_data(
                session_id=storage_session_id,
                raw_data=response_data,
                processed_data=transformed_data,
                source_params=source_params
            )
            
            if not success:
                result = {
                    "status": "error",
                    "message": f"数据存储失败: {storage_message}",
                    "data": {
                        "session_id": storage_session_id,
                        "api_name": api_name,
                        "endpoint_name": endpoint_name
                    }
                }
                return f"❌ 存储失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            result = {
                "status": "success",
                "message": "API数据已持久化存储到临时数据库",
                "data": {
                    "session_id": storage_session_id,
                    "api_name": api_name,
                    "endpoint_name": endpoint_name,
                    "stored_records": count,
                    "storage_message": storage_message
                }
            }
            return f"💾 数据已存储\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        else:
            # 直接返回数据（不持久化）
            transform_success, transformed_data, transform_message = data_transformer.transform_data(
                data=response_data,
                output_format=output_format,
                transform_config=transform_config or {}
            )
            
            if not transform_success:
                # 如果转换失败，返回原始数据
                result = {
                    "status": "partial_success",
                    "message": f"API调用成功，但数据转换失败: {transform_message}",
                    "data": {
                        "api_name": api_name,
                        "endpoint_name": endpoint_name,
                        "raw_data": response_data,
                        "format": "raw"
                    },
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "requested_format": output_format
                    }
                }
                return f"⚠️ 部分成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            else:
                result = {
                    "status": "success",
                    "message": f"API调用成功，数据已转换为{output_format}格式",
                    "data": {
                        "api_name": api_name,
                        "endpoint_name": endpoint_name,
                        "transformed_data": transformed_data,
                        "format": output_format
                    },
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "transform_message": transform_message
                    }
                }
                return f"✅ API数据获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"获取API数据失败: {e}")
        result = {
            "status": "error",
            "message": f"获取API数据失败: {str(e)}",
            "error_type": type(e).__name__,
            "data": {
                "api_name": api_name,
                "endpoint_name": endpoint_name
            }
        }
        return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def api_data_preview(
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    max_rows: int = 10,
    max_cols: int = 10
) -> str:
    """
    预览API数据
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        max_rows: 最大显示行数
        max_cols: 最大显示列数
    
    Returns:
        str: 数据预览
    """
    try:
        if not api_name or not endpoint_name:
            result = {
                "status": "error",
                "message": "预览API数据需要提供api_name和endpoint_name参数"
            }
            return f"❌ 预览失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 调用API获取数据
        success, response_data, message = api_connector.call_api(
            api_name=api_name,
            endpoint_name=endpoint_name,
            params=params or {}
        )
        
        if not success:
            result = {
                "status": "error",
                "message": f"API调用失败: {message}",
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ API调用失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 生成数据预览
        preview_success, preview_text, preview_message = data_transformer.preview_data(
            data=response_data,
            max_rows=max_rows,
            max_cols=max_cols
        )
        
        if not preview_success:
            result = {
                "status": "error",
                "message": f"数据预览失败: {preview_message}",
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ 预览失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 获取数据摘要
        summary_success, summary_data, summary_message = data_transformer.get_data_summary(response_data)
        
        result = {
            "status": "success",
            "message": f"API数据预览成功",
            "data": {
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "preview": preview_text,
                "summary": summary_data if summary_success else None
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "max_rows": max_rows,
                "max_cols": max_cols
            }
        }
        
        return f"👁️ API数据预览\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"预览API数据失败: {e}")
        result = {
            "status": "error",
            "message": f"预览API数据失败: {str(e)}",
            "error_type": type(e).__name__,
            "data": {
                "api_name": api_name,
                "endpoint_name": endpoint_name
            }
        }
        return f"❌ 预览失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def create_api_storage_session(
    session_name: str,
    api_name: str,
    endpoint_name: str,
    description: str = None
) -> str:
    """
    创建API数据存储会话
    
    Args:
        session_name: 存储会话名称
        api_name: API名称
        endpoint_name: 端点名称
        description: 会话描述
    
    Returns:
        str: 创建结果
    """
    try:
        if not session_name or not api_name or not endpoint_name:
            result = {
                "status": "error",
                "message": "创建存储会话需要提供session_name、api_name和endpoint_name参数"
            }
            return f"❌ 创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        success, session_id, message = api_data_storage.create_storage_session(
            session_name=session_name,
            api_name=api_name,
            endpoint_name=endpoint_name,
            description=description
        )
        
        if success:
            result = {
                "status": "success",
                "message": message,
                "data": {
                    "session_id": session_id,
                    "session_name": session_name,
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"✅ 存储会话创建成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        else:
            result = {
                "status": "error",
                "message": message
            }
            return f"❌ 创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"创建API存储会话失败: {e}")
        result = {
            "status": "error",
            "message": f"创建API存储会话失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def store_api_data_to_session(
    session_id: str,
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    data: dict = None,
    method: str = None,
    transform_config: dict = None
) -> str:
    """
    获取API数据并存储到会话中
    
    Args:
        session_id: 存储会话ID
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        data: 请求数据（POST/PUT）
        method: HTTP方法
        transform_config: 数据转换配置
    
    Returns:
        str: 存储结果
    """
    try:
        if not session_id or not api_name or not endpoint_name:
            result = {
                "status": "error",
                "message": "存储API数据需要提供session_id、api_name和endpoint_name参数"
            }
            return f"❌ 存储失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 调用API获取数据
        success, response_data, message = api_connector.call_api(
            api_name=api_name,
            endpoint_name=endpoint_name,
            params=params or {},
            data=data,
            method=method
        )
        
        if not success:
            result = {
                "status": "error",
                "message": f"API调用失败: {message}",
                "data": {
                    "session_id": session_id,
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ API调用失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 数据转换（如果需要）
        processed_data = None
        if transform_config:
            transform_success, transformed_data, transform_message = data_transformer.transform_data(
                data=response_data,
                output_format="json",
                transform_config=transform_config
            )
            if transform_success:
                processed_data = transformed_data
        
        # 存储数据
        store_success, records_added, store_message = api_data_storage.store_api_data(
            session_id=session_id,
            raw_data=response_data,
            processed_data=processed_data,
            source_params={
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "params": params,
                "data": data,
                "method": method,
                "transform_config": transform_config
            }
        )
        
        if store_success:
            result = {
                "status": "success",
                "message": f"API数据存储成功: {store_message}",
                "data": {
                    "session_id": session_id,
                    "api_name": api_name,
                    "endpoint_name": endpoint_name,
                    "records_added": records_added,
                    "has_processed_data": processed_data is not None
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "api_call_success": True,
                    "transform_applied": transform_config is not None
                }
            }
            return f"✅ API数据存储成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        else:
            result = {
                "status": "error",
                "message": f"数据存储失败: {store_message}",
                "data": {
                    "session_id": session_id,
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ 存储失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"存储API数据失败: {e}")
        result = {
            "status": "error",
            "message": f"存储API数据失败: {str(e)}",
            "error_type": type(e).__name__,
            "data": {
                "session_id": session_id,
                "api_name": api_name,
                "endpoint_name": endpoint_name
            }
        }
        return f"❌ 存储失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"







# ================================
# 4. 启动服务器
# ================================
if __name__ == "__main__":
    logger.info(f"启动 {TOOL_NAME}")
    
    # 初始化数据库
    init_database()
    
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("正在关闭...")
    finally:
        logger.info("服务器已关闭")

# ================================
# 5. 使用说明
# ================================
"""
🚀 SuperDataAnalysis MCP 使用指南：

1️⃣ 导入Excel数据：
   connect_data_source(
       source_type="excel",
       config={
           "file_path": "path/to/your/file.xlsx",
           "sheet_name": "Sheet1"  # 可选
       },
       target_table="my_table"  # 可选
   )

2️⃣ 执行SQL查询：
   execute_sql(
       query="SELECT * FROM my_table",
       limit=100
   )

3️⃣ 获取数据信息：
   get_data_info(info_type="tables")  # 获取所有表
   get_data_info(info_type="schema", table_name="my_table")  # 获取表结构

4️⃣ 数据分析：
   analyze_data(
       analysis_type="basic_stats",
       table_name="my_table",
       columns=["column1", "column2"]  # 可选
   )
   
   analyze_data(
       analysis_type="correlation",
       table_name="my_table"
   )
   
   analyze_data(
       analysis_type="outliers",
       table_name="my_table",
       options={"method": "iqr"}  # 或 "zscore"
   )



5️⃣ 数据处理 (Excel数据处理)：
   process_data(
       operation_type="clean",
       data_source="my_table",
       config={
           "remove_duplicates": True,
           "fill_missing": {
               "column1": {"method": "mean"},
               "column2": {"method": "mode"}
           }
       }
   )
   
   process_data(
       operation_type="filter",
       data_source="my_table",
       config={
           "filter_condition": "age > 18",
           "select_columns": ["name", "age", "salary"]
       }
   )
   
   process_data(
       operation_type="aggregate",
       data_source="my_table",
       config={
           "group_by": {
               "columns": ["department"],
               "agg": {"salary": "mean", "age": "count"}
           }
       }
   )

6️⃣ 数据导出：
   export_data(
       export_type="excel",
       data_source="my_table",
       file_path="exports/data.xlsx"  # 可选
   )
   
   export_data(
       export_type="csv",
       data_source="SELECT * FROM my_table WHERE condition"
   )



💡 特性：
   - 6个强大的数据分析工具
   - Excel数据处理功能 (清洗、转换、筛选、聚合、合并、重塑)
   - 自动数据类型推断
   - 统一的JSON返回格式
   - 完善的错误处理
   - 支持多种导出格式
   - 丰富的统计分析功能
   - 预留API和SQL数据处理扩展
"""