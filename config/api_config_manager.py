#!/usr/bin/env python3
"""
API配置管理器
负责加载和管理API配置信息
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from dotenv import load_dotenv
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class APIConfigManager:
    """API配置管理器类"""
    
    def __init__(self, config_file: str = "config/api_config.json"):
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
                logger.error(f"API配置文件不存在: {self.config_file}")
                self.config_data = {"apis": {}, "default_settings": {}, "security": {}, "data_processing": {}}
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # 处理环境变量替换
            self._resolve_environment_variables()
            
            logger.info(f"API配置文件加载成功: {self.config_file}")
            
        except Exception as e:
            logger.error(f"加载API配置文件失败: {e}")
            self.config_data = {"apis": {}, "default_settings": {}, "security": {}, "data_processing": {}}
    
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
    
    def get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        """获取指定API的配置"""
        apis = self.config_data.get("apis", {})
        if api_name not in apis:
            logger.error(f"API配置不存在: {api_name}")
            return None
        
        config = apis[api_name].copy()
        
        # 检查是否启用
        if not config.get("enabled", True):
            logger.warning(f"API连接已禁用: {api_name}")
            return None
        
        return config
    
    def list_apis(self) -> Dict[str, Dict[str, Any]]:
        """列出所有配置的API"""
        apis = self.config_data.get("apis", {})
        result = {}
        
        for name, config in apis.items():
            # 只返回基本信息，不包含敏感信息
            result[name] = {
                "name": config.get("name", name),
                "base_url": config.get("base_url", ""),
                "auth_type": config.get("auth_type", ""),
                "data_format": config.get("data_format", "json"),
                "description": config.get("description", ""),
                "enabled": config.get("enabled", True),
                "endpoints": list(config.get("endpoints", {}).keys())
            }
        
        return result
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取默认设置"""
        return self.config_data.get("default_settings", {
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 1,
            "max_response_size": "10MB",
            "follow_redirects": True,
            "verify_ssl": True,
            "user_agent": "SuperDataAnalysis-MCP/1.0"
        })
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self.config_data.get("security", {
            "allowed_domains": [],
            "blocked_domains": [],
            "require_https": False,
            "max_redirects": 5,
            "max_response_size_bytes": 10485760
        })
    
    def get_data_processing_config(self) -> Dict[str, Any]:
        """获取数据处理配置"""
        return self.config_data.get("data_processing", {
            "auto_flatten_json": True,
            "max_nesting_level": 5,
            "handle_pagination": True,
            "pagination_config": {
                "page_param": "page",
                "limit_param": "limit",
                "offset_param": "offset",
                "max_pages": 100
            }
        })
    
    def validate_api_config(self, api_name: str) -> tuple[bool, str]:
        """验证API配置的完整性"""
        config = self.get_api_config(api_name)
        if not config:
            return False, f"API配置不存在或已禁用: {api_name}"
        
        # 验证必需字段
        required_fields = ["base_url", "auth_type"]
        for field in required_fields:
            if not config.get(field):
                return False, f"缺少必需的配置字段: {field}"
        
        # 验证URL格式
        base_url = config.get("base_url")
        try:
            parsed_url = urlparse(base_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return False, f"无效的base_url格式: {base_url}"
        except Exception:
            return False, f"无效的base_url格式: {base_url}"
        
        # 验证认证配置
        auth_type = config.get("auth_type")
        auth_config = config.get("auth_config", {})
        
        if auth_type == "api_key":
            if not auth_config.get("api_key"):
                return False, "API Key认证缺少api_key配置"
        elif auth_type == "bearer_token":
            if not auth_config.get("token"):
                return False, "Bearer Token认证缺少token配置"
        elif auth_type == "basic":
            if not auth_config.get("username") or not auth_config.get("password"):
                return False, "Basic认证缺少username或password配置"
        elif auth_type == "custom_header":
            if not auth_config.get("headers"):
                return False, "自定义Header认证缺少headers配置"
        elif auth_type != "none":
            return False, f"不支持的认证类型: {auth_type}"
        
        # 验证端点配置
        endpoints = config.get("endpoints", {})
        if not endpoints:
            return False, "缺少端点配置"
        
        for endpoint_name, endpoint_config in endpoints.items():
            if not endpoint_config.get("path"):
                return False, f"端点 {endpoint_name} 缺少path配置"
            if not endpoint_config.get("method"):
                return False, f"端点 {endpoint_name} 缺少method配置"
        
        return True, "配置验证通过"
    
    def add_api_config(self, api_name: str, config: Dict[str, Any]) -> bool:
        """添加新的API配置"""
        try:
            if "apis" not in self.config_data:
                self.config_data["apis"] = {}
            
            self.config_data["apis"][api_name] = config
            self._save_config()
            logger.info(f"API配置已添加: {api_name}")
            return True
        except Exception as e:
            logger.error(f"添加API配置失败: {e}")
            return False
    
    def remove_api_config(self, api_name: str) -> bool:
        """删除API配置"""
        try:
            if api_name in self.config_data.get("apis", {}):
                del self.config_data["apis"][api_name]
                self._save_config()
                logger.info(f"API配置已删除: {api_name}")
                return True
            else:
                logger.warning(f"API配置不存在: {api_name}")
                return False
        except Exception as e:
            logger.error(f"删除API配置失败: {e}")
            return False
    
    def update_api_config(self, api_name: str, config: Dict[str, Any]) -> bool:
        """更新API配置"""
        try:
            if api_name not in self.config_data.get("apis", {}):
                logger.error(f"API配置不存在: {api_name}")
                return False
            
            self.config_data["apis"][api_name].update(config)
            self._save_config()
            logger.info(f"API配置已更新: {api_name}")
            return True
        except Exception as e:
            logger.error(f"更新API配置失败: {e}")
            return False
    
    def _save_config(self):
        """保存配置文件"""
        try:
            config_path = Path(self.config_file)
            # 创建备份
            backup_path = config_path.with_suffix('.json.bak')
            if config_path.exists():
                config_path.rename(backup_path)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            # 删除备份
            if backup_path.exists():
                backup_path.unlink()
            
            logger.info("API配置文件已保存")
        except Exception as e:
            logger.error(f"保存API配置文件失败: {e}")
            # 恢复备份
            backup_path = Path(self.config_file).with_suffix('.json.bak')
            if backup_path.exists():
                backup_path.rename(self.config_file)
            raise
    
    def reload_config(self):
        """重新加载配置文件"""
        logger.info("重新加载API配置文件")
        self._load_env_variables()
        self._load_config()
    
    def get_endpoint_config(self, api_name: str, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """获取指定端点的配置"""
        api_config = self.get_api_config(api_name)
        if not api_config:
            return None
        
        endpoints = api_config.get("endpoints", {})
        if endpoint_name not in endpoints:
            logger.error(f"端点配置不存在: {api_name}.{endpoint_name}")
            return None
        
        return endpoints[endpoint_name]
    
    def is_domain_allowed(self, url: str) -> bool:
        """检查域名是否被允许访问"""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            security_config = self.get_security_config()
            
            # 检查黑名单
            blocked_domains = security_config.get("blocked_domains", [])
            for blocked in blocked_domains:
                if blocked.lower() in domain:
                    return False
            
            # 检查白名单（如果配置了白名单）
            allowed_domains = security_config.get("allowed_domains", [])
            if allowed_domains:
                for allowed in allowed_domains:
                    if allowed.lower() in domain:
                        return True
                return False
            
            # 检查HTTPS要求
            if security_config.get("require_https", False) and parsed_url.scheme != "https":
                return False
            
            return True
        except Exception:
            return False

# 创建全局实例
api_config_manager = APIConfigManager()