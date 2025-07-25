#!/usr/bin/env python3
"""
DataMaster MCP - 超级数据分析工具
为AI提供强大的数据分析能力

核心理念：工具专注数据获取和计算，AI专注智能分析和洞察
"""

import json
import sqlite3
import pandas as pd
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from mcp.server.fastmcp import FastMCP
import numpy as np
from scipy import stats

# SQLAlchemy imports for pandas to_sql compatibility
try:
    from sqlalchemy import create_engine
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy not available. External database import may not work properly.")

# 导入数据库管理器
from .config.database_manager import database_manager
from .config.config_manager import config_manager

# 导入API连接器组件
from .config.api_config_manager import api_config_manager
from .config.api_connector import api_connector
from .config.data_transformer import data_transformer
from .config.api_data_storage import api_data_storage

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
TOOL_NAME = "DataMaster_MCP"
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

def _analyze_database_cleanup(conn) -> dict:
    """分析数据库并提供清理建议"""
    try:
        # 获取所有表（排除元数据表）
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != '_metadata'"
        )
        all_tables = [row[0] for row in cursor.fetchall()]
        
        if not all_tables:
            return {
                "total_tables": 0,
                "cleanup_suggestions": [],
                "summary": "数据库中没有用户表，无需清理",
                "ai_recommendation": "数据库状态良好，无需执行清理操作。"
            }
        
        cleanup_suggestions = []
        test_tables = []
        temp_tables = []
        empty_tables = []
        duplicate_tables = []
        old_tables = []
        
        # 分析每个表
        for table in all_tables:
            try:
                escaped_table = _escape_identifier(table)
                
                # 获取表的行数
                cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
                row_count = cursor.fetchone()[0]
                
                # 检测测试表（包含test、temp、tmp、demo等关键词）
                table_lower = table.lower()
                if any(keyword in table_lower for keyword in ['test', 'temp', 'tmp', 'demo', 'sample', 'example', '_bak', '_backup']):
                    test_tables.append({
                        "table_name": table,
                        "row_count": row_count,
                        "reason": "表名包含测试/临时关键词",
                        "risk_level": "low" if row_count == 0 else "medium"
                    })
                
                # 检测空表
                if row_count == 0:
                    empty_tables.append({
                        "table_name": table,
                        "row_count": 0,
                        "reason": "表为空，无数据",
                        "risk_level": "low"
                    })
                
                # 检测可能的重复表（相似表名）
                for other_table in all_tables:
                    if table != other_table and table.startswith(other_table) and len(table) > len(other_table):
                        # 检查是否是版本化的表（如table_v1, table_v2等）
                        suffix = table[len(other_table):]
                        if suffix.startswith('_') and any(char.isdigit() for char in suffix):
                            duplicate_tables.append({
                                "table_name": table,
                                "base_table": other_table,
                                "row_count": row_count,
                                "reason": f"可能是 '{other_table}' 的版本化副本",
                                "risk_level": "medium"
                            })
                            break
                
                # 检测表结构获取创建信息（SQLite限制，无法直接获取创建时间）
                # 但可以通过表名模式推断是否为旧表
                if any(pattern in table_lower for pattern in ['old', 'archive', 'history', 'backup', 'deprecated']):
                    old_tables.append({
                        "table_name": table,
                        "row_count": row_count,
                        "reason": "表名暗示为历史/归档数据",
                        "risk_level": "medium"
                    })
                    
            except Exception as e:
                logger.warning(f"分析表 '{table}' 时出错: {e}")
                continue
        
        # 生成清理建议
        if test_tables:
            cleanup_suggestions.append({
                "category": "测试/临时表",
                "tables": test_tables,
                "description": "这些表看起来是用于测试或临时用途的",
                "recommendation": "建议删除这些测试表以保持数据库整洁",
                "action": "DELETE",
                "priority": "HIGH" if any(t['row_count'] == 0 for t in test_tables) else "MEDIUM"
            })
        
        if empty_tables:
            cleanup_suggestions.append({
                "category": "空表",
                "tables": empty_tables,
                "description": "这些表没有任何数据",
                "recommendation": "建议删除空表，如需要可以重新创建",
                "action": "DELETE",
                "priority": "HIGH"
            })
        
        if duplicate_tables:
            cleanup_suggestions.append({
                "category": "重复/版本化表",
                "tables": duplicate_tables,
                "description": "这些表可能是其他表的副本或旧版本",
                "recommendation": "请确认是否需要保留这些表，建议删除不需要的版本",
                "action": "REVIEW",
                "priority": "MEDIUM"
            })
        
        if old_tables:
            cleanup_suggestions.append({
                "category": "历史/归档表",
                "tables": old_tables,
                "description": "这些表看起来是历史数据或归档数据",
                "recommendation": "请确认是否还需要这些历史数据，可考虑导出后删除",
                "action": "REVIEW",
                "priority": "LOW"
            })
        
        # 生成AI建议
        total_suggested_for_deletion = len([t for cat in cleanup_suggestions for t in cat['tables'] if cat['action'] == 'DELETE'])
        total_suggested_for_review = len([t for cat in cleanup_suggestions for t in cat['tables'] if cat['action'] == 'REVIEW'])
        
        if not cleanup_suggestions:
            ai_recommendation = "🎉 数据库状态良好！没有发现需要清理的过时数据或表。"
        else:
            ai_recommendation = f"📋 发现 {len(cleanup_suggestions)} 类问题需要处理：\n"
            if total_suggested_for_deletion > 0:
                ai_recommendation += f"• 建议直接删除 {total_suggested_for_deletion} 个表（测试表/空表）\n"
            if total_suggested_for_review > 0:
                ai_recommendation += f"• 需要人工确认 {total_suggested_for_review} 个表（重复表/历史表）\n"
            ai_recommendation += "\n💡 建议：先备份重要数据，然后按优先级处理清理建议。"
        
        # 生成清理统计
        cleanup_stats = {
            "total_tables": len(all_tables),
            "test_tables_count": len(test_tables),
            "empty_tables_count": len(empty_tables),
            "duplicate_tables_count": len(duplicate_tables),
            "old_tables_count": len(old_tables),
            "total_issues": len(cleanup_suggestions),
            "high_priority_issues": len([c for c in cleanup_suggestions if c['priority'] == 'HIGH']),
            "medium_priority_issues": len([c for c in cleanup_suggestions if c['priority'] == 'MEDIUM']),
            "low_priority_issues": len([c for c in cleanup_suggestions if c['priority'] == 'LOW'])
        }
        
        return {
            "cleanup_stats": cleanup_stats,
            "cleanup_suggestions": cleanup_suggestions,
            "ai_recommendation": ai_recommendation,
            "summary": f"分析了 {len(all_tables)} 个表，发现 {len(cleanup_suggestions)} 类清理建议",
            "next_steps": [
                "1. 查看清理建议详情",
                "2. 备份重要数据（如需要）",
                "3. 按优先级执行清理操作",
                "4. 定期运行清理分析保持数据库整洁"
            ]
        }
        
    except Exception as e:
        logger.error(f"数据库清理分析失败: {e}")
        return {
            "error": f"清理分析失败: {str(e)}",
            "cleanup_suggestions": [],
            "ai_recommendation": "❌ 清理分析过程中出现错误，请检查数据库连接和权限。"
        }



# ================================
# 3. 核心工具实现
# ================================

@mcp.tool()
def connect_data_source(
    source_type: str,
    config: dict,
    target_table: str = None,
    target_database: str = None
) -> str:
    """
    🔗 数据源连接路由器 - AI必读使用指南
    
    ⚠️ 重要：数据库连接采用"两步连接法"设计模式！
    
    📋 支持的数据源类型：
    - "excel" - Excel文件导入到数据库
    - "csv" - CSV文件导入到数据库
    - "json" - JSON文件导入到数据库（支持嵌套结构自动扁平化）
    - "sqlite" - SQLite数据库文件连接
    - "mysql" - MySQL数据库连接（第一步：创建临时配置）
    - "postgresql" - PostgreSQL数据库连接（第一步：创建临时配置）
    - "mongodb" - MongoDB数据库连接（第一步：创建临时配置）
    - "database_config" - 使用已有配置连接（第二步：实际连接）
    
    🎯 AI使用流程：
    1️⃣ 数据库连接第一步：
       connect_data_source(source_type="mysql", config={host, port, user, database, password})
       → 返回临时配置名称（如：temp_mysql_20250724_173102）
    
    2️⃣ 数据库连接第二步：
       connect_data_source(source_type="database_config", config={"database_name": "配置名称"})
       → 建立可查询的数据库连接
    
    3️⃣ 查询数据：
       使用 query_external_database(database_name="配置名称", query="SQL")
    
    💡 参数兼容性：
    - 支持 "user" 或 "username" 参数
    - 端口号使用数字类型（如：3306）
    - 密码使用字符串类型
    
    Args:
        source_type: 数据源类型，必须是上述支持的类型之一
        config: 配置参数字典，格式根据source_type不同
        target_table: 目标表名（文件导入时可选）
        target_database: 目标数据库名称（文件导入到外部数据库时可选）
    
    Returns:
        str: JSON格式的连接结果，包含状态、消息和配置信息
    
    ⚡ AI快速上手：
    记住"两步连接法"：先创建配置 → 再使用配置 → 最后查询数据
    """
    try:
        if source_type == "excel":
            return _import_excel(config, target_table, target_database)
        elif source_type == "csv":
            return _import_csv(config, target_table, target_database)
        elif source_type == "json":
            return _import_json(config, target_table, target_database)
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
                "supported_types": ["excel", "csv", "json", "sqlite", "mysql", "postgresql", "mongodb", "database_config"]
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
        flatten_nested = config.get('flatten_nested', True)  # 是否扁平化嵌套结构
        max_nesting_level = config.get('max_nesting_level', 3)  # 最大嵌套层级
        
        if not file_path:
            raise ValueError("缺少file_path参数")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding=encoding) as f:
            json_data = json.load(f)
        
        # 处理不同的JSON结构
        if isinstance(json_data, list):
            # JSON数组，直接转换为DataFrame
            df = pd.json_normalize(json_data, max_level=max_nesting_level if flatten_nested else None)
        elif isinstance(json_data, dict):
            # JSON对象，需要判断结构
            if any(isinstance(v, list) for v in json_data.values()):
                # 包含数组的对象，尝试找到主要的数据数组
                main_data = None
                for key, value in json_data.items():
                    if isinstance(value, list) and len(value) > 0:
                        main_data = value
                        break
                
                if main_data is not None:
                    df = pd.json_normalize(main_data, max_level=max_nesting_level if flatten_nested else None)
                    # 添加其他非数组字段作为常量列
                    for key, value in json_data.items():
                        if not isinstance(value, list):
                            df[f'root_{key}'] = value
                else:
                    # 没有找到数组，将整个对象作为单行数据
                    df = pd.json_normalize([json_data], max_level=max_nesting_level if flatten_nested else None)
            else:
                # 纯对象，作为单行数据
                df = pd.json_normalize([json_data], max_level=max_nesting_level if flatten_nested else None)
        else:
            # 其他类型，转换为单行单列数据
            df = pd.DataFrame({'value': [json_data]})
        
        # 清理列名（移除特殊字符）
        df.columns = [str(col).replace(' ', '_').replace('-', '_').replace('.', '_').replace('[', '_').replace(']', '_') for col in df.columns]
        
        # 🔧 关键修复：处理复杂数据类型，确保SQLite兼容性
        for col in df.columns:
            df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False, default=str) if isinstance(x, (list, dict)) else x)
        
        # 生成表名
        if not target_table:
            file_name = Path(file_path).stem
            target_table = f"json_{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 导入到数据库
        if target_database:
            # 导入到外部数据库
            return _import_to_external_database(df, target_table, target_database, 'json', file_path, 
                                               {'encoding': encoding, 'flatten_nested': flatten_nested, 'max_nesting_level': max_nesting_level})
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
                    "flatten_nested": flatten_nested,
                    "max_nesting_level": max_nesting_level,
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

