#!/usr/bin/env python3
"""
DataMaster MCP - 数据库模块重构示例

这个文件展示了如何将 main.py 中的数据库相关功能拆分到独立模块中。
这是一个示例文件，展示重构后的代码结构。

包含的工具函数：
- connect_data_source()     # 数据源连接
- execute_sql()            # SQL执行  
- query_external_database() # 外部数据库查询
- list_data_sources()      # 数据源列表
- manage_database_config() # 数据库配置管理
"""

import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from mcp.server.fastmcp import FastMCP

# 导入配置管理模块
from ..config.database_config import DatabaseConfigManager
from ..config.api_config import APIConfigManager
from ..config.storage_config import StorageConfigManager

# 导入工具函数
from ..utils.helpers import (
    _serialize_dataframe,
    _handle_data_format,
    _escape_identifier,
    _safe_table_query,
    _table_exists
)
from ..utils.validators import validate_database_config
from ..utils.formatters import format_query_result

# 获取MCP实例（从main.py传入）
mcp: FastMCP = None

# 日志配置
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = "datamaster.db"

# ================================
# 数据库连接和基础操作
# ================================

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化数据库"""
    with get_db_connection() as conn:
        # 创建元数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _metadata (
                table_name TEXT PRIMARY KEY,
                created_at TEXT,
                source_type TEXT,
                source_path TEXT,
                row_count INTEGER,
                last_accessed TEXT
            )
        """)
        conn.commit()

# ================================
# MCP工具函数定义
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
    
    Args:
        source_type: 数据源类型，必须是上述支持的类型之一
        config: 配置参数字典，格式根据source_type不同
        target_table: 目标表名（文件导入时可选）
        target_database: 目标数据库名称（文件导入到外部数据库时可选）
    
    Returns:
        str: JSON格式的连接结果，包含状态、消息和配置信息
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
    
    Args:
        query: SQL查询语句（推荐使用SELECT语句）
        params: 查询参数字典，用于参数化查询（可选）
        limit: 结果行数限制，默认1000行（可选）
        data_source: 数据源名称，默认本地SQLite（可选）
    
    Returns:
        str: JSON格式查询结果，包含列名、数据行和统计信息
    """
    try:
        # 安全检查：只允许SELECT查询
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            result = {
                "status": "error",
                "message": "出于安全考虑，只允许SELECT查询",
                "query_type": "forbidden"
            }
            return f"❌ 查询被拒绝\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 添加LIMIT限制
        if 'LIMIT' not in query_upper:
            query += f" LIMIT {limit}"
        
        # 执行查询
        with get_db_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            
            # 获取结果
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            # 转换为字典列表
            data = [dict(row) for row in rows]
            
            result = {
                "status": "success",
                "message": "查询执行成功",
                "data": {
                    "columns": columns,
                    "rows": data,
                    "row_count": len(data),
                    "column_count": len(columns)
                },
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "data_source": data_source or "本地SQLite",
                    "limit_applied": limit
                }
            }
            
            return f"✅ 查询执行成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"SQL查询失败: {e}")
        result = {
            "status": "error",
            "message": f"SQL查询失败: {str(e)}",
            "error_type": type(e).__name__,
            "query": query
        }
        return f"❌ 查询失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

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
    
    Args:
        database_name: 数据库配置名称（从connect_data_source获得）
        query: 查询语句，SQL或MongoDB查询语法
        limit: 结果行数限制，默认1000行
    
    Returns:
        str: JSON格式查询结果，包含数据行、统计信息和元数据
    """
    try:
        # 获取数据库配置
        db_manager = DatabaseConfigManager()
        config = db_manager.get_config(database_name)
        
        if not config:
            result = {
                "status": "error",
                "message": f"数据库配置不存在: {database_name}",
                "available_configs": db_manager.list_configs()
            }
            return f"❌ 配置不存在\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 根据数据库类型执行查询
        db_type = config.get('type', '').lower()
        
        if db_type in ['mysql', 'postgresql']:
            return _query_sql_database(config, query, limit, database_name)
        elif db_type == 'mongodb':
            return _query_mongodb(config, query, limit, database_name)
        else:
            result = {
                "status": "error",
                "message": f"不支持的数据库类型: {db_type}",
                "supported_types": ["mysql", "postgresql", "mongodb"]
            }
            return f"❌ 数据库类型不支持\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"外部数据库查询失败: {e}")
        result = {
            "status": "error",
            "message": f"外部数据库查询失败: {str(e)}",
            "error_type": type(e).__name__,
            "database_name": database_name
        }
        return f"❌ 查询失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

