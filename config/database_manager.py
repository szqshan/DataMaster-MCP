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
from datetime import datetime, date, time
from decimal import Decimal

# 增强的MySQL驱动检测
def detect_mysql_drivers():
    """检测可用的MySQL驱动"""
    drivers = {}
    
    # 检测 pymysql
    try:
        import pymysql
        drivers['pymysql'] = {
            'available': True,
            'version': getattr(pymysql, '__version__', 'unknown'),
            'module': pymysql
        }
    except ImportError as e:
        drivers['pymysql'] = {'available': False, 'error': str(e)}
    
    # 检测 mysql-connector-python
    try:
        import mysql.connector
        drivers['mysql.connector'] = {
            'available': True,
            'version': getattr(mysql.connector, '__version__', 'unknown'),
            'module': mysql.connector
        }
    except ImportError as e:
        drivers['mysql.connector'] = {'available': False, 'error': str(e)}
    
    return drivers

# 使用增强检测
MYSQL_DRIVERS = detect_mysql_drivers()
MYSQL_AVAILABLE = any(driver['available'] for driver in MYSQL_DRIVERS.values())

# 获取首选驱动
def get_preferred_mysql_driver():
    """获取首选的MySQL驱动"""
    if MYSQL_DRIVERS['pymysql']['available']:
        return 'pymysql', MYSQL_DRIVERS['pymysql']['module']
    elif MYSQL_DRIVERS['mysql.connector']['available']:
        return 'mysql.connector', MYSQL_DRIVERS['mysql.connector']['module']
    else:
        available_drivers = [name for name, info in MYSQL_DRIVERS.items() if info['available']]
        if available_drivers:
            driver_name = available_drivers[0]
            return driver_name, MYSQL_DRIVERS[driver_name]['module']
        raise ImportError("没有可用的MySQL驱动，请安装 pymysql 或 mysql-connector-python")

# 向后兼容
try:
    import pymysql
except ImportError:
    pymysql = None

# 增强的PostgreSQL驱动检测
def detect_postgresql_drivers():
    """检测可用的PostgreSQL驱动"""
    drivers = {}
    
    # 检测 psycopg2
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        drivers['psycopg2'] = {
            'available': True,
            'version': getattr(psycopg2, '__version__', 'unknown'),
            'module': psycopg2,
            'extras': {'RealDictCursor': RealDictCursor}
        }
    except ImportError as e:
        drivers['psycopg2'] = {'available': False, 'error': str(e)}
    
    # 检测 psycopg2-binary
    try:
        import psycopg2.extensions
        # psycopg2-binary 通常与 psycopg2 共享相同的模块
        if 'psycopg2' in drivers and drivers['psycopg2']['available']:
            drivers['psycopg2-binary'] = {
                'available': True,
                'version': drivers['psycopg2']['version'],
                'module': drivers['psycopg2']['module'],
                'extras': drivers['psycopg2']['extras']
            }
    except ImportError as e:
        drivers['psycopg2-binary'] = {'available': False, 'error': str(e)}
    
    # 检测 asyncpg (异步PostgreSQL驱动)
    try:
        import asyncpg
        drivers['asyncpg'] = {
            'available': True,
            'version': getattr(asyncpg, '__version__', 'unknown'),
            'module': asyncpg,
            'type': 'async'
        }
    except ImportError as e:
        drivers['asyncpg'] = {'available': False, 'error': str(e)}
    
    return drivers

# 使用增强检测
POSTGRESQL_DRIVERS = detect_postgresql_drivers()
POSTGRESQL_AVAILABLE = any(driver['available'] and driver.get('type') != 'async' for driver in POSTGRESQL_DRIVERS.values())