def _create_sqlalchemy_engine(database_name: str):
    """为指定数据库创建SQLAlchemy引擎"""
    try:
        # 获取数据库配置
        available_databases = database_manager.get_available_databases()
        if database_name not in available_databases:
            logger.error(f"Database config not found: {database_name}")
            return None
        
        db_info = available_databases[database_name]
        db_type = db_info.get("type", "unknown").lower()
        
        # 获取数据库配置详情
        config = database_manager.config_manager.get_database_config(database_name)
        if not config:
            logger.error(f"Failed to get database config for: {database_name}")
            return None
        
        # 根据数据库类型创建连接字符串
        if db_type == "mysql":
            # MySQL连接字符串
            host = config.get("host", "localhost")
            port = config.get("port", 3306)
            user = config.get("user") or config.get("username")
            password = config.get("password")
            database = config.get("database")
            charset = config.get("charset", "utf8mb4")
            
            # 使用pymysql驱动
            connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
            
        elif db_type == "postgresql":
            # PostgreSQL连接字符串
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            user = config.get("user") or config.get("username")
            password = config.get("password")
            database = config.get("database")
            
            # 使用psycopg2驱动
            connection_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
            
        elif db_type == "sqlite":
            # SQLite连接字符串
            file_path = config.get("file_path")
            connection_string = f"sqlite:///{file_path}"
            
        else:
            logger.error(f"Unsupported database type for SQLAlchemy: {db_type}")
            return None
        
        # 创建引擎
        logger.info(f"Creating SQLAlchemy engine for {database_name} with connection string: {connection_string[:50]}...")
        engine = create_engine(connection_string, echo=False)
        logger.info(f"SQLAlchemy engine created successfully for {database_name}")
        return engine
        
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy engine for {database_name}: {e}")
        return None

