#!/usr/bin/env python3
"""
数据库连接管理器
支持 MySQL、PostgreSQL、MongoDB、SQLite 多种数据库
"""

import sqlite3
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import json
from contextlib import contextmanager

# 可选依赖导入
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    pymysql = None

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    psycopg2 = None
    RealDictCursor = None

try:
    import pymongo
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    pymongo = None

from .config_manager import config_manager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库连接管理器"""
    
    def __init__(self):
        self.connections = {}
        self.config_manager = config_manager
    
    def get_available_databases(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的数据库配置"""
        return self.config_manager.list_databases()
    
    def test_connection(self, database_name: str) -> tuple[bool, str]:
        """测试数据库连接"""
        try:
            # 验证配置
            is_valid, message = self.config_manager.validate_database_config(database_name)
            if not is_valid:
                return False, message
            
            config = self.config_manager.get_database_config(database_name)
            db_type = config["type"]
            
            if db_type == "mysql":
                return self._test_mysql_connection(config)
            elif db_type == "postgresql":
                return self._test_postgresql_connection(config)
            elif db_type == "mongodb":
                return self._test_mongodb_connection(config)
            elif db_type == "sqlite":
                return self._test_sqlite_connection(config)
            else:
                return False, f"不支持的数据库类型: {db_type}"
                
        except Exception as e:
            logger.error(f"测试数据库连接失败: {e}")
            return False, f"连接测试失败: {str(e)}"
    
    def _test_mysql_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """测试 MySQL 连接"""
        if not MYSQL_AVAILABLE:
            return False, "MySQL 驱动未安装，请运行: pip install pymysql"
        
        try:
            connection = pymysql.connect(
                host=config["host"],
                port=config.get("port", 3306),
                user=config["username"],
                password=config["password"],
                database=config["database"],
                charset=config.get("charset", "utf8mb4"),
                connect_timeout=10
            )
            connection.close()
            return True, "MySQL 连接测试成功"
        except Exception as e:
            return False, f"MySQL 连接失败: {str(e)}"
    
    def _test_postgresql_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """测试 PostgreSQL 连接"""
        if not POSTGRESQL_AVAILABLE:
            return False, "PostgreSQL 驱动未安装，请运行: pip install psycopg2-binary"
        
        try:
            connection = psycopg2.connect(
                host=config["host"],
                port=config.get("port", 5432),
                user=config["username"],
                password=config["password"],
                database=config["database"],
                connect_timeout=10
            )
            connection.close()
            return True, "PostgreSQL 连接测试成功"
        except Exception as e:
            return False, f"PostgreSQL 连接失败: {str(e)}"
    
    def _test_mongodb_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """测试 MongoDB 连接"""
        if not MONGODB_AVAILABLE:
            return False, "MongoDB 驱动未安装，请运行: pip install pymongo"
        
        try:
            # 构建连接字符串
            if config.get("username") and config.get("password"):
                uri = f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config.get('port', 27017)}/{config['database']}"
                if config.get("auth_source"):
                    uri += f"?authSource={config['auth_source']}"
            else:
                uri = f"mongodb://{config['host']}:{config.get('port', 27017)}/{config['database']}"
            
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
            # 测试连接
            client.server_info()
            client.close()
            return True, "MongoDB 连接测试成功"
        except Exception as e:
            return False, f"MongoDB 连接失败: {str(e)}"
    
    def _test_sqlite_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """测试 SQLite 连接"""
        try:
            file_path = Path(config["file_path"])
            if not file_path.exists():
                return False, f"SQLite 文件不存在: {file_path}"
            
            connection = sqlite3.connect(str(file_path), timeout=10)
            connection.close()
            return True, "SQLite 连接测试成功"
        except Exception as e:
            return False, f"SQLite 连接失败: {str(e)}"
    
    @contextmanager
    def get_connection(self, database_name: str):
        """获取数据库连接（上下文管理器）"""
        connection = None
        try:
            config = self.config_manager.get_database_config(database_name)
            if not config:
                raise ValueError(f"数据库配置不存在: {database_name}")
            
            db_type = config["type"]
            
            if db_type == "mysql":
                connection = self._get_mysql_connection(config)
            elif db_type == "postgresql":
                connection = self._get_postgresql_connection(config)
            elif db_type == "mongodb":
                connection = self._get_mongodb_connection(config)
            elif db_type == "sqlite":
                connection = self._get_sqlite_connection(config)
            else:
                raise ValueError(f"不支持的数据库类型: {db_type}")
            
            yield connection
            
        except Exception as e:
            logger.error(f"获取数据库连接失败: {e}")
            raise
        finally:
            if connection:
                try:
                    if hasattr(connection, 'close'):
                        connection.close()
                except Exception as e:
                    logger.warning(f"关闭数据库连接失败: {e}")
    
    def _get_mysql_connection(self, config: Dict[str, Any]):
        """获取 MySQL 连接"""
        if not MYSQL_AVAILABLE:
            raise ImportError("MySQL 驱动未安装，请运行: pip install pymysql")
        
        return pymysql.connect(
            host=config["host"],
            port=config.get("port", 3306),
            user=config["username"],
            password=config["password"],
            database=config["database"],
            charset=config.get("charset", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def _get_postgresql_connection(self, config: Dict[str, Any]):
        """获取 PostgreSQL 连接"""
        if not POSTGRESQL_AVAILABLE:
            raise ImportError("PostgreSQL 驱动未安装，请运行: pip install psycopg2-binary")
        
        return psycopg2.connect(
            host=config["host"],
            port=config.get("port", 5432),
            user=config["username"],
            password=config["password"],
            database=config["database"]
        )
    
    def _get_mongodb_connection(self, config: Dict[str, Any]):
        """获取 MongoDB 连接"""
        if not MONGODB_AVAILABLE:
            raise ImportError("MongoDB 驱动未安装，请运行: pip install pymongo")
        
        # 构建连接字符串
        if config.get("username") and config.get("password"):
            uri = f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config.get('port', 27017)}/{config['database']}"
            if config.get("auth_source"):
                uri += f"?authSource={config['auth_source']}"
        else:
            uri = f"mongodb://{config['host']}:{config.get('port', 27017)}/{config['database']}"
        
        client = pymongo.MongoClient(uri)
        return client[config["database"]]
    
    def _get_sqlite_connection(self, config: Dict[str, Any]):
        """获取 SQLite 连接"""
        file_path = Path(config["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"SQLite 文件不存在: {file_path}")
        
        connection = sqlite3.connect(str(file_path))
        connection.row_factory = sqlite3.Row  # 返回字典格式的行
        return connection
    
    def execute_query(self, database_name: str, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """执行查询语句"""
        try:
            # 安全检查
            security_config = self.config_manager.get_security_config()
            if not security_config.get("allow_write_operations", False):
                blocked_keywords = security_config.get("blocked_keywords", [])
                query_upper = query.upper().strip()
                for keyword in blocked_keywords:
                    if keyword in query_upper:
                        return {
                            "success": False,
                            "error": f"查询包含被禁止的关键字: {keyword}",
                            "data": []
                        }
            
            config = self.config_manager.get_database_config(database_name)
            if not config:
                return {
                    "success": False,
                    "error": f"数据库配置不存在: {database_name}",
                    "data": []
                }
            
            db_type = config["type"]
            
            if db_type in ["mysql", "postgresql", "sqlite"]:
                return self._execute_sql_query(database_name, query, params)
            elif db_type == "mongodb":
                return self._execute_mongodb_query(database_name, query, params)
            else:
                return {
                    "success": False,
                    "error": f"不支持的数据库类型: {db_type}",
                    "data": []
                }
                
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def _execute_sql_query(self, database_name: str, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """执行 SQL 查询"""
        with self.get_connection(database_name) as connection:
            if hasattr(connection, 'cursor'):
                # MySQL/PostgreSQL
                cursor = connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    return {
                        "success": True,
                        "data": [dict(row) if hasattr(row, 'keys') else row for row in rows],
                        "row_count": len(rows)
                    }
                else:
                    connection.commit()
                    return {
                        "success": True,
                        "data": [],
                        "affected_rows": cursor.rowcount
                    }
            else:
                # SQLite
                cursor = connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    return {
                        "success": True,
                        "data": [dict(row) for row in rows],
                        "row_count": len(rows)
                    }
                else:
                    connection.commit()
                    return {
                        "success": True,
                        "data": [],
                        "affected_rows": cursor.rowcount
                    }
    
    def _execute_mongodb_query(self, database_name: str, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """执行 MongoDB 查询"""
        # MongoDB 查询需要特殊处理，这里提供基本框架
        # 实际使用时需要根据具体需求实现
        try:
            with self.get_connection(database_name) as db:
                # 这里需要解析查询字符串并转换为 MongoDB 操作
                # 简化实现：假设查询是 JSON 格式的 find 操作
                query_obj = json.loads(query)
                collection_name = query_obj.get("collection")
                operation = query_obj.get("operation", "find")
                filter_obj = query_obj.get("filter", {})
                
                collection = db[collection_name]
                
                if operation == "find":
                    cursor = collection.find(filter_obj)
                    results = list(cursor)
                    # 转换 ObjectId 为字符串
                    for result in results:
                        if '_id' in result:
                            result['_id'] = str(result['_id'])
                    
                    return {
                        "success": True,
                        "data": results,
                        "row_count": len(results)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"不支持的 MongoDB 操作: {operation}",
                        "data": []
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"MongoDB 查询失败: {str(e)}",
                "data": []
            }
    
    def get_table_list(self, database_name: str) -> List[str]:
        """获取数据库中的表列表"""
        try:
            config = self.config_manager.get_database_config(database_name)
            if not config:
                return []
            
            db_type = config["type"]
            
            if db_type == "mysql":
                result = self.execute_query(database_name, "SHOW TABLES")
            elif db_type == "postgresql":
                result = self.execute_query(database_name, 
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            elif db_type == "sqlite":
                result = self.execute_query(database_name, 
                    "SELECT name FROM sqlite_master WHERE type='table'")
            elif db_type == "mongodb":
                with self.get_connection(database_name) as db:
                    return db.list_collection_names()
            else:
                return []
            
            if result["success"]:
                # 提取表名
                tables = []
                for row in result["data"]:
                    if isinstance(row, dict):
                        # 取第一个值作为表名
                        tables.append(list(row.values())[0])
                    else:
                        tables.append(row[0])
                return tables
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取表列表失败: {e}")
            return []
    
    def get_table_schema(self, database_name: str, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        try:
            config = self.config_manager.get_database_config(database_name)
            if not config:
                return {"success": False, "error": "数据库配置不存在"}
            
            db_type = config["type"]
            
            if db_type == "mysql":
                result = self.execute_query(database_name, f"DESCRIBE {table_name}")
            elif db_type == "postgresql":
                result = self.execute_query(database_name, 
                    f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table_name}'")
            elif db_type == "sqlite":
                result = self.execute_query(database_name, f"PRAGMA table_info({table_name})")
            elif db_type == "mongodb":
                # MongoDB 是无模式的，返回集合的示例文档结构
                with self.get_connection(database_name) as db:
                    collection = db[table_name]
                    sample_doc = collection.find_one()
                    if sample_doc:
                        schema = {}
                        for key, value in sample_doc.items():
                            schema[key] = type(value).__name__
                        return {"success": True, "schema": schema}
                    else:
                        return {"success": True, "schema": {}}
            else:
                return {"success": False, "error": "不支持的数据库类型"}
            
            return result
            
        except Exception as e:
            logger.error(f"获取表结构失败: {e}")
            return {"success": False, "error": str(e)}

# 全局数据库管理器实例
database_manager = DatabaseManager()