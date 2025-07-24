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
            
            # 统一参数处理：支持 user 和 username 两种参数名
            username = config.get("username") or config.get("user")
            if not username:
                return False, "缺少必需的配置字段: username (或 user)"
            
            if driver_name == 'pymysql':
                connection = driver_module.connect(
                    host=config["host"],
                    port=config.get("port", 3306),
                    user=username,
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
                    user=username,
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
        
        # 统一参数处理：支持 user 和 username 两种参数名
        username = config.get("username") or config.get("user")
        if not username:
            return False, "缺少必需的配置字段: username (或 user)"
        
        # 测试连接
        try:
            connection = psycopg2_module.connect(
                host=config["host"],
                port=config.get("port", 5432),
                user=username,
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
        
        # 统一参数处理：支持 user 和 username 两种参数名
        username = config.get("username") or config.get("user")
        if not username:
            raise ValueError("缺少必需的配置字段: username (或 user)")
        
        if driver_name == 'pymysql':
            return driver_module.connect(
                host=config["host"],
                port=config.get("port", 3306),
                user=username,
                password=config["password"],
                database=config["database"],
                charset=config.get("charset", "utf8mb4"),
                cursorclass=driver_module.cursors.DictCursor
            )
        elif driver_name == 'mysql.connector':
            return driver_module.connect(
                host=config["host"],
                port=config.get("port", 3306),
                user=username,
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
        
        # 统一参数处理：支持 user 和 username 两种参数名
        username = config.get("username") or config.get("user")
        if not username:
            raise ValueError("缺少必需的配置字段: username (或 user)")
        
        connection = psycopg2_module.connect(
            host=config["host"],
            port=config.get("port", 5432),
            user=username,
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
        # 返回一个包装对象，避免数据库对象的布尔值测试问题
        class MongoDBConnection:
            def __init__(self, client, database):
                self.client = client
                self.database = database
                
            def __getitem__(self, collection_name):
                return self.database[collection_name]
                
            def list_collection_names(self):
                return self.database.list_collection_names()
                
            def close(self):
                self.client.close()
                
        return MongoDBConnection(client, client[config["database"]])
    
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
        try:
            with self.get_connection(database_name) as db:
                # 处理不同类型的MongoDB查询
                query = query.strip()
                
                # 处理MongoDB shell命令
                if query.startswith('show '):
                    return self._handle_mongodb_show_command(db, query)
                elif query.startswith('db.'):
                    return self._handle_mongodb_db_command(db, query)
                else:
                    # 尝试解析为JSON格式的查询
                    try:
                        query_obj = json.loads(query)
                        return self._handle_mongodb_json_query(db, query_obj)
                    except json.JSONDecodeError:
                        return {
                            "success": False,
                            "error": f"无法解析MongoDB查询: {query}",
                            "data": []
                        }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"MongoDB 查询失败: {str(e)}",
                "data": []
            }
    
    def _handle_mongodb_show_command(self, db, query: str) -> Dict[str, Any]:
        """处理MongoDB show命令"""
        try:
            if query == "show dbs" or query == "show databases":
                client = db.client
                databases = client.list_database_names()
                return {
                    "success": True,
                    "data": [{"database": name} for name in databases],
                    "row_count": len(databases)
                }
            elif query == "show collections":
                collections = db.list_collection_names()
                return {
                    "success": True,
                    "data": [{"collection": name} for name in collections],
                    "row_count": len(collections)
                }
            else:
                return {
                    "success": False,
                    "error": f"不支持的show命令: {query}",
                    "data": []
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"执行show命令失败: {str(e)}",
                "data": []
            }
    
    def _handle_mongodb_db_command(self, db, query: str) -> Dict[str, Any]:
        """处理MongoDB db.命令"""
        try:
            # 简单的命令解析
            if ".find(" in query:
                # 提取集合名和查询条件
                parts = query.split('.')
                if len(parts) >= 3 and parts[0] == 'db':
                    collection_name = parts[1]
                    collection = db[collection_name]
                    
                    # 提取find参数
                    find_start = query.find('.find(')
                    find_end = query.rfind(')')
                    if find_start != -1 and find_end != -1:
                        find_params = query[find_start + 6:find_end]
                        if find_params.strip():
                            try:
                                filter_obj = json.loads(find_params)
                            except json.JSONDecodeError:
                                filter_obj = {}
                        else:
                            filter_obj = {}
                        
                        cursor = collection.find(filter_obj)
                        results = list(cursor)
                        
                        # 处理BSON序列化问题
                        processed_results = []
                        for result in results:
                            processed_result = self._process_mongodb_document(result)
                            processed_results.append(processed_result)
                        
                        return {
                            "success": True,
                            "data": processed_results,
                            "row_count": len(processed_results)
                        }
            
            elif ".insertOne(" in query:
                # 处理插入操作
                parts = query.split('.')
                if len(parts) >= 3 and parts[0] == 'db':
                    collection_name = parts[1]
                    collection = db[collection_name]
                    
                    # 提取插入数据
                    insert_start = query.find('.insertOne(')
                    insert_end = query.rfind(')')
                    if insert_start != -1 and insert_end != -1:
                        insert_data = query[insert_start + 11:insert_end]
                        try:
                            doc = json.loads(insert_data)
                            # 处理datetime对象
                            doc = self._prepare_mongodb_document(doc)
                            result = collection.insert_one(doc)
                            return {
                                "success": True,
                                "data": [{"inserted_id": str(result.inserted_id)}],
                                "row_count": 1
                            }
                        except json.JSONDecodeError as e:
                            return {
                                "success": False,
                                "error": f"无法解析插入数据: {str(e)}",
                                "data": []
                            }
            
            elif ".aggregate(" in query:
                # 处理聚合操作
                parts = query.split('.')
                if len(parts) >= 3 and parts[0] == 'db':
                    collection_name = parts[1]
                    collection = db[collection_name]
                    
                    # 提取聚合管道
                    agg_start = query.find('.aggregate(')
                    agg_end = query.rfind(')')
                    if agg_start != -1 and agg_end != -1:
                        agg_pipeline = query[agg_start + 11:agg_end]
                        try:
                            # 尝试多种解析方式
                            pipeline = self._parse_mongodb_pipeline(agg_pipeline)
                            cursor = collection.aggregate(pipeline)
                            results = list(cursor)
                            
                            # 处理BSON序列化问题
                            processed_results = []
                            for result in results:
                                processed_result = self._process_mongodb_document(result)
                                processed_results.append(processed_result)
                            
                            return {
                                "success": True,
                                "data": processed_results,
                                "row_count": len(processed_results)
                            }
                        except Exception as e:
                            return {
                                "success": False,
                                "error": f"无法解析聚合管道: {str(e)}\n原始管道: {agg_pipeline}",
                                "data": []
                            }
            
            return {
                "success": False,
                "error": f"不支持的MongoDB命令: {query}",
                "data": []
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"执行MongoDB命令失败: {str(e)}",
                "data": []
            }
    
    def _handle_mongodb_json_query(self, db, query_obj: dict) -> Dict[str, Any]:
        """处理JSON格式的MongoDB查询"""
        try:
            collection_name = query_obj.get("collection")
            operation = query_obj.get("operation", "find")
            filter_obj = query_obj.get("filter", {})
            
            if not collection_name:
                return {
                    "success": False,
                    "error": "缺少collection参数",
                    "data": []
                }
            
            collection = db[collection_name]
            
            if operation == "find":
                cursor = collection.find(filter_obj)
                results = list(cursor)
                
                # 处理BSON序列化问题
                processed_results = []
                for result in results:
                    processed_result = self._process_mongodb_document(result)
                    processed_results.append(processed_result)
                
                return {
                    "success": True,
                    "data": processed_results,
                    "row_count": len(processed_results)
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
                "error": f"执行JSON查询失败: {str(e)}",
                "data": []
            }
    
    def _process_mongodb_document(self, doc: dict) -> dict:
        """处理MongoDB文档，解决BSON序列化问题"""
        processed_doc = {}
        for key, value in doc.items():
            try:
                # 测试是否可以JSON序列化
                json.dumps(value)
                processed_doc[key] = value
            except (TypeError, ValueError):
                # 使用自定义序列化函数
                processed_doc[key] = json_serializer(value)
        return processed_doc
    
    def _prepare_mongodb_document(self, doc: dict) -> dict:
        """准备MongoDB文档，处理Python对象到BSON的转换"""
        prepared_doc = {}
        for key, value in doc.items():
            if isinstance(value, (datetime, date, time)):
                # 保持datetime对象，MongoDB可以直接存储
                prepared_doc[key] = value
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                prepared_doc[key] = self._prepare_mongodb_document(value)
            elif isinstance(value, list):
                # 处理列表
                prepared_doc[key] = [self._prepare_mongodb_document(item) if isinstance(item, dict) else item for item in value]
            else:
                prepared_doc[key] = value
        return prepared_doc
    
    def _parse_mongodb_pipeline(self, pipeline_str: str) -> list:
        """解析MongoDB聚合管道，支持多种格式"""
        # 清理字符串
        pipeline_str = pipeline_str.strip()
        
        # 尝试直接JSON解析
        try:
            return json.loads(pipeline_str)
        except json.JSONDecodeError:
            pass
        
        # 尝试修复常见的JSON格式问题
        try:
            # 替换单引号为双引号
            fixed_str = pipeline_str.replace("'", '"')
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            pass
        
        # 尝试处理JavaScript风格的对象
        try:
            import re
            # 为未加引号的键添加引号
            fixed_str = re.sub(r'(\w+)\s*:', r'"\1":', pipeline_str)
            # 替换单引号为双引号
            fixed_str = fixed_str.replace("'", '"')
            return json.loads(fixed_str)
        except (json.JSONDecodeError, ImportError):
            pass
        
        # 尝试eval（仅用于简单情况，有安全风险但在受控环境下可用）
        try:
            # 只允许基本的数据结构
            if all(char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789[]{}:,"\' ._-$' for char in pipeline_str):
                # 替换JavaScript风格的对象为Python字典
                python_str = pipeline_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                result = eval(python_str)
                if isinstance(result, list):
                    return result
        except:
            pass
        
        # 如果所有方法都失败，抛出详细错误
        raise ValueError(f"无法解析MongoDB聚合管道。支持的格式:\n" +
                        "1. 标准JSON: [{\"$match\": {\"field\": \"value\"}}]\n" +
                        "2. JavaScript风格: [{'$match': {'field': 'value'}}]\n" +
                        "3. 无引号键: [{$match: {field: 'value'}}]\n" +
                        f"实际输入: {pipeline_str}")
    
    def get_table_list(self, database_name: str) -> List[str]:
        """获取数据库中的表列表"""
        try:
            config = self.config_manager.get_database_config(database_name)
            if not config:
                return []
            
            db_type = config["type"]
            
            if db_type == "mysql":
                # 使用INFORMATION_SCHEMA查询，更可靠
                db_name = config.get("database", "mysql")
                result = self.execute_query(database_name, 
                    f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{db_name}'")
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
                logger.error(f"查询表列表失败: {result.get('error', '未知错误')}")
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