@mcp.tool()
def list_data_sources() -> str:
    """
    📋 数据源列表工具 - 查看所有可用的数据源
    
    🎯 功能说明：
    - 显示本地SQLite数据库状态
    - 列出所有外部数据库配置
    - 显示每个数据源的连接状态和基本信息
    - 区分临时配置和永久配置
    
    Returns:
        str: JSON格式的数据源列表，包含详细的配置信息
    """
    try:
        result = {
            "status": "success",
            "message": "数据源列表获取成功",
            "data": {
                "local_database": {
                    "name": "本地SQLite数据库",
                    "type": "sqlite",
                    "path": DB_PATH,
                    "status": "可用",
                    "is_default": True
                },
                "external_databases": []
            }
        }
        
        # 获取外部数据库配置
        db_manager = DatabaseConfigManager()
        configs = db_manager.list_configs()
        
        for config_name, config_info in configs.items():
            db_info = {
                "name": config_name,
                "type": config_info.get('type', 'unknown'),
                "host": config_info.get('host', 'N/A'),
                "database": config_info.get('database', 'N/A'),
                "status": "已配置",
                "is_temporary": config_name.startswith('temp_'),
                "created_at": config_info.get('created_at', 'N/A')
            }
            result["data"]["external_databases"].append(db_info)
        
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
    
    Args:
        action: 操作类型，必须是上述支持的操作之一
        config: 配置参数字典，根据action类型提供不同参数
    
    Returns:
        str: JSON格式操作结果，包含状态、消息和相关数据
    """
    try:
        db_manager = DatabaseConfigManager()
        
        if action == "list":
            configs = db_manager.list_configs()
            result = {
                "status": "success",
                "message": "配置列表获取成功",
                "data": {
                    "total_count": len(configs),
                    "configs": configs
                }
            }
            
        elif action == "test":
            if not config or "database_name" not in config:
                raise ValueError("test操作需要提供database_name参数")
            
            database_name = config["database_name"]
            test_result = db_manager.test_connection(database_name)
            
            result = {
                "status": "success",
                "message": "连接测试完成",
                "data": {
                    "database_name": database_name,
                    "test_result": test_result
                }
            }
            
        elif action == "add":
            if not config or "database_name" not in config or "database_config" not in config:
                raise ValueError("add操作需要提供database_name和database_config参数")
            
            database_name = config["database_name"]
            database_config = config["database_config"]
            
            # 验证配置
            if not validate_database_config(database_config):
                raise ValueError("数据库配置格式无效")
            
            db_manager.add_config(database_name, database_config)
            
            result = {
                "status": "success",
                "message": f"数据库配置 '{database_name}' 添加成功",
                "data": {
                    "database_name": database_name,
                    "config_added": True
                }
            }
            
        elif action == "remove":
            if not config or "database_name" not in config:
                raise ValueError("remove操作需要提供database_name参数")
            
            database_name = config["database_name"]
            db_manager.remove_config(database_name)
            
            result = {
                "status": "success",
                "message": f"数据库配置 '{database_name}' 删除成功",
                "data": {
                    "database_name": database_name,
                    "config_removed": True
                }
            }
            
        elif action == "cleanup_temp":
            cleaned_configs = db_manager.cleanup_temp_configs()
            
            result = {
                "status": "success",
                "message": f"清理了 {len(cleaned_configs)} 个临时配置",
                "data": {
                    "cleaned_configs": cleaned_configs,
                    "cleanup_count": len(cleaned_configs)
                }
            }
            
        else:
            result = {
                "status": "error",
                "message": f"不支持的操作类型: {action}",
                "supported_actions": ["list", "test", "add", "remove", "reload", "list_temp", "cleanup_temp"]
            }
            
        return f"✅ 操作完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"数据库配置管理失败: {e}")
        result = {
            "status": "error",
            "message": f"数据库配置管理失败: {str(e)}",
            "error_type": type(e).__name__,
            "action": action
        }
        return f"❌ 操作失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

# ================================
# 私有辅助函数（从main.py迁移）
# ================================

def _import_excel(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入Excel文件到本地SQLite或外部数据库"""
    # 这里是从main.py迁移的具体实现
    # 为了示例简洁，这里只显示函数签名
    pass

def _import_csv(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入CSV文件到本地SQLite或外部数据库"""
    # 这里是从main.py迁移的具体实现
    pass

def _import_json(config: dict, target_table: str = None, target_database: str = None) -> str:
    """导入JSON文件到本地SQLite或外部数据库"""
    # 这里是从main.py迁移的具体实现
    pass

def _connect_sqlite(config: dict, target_table: str = None) -> str:
    """连接SQLite数据库"""
    # 这里是从main.py迁移的具体实现
    pass

def _connect_external_database(db_type: str, config: dict, target_table: str = None) -> str:
    """连接外部数据库"""
    # 这里是从main.py迁移的具体实现
    pass

def _connect_from_config(config: dict, target_table: str = None) -> str:
    """从配置连接数据库"""
    # 这里是从main.py迁移的具体实现
    pass

def _query_sql_database(config: dict, query: str, limit: int, database_name: str) -> str:
    """查询SQL数据库"""
    # 这里是从main.py迁移的具体实现
    pass

def _query_mongodb(config: dict, query: str, limit: int, database_name: str) -> str:
    """查询MongoDB数据库"""
    # 这里是从main.py迁移的具体实现
    pass

# ================================
# 模块初始化函数
# ================================

def init_database_module(mcp_instance: FastMCP):
    """
    初始化数据库模块
    
    Args:
        mcp_instance: FastMCP实例，用于注册工具函数
    """
    global mcp
    mcp = mcp_instance
    
    # 初始化数据库
    init_database()
    
    logger.info("数据库模块初始化完成")

# ================================
# 模块导出
# ================================

__all__ = [
    'connect_data_source',
    'execute_sql', 
    'query_external_database',
    'list_data_sources',
    'manage_database_config',
    'init_database_module'
]