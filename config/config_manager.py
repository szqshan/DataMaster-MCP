#!/usr/bin/env python3
"""
配置管理器
负责加载和管理数据库配置信息
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from dotenv import load_dotenv
import re

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: str = "config/database_config.json"):
        self.config_file = config_file
        self.config_data = {}
        self._load_env_variables()
        self._load_config()
    
    def _load_env_variables(self):
        """加载环境变量"""
        try:
            # 尝试加载 .env 文件
            env_file = Path(".env")
            if env_file.exists():
                load_dotenv(env_file)
                logger.info("已加载 .env 文件")
            else:
                logger.info(".env 文件不存在，使用系统环境变量")
        except Exception as e:
            logger.warning(f"加载环境变量失败: {e}")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                logger.error(f"配置文件不存在: {self.config_file}")
                self.config_data = {"databases": {}, "default_limits": {}, "security": {}}
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # 处理环境变量替换
            self._resolve_environment_variables()
            
            logger.info(f"配置文件加载成功: {self.config_file}")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config_data = {"databases": {}, "default_limits": {}, "security": {}}
    
    def _resolve_environment_variables(self):
        """解析配置中的环境变量引用"""
        def replace_env_vars(obj):
            if isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            elif isinstance(obj, str):
                # 查找 ${VAR_NAME} 格式的环境变量引用
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, obj)
                for var_name in matches:
                    env_value = os.getenv(var_name, '')
                    obj = obj.replace(f'${{{var_name}}}', env_value)
                return obj
            else:
                return obj
        
        self.config_data = replace_env_vars(self.config_data)
    
    def get_database_config(self, database_name: str) -> Optional[Dict[str, Any]]:
        """获取指定数据库的配置"""
        databases = self.config_data.get("databases", {})
        if database_name not in databases:
            logger.error(f"数据库配置不存在: {database_name}")
            return None
        
        config = databases[database_name].copy()
        
        # 检查是否启用
        if not config.get("enabled", True):
            logger.warning(f"数据库连接已禁用: {database_name}")
            return None
        
        return config
    
    def list_databases(self) -> Dict[str, Dict[str, Any]]:
        """列出所有配置的数据库"""
        databases = self.config_data.get("databases", {})
        result = {}
        
        for name, config in databases.items():
            # 只返回基本信息，不包含敏感信息
            result[name] = {
                "type": config.get("type"),
                "description": config.get("description", ""),
                "enabled": config.get("enabled", True),
                "host": config.get("host", ""),
                "database": config.get("database", ""),
                "file_path": config.get("file_path", ""),
                "is_temporary": config.get("_is_temporary", False),
                "created_at": config.get("_created_at")
            }
        
        return result
    
    def cleanup_temporary_configs(self) -> tuple[bool, str]:
        """清理所有临时配置"""
        try:
            temp_configs = []
            for name, config in self.config_data.get("databases", {}).items():
                if config.get("_is_temporary", False):
                    temp_configs.append(name)
            
            if not temp_configs:
                return True, "没有找到临时配置"
            
            removed_count = 0
            for config_name in temp_configs:
                if self.remove_database_config(config_name):
                    removed_count += 1
            
            return True, f"成功清理 {removed_count} 个临时配置: {', '.join(temp_configs)}"
        except Exception as e:
            return False, f"清理临时配置失败: {str(e)}"
    
    def get_temporary_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有临时配置"""
        temp_configs = {}
        for name, config in self.config_data.get("databases", {}).items():
            if config.get("_is_temporary", False) and config.get("enabled", True):
                temp_configs[name] = {
                    "type": config.get("type"),
                    "host": config.get("host"),
                    "database": config.get("database"),
                    "description": config.get("description", ""),
                    "created_at": config.get("_created_at")
                }
        return temp_configs
    
    def get_default_limits(self) -> Dict[str, Any]:
        """获取默认限制配置"""
        return self.config_data.get("default_limits", {
            "query_timeout": 30,
            "max_rows": 10000,
            "connection_pool_size": 5,
            "retry_attempts": 3,
            "retry_delay": 1
        })
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self.config_data.get("security", {
            "allow_write_operations": False,
            "allowed_schemas": [],
            "blocked_keywords": ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
        })
    
    def validate_database_config(self, database_name: str) -> tuple[bool, str]:
        """验证数据库配置的完整性"""
        config = self.get_database_config(database_name)
        if not config:
            return False, f"数据库配置不存在或已禁用: {database_name}"
        
        db_type = config.get("type")
        if not db_type:
            return False, "缺少数据库类型配置"
        
        # 根据数据库类型验证必需字段
        if db_type == "mysql":
            required_fields = ["host", "database", "password"]
            # 检查用户名字段（支持 username 或 user）
            if not (config.get("username") or config.get("user")):
                return False, "缺少必需的配置字段: username (或 user)"
        elif db_type == "postgresql":
            required_fields = ["host", "database", "password"]
            # 检查用户名字段（支持 username 或 user）
            if not (config.get("username") or config.get("user")):
                return False, "缺少必需的配置字段: username (或 user)"
        elif db_type == "mongodb":
            required_fields = ["host", "database"]
        elif db_type == "sqlite":
            required_fields = ["file_path"]
        else:
            return False, f"不支持的数据库类型: {db_type}"
        
        for field in required_fields:
            if not config.get(field):
                return False, f"缺少必需的配置字段: {field}"
        
        return True, "配置验证通过"
    
    def add_database_config(self, database_name: str, config: Dict[str, Any]) -> bool:
        """添加新的数据库配置"""
        try:
            if "databases" not in self.config_data:
                self.config_data["databases"] = {}
            
            self.config_data["databases"][database_name] = config
            self._save_config()
            logger.info(f"数据库配置已添加: {database_name}")
            return True
        except Exception as e:
            logger.error(f"添加数据库配置失败: {e}")
            return False
    
    def remove_database_config(self, database_name: str) -> bool:
        """删除数据库配置"""
        try:
            if database_name in self.config_data.get("databases", {}):
                del self.config_data["databases"][database_name]
                self._save_config()
                logger.info(f"数据库配置已删除: {database_name}")
                return True
            else:
                logger.warning(f"数据库配置不存在: {database_name}")
                return False
        except Exception as e:
            logger.error(f"删除数据库配置失败: {e}")
            return False
    
    def _save_config(self):
        """保存配置文件"""
        try:
            config_path = Path(self.config_file)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            logger.info("配置文件已保存")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    
    def reload_config(self):
        """重新加载配置"""
        self._load_env_variables()
        self._load_config()
        logger.info("配置已重新加载")

# 全局配置管理器实例
config_manager = ConfigManager()