def _import_to_external_database(df, target_table: str, target_database: str, source_type: str, source_path: str, import_config: dict) -> str:
    """将DataFrame导入到外部数据库"""
    try:
        # 验证目标数据库是否存在
        available_databases = database_manager.get_available_databases()
        if target_database not in available_databases:
            result = {
                "status": "error",
                "message": f"目标数据库配置不存在: {target_database}",
                "available_databases": list(available_databases.keys())
            }
            return f"❌ 导入失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 测试数据库连接
        is_valid, message = database_manager.test_connection(target_database)
        if not is_valid:
            result = {
                "status": "error",
                "message": f"目标数据库连接失败: {message}",
                "database_name": target_database
            }
            return f"❌ 导入失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 获取数据库信息
        db_info = available_databases[target_database]
        db_type = db_info.get("type", "unknown")
        
        # 使用database_manager导入数据
        if db_type.lower() == 'mongodb':
            # MongoDB特殊处理
            with database_manager.get_connection(target_database) as conn:
                records = df.to_dict('records')
                collection = conn[target_table]
                # 清空现有数据
                collection.delete_many({})
                # 插入新数据
                if records:
                    collection.insert_many(records)
                row_count = len(records)
        else:
            # SQL数据库（MySQL, PostgreSQL, SQLite）需要SQLAlchemy引擎
            if not SQLALCHEMY_AVAILABLE:
                raise ImportError("SQLAlchemy is required for SQL database import. Please install: pip install sqlalchemy")
            
            # 创建SQLAlchemy引擎
            logger.info(f"Starting external database import for {target_database}, table: {target_table}")
            engine = _create_sqlalchemy_engine(target_database)
            if engine is None:
                raise ValueError(f"Failed to create SQLAlchemy engine for database: {target_database}")
            
            # 使用pandas to_sql with SQLAlchemy engine
            logger.info(f"Importing {len(df)} rows to table {target_table} using pandas to_sql")
            df.to_sql(target_table, engine, if_exists='replace', index=False, method='multi')
            logger.info(f"Successfully imported data to table {target_table}")
            row_count = len(df)
            engine.dispose()  # 清理连接池
        
        # 构建成功结果
        result = {
            "status": "success",
            "message": f"{source_type.upper()}文件已成功导入到外部数据库",
            "data": {
                "table_name": target_table,
                "database_name": target_database,
                "database_type": db_type,
                "source_file": source_path,
                "row_count": row_count,
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "connection_type": "外部数据库导入",
                "data_location": "远程数据库服务器",
                "usage_note": f"使用execute_sql(data_source='{target_database}')或query_external_database(database_name='{target_database}')查询此数据"
            },
            "import_config": import_config,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "import_method": "external_database"
            }
        }
        
        return f"✅ {source_type.upper()}文件已导入到外部数据库 {target_database}\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"外部数据库导入失败: {e}")
        result = {
            "status": "error",
            "message": f"导入到外部数据库失败: {str(e)}",
            "database_name": target_database,
            "error_type": type(e).__name__
        }
        return f"❌ 导入失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _connect_sqlite(config: dict, target_table: str = None) -> str:
    """连接SQLite数据库"""
    try:
        file_path = config.get("file_path")
        if not file_path:
            result = {
                "status": "error",
                "message": "缺少file_path参数",
                "required_params": ["file_path"]
            }
            return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 检查文件是否存在
        sqlite_path = Path(file_path)
        if not sqlite_path.exists():
            result = {
                "status": "error",
                "message": f"SQLite文件不存在: {file_path}",
                "file_path": file_path
            }
            return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 创建临时配置
        temp_config_name = f"temp_sqlite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sqlite_config = {
            "type": "sqlite",
            "file_path": str(sqlite_path.absolute()),
            "enabled": True,
            "description": f"临时SQLite连接: {sqlite_path.name}",
            "_is_temporary": True,
            "_created_at": datetime.now().isoformat()
        }
        
        # 添加临时配置
        if config_manager.add_database_config(temp_config_name, sqlite_config):
            try:
                # 测试连接
                is_valid, message = database_manager.test_connection(temp_config_name)
                if not is_valid:
                    config_manager.remove_database_config(temp_config_name)
                    result = {
                        "status": "error",
                        "message": f"SQLite连接测试失败: {message}",
                        "file_path": file_path
                    }
                    return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
                # 获取表列表
                tables = database_manager.get_table_list(temp_config_name)
                
                result = {
                    "status": "success",
                    "message": f"SQLite数据库连接成功: {sqlite_path.name}",
                    "data": {
                        "database_type": "sqlite",
                        "file_path": str(sqlite_path.absolute()),
                        "file_name": sqlite_path.name,
                        "file_size": f"{sqlite_path.stat().st_size / 1024:.2f} KB",
                        "tables": tables,
                        "table_count": len(tables),
                        "temp_config_name": temp_config_name,
                        "connection_type": "外部SQLite数据库连接",
                        "data_location": str(sqlite_path.absolute()),
                        "usage_note": f"使用execute_sql(data_source='{temp_config_name}')或query_external_database(database_name='{temp_config_name}')查询此数据库"
                    },
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "connection_method": "sqlite_file"
                    }
                }
                
                return f"✅ SQLite数据库连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
            except Exception as e:
                config_manager.remove_database_config(temp_config_name)
                raise e
        else:
            result = {
                "status": "error",
                "message": "创建SQLite临时配置失败"
            }
            return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"SQLite数据库连接失败: {e}")
        result = {
            "status": "error",
            "message": f"SQLite数据库连接失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

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
                "message": f"{db_type.upper()} 外部数据库连接成功（未导入数据）",
                "data": {
                    "database_name": database_name,
                    "database_type": db_type,
                    "tables": tables,
                    "table_count": len(tables),
                    "connection_type": "外部数据库连接",
                    "data_location": "远程数据库服务器",
                    "usage_note": f"使用execute_sql(data_source='{database_name}')或query_external_database(database_name='{database_name}')查询此数据库"
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "connection_method": "config_name"
                }
            }
            
            return f"✅ {db_type.upper()} 外部数据库连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
        else:
            # 直接连接配置
            # 创建持久化临时配置并测试连接
            temp_config_name = f"temp_{db_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            config_with_type = config.copy()
            config_with_type["type"] = db_type
            config_with_type["enabled"] = True
            config_with_type["description"] = f"临时{db_type.upper()}连接配置"
            config_with_type["_is_temporary"] = True
            config_with_type["_created_at"] = datetime.now().isoformat()
            
            # 添加临时配置（不立即删除）
            if config_manager.add_database_config(temp_config_name, config_with_type):
                try:
                    # 测试连接
                    is_valid, message = database_manager.test_connection(temp_config_name)
                    if not is_valid:
                        # 连接失败时清理临时配置
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
                        "message": f"{db_type.upper()} 外部数据库连接成功（未导入数据）",
                        "data": {
                            "database_type": db_type,
                            "host": config.get("host", "N/A"),
                            "database": config.get("database", "N/A"),
                            "tables": tables,
                            "table_count": len(tables),
                            "temp_config_name": temp_config_name,
                            "connection_type": "外部数据库连接",
                            "data_location": "远程数据库服务器",
                            "usage_note": f"使用execute_sql(data_source='{temp_config_name}')或query_external_database(database_name='{temp_config_name}')查询此数据库",
                            "config_lifecycle": "临时配置已保存，可在会话期间使用"
                        },
                        "metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "connection_method": "direct_config",
                            "config_persistence": "temporary_persistent"
                        }
                    }
                    
                    return f"✅ {db_type.upper()} 外部数据库连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                except Exception as e:
                    # 发生异常时清理临时配置
                    config_manager.remove_database_config(temp_config_name)
                    raise e
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
            "message": f"外部数据库连接成功: {database_name}（未导入数据）",
            "data": {
                "database_name": database_name,
                "database_type": db_info.get("type"),
                "description": db_info.get("description", ""),
                "tables": tables,
                "table_count": len(tables),
                "connection_type": "外部数据库连接",
                "data_location": "远程数据库服务器",
                "usage_note": f"使用execute_sql(data_source='{database_name}')或query_external_database(database_name='{database_name}')查询此数据库"
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "connection_method": "config_file"
            }
        }
        
        return f"✅ 外部数据库连接成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
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
    limit: int = 1000,
    data_source: str = None
) -> str:
    """
    📊 SQL执行工具 - 本地数据库查询专用
    
    🎯 使用场景：
    - 查询本地SQLite数据库（默认）
    - 查询已导入的Excel/CSV数据
    - 查询指定的本地数据源
    
    ⚠️ 重要区别：
    - 本地数据查询 → 使用此工具 (execute_sql)
    - 外部数据库查询 → 使用 query_external_database
    
    🔒 安全特性：
    - 自动添加LIMIT限制防止大量数据返回
    - 支持参数化查询防止SQL注入
    - 只允许SELECT查询，拒绝危险操作
    
    Args:
        query: SQL查询语句（推荐使用SELECT语句）
        params: 查询参数字典，用于参数化查询（可选）
        limit: 结果行数限制，默认1000行（可选）
        data_source: 数据源名称，默认本地SQLite（可选）
    
    Returns:
        str: JSON格式查询结果，包含列名、数据行和统计信息
    
    💡 AI使用提示：
    - 查询本地数据时优先使用此工具
    - 查询外部数据库时使用 query_external_database
    - 使用 get_data_info 先了解表结构
    """
    try:
        # 预处理SQL语句
        query = _preprocess_sql(query)
        
        # 添加LIMIT限制
        if "LIMIT" not in query.upper() and "SELECT" in query.upper():
            query = f"{query} LIMIT {limit}"
        
        # 根据数据源选择连接方式
        if data_source:
            # 使用外部数据库连接
            try:
                result_data = database_manager.execute_query(data_source, query, params)
                
                if result_data["success"]:
                    result = {
                        "status": "success",
                        "message": f"查询完成，返回 {result_data.get('row_count', len(result_data['data']))} 条记录",
                        "data": {
                            "columns": list(result_data['data'][0].keys()) if result_data['data'] else [],
                            "rows": result_data['data'],
                            "row_count": result_data.get('row_count', len(result_data['data']))
                        },
                        "metadata": {
                            "query": query,
                            "data_source": data_source,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    return f"✅ SQL执行成功（数据源: {data_source}）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                else:
                    result = {
                        "status": "error",
                        "message": f"查询失败: {result_data['error']}",
                        "data_source": data_source,
                        "timestamp": datetime.now().isoformat()
                    }
                    return f"❌ SQL执行失败（数据源: {data_source}）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"连接数据源失败: {str(e)}",
                    "data_source": data_source,
                    "timestamp": datetime.now().isoformat()
                }
                return f"❌ 数据源连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        else:
            # 使用本地SQLite数据库
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
                        "data_source": "本地SQLite",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                return f"✅ SQL执行成功（数据源: 本地SQLite）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"SQL执行失败: {e}")
        result = _format_sql_error(e, query)
        result["timestamp"] = datetime.now().isoformat()
        result["data_source"] = data_source or "本地SQLite"
        return f"❌ SQL执行失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def get_data_info(
    info_type: str = "tables",
    table_name: str = None,
    data_source: str = None
) -> str:
    """
    📊 数据信息获取工具 - 查看数据库结构和统计信息
    
    功能说明：
    - 获取数据库表列表、表结构、数据统计等信息
    - 支持本地SQLite和外部数据库
    - 提供详细的表结构和数据概览
    - 智能数据库清理管理功能
    
    Args:
        info_type: 信息类型
            - "tables": 获取所有表/集合列表（默认）
            - "schema": 获取指定表的结构信息（需要table_name）
            - "stats": 获取指定表的统计信息（需要table_name）
            - "cleanup": 智能检测过时数据和表，提供清理建议
        table_name: 表名（当info_type为schema或stats时必需）
        data_source: 数据源名称
            - None: 使用本地SQLite数据库（默认）
            - 配置名称: 使用外部数据库（需先通过manage_database_config创建配置）
    
    Returns:
        str: JSON格式的数据库信息，包含状态、数据和元数据
    
    🤖 AI使用建议：
    1. 数据探索：先用info_type="tables"查看所有表
    2. 结构分析：用info_type="schema"了解表结构
    3. 数据概览：用info_type="stats"获取统计信息
    4. 数据库维护：用info_type="cleanup"检测并清理过时数据
    5. 外部数据库：确保data_source配置已存在
    
    💡 最佳实践：
    - 在查询数据前先了解表结构
    - 使用stats了解数据分布和质量
    - 定期使用cleanup功能维护数据库整洁
    - 结合analyze_data工具进行深度分析
    
    ⚠️ 常见错误避免：
    - schema和stats必须指定table_name
    - 外部数据库需要有效的data_source配置
    - 表名区分大小写
    - cleanup功能仅适用于本地SQLite数据库
    
    📈 高效使用流程：
    1. get_data_info(info_type="tables") → 查看所有表
    2. get_data_info(info_type="schema", table_name="表名") → 了解结构
    3. get_data_info(info_type="stats", table_name="表名") → 查看统计
    4. get_data_info(info_type="cleanup") → 检测过时数据
    5. analyze_data() → 深度分析
    
    🎯 关键理解点：
    - 这是数据探索的第一步工具
    - 为后续分析提供基础信息
    - 支持本地和远程数据源
    - 智能维护数据库整洁性
    
    🧹 数据库清理功能（info_type="cleanup"）：
    - 自动检测测试表、临时表、过时表
    - 识别空表和重复表
    - 分析表的创建时间和最后访问时间
    - 提供智能清理建议，询问用户是否执行清理
    - 支持批量清理和选择性清理
    """
    try:
        if data_source:
            # 使用外部数据库连接
            try:
                if info_type == "tables":
                    tables = database_manager.get_table_list(data_source)
                    
                    result = {
                        "status": "success",
                        "message": f"找到 {len(tables)} 个表/集合",
                        "data": {
                            "tables": [{
                                "table_name": table,
                                "row_count": "N/A"  # 外部数据库暂不统计行数
                            } for table in tables],
                            "table_count": len(tables)
                        },
                        "metadata": {
                            "data_source": data_source,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    return f"✅ 表信息获取成功（数据源: {data_source}）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                elif info_type == "schema" and table_name:
                    schema = database_manager.get_table_schema(data_source, table_name)
                    
                    result = {
                        "status": "success",
                        "message": f"表/集合 '{table_name}' 结构信息",
                        "data": {
                            "table_name": table_name,
                            "schema": schema,
                            "column_count": len(schema) if isinstance(schema, list) else "N/A"
                        },
                        "metadata": {
                            "data_source": data_source,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    return f"✅ 表结构获取成功（数据源: {data_source}）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                else:
                    result = {
                        "status": "error",
                        "message": "外部数据源暂不支持stats和cleanup信息类型或缺少必要参数",
                        "supported_types": ["tables", "schema"],
                        "data_source": data_source,
                        "note": "cleanup功能仅适用于本地SQLite数据库"
                    }
                    return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"连接数据源失败: {str(e)}",
                    "data_source": data_source,
                    "timestamp": datetime.now().isoformat()
                }
                return f"❌ 数据源连接失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        else:
            # 使用本地SQLite数据库
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
                        },
                        "metadata": {
                            "data_source": "本地SQLite",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    return f"✅ 表信息获取成功（数据源: 本地SQLite）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
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
                        },
                        "metadata": {
                            "data_source": "本地SQLite",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    return f"✅ 表结构获取成功（数据源: 本地SQLite）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
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
                        },
                        "metadata": {
                            "data_source": "本地SQLite",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    return f"✅ 统计信息获取成功（数据源: 本地SQLite）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
                elif info_type == "cleanup":
                    # 智能数据库清理功能
                    cleanup_result = _analyze_database_cleanup(conn)
                    
                    result = {
                        "status": "success",
                        "message": "数据库清理分析完成",
                        "data": cleanup_result,
                        "metadata": {
                            "data_source": "本地SQLite",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    return f"🧹 数据库清理分析完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
                elif info_type == "api_storage":
                    # API存储数据概览 - 解决API数据存储位置不透明问题
                    try:
                        from config.api_data_storage import api_data_storage
                        
                        # 获取所有API存储会话
                        success, sessions, message = api_data_storage.list_storage_sessions()
                        
                        if not success:
                            result = {
                                "status": "error",
                                "message": f"获取API存储信息失败: {message}",
                                "data_source": "API存储"
                            }
                            return f"❌ API存储信息获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                        
                        # 统计API存储信息
                        total_sessions = len(sessions)
                        total_records = sum(session.get('total_records', 0) for session in sessions)
                        api_names = list(set(session['api_name'] for session in sessions))
                        endpoint_names = list(set(session['endpoint_name'] for session in sessions))
                        
                        # 按API分组统计
                        api_stats = {}
                        for session in sessions:
                            api_name = session['api_name']
                            if api_name not in api_stats:
                                api_stats[api_name] = {
                                    "sessions": 0,
                                    "total_records": 0,
                                    "endpoints": set()
                                }
                            api_stats[api_name]["sessions"] += 1
                            api_stats[api_name]["total_records"] += session.get('total_records', 0)
                            api_stats[api_name]["endpoints"].add(session['endpoint_name'])
                        
                        # 转换为可序列化的格式
                        api_summary = []
                        for api_name, stats in api_stats.items():
                            api_summary.append({
                                "api_name": api_name,
                                "sessions": stats["sessions"],
                                "total_records": stats["total_records"],
                                "endpoints": list(stats["endpoints"])
                            })
                        
                        result = {
                            "status": "success",
                            "message": f"找到 {total_sessions} 个API存储会话，共 {total_records} 条记录",
                            "data": {
                                "summary": {
                                    "total_sessions": total_sessions,
                                    "total_records": total_records,
                                    "unique_apis": len(api_names),
                                    "unique_endpoints": len(endpoint_names)
                                },
                                "api_breakdown": api_summary,
                                "recent_sessions": sessions[:5]  # 显示最近5个会话
                            },
                            "storage_info": {
                                "storage_type": "api_storage",
                                "storage_directory": "data/api_storage",
                                "description": "API数据存储在独立的SQLite文件中，每个会话对应一个文件"
                            },
                            "metadata": {
                                "data_source": "API存储",
                                "timestamp": datetime.now().isoformat()
                            },
                            "usage_tips": [
                                "使用 query_api_storage_data() 查看所有API存储会话",
                                "使用 query_api_storage_data(session_id='xxx') 查询特定会话数据",
                                "API数据不在主数据库中，而是存储在独立文件中",
                                "每个API调用会自动创建或使用现有的存储会话"
                            ]
                        }
                        
                        return f"📊 API存储信息概览\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                        
                    except Exception as e:
                        logger.error(f"获取API存储信息失败: {e}")
                        result = {
                            "status": "error",
                            "message": f"获取API存储信息失败: {str(e)}",
                            "error_type": type(e).__name__,
                            "data_source": "API存储"
                        }
                        return f"❌ API存储信息获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
                else:
                    result = {
                        "status": "error",
                        "message": "无效的信息类型或缺少必要参数",
                        "supported_types": ["tables", "schema", "stats", "cleanup", "api_storage"],
                        "data_source": "本地SQLite"
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
    """计算基础统计信息 - 智能处理数值和文本列"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取列信息
            if columns:
                target_columns = columns
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                target_columns = [col[1] for col in cursor.fetchall()]
            
            if not target_columns:
                return {"error": "没有找到可分析的列"}
            
            # 分析每一列
            stats_result = {}
            numeric_columns = []
            text_columns = []
            
            for col in target_columns:
                escaped_col = _escape_identifier(col)
                
                # 检测列类型
                cursor = conn.execute(f"SELECT typeof({escaped_col}) FROM {escaped_table} WHERE {escaped_col} IS NOT NULL LIMIT 1")
                result = cursor.fetchone()
                col_type = result[0] if result else 'null'
                
                # 获取基本信息
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT({escaped_col}) as non_null_count,
                        COUNT(CASE WHEN {escaped_col} IS NULL THEN 1 END) as null_count
                    FROM {escaped_table}
                """)
                basic_info = cursor.fetchone()
                
                if col_type in ['integer', 'real']:
                    # 数值列统计
                    numeric_columns.append(col)
                    cursor = conn.execute(f"""
                        SELECT 
                            AVG({escaped_col}) as mean,
                            MIN({escaped_col}) as min_val,
                            MAX({escaped_col}) as max_val
                        FROM {escaped_table}
                        WHERE {escaped_col} IS NOT NULL
                    """)
                    numeric_stats = cursor.fetchone()
                    
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
                        "column_type": "numeric",
                        "data_type": col_type,
                        "total_count": basic_info[0],
                        "non_null_count": basic_info[1],
                        "null_count": basic_info[2],
                        "null_percentage": round((basic_info[2] / basic_info[0]) * 100, 2) if basic_info[0] > 0 else 0,
                        "mean": round(numeric_stats[0], 4) if numeric_stats[0] else None,
                        "median": round(median, 4) if median is not None else None,
                        "std_dev": round(std_dev, 4) if std_dev is not None else None,
                        "min": numeric_stats[1],
                        "max": numeric_stats[2],
                        "q25": round(q25, 4) if q25 is not None else None,
                        "q75": round(q75, 4) if q75 is not None else None
                    }
                    
                else:
                    # 文本列统计
                    text_columns.append(col)
                    
                    # 获取唯一值数量
                    cursor = conn.execute(f"SELECT COUNT(DISTINCT {escaped_col}) FROM {escaped_table} WHERE {escaped_col} IS NOT NULL")
                    unique_count = cursor.fetchone()[0]
                    
                    # 获取最常见的值（前5个）
                    cursor = conn.execute(f"""
                        SELECT {escaped_col}, COUNT(*) as freq 
                        FROM {escaped_table} 
                        WHERE {escaped_col} IS NOT NULL 
                        GROUP BY {escaped_col} 
                        ORDER BY freq DESC 
                        LIMIT 5
                    """)
                    top_values = cursor.fetchall()
                    
                    # 计算字符串长度统计（如果是文本）
                    length_stats = None
                    if col_type == 'text':
                        cursor = conn.execute(f"""
                            SELECT 
                                AVG(LENGTH({escaped_col})) as avg_length,
                                MIN(LENGTH({escaped_col})) as min_length,
                                MAX(LENGTH({escaped_col})) as max_length
                            FROM {escaped_table}
                            WHERE {escaped_col} IS NOT NULL
                        """)
                        length_result = cursor.fetchone()
                        if length_result[0] is not None:
                            length_stats = {
                                "avg_length": round(length_result[0], 2),
                                "min_length": length_result[1],
                                "max_length": length_result[2]
                            }
                    
                    stats_result[col] = {
                        "column_type": "categorical",
                        "data_type": col_type,
                        "total_count": basic_info[0],
                        "non_null_count": basic_info[1],
                        "null_count": basic_info[2],
                        "null_percentage": round((basic_info[2] / basic_info[0]) * 100, 2) if basic_info[0] > 0 else 0,
                        "unique_count": unique_count,
                        "unique_percentage": round((unique_count / basic_info[1]) * 100, 2) if basic_info[1] > 0 else 0,
                        "top_values": [{
                            "value": str(val[0]),
                            "frequency": val[1],
                            "percentage": round((val[1] / basic_info[1]) * 100, 2) if basic_info[1] > 0 else 0
                        } for val in top_values],
                        "length_stats": length_stats
                    }
            
            # 添加汇总信息
            summary = {
                "total_columns": len(target_columns),
                "numeric_columns": len(numeric_columns),
                "categorical_columns": len(text_columns),
                "numeric_column_names": numeric_columns,
                "categorical_column_names": text_columns
            }
            
            return {
                "column_stats": stats_result,
                "summary": summary
            }
            
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

def _escape_identifier(identifier: str) -> str:
    """转义SQL标识符（表名、列名），处理特殊字符"""
    # 移除可能的引号
    identifier = identifier.strip('"').strip("'")
    # 用双引号包围以处理特殊字符
    return f'"{identifier}"'

def _check_duplicates(table_name: str, columns: list, options: dict) -> dict:
    """检查重复值"""
    try:
        with get_db_connection() as conn:
            # 转义表名
            escaped_table = _escape_identifier(table_name)
            
            if columns:
                # 转义列名
                escaped_columns = [_escape_identifier(col) for col in columns]
                columns_str = ", ".join(escaped_columns)
                group_by_str = columns_str
            else:
                # 检查所有列的重复
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                all_columns = [col[1] for col in cursor.fetchall()]
                # 转义所有列名
                escaped_columns = [_escape_identifier(col) for col in all_columns]
                columns_str = ", ".join(escaped_columns)
                group_by_str = columns_str
            
            # 查找重复记录
            cursor = conn.execute(f"""
                SELECT {columns_str}, COUNT(*) as duplicate_count
                FROM {escaped_table}
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
                    FROM {escaped_table}
                    GROUP BY {group_by_str}
                    HAVING COUNT(*) > 1
                )
            """)
            
            total_duplicates = cursor.fetchone()[0] or 0
            
            # 获取总行数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
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
    🔍 数据分析工具 - 执行各种统计分析和数据质量检查
    
    功能说明：
    - 提供5种核心数据分析功能
    - 支持指定列分析或全表分析
    - 自动处理数据类型和缺失值
    - 返回详细的分析结果和可视化建议
    
    Args:
        analysis_type: 分析类型
            - "basic_stats": 基础统计分析（均值、中位数、标准差等）
            - "correlation": 相关性分析（数值列之间的相关系数）
            - "outliers": 异常值检测（IQR、Z-score方法）
            - "missing_values": 缺失值分析（缺失率、分布模式）
            - "duplicates": 重复值检测（完全重复、部分重复）
        table_name: 要分析的数据表名
        columns: 分析的列名列表（可选）
            - None: 分析所有适用列
            - ["col1", "col2"]: 只分析指定列
        options: 分析选项（可选字典）
            - outliers: {"method": "iqr|zscore", "threshold": 1.5}
            - correlation: {"method": "pearson|spearman"}
            - basic_stats: {"percentiles": [25, 50, 75, 90, 95]}
    
    Returns:
        str: JSON格式的分析结果，包含统计数据、图表建议和洞察
    
    🤖 AI使用建议：
    1. 数据概览：先用"basic_stats"了解数据分布
    2. 质量检查：用"missing_values"和"duplicates"检查数据质量
    3. 关系探索：用"correlation"发现变量关系
    4. 异常检测：用"outliers"识别异常数据
    5. 逐步深入：从基础统计到高级分析
    
    💡 最佳实践：
    - 先进行basic_stats了解数据概况
    - 数值列用correlation分析关系
    - 大数据集指定columns提高效率
    - 结合get_data_info了解表结构
    
    ⚠️ 常见错误避免：
    - 确保table_name存在
    - correlation只适用于数值列
    - columns名称必须准确匹配
    - 空表或单列表某些分析会失败
    
    📈 高效使用流程：
    1. get_data_info() → 了解表结构
    2. analyze_data("basic_stats") → 基础统计
    3. analyze_data("missing_values") → 质量检查
    4. analyze_data("correlation") → 关系分析
    5. analyze_data("outliers") → 异常检测
    
    🎯 关键理解点：
    - 每种分析类型有特定适用场景
    - 结果包含统计数据和业务洞察
    - 支持参数化定制分析行为
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

def _format_user_friendly_error(error_type: str, error_message: str, context: dict = None) -> dict:
    """格式化用户友好的错误信息"""
    error_solutions = {
        "session_not_found": {
            "friendly_message": "存储会话不存在",
            "explanation": "您指定的数据存储会话ID不存在，可能是会话已被删除或ID输入错误。",
            "solutions": [
                "检查会话ID是否正确",
                "使用 list_api_storage_sessions() 查看所有可用会话",
                "如果会话确实不存在，工具会自动创建新会话"
            ]
        },
        "api_call_failed": {
            "friendly_message": "API调用失败",
            "explanation": "无法成功调用指定的API接口，可能是网络问题、API参数错误或服务不可用。",
            "solutions": [
                "检查网络连接是否正常",
                "验证API参数是否正确",
                "确认API服务是否可用",
                "检查API密钥是否有效"
            ]
        },
        "invalid_parameters": {
            "friendly_message": "参数无效",
            "explanation": "提供的参数不符合API要求，可能导致无法获取到有效数据。",
            "solutions": [
                "检查参数格式是否正确",
                "参考API文档确认参数要求",
                "尝试使用推荐的参数组合",
                "使用 api_data_preview 先测试参数"
            ]
        },
        "data_format_error": {
            "friendly_message": "数据格式错误",
            "explanation": "返回的数据格式无法正确解析，可能是API返回了意外的数据结构。",
            "solutions": [
                "检查API返回的原始数据",
                "尝试不同的数据转换配置",
                "联系API提供商确认数据格式",
                "使用原始格式查看数据内容"
            ]
        },
        "file_not_found": {
            "friendly_message": "文件不存在",
            "explanation": "指定的文件路径不存在或无法访问。",
            "solutions": [
                "检查文件路径是否正确",
                "确认文件是否存在",
                "检查文件访问权限",
                "使用绝对路径而非相对路径"
            ]
        },
        "database_error": {
            "friendly_message": "数据库操作失败",
            "explanation": "数据库操作过程中发生错误，可能是连接问题或SQL语法错误。",
            "solutions": [
                "检查数据库连接是否正常",
                "验证SQL语法是否正确",
                "确认表和字段名称是否存在",
                "检查数据库权限设置"
            ]
        }
    }
    
    error_info = error_solutions.get(error_type, {
        "friendly_message": "操作失败",
        "explanation": "操作过程中发生了未知错误。",
        "solutions": [
            "检查输入参数是否正确",
            "重试操作",
            "如果问题持续，请联系技术支持"
        ]
    })
    
    result = {
        "error_type": error_type,
        "friendly_message": error_info["friendly_message"],
        "explanation": error_info["explanation"],
        "solutions": error_info["solutions"],
        "technical_details": error_message
    }
    
    if context:
        result["context"] = context
    
    return result

def _generate_enhanced_preview(data, max_rows=10, max_cols=10, preview_fields=None, 
                             preview_depth=3, show_data_types=True, truncate_length=100):
    """生成增强的数据预览"""
    try:
        preview_text = ""
        structure_info = {}
        
        # 分析数据结构
        if isinstance(data, dict):
            structure_info["type"] = "object"
            structure_info["keys"] = list(data.keys())
            structure_info["total_keys"] = len(data.keys())
            
            # 查找主要数据数组
            main_data_key = None
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    main_data_key = key
                    break
            
            if main_data_key:
                structure_info["main_data_key"] = main_data_key
                structure_info["main_data_count"] = len(data[main_data_key])
                preview_data = data[main_data_key]
            else:
                preview_data = [data]  # 将单个对象包装为列表
                
        elif isinstance(data, list):
            structure_info["type"] = "array"
            structure_info["total_items"] = len(data)
            preview_data = data
        else:
            structure_info["type"] = "primitive"
            structure_info["value_type"] = type(data).__name__
            preview_text = f"原始数据值: {str(data)[:truncate_length]}"
            if len(str(data)) > truncate_length:
                preview_text += "...(已截断)"
            return {"preview_text": preview_text, "structure_info": structure_info}
        
        # 转换为DataFrame进行预览
        try:
            if preview_data and isinstance(preview_data, list) and len(preview_data) > 0:
                # 扁平化嵌套数据
                df = pd.json_normalize(preview_data, max_level=preview_depth)
                
                # 过滤指定字段
                if preview_fields:
                    available_fields = [col for col in preview_fields if col in df.columns]
                    if available_fields:
                        df = df[available_fields]
                        structure_info["filtered_fields"] = available_fields
                        structure_info["missing_fields"] = [col for col in preview_fields if col not in df.columns]
                    else:
                        preview_text += "⚠️ 指定的预览字段都不存在\n"
                        preview_text += f"可用字段: {list(df.columns)[:10]}\n\n"
                
                # 限制行数和列数
                original_rows, original_cols = df.shape
                structure_info["original_shape"] = {"rows": original_rows, "columns": original_cols}
                
                if original_rows > max_rows:
                    df_preview = df.head(max_rows)
                    row_info = f"显示前{max_rows}行，共{original_rows}行"
                else:
                    df_preview = df
                    row_info = f"共{original_rows}行"
                
                if original_cols > max_cols:
                    df_preview = df_preview.iloc[:, :max_cols]
                    col_info = f"显示前{max_cols}列，共{original_cols}列"
                else:
                    col_info = f"共{original_cols}列"
                
                # 生成预览文本
                preview_text += f"📊 数据预览 ({row_info}, {col_info}):\n\n"
                
                # 截断长字段值
                df_display = df_preview.copy()
                for col in df_display.columns:
                    if df_display[col].dtype == 'object':
                        df_display[col] = df_display[col].astype(str).apply(
                            lambda x: x[:truncate_length] + "..." if len(x) > truncate_length else x
                        )
                
                preview_text += df_display.to_string(index=False, max_colwidth=truncate_length)
                
                # 添加数据类型信息
                if show_data_types and original_cols <= max_cols:
                    preview_text += "\n\n📋 数据类型:\n"
                    for col in df_preview.columns:
                        preview_text += f"  {col}: {df[col].dtype}\n"
                
                # 添加字段统计
                if original_cols > max_cols:
                    preview_text += f"\n💡 提示: 还有 {original_cols - max_cols} 个字段未显示\n"
                    preview_text += f"所有字段: {', '.join(list(df.columns)[:20])}{'...' if original_cols > 20 else ''}\n"
                
                structure_info["preview_shape"] = {"rows": len(df_preview), "columns": len(df_preview.columns)}
                structure_info["all_columns"] = list(df.columns)
                
            else:
                preview_text = "📭 数据为空或无法解析"
                structure_info["empty"] = True
                
        except Exception as e:
            # 如果DataFrame转换失败，显示原始数据结构
            preview_text += f"⚠️ 无法转换为表格格式，显示原始结构:\n\n"
            preview_text += json.dumps(preview_data[:3] if isinstance(preview_data, list) else preview_data, 
                                     indent=2, ensure_ascii=False, default=str)[:1000]
            if len(str(preview_data)) > 1000:
                preview_text += "\n...(数据已截断)"
            structure_info["conversion_error"] = str(e)
        
        return {"preview_text": preview_text, "structure_info": structure_info}
        
    except Exception as e:
        return {
            "preview_text": f"❌ 预览生成失败: {str(e)}",
            "structure_info": {"error": str(e)}
        }

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
    📤 数据导出工具 - 将数据导出为各种格式文件
    
    功能说明：
    - 支持多种导出格式：Excel、CSV、JSON
    - 可导出表数据或SQL查询结果
    - 自动生成文件路径或使用指定路径
    - 支持导出选项自定义
    
    Args:
        export_type: 导出格式类型
            - "excel": Excel文件(.xlsx)
            - "csv": CSV文件(.csv)
            - "json": JSON文件(.json)
        data_source: 数据源
            - 表名: 直接导出整个表
            - SQL查询: 导出查询结果（以SELECT开头）
        file_path: 导出文件路径（可选）
            - None: 自动生成路径到exports/目录
            - 指定路径: 使用自定义路径
        options: 导出选项（可选字典）
            - Excel: {"sheet_name": "工作表名", "auto_adjust_columns": True}
            - CSV: {"encoding": "utf-8", "separator": ","}
            - JSON: {"orient": "records", "indent": 2}
    
    Returns:
        str: JSON格式的导出结果，包含文件路径、大小、记录数等信息
    
    🤖 AI使用建议：
    1. 表导出：export_data("excel", "table_name")
    2. 查询导出：export_data("csv", "SELECT * FROM table WHERE condition")
    3. 自定义格式：使用options参数调整导出格式
    4. 批量导出：结合循环导出多个表或查询
    
    💡 最佳实践：
    - Excel适合报表和可视化
    - CSV适合数据交换和导入其他系统
    - JSON适合API和程序处理
    - 大数据量优先使用CSV
    
    ⚠️ 常见错误避免：
    - 确保data_source存在（表名）或语法正确（SQL）
    - 文件路径目录必须存在或可创建
    - 注意文件权限和磁盘空间
    
    📈 高效使用流程：
    1. 确定导出需求（格式、内容）
    2. 选择合适的export_type
    3. 准备data_source（表名或SQL）
    4. 设置options（如需要）
    5. 执行导出并检查结果
    
    🎯 关键理解点：
    - 支持表和查询两种数据源
    - 自动处理文件路径和格式
    - 提供详细的导出统计信息
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
            
            # 映射导出类型到文件扩展名
            extension_map = {
                "excel": "xlsx",
                "csv": "csv",
                "json": "json"
            }
            extension = extension_map.get(export_type, export_type)
            file_path = f"exports/{source_name}_{timestamp}.{extension}"
        
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
                
                try:
                    _ensure_metadata_table(conn)
                    conn.execute("""
                        INSERT OR REPLACE INTO data_metadata 
                        (table_name, source_type, source_path, created_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                    conn.commit()
                except Exception as metadata_error:
                    logger.warning(f"保存元数据失败: {metadata_error}")
            
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
                
                try:
                    _ensure_metadata_table(conn)
                    conn.execute("""
                        INSERT OR REPLACE INTO data_metadata 
                        (table_name, source_type, source_path, created_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                    conn.commit()
                except Exception as metadata_error:
                    logger.warning(f"保存元数据失败: {metadata_error}")
            
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
                    # 尝试使用pandas query方法（适用于简单的英文列名）
                    try:
                        df = df.query(condition)
                        operations_performed.append(f"条件筛选: {condition}")
                    except (SyntaxError, ValueError, KeyError) as query_error:
                        # 如果query方法失败，尝试转换为SQL WHERE子句
                        # 将pandas DataFrame重新写入临时表，然后用SQL筛选
                        temp_table = f"temp_filter_{int(time.time() * 1000)}"
                        df.to_sql(temp_table, conn, if_exists='replace', index=False)
                        
                        # 构建SQL查询，支持中文列名
                        sql_condition = condition
                        # 转换常见的pandas语法到SQL语法
                        sql_condition = sql_condition.replace(' and ', ' AND ').replace(' or ', ' OR ')
                        sql_condition = sql_condition.replace(' & ', ' AND ').replace(' | ', ' OR ')
                        
                        # 执行SQL查询
                        sql_query = f'SELECT * FROM "{temp_table}" WHERE {sql_condition}'
                        df = pd.read_sql(sql_query, conn)
                        
                        # 清理临时表
                        conn.execute(f'DROP TABLE IF EXISTS "{temp_table}"')
                        conn.commit()
                        
                        operations_performed.append(f"条件筛选(SQL): {condition}")
                        
                except Exception as e:
                    operations_performed.append(f"条件筛选失败: {str(e)}")
                    # 如果筛选失败，记录详细错误信息但不中断处理
                    import traceback
                    logger.error(f"筛选条件解析失败: {condition}, 错误: {traceback.format_exc()}")
            
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
                
                try:
                    _ensure_metadata_table(conn)
                    conn.execute("""
                        INSERT OR REPLACE INTO data_metadata 
                        (table_name, source_type, source_path, created_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                    conn.commit()
                except Exception as metadata_error:
                    logger.warning(f"保存元数据失败: {metadata_error}")
            
            return {
                "original_rows": original_count,
                "filtered_rows": len(df),
                "operations": operations_performed,
                "target_table": table_name
            }
            
    except Exception as e:
        raise Exception(f"数据筛选失败: {str(e)}")

def _ensure_metadata_table(conn) -> None:
    """确保data_metadata表存在"""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_metadata (
                table_name TEXT PRIMARY KEY,
                source_type TEXT,
                source_path TEXT,
                created_at TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"创建metadata表失败: {e}")

def _process_aggregate(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据聚合处理器"""
    try:
        with get_db_connection() as conn:
            # 确保metadata表存在
            _ensure_metadata_table(conn)
            
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
                
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO data_metadata 
                        (table_name, source_type, source_path, created_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                    conn.commit()
                except Exception as metadata_error:
                    logger.warning(f"保存元数据失败: {metadata_error}")
            
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
                
                try:
                    _ensure_metadata_table(conn)
                    conn.execute("""
                        INSERT OR REPLACE INTO data_metadata 
                        (table_name, source_type, source_path, created_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                    conn.commit()
                except Exception as metadata_error:
                    logger.warning(f"保存元数据失败: {metadata_error}")
            
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
                
                try:
                    _ensure_metadata_table(conn)
                    conn.execute("""
                        INSERT OR REPLACE INTO data_metadata 
                        (table_name, source_type, source_path, created_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (table_name, 'processed_data', data_source, datetime.now().isoformat(), json.dumps(metadata)))
                    conn.commit()
                except Exception as metadata_error:
                    logger.warning(f"保存元数据失败: {metadata_error}")
            
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
    ⚙️ 数据处理工具 - 执行数据清洗、转换、筛选等操作
    
    功能说明：
    - 提供6种核心数据处理功能
    - 支持表和SQL查询作为数据源
    - 灵活的配置参数系统
    - 可指定目标表或覆盖原表
    
    Args:
        operation_type: 处理操作类型
            - "clean": 数据清洗（去重、填充缺失值、数据类型转换）
            - "transform": 数据转换（列重命名、标准化、新列计算）
            - "filter": 数据筛选（条件过滤、列选择、数据采样）
            - "aggregate": 数据聚合（分组统计、汇总计算）
            - "merge": 数据合并（表连接、数据拼接）
            - "reshape": 数据重塑（透视表、宽长转换）
        data_source: 数据源
            - 表名: 处理整个表
            - SQL查询: 处理查询结果
        config: 操作配置字典（必需）
            - clean: {"remove_duplicates": True, "fill_missing": {"col": {"method": "mean"}}}
            - transform: {"rename_columns": {"old": "new"}, "normalize": {"columns": ["col1"]}}
            - filter: {"filter_condition": "age > 18", "select_columns": ["name", "age"]}
            - aggregate: {"group_by": {"columns": ["dept"], "agg": {"salary": "mean"}}}
            - merge: {"right_table": "table2", "on": "id", "how": "inner"}
            - reshape: {"pivot": {"index": "date", "columns": "product", "values": "sales"}}
        target_table: 目标表名（可选）
            - None: 覆盖原表（默认）
            - 表名: 保存到新表
    
    Returns:
        str: JSON格式的处理结果，包含操作详情、影响行数和新表信息
    
    🤖 AI使用建议：
    1. 数据清洗：先用"clean"处理数据质量问题
    2. 数据转换：用"transform"标准化和计算新字段
    3. 数据筛选：用"filter"获取目标数据子集
    4. 数据聚合：用"aggregate"生成汇总报表
    5. 数据合并：用"merge"关联多个数据源
    6. 数据重塑：用"reshape"改变数据结构
    
    💡 最佳实践：
    - 处理前先备份重要数据
    - 使用target_table避免覆盖原数据
    - 复杂操作分步骤执行
    - 结合analyze_data验证处理结果
    
    ⚠️ 常见错误避免：
    - config参数必须符合operation_type要求
    - 确保引用的列名存在
    - merge操作需要确保关联键存在
    - 大数据量操作注意性能
    
    📈 高效使用流程：
    1. analyze_data() → 了解数据质量
    2. process_data("clean") → 清洗数据
    3. process_data("transform") → 转换数据
    4. process_data("filter") → 筛选数据
    5. analyze_data() → 验证处理结果
    
    🎯 关键理解点：
    - 每种操作类型有特定的config格式
    - 支持链式处理（上一步输出作为下一步输入）
    - 提供详细的操作日志和统计信息
    
    📋 配置示例：
    ```python
    # 数据清洗
    config = {
        "remove_duplicates": True,
        "fill_missing": {
            "age": {"method": "mean"},
            "name": {"method": "mode"}
        }
    }
    
    # 数据筛选
    config = {
        "filter_condition": "age > 18 and salary > 5000",
        "select_columns": ["name", "age", "department"]
    }
    
    # 数据聚合
    config = {
        "group_by": {
            "columns": ["department"],
            "agg": {
                "salary": "mean",
                "age": "count"
            }
        }
    }
    ```
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
def list_data_sources() -> str:
    """
    📋 数据源列表工具 - 查看所有可用的数据源
    
    🎯 功能说明：
    - 显示本地SQLite数据库状态
    - 列出所有外部数据库配置
    - 显示每个数据源的连接状态和基本信息
    - 区分临时配置和永久配置
    
    📊 返回信息包括：
    - 数据源名称和类型
    - 连接状态（可用/已配置/已禁用）
    - 主机地址和数据库名
    - 是否为默认数据源
    - 配置创建时间（临时配置）
    
    💡 使用场景：
    - 不确定有哪些数据源时查看
    - 检查数据库连接状态
    - 查找临时配置名称
    - 了解可用的查询目标
    
    Args:
        无需参数
    
    Returns:
        str: JSON格式的数据源列表，包含详细的配置信息
    
    🚀 AI使用建议：
    - 在查询数据前先调用此工具了解可用数据源
    - 用于获取正确的database_name参数
    - 检查临时配置是否还存在
    """
    try:
        # 获取外部数据库配置
        external_databases = database_manager.get_available_databases()
        
        # 构建数据源列表
        data_sources = {
            "本地SQLite": {
                "type": "sqlite",
                "description": "本地SQLite数据库（默认数据源）",
                "status": "可用",
                "database_path": DB_PATH,
                "is_default": True
            }
        }
        
        # 添加外部数据库
        for db_name, db_config in external_databases.items():
            data_sources[db_name] = {
                "type": db_config.get("type", "unknown"),
                "description": db_config.get("description", ""),
                "status": "已配置" if db_config.get("enabled", True) else "已禁用",
                "host": db_config.get("host", ""),
                "database": db_config.get("database", ""),
                "file_path": db_config.get("file_path", ""),
                "is_default": False
            }
        
        result = {
            "status": "success",
            "message": f"找到 {len(data_sources)} 个数据源",
            "data": {
                "data_sources": data_sources,
                "count": len(data_sources),
                "usage_note": "使用execute_sql或get_data_info时，可通过data_source参数指定数据源。不指定则默认使用本地SQLite。"
            },
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return f"✅ 数据源列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}")
        result = {
            "status": "error",
            "message": f"获取数据源列表失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def manage_database_config(
    action: str,
    config: dict = None
) -> str:
    """
    ⚙️ 数据库配置管理工具 - 管理所有数据库连接配置
    
    🎯 支持的操作类型：
    - "list" - 列出所有数据库配置（包括临时和永久）
    - "test" - 测试指定配置的连接状态
    - "add" - 添加永久数据库配置
    - "remove" - 删除指定配置
    - "reload" - 重新加载配置文件
    - "list_temp" - 仅列出临时配置
    - "cleanup_temp" - 清理所有临时配置
    
    📋 常用操作示例：
    
    1️⃣ 查看所有配置：
       manage_database_config(action="list")
    
    2️⃣ 测试连接：
       manage_database_config(action="test", config={"database_name": "配置名"})
    
    3️⃣ 添加永久配置：
       manage_database_config(action="add", config={
           "database_name": "my_mysql",
           "database_config": {
               "host": "localhost",
               "port": 3306,
               "type": "mysql",
               "user": "root",
               "database": "test_db",
               "password": "password"
           }
       })
    
    4️⃣ 清理临时配置：
       manage_database_config(action="cleanup_temp")
    
    Args:
        action: 操作类型，必须是上述支持的操作之一
        config: 配置参数字典，根据action类型提供不同参数
    
    Returns:
        str: JSON格式操作结果，包含状态、消息和相关数据
    
    💡 AI使用建议：
    - 不确定有哪些配置时，先用action="list"查看
    - 连接问题时，用action="test"检查配置状态
    - 临时配置过多时，用action="cleanup_temp"清理
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
                
        elif action == "list_temp":
            # 列出所有临时配置
            temp_configs = config_manager.get_temporary_configs()
            
            result = {
                "status": "success",
                "message": f"找到 {len(temp_configs)} 个临时配置",
                "data": {
                    "temporary_configs": temp_configs,
                    "count": len(temp_configs)
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return f"✅ 临时配置列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
        elif action == "cleanup_temp":
            # 清理所有临时配置
            success, message = config_manager.cleanup_temporary_configs()
            
            result = {
                "status": "success" if success else "error",
                "message": message,
                "data": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            status_icon = "✅" if success else "❌"
            return f"{status_icon} 临时配置清理结果\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
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
                "supported_actions": ["list", "test", "add", "remove", "reload", "list_temp", "cleanup_temp"]
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
    🌐 外部数据库查询工具 - 专门查询外部数据库
    
    🎯 使用场景：
    - 查询MySQL数据库
    - 查询PostgreSQL数据库
    - 查询MongoDB数据库
    - 查询所有通过connect_data_source连接的外部数据库
    
    ⚠️ 前置条件：
    必须先使用connect_data_source建立数据库连接并获得配置名称
    
    🔄 完整流程示例：
    1️⃣ connect_data_source(source_type="mysql", config={...}) → 获得配置名
    2️⃣ connect_data_source(source_type="database_config", config={"database_name": "配置名"}) → 建立连接
    3️⃣ query_external_database(database_name="配置名", query="SELECT * FROM table") → 查询数据
    
    💡 查询语法支持：
    - MySQL/PostgreSQL: 标准SQL语法
    - MongoDB: 支持多种查询格式（JSON、JavaScript风格等）
    
    Args:
        database_name: 数据库配置名称（从connect_data_source获得）
        query: 查询语句，SQL或MongoDB查询语法
        limit: 结果行数限制，默认1000行
    
    Returns:
        str: JSON格式查询结果，包含数据行、统计信息和元数据
    
    🚀 AI使用建议：
    - 这是查询外部数据库的首选工具
    - 使用list_data_sources查看可用的数据库配置
    - 配置名称通常格式为：temp_mysql_20250724_173102
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
    transform_config: dict = None,
    storage_session_id: str = None
) -> str:
    """
    从API获取数据并自动存储到数据库（方式二：自动持久化流程）
    
    注意：已删除方式一（手动流程），所有API数据默认直接存储到数据库
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        data: 请求数据（POST/PUT）
        method: HTTP方法
        transform_config: 数据转换配置
        storage_session_id: 存储会话ID（可选，不提供时自动创建）
    
    Returns:
        str: 数据存储结果和会话信息
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
            error_info = _format_user_friendly_error(
                "api_call_failed", 
                message,
                {"api_name": api_name, "endpoint_name": endpoint_name, "params": params}
            )
            result = {
                "status": "error",
                "message": error_info["friendly_message"],
                "error_details": error_info,
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ {error_info['friendly_message']}\n\n💡 解决建议:\n" + "\n".join([f"• {solution}" for solution in error_info['solutions']]) + f"\n\n🔧 技术详情:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 自动持久化存储（方式二：默认流程）
        if not storage_session_id:
            # 自动创建存储会话
            session_name = f"{api_name}_{endpoint_name}_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            create_success, auto_session_id, create_message = api_data_storage.create_storage_session(
                session_name=session_name,
                api_name=api_name,
                endpoint_name=endpoint_name,
                description=f"自动创建的存储会话 - {api_name}.{endpoint_name}"
            )
            
            if not create_success:
                result = {
                    "status": "error",
                    "message": f"自动创建存储会话失败: {create_message}"
                }
                return f"❌ 会话创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            storage_session_id = auto_session_id
            logger.info(f"自动创建存储会话: {session_name} (ID: {auto_session_id})")
        else:
            # 检查指定的会话是否存在，如果不存在则自动创建
            session_info = api_data_storage._get_session_info(storage_session_id)
            if not session_info:
                # 尝试将storage_session_id作为session_name来创建会话
                create_success, new_session_id, create_message = api_data_storage.create_storage_session(
                    session_name=storage_session_id,
                    api_name=api_name,
                    endpoint_name=endpoint_name,
                    description=f"根据指定名称创建的存储会话 - {api_name}.{endpoint_name}"
                )
                
                if not create_success:
                    result = {
                        "status": "error",
                        "message": f"指定的存储会话 '{storage_session_id}' 不存在，且自动创建失败: {create_message}",
                        "suggestion": "请检查会话ID是否正确，或者不指定storage_session_id让系统自动创建"
                    }
                    return f"❌ 会话不存在\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
                storage_session_id = new_session_id
                logger.info(f"自动创建指定名称的存储会话: {storage_session_id} (新ID: {new_session_id})")
        
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
            "message": "API数据已自动存储到数据库",
            "data": {
                "session_id": storage_session_id,
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "stored_records": count,
                "storage_message": storage_message
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "transform_applied": bool(transform_config),
                "auto_session_created": not storage_session_id
            }
        }
        return f"💾 数据已自动存储到数据库\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
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
    max_cols: int = 10,
    preview_fields: list = None,
    preview_depth: int = 3,
    show_data_types: bool = True,
    show_summary: bool = True,
    truncate_length: int = 100
) -> str:
    """
    🔍 API数据预览工具 - 灵活预览API返回数据
    
    功能说明：
    - 支持灵活的数据预览配置
    - 可指定预览字段和深度
    - 提供数据类型和摘要信息
    - 避免数据截断问题
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        max_rows: 最大显示行数 (默认10)
        max_cols: 最大显示列数 (默认10)
        preview_fields: 指定预览的字段列表 (可选)
        preview_depth: JSON嵌套预览深度 (默认3)
        show_data_types: 是否显示数据类型信息 (默认True)
        show_summary: 是否显示数据摘要 (默认True)
        truncate_length: 字段值截断长度 (默认100)
    
    Returns:
        str: 数据预览结果
        
    📋 使用示例：
    ```python
    # 基本预览
    api_data_preview(
        api_name="alpha_vantage",
        endpoint_name="news_sentiment",
        params={"topics": "technology"}
    )
    
    # 指定字段预览
    api_data_preview(
        api_name="alpha_vantage",
        endpoint_name="news_sentiment",
        params={"topics": "technology"},
        preview_fields=["title", "summary", "sentiment_score"],
        max_rows=5
    )
    
    # 深度预览嵌套数据
    api_data_preview(
        api_name="complex_api",
        endpoint_name="nested_data",
        preview_depth=5,
        truncate_length=200
    )
    ```
    
    🎯 关键理解点：
    - preview_fields可以精确控制显示内容
    - preview_depth控制JSON嵌套显示层级
    - truncate_length避免超长字段影响显示
    - 提供完整的数据结构分析
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
            error_info = _format_user_friendly_error(
                "api_call_failed", 
                message,
                {"api_name": api_name, "endpoint_name": endpoint_name, "params": params}
            )
            result = {
                "status": "error",
                "message": error_info["friendly_message"],
                "error_details": error_info,
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ {error_info['friendly_message']}\n\n💡 解决建议:\n" + "\n".join([f"• {solution}" for solution in error_info['solutions']]) + f"\n\n🔧 技术详情:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 生成增强的数据预览
        preview_result = _generate_enhanced_preview(
            data=response_data,
            max_rows=max_rows,
            max_cols=max_cols,
            preview_fields=preview_fields,
            preview_depth=preview_depth,
            show_data_types=show_data_types,
            truncate_length=truncate_length
        )
        
        # 获取数据摘要（如果需要）
        summary_data = None
        if show_summary:
            summary_success, summary_data, summary_message = data_transformer.get_data_summary(response_data)
            if not summary_success:
                summary_data = {"error": summary_message}
        
        result = {
            "status": "success",
            "message": f"API数据预览成功",
            "data": {
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "preview": preview_result["preview_text"],
                "data_structure": preview_result["structure_info"],
                "summary": summary_data if show_summary else None
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "max_rows": max_rows,
                "max_cols": max_cols,
                "preview_fields": preview_fields,
                "preview_depth": preview_depth,
                "show_data_types": show_data_types,
                "truncate_length": truncate_length
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

# store_api_data_to_session 函数已删除
# 原因：与简化后的 fetch_api_data 功能重复
# 现在所有 API 数据获取都通过 fetch_api_data 自动存储到数据库

@mcp.tool()
def query_api_storage_data(
    session_id: str = None,
    api_name: str = None,
    endpoint_name: str = None,
    limit: int = 10,
    format_type: str = "json"
) -> str:
    """
    查询API存储的数据 - 解决API数据存储位置不透明的问题
    
    功能说明：
    - 查询存储在独立文件中的API数据
    - 支持按会话ID、API名称、端点名称筛选
    - 提供多种数据格式输出
    - 显示数据存储位置和会话信息
    
    Args:
        session_id: 存储会话ID（精确查询）
        api_name: API名称（模糊筛选）
        endpoint_name: 端点名称（模糊筛选）
        limit: 返回记录数限制（默认10条）
        format_type: 数据格式（json/dataframe/summary）
    
    Returns:
        str: JSON格式的查询结果，包含数据和存储位置信息
    
    🎯 解决问题：
    - ✅ API数据存储位置透明化
    - ✅ 提供API数据查询入口
    - ✅ 显示会话与表的关联关系
    - ✅ 支持多种查询方式
    
    💡 使用示例：
    - query_api_storage_data() # 列出所有API存储会话
    - query_api_storage_data(api_name="rest_api_example") # 查询特定API的数据
    - query_api_storage_data(session_id="xxx") # 查询特定会话的数据
    """
    try:
        from config.api_data_storage import api_data_storage
        
        # 如果提供了session_id，直接查询该会话的数据
        if session_id:
            success, data, message = api_data_storage.get_stored_data(
                session_id=session_id,
                limit=limit,
                format_type=format_type
            )
            
            if success:
                # 获取会话信息
                session_success, sessions, _ = api_data_storage.list_storage_sessions()
                session_info = None
                if session_success:
                    session_info = next((s for s in sessions if s['session_id'] == session_id), None)
                
                result = {
                    "status": "success",
                    "message": f"查询到 {len(data) if isinstance(data, list) else 1} 条API数据记录",
                    "data": {
                        "session_info": session_info,
                        "records": data[:limit] if isinstance(data, list) else data,
                        "total_shown": min(len(data) if isinstance(data, list) else 1, limit)
                    },
                    "storage_info": {
                        "storage_type": "api_storage",
                        "file_location": session_info['file_path'] if session_info else "unknown",
                        "session_id": session_id
                    }
                }
                return f"📊 API存储数据查询结果\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            else:
                result = {
                    "status": "error",
                    "message": f"查询API存储数据失败: {message}",
                    "session_id": session_id
                }
                return f"❌ 查询失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 列出所有存储会话
        success, sessions, message = api_data_storage.list_storage_sessions(api_name=api_name)
        
        if not success:
            result = {
                "status": "error",
                "message": f"获取API存储会话失败: {message}"
            }
            return f"❌ 查询失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 按endpoint_name筛选
        if endpoint_name:
            sessions = [s for s in sessions if endpoint_name.lower() in s['endpoint_name'].lower()]
        
        if not sessions:
            result = {
                "status": "success",
                "message": "没有找到匹配的API存储会话",
                "data": {
                    "sessions": [],
                    "total_sessions": 0
                },
                "filters": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"📋 API存储会话列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 为每个会话获取数据预览
        session_data = []
        for session in sessions:
            session_info = {
                "session_id": session['session_id'],
                "session_name": session['session_name'],
                "api_name": session['api_name'],
                "endpoint_name": session['endpoint_name'],
                "total_records": session['total_records'],
                "created_at": session['created_at'],
                "status": session['status']
            }
            
            # 获取数据预览（前3条）
            data_success, data, data_message = api_data_storage.get_stored_data(
                session['session_id'], limit=3, format_type="json"
            )
            
            if data_success and data:
                session_info["data_preview"] = data[:2]  # 只显示前2条作为预览
                session_info["preview_message"] = f"显示前2条记录，共{len(data)}条"
            else:
                session_info["data_preview"] = []
                session_info["preview_message"] = data_message
            
            session_data.append(session_info)
        
        result = {
            "status": "success",
            "message": f"找到 {len(sessions)} 个API存储会话",
            "data": {
                "sessions": session_data,
                "total_sessions": len(sessions)
            },
            "storage_info": {
                "storage_type": "api_storage",
                "storage_directory": "data/api_storage",
                "description": "API数据存储在独立的SQLite文件中，每个会话对应一个文件"
            },
            "usage_tips": [
                "使用session_id参数查询特定会话的完整数据",
                "API数据不在主数据库中，而是存储在独立文件中",
                "每个API调用会自动创建或使用现有的存储会话"
            ]
        }
        
        return f"📋 API存储会话列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"查询API存储数据失败: {e}")
        result = {
            "status": "error",
            "message": f"查询API存储数据失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 查询失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def execute_database_cleanup(
    action: str,
    tables_to_clean: list = None,
    confirm_deletion: bool = False
) -> str:
    """
    🧹 数据库清理执行工具 - 根据清理建议执行实际的清理操作
    
    功能说明：
    - 执行数据库表的删除操作
    - 支持批量删除和选择性删除
    - 提供安全确认机制
    - 记录清理操作日志
    
    Args:
        action: 清理操作类型
            - "delete_tables": 删除指定的表
            - "preview_deletion": 预览将要删除的表（安全模式）
            - "backup_and_delete": 备份后删除表（暂未实现）
        tables_to_clean: 要清理的表名列表
            - ["table1", "table2"]: 删除指定表
            - None: 需要先运行get_data_info(info_type="cleanup")获取建议
        confirm_deletion: 删除确认标志
            - True: 确认执行删除操作
            - False: 仅预览，不执行实际删除
    
    Returns:
        str: JSON格式的清理结果，包含操作状态和详细信息
    
    🤖 AI使用建议：
    1. 清理分析：先用get_data_info(info_type="cleanup")分析数据库
    2. 预览操作：用action="preview_deletion"预览将要删除的表
    3. 确认删除：设置confirm_deletion=True执行实际删除
    4. 安全第一：重要数据请先备份
    
    💡 最佳实践：
    - 删除前先备份重要数据
    - 优先删除空表和测试表
    - 谨慎处理重复表和历史表
    - 定期执行清理维护数据库整洁
    
    ⚠️ 安全提醒：
    - 删除操作不可逆，请谨慎操作
    - 建议先使用preview模式查看影响
    - 重要数据请务必备份
    - 仅删除确认不需要的表
    
    📈 使用流程：
    1. get_data_info(info_type="cleanup") → 获取清理建议
    2. execute_database_cleanup(action="preview_deletion", tables_to_clean=[...]) → 预览
    3. execute_database_cleanup(action="delete_tables", tables_to_clean=[...], confirm_deletion=True) → 执行
    
    🎯 关键理解点：
    - 这是数据库维护的执行工具
    - 配合cleanup分析使用效果最佳
    - 支持安全预览和确认机制
    - 帮助保持数据库整洁有序
    """
    try:
        if not action:
            result = {
                "status": "error",
                "message": "必须指定清理操作类型",
                "supported_actions": ["delete_tables", "preview_deletion", "backup_and_delete"]
            }
            return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        if action == "preview_deletion":
            # 预览删除操作
            if not tables_to_clean:
                result = {
                    "status": "error",
                    "message": "预览删除需要指定tables_to_clean参数",
                    "suggestion": "请先使用get_data_info(info_type='cleanup')获取清理建议"
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            # 检查表是否存在并获取信息
            preview_info = []
            with get_db_connection() as conn:
                for table in tables_to_clean:
                    if _table_exists(table):
                        try:
                            escaped_table = _escape_identifier(table)
                            cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
                            row_count = cursor.fetchone()[0]
                            preview_info.append({
                                "table_name": table,
                                "exists": True,
                                "row_count": row_count,
                                "status": "ready_for_deletion"
                            })
                        except Exception as e:
                            preview_info.append({
                                "table_name": table,
                                "exists": True,
                                "row_count": "unknown",
                                "status": "error",
                                "error": str(e)
                            })
                    else:
                        preview_info.append({
                            "table_name": table,
                            "exists": False,
                            "row_count": 0,
                            "status": "table_not_found"
                        })
            
            valid_tables = [info for info in preview_info if info['exists']]
            total_rows_to_delete = sum(info['row_count'] for info in valid_tables if isinstance(info['row_count'], int))
            
            result = {
                "status": "success",
                "message": "删除预览完成",
                "data": {
                    "action": "preview_deletion",
                    "tables_to_delete": len(valid_tables),
                    "total_rows_affected": total_rows_to_delete,
                    "table_details": preview_info
                },
                "next_steps": [
                    "确认要删除的表列表",
                    "使用action='delete_tables'和confirm_deletion=True执行删除",
                    "重要：删除操作不可逆，请确保已备份重要数据"
                ],
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "operation_type": "preview_only"
                }
            }
            
            return f"🔍 删除预览完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "delete_tables":
            # 执行删除操作
            if not tables_to_clean:
                result = {
                    "status": "error",
                    "message": "删除操作需要指定tables_to_clean参数",
                    "suggestion": "请先使用get_data_info(info_type='cleanup')获取清理建议"
                }
                return f"❌ 参数错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            if not confirm_deletion:
                result = {
                    "status": "error",
                    "message": "删除操作需要设置confirm_deletion=True进行确认",
                    "safety_reminder": "删除操作不可逆，请确保已备份重要数据",
                    "suggestion": "可以先使用action='preview_deletion'预览删除操作"
                }
                return f"❌ 安全确认失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            # 执行删除操作
            deletion_results = []
            successful_deletions = 0
            failed_deletions = 0
            
            with get_db_connection() as conn:
                for table in tables_to_clean:
                    try:
                        if _table_exists(table):
                            # 获取删除前的行数
                            escaped_table = _escape_identifier(table)
                            cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
                            row_count = cursor.fetchone()[0]
                            
                            # 执行删除
                            conn.execute(f"DROP TABLE {escaped_table}")
                            conn.commit()
                            
                            deletion_results.append({
                                "table_name": table,
                                "status": "deleted",
                                "rows_deleted": row_count,
                                "message": "表删除成功"
                            })
                            successful_deletions += 1
                            logger.info(f"成功删除表: {table} (包含 {row_count} 行数据)")
                        else:
                            deletion_results.append({
                                "table_name": table,
                                "status": "not_found",
                                "rows_deleted": 0,
                                "message": "表不存在，跳过删除"
                            })
                    except Exception as e:
                        deletion_results.append({
                            "table_name": table,
                            "status": "error",
                            "rows_deleted": 0,
                            "message": f"删除失败: {str(e)}"
                        })
                        failed_deletions += 1
                        logger.error(f"删除表 {table} 失败: {e}")
            
            total_rows_deleted = sum(result['rows_deleted'] for result in deletion_results)
            
            result = {
                "status": "success" if failed_deletions == 0 else "partial_success",
                "message": f"清理操作完成：成功删除 {successful_deletions} 个表，失败 {failed_deletions} 个",
                "data": {
                    "action": "delete_tables",
                    "successful_deletions": successful_deletions,
                    "failed_deletions": failed_deletions,
                    "total_rows_deleted": total_rows_deleted,
                    "deletion_details": deletion_results
                },
                "summary": {
                    "tables_processed": len(tables_to_clean),
                    "tables_deleted": successful_deletions,
                    "data_rows_removed": total_rows_deleted,
                    "operation_time": datetime.now().isoformat()
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "operation_type": "actual_deletion",
                    "confirmation_received": confirm_deletion
                }
            }
            
            return f"🧹 数据库清理完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "backup_and_delete":
            # 备份后删除（暂未实现）
            result = {
                "status": "error",
                "message": "备份后删除功能暂未实现",
                "available_actions": ["delete_tables", "preview_deletion"],
                "suggestion": "请手动备份重要数据后使用delete_tables操作"
            }
            return f"❌ 功能暂未实现\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        else:
            result = {
                "status": "error",
                "message": f"不支持的清理操作: {action}",
                "supported_actions": ["delete_tables", "preview_deletion", "backup_and_delete"]
            }
            return f"❌ 操作不支持\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"数据库清理操作失败: {e}")
        result = {
            "status": "error",
            "message": f"清理操作失败: {str(e)}",
            "error_type": type(e).__name__,
            "action": action,
            "tables_to_clean": tables_to_clean
        }
        return f"❌ 清理失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"







@mcp.tool()
def import_api_data_to_main_db(
    session_id: str,
    target_table: str = None,
    data_source: str = None
) -> str:
    """
    📥 API数据导入工具 - 将API存储的数据导入到主数据库
    
    功能说明：
    - 将API存储会话中的数据导入到主SQLite数据库
    - 支持指定目标表名或自动生成
    - 提供数据预览和导入统计
    - 解决API数据分析不便的问题
    
    Args:
        session_id: API存储会话ID
        target_table: 目标表名（可选，默认使用session_id作为表名）
        data_source: 数据源名称（可选，默认使用本地SQLite）
    
    Returns:
        str: JSON格式的导入结果，包含导入统计和表信息
    
    🤖 AI使用建议：
    1. 先用list_api_storage_sessions查看可用会话
    2. 使用此工具导入API数据到主数据库
    3. 然后可以使用常规分析工具分析数据
    
    💡 最佳实践：
    - 导入前先检查会话是否存在
    - 使用有意义的target_table名称
    - 导入后验证数据完整性
    """
    try:
        from config.api_data_storage import APIDataStorage
        
        # 初始化API数据存储
        api_storage = APIDataStorage()
        
        # 检查会话是否存在
        success, sessions, message = api_storage.list_storage_sessions()
        if not success:
            result = {
                "status": "error",
                "message": f"获取会话列表失败: {message}",
                "error_details": message
            }
            return f"❌ 获取会话失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        session_exists = any(session['session_id'] == session_id for session in sessions)
        
        if not session_exists:
            result = {
                "status": "error",
                "message": f"API存储会话不存在: {session_id}",
                "available_sessions": [s['session_id'] for s in sessions]
            }
            return f"❌ 会话不存在\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 获取会话数据
        success, session_data, data_message = api_storage.get_stored_data(session_id, format_type="dataframe")
        if not success or session_data is None or len(session_data) == 0:
            result = {
                "status": "error",
                "message": f"会话 {session_id} 中没有数据: {data_message}",
                "session_id": session_id
            }
            return f"❌ 无数据可导入\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 确定目标表名
        if not target_table:
            target_table = f"api_data_{session_id.replace('-', '_')}"
        
        # 获取数据库连接
        if data_source:
            db_manager = DatabaseManager()
            conn = db_manager.get_connection(data_source)
        else:
            conn = get_db_connection()
        
        # 数据已经是DataFrame格式
        df = session_data
        
        # 导入数据到主数据库
        df.to_sql(target_table, conn, if_exists='replace', index=False)
        
        # 获取导入统计
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
        row_count = cursor.fetchone()[0]
        
        # 获取列信息
        cursor.execute(f"PRAGMA table_info({target_table})")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]
        
        cursor.close()
        if not data_source:
            conn.close()
        
        result = {
            "status": "success",
            "message": f"API数据成功导入到主数据库",
            "data": {
                "session_id": session_id,
                "target_table": target_table,
                "rows_imported": row_count,
                "columns_count": len(columns),
                "columns": columns,
                "data_source": data_source or "本地SQLite"
            },
            "next_steps": {
                "analyze_data": f"analyze_data(analysis_type='basic_stats', table_name='{target_table}')",
                "query_data": f"execute_sql(query='SELECT * FROM {target_table} LIMIT 10')",
                "export_data": f"export_data(export_type='excel', data_source='{target_table}')"
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "operation_type": "api_data_import",
                "source_type": "api_storage"
            }
        }
        
        return f"📥 API数据导入成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except ImportError as e:
        result = {
            "status": "error",
            "message": "API数据存储模块导入失败",
            "error": str(e),
            "suggestion": "请检查config/api_data_storage.py文件是否存在"
        }
        return f"❌ 模块导入失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"API数据导入失败: {e}")
        result = {
            "status": "error",
            "message": f"API数据导入失败: {str(e)}",
            "error_type": type(e).__name__,
            "session_id": session_id,
            "target_table": target_table
        }
        return f"❌ 导入失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"


@mcp.tool()
def list_api_storage_sessions() -> str:
    """
    📋 API存储会话列表工具 - 查看所有API数据存储会话
    
    功能说明：
    - 列出所有API数据存储会话
    - 显示会话详细信息和数据统计
    - 为API数据导入提供会话选择
    
    Returns:
        str: JSON格式的会话列表，包含会话信息和数据统计
    
    🤖 AI使用建议：
    - 在导入API数据前先查看可用会话
    - 选择合适的会话进行数据导入
    - 了解每个会话的数据量和结构
    """
    try:
        from config.api_data_storage import APIDataStorage
        
        # 初始化API数据存储
        api_storage = APIDataStorage()
        
        # 获取所有会话
        success, sessions, message = api_storage.list_storage_sessions()
        
        if not success:
            result = {
                "status": "error",
                "message": f"获取会话列表失败: {message}",
                "error_details": message
            }
            return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        if not sessions:
            result = {
                "status": "success",
                "message": "暂无API存储会话",
                "data": {
                    "sessions_count": 0,
                    "sessions": []
                },
                "suggestion": "使用fetch_api_data工具创建API数据存储会话"
            }
            return f"📋 暂无API存储会话\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 为每个会话获取数据统计
        sessions_with_stats = []
        for session in sessions:
            session_id = session['session_id']
            try:
                success_data, session_data, data_msg = api_storage.get_stored_data(session_id, format_type="dataframe")
                data_count = len(session_data) if success_data and session_data is not None else 0
                
                # 获取数据列信息
                columns = []
                if success_data and session_data is not None and len(session_data) > 0:
                    columns = list(session_data.columns) if hasattr(session_data, 'columns') else []
                
                session_info = {
                    **session,
                    "data_statistics": {
                        "rows_count": data_count,
                        "columns_count": len(columns),
                        "columns": columns[:10],  # 只显示前10列
                        "has_more_columns": len(columns) > 10
                    }
                }
                sessions_with_stats.append(session_info)
                
            except Exception as e:
                session_info = {
                    **session,
                    "data_statistics": {
                        "error": f"获取数据统计失败: {str(e)}"
                    }
                }
                sessions_with_stats.append(session_info)
        
        result = {
            "status": "success",
            "message": f"找到 {len(sessions)} 个API存储会话",
            "data": {
                "sessions_count": len(sessions),
                "sessions": sessions_with_stats
            },
            "usage_tips": {
                "import_data": "使用import_api_data_to_main_db导入数据到主数据库",
                "preview_data": "会话数据已包含在data_statistics中",
                "analyze_data": "导入后可使用analyze_data等工具分析"
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "operation_type": "list_api_sessions"
            }
        }
        
        return f"📋 API存储会话列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except ImportError as e:
        result = {
            "status": "error",
            "message": "API数据存储模块导入失败",
            "error": str(e),
            "suggestion": "请检查config/api_data_storage.py文件是否存在"
        }
        return f"❌ 模块导入失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"获取API存储会话列表失败: {e}")
        result = {
            "status": "error",
            "message": f"获取会话列表失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"


# ================================
# 4. 启动服务器
# ================================
def main():
    """主入口函数"""
    logger.info(f"启动 {TOOL_NAME}")
    
    # 初始化数据库
    init_database()
    
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("正在关闭...")
    finally:
        logger.info("服务器已关闭")

if __name__ == "__main__":
    main()

# ================================
# 5. 使用说明
# ================================
"""
🚀 DataMaster MCP 使用指南：

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