# 获取首选驱动
def get_preferred_postgresql_driver():
    """获取首选的PostgreSQL驱动"""
    # 优先选择 psycopg2 或 psycopg2-binary
    if POSTGRESQL_DRIVERS['psycopg2']['available']:
        return 'psycopg2', POSTGRESQL_DRIVERS['psycopg2']['module'], POSTGRESQL_DRIVERS['psycopg2']['extras']
    elif POSTGRESQL_DRIVERS['psycopg2-binary']['available']:
        return 'psycopg2-binary', POSTGRESQL_DRIVERS['psycopg2-binary']['module'], POSTGRESQL_DRIVERS['psycopg2-binary']['extras']
    else:
        available_drivers = [name for name, info in POSTGRESQL_DRIVERS.items() 
                           if info['available'] and info.get('type') != 'async']
        if available_drivers:
            driver_name = available_drivers[0]
            driver_info = POSTGRESQL_DRIVERS[driver_name]
            return driver_name, driver_info['module'], driver_info.get('extras', {})
        raise ImportError("没有可用的PostgreSQL驱动，请安装 psycopg2-binary")

# 向后兼容
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
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

def json_serializer(obj):
    """JSON序列化函数，处理datetime等特殊对象类型"""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        return str(obj)

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
        """测试 MySQL 连接（使用增强驱动检测）"""
        if not MYSQL_AVAILABLE:
            driver_status = "\n".join([f"  {name}: {'✅' if info['available'] else '❌'} {info.get('version', info.get('error', ''))}" 
                                     for name, info in MYSQL_DRIVERS.items()])
            return False, f"MySQL 驱动未安装或不可用:\n{driver_status}\n请运行: pip install pymysql mysql-connector-python"
        
        try:
            driver_name, driver_module = get_preferred_mysql_driver()
            
            if driver_name == 'pymysql':
                connection = driver_module.connect(
                    host=config["host"],
                    port=config.get("port", 3306),
                    user=config.get("user", config.get("username")),
                    password=config["password"],
                    database=config["database"],
                    charset=config.get("charset", "utf8mb4"),
                    connect_timeout=10
                )
                
                with connection.cursor() as cursor:
                    cursor.execute("SELECT VERSION()")
                    version = cursor.fetchone()[0]
                    
            elif driver_name == 'mysql.connector':
                connection = driver_module.connect(
                    host=config["host"],
                    port=config.get("port", 3306),
                    user=config.get("user", config.get("username")),
                    password=config["password"],
                    database=config["database"],
                    charset=config.get("charset", "utf8mb4"),
                    connection_timeout=10
                )
                
                cursor = connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                cursor.close()
                
            else:
                return False, f"不支持的MySQL驱动: {driver_name}"
            
            connection.close()
            return True, f"连接成功 (使用{driver_name})，MySQL版本: {version}"
            
        except Exception as e:
            return False, f"连接失败 (使用{driver_name if 'driver_name' in locals() else 'unknown'}): {str(e)}"
    
    def _test_postgresql_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """测试 PostgreSQL 连接（增强版）"""
        # 检查驱动可用性
        if not POSTGRESQL_AVAILABLE:
            error_details = []
            for driver_name, driver_info in POSTGRESQL_DRIVERS.items():
                if not driver_info['available']:
                    error_details.append(f"  - {driver_name}: {driver_info.get('error', '未知错误')}")
            
            error_msg = "PostgreSQL驱动未安装或不可用:\n" + "\n".join(error_details)
            error_msg += "\n\n建议安装命令:\n  pip install psycopg2-binary"
            return False, error_msg
        
        # 获取首选驱动
        try:
            driver_name, psycopg2_module, extras = get_preferred_postgresql_driver()
            RealDictCursor = extras.get('RealDictCursor')
        except ImportError as e:
            return False, f"无法获取PostgreSQL驱动: {str(e)}"
        
        # 测试连接
        try:
            connection = psycopg2_module.connect(
                host=config["host"],
                port=config.get("port", 5432),
                user=config.get("user", config.get("username")),
                password=config["password"],
                database=config["database"],
                connect_timeout=10
            )
            
            cursor = connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            
            # 获取驱动版本信息
            driver_info = POSTGRESQL_DRIVERS[driver_name]
            driver_version = driver_info.get('version', 'unknown')
            
            return True, f"连接成功，使用驱动: {driver_name} v{driver_version}，数据库版本: {version}"
        except Exception as e:
            return False, f"连接失败 (使用驱动: {driver_name}): {str(e)}"
    
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
        """获取 MySQL 连接（使用增强驱动检测）"""
        if not MYSQL_AVAILABLE:
            driver_status = "\n".join([f"  {name}: {'✅' if info['available'] else '❌'} {info.get('version', info.get('error', ''))}" 
                                     for name, info in MYSQL_DRIVERS.items()])
            raise ImportError(f"MySQL 驱动未安装或不可用:\n{driver_status}\n请运行: pip install pymysql mysql-connector-python")
        
        driver_name, driver_module = get_preferred_mysql_driver()
        
        if driver_name == 'pymysql':
            return driver_module.connect(
                host=config["host"],
                port=config.get("port", 3306),
                user=config.get("user", config.get("username")),
                password=config["password"],
                database=config["database"],
                charset=config.get("charset", "utf8mb4"),
                cursorclass=driver_module.cursors.DictCursor
            )
        elif driver_name == 'mysql.connector':
            return driver_module.connect(
                host=config["host"],
                port=config.get("port", 3306),
                user=config.get("user", config.get("username")),
                password=config["password"],
                database=config["database"],
                charset=config.get("charset", "utf8mb4"),
                autocommit=True
            )
        else:
            raise ImportError(f"不支持的MySQL驱动: {driver_name}")
    
    def _get_postgresql_connection(self, config: Dict[str, Any]):
        """获取 PostgreSQL 连接（增强版）"""
        if not POSTGRESQL_AVAILABLE:
            error_details = []
            for driver_name, driver_info in POSTGRESQL_DRIVERS.items():
                if not driver_info['available']:
                    error_details.append(f"  - {driver_name}: {driver_info.get('error', '未知错误')}")
            
            error_msg = "PostgreSQL驱动未安装或不可用:\n" + "\n".join(error_details)
            error_msg += "\n\n建议安装命令:\n  pip install psycopg2-binary"
            raise ImportError(error_msg)
        
        # 获取首选驱动
        driver_name, psycopg2_module, extras = get_preferred_postgresql_driver()
        RealDictCursor = extras.get('RealDictCursor')
        
        connection = psycopg2_module.connect(
            host=config["host"],
            port=config.get("port", 5432),
            user=config.get("user", config.get("username")),
            password=config["password"],
            database=config["database"]
        )
        
        # 如果支持字典游标，设置为默认
        if RealDictCursor:
            connection.cursor_factory = RealDictCursor
        
        return connection
    
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
                    # 处理查询结果，确保datetime等对象可以序列化
                    processed_data = []
                    for row in rows:
                        if hasattr(row, 'keys'):
                            # 字典类型的行（如psycopg2的DictCursor）
                            processed_row = {}
                            for key, value in dict(row).items():
                                try:
                                    json.dumps(value)  # 测试是否可序列化
                                    processed_row[key] = value
                                except (TypeError, ValueError):
                                    processed_row[key] = json_serializer(value)
                            processed_data.append(processed_row)
                        else:
                            # 元组类型的行
                            processed_row = []
                            for value in row:
                                try:
                                    json.dumps(value)  # 测试是否可序列化
                                    processed_row.append(value)
                                except (TypeError, ValueError):
                                    processed_row.append(json_serializer(value))
                            processed_data.append(processed_row)
                    
                    return {
                        "success": True,
                        "data": processed_data,
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
                    # 获取列名
                    columns = [description[0] for description in cursor.description] if cursor.description else []
                    
                    # 处理查询结果，确保datetime等对象可以序列化
                    processed_data = []
                    for row in rows:
                        processed_row = {}
                        for i, value in enumerate(row):
                            column_name = columns[i] if i < len(columns) else f"column_{i}"
                            try:
                                json.dumps(value)  # 测试是否可序列化
                                processed_row[column_name] = value
                            except (TypeError, ValueError):
                                processed_row[column_name] = json_serializer(value)
                        processed_data.append(processed_row)
                    
                    return {
                        "success": True,
                        "data": processed_data,
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