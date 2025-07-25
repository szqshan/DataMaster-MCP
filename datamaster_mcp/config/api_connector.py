#!/usr/bin/env python3
"""
API连接器
负责HTTP请求和响应处理
"""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin, urlparse
import base64
from pathlib import Path
import xml.etree.ElementTree as ET
from io import StringIO
import csv

# 可选依赖导入
try:
    import xmltodict
    XML_PARSER_AVAILABLE = True
except ImportError:
    XML_PARSER_AVAILABLE = False
    xmltodict = None

from .api_config_manager import api_config_manager

logger = logging.getLogger(__name__)

class APIConnector:
    """API连接器类"""
    
    def __init__(self):
        self.config_manager = api_config_manager
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """设置HTTP会话"""
        default_settings = self.config_manager.get_default_settings()
        
        # 设置默认超时
        self.session.timeout = default_settings.get("timeout", 30)
        
        # 设置User-Agent
        user_agent = default_settings.get("user_agent", "DataMaster-MCP/1.0")
        self.session.headers.update({"User-Agent": user_agent})
        
        # SSL验证设置
        self.session.verify = default_settings.get("verify_ssl", True)
        
        # 重定向设置
        if not default_settings.get("follow_redirects", True):
            self.session.max_redirects = 0
        else:
            security_config = self.config_manager.get_security_config()
            self.session.max_redirects = security_config.get("max_redirects", 5)
    
    def test_api_connection(self, api_name: str) -> tuple[bool, str]:
        """测试API连接"""
        try:
            # 验证配置
            is_valid, message, suggestions = self.config_manager.validate_api_config(api_name)
            if not is_valid:
                error_msg = message
                if suggestions:
                    error_msg += "\n\n修复建议:\n" + "\n".join(f"• {s}" for s in suggestions)
                return False, error_msg
            
            config = self.config_manager.get_api_config(api_name)
            base_url = config["base_url"]
            
            # 检查域名是否被允许
            if not self.config_manager.is_domain_allowed(base_url):
                return False, f"域名不被允许访问: {urlparse(base_url).netloc}"
            
            # 尝试连接基础URL
            headers = self._build_auth_headers(config)
            response = self.session.get(base_url, headers=headers, timeout=10)
            
            if response.status_code < 500:  # 4xx错误也算连接成功
                return True, f"API连接测试成功 (状态码: {response.status_code})"
            else:
                return False, f"API服务器错误 (状态码: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "连接失败，请检查网络或URL"
        except requests.exceptions.SSLError:
            return False, "SSL证书验证失败"
        except Exception as e:
            logger.error(f"测试API连接失败: {e}")
            return False, f"连接测试失败: {str(e)}"
    
    def _build_auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """构建认证头"""
        headers = {}
        auth_type = config.get("auth_type", "none")
        auth_config = config.get("auth_config", {})
        
        if auth_type == "bearer_token":
            token = auth_config.get("token", "")
            header_name = auth_config.get("header_name", "Authorization")
            token_prefix = auth_config.get("token_prefix", "Bearer")
            if token:
                headers[header_name] = f"{token_prefix} {token}"
        
        elif auth_type == "basic":
            username = auth_config.get("username", "")
            password = auth_config.get("password", "")
            if username and password:
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        elif auth_type == "custom_header":
            custom_headers = auth_config.get("headers", {})
            headers.update(custom_headers)
        
        # 添加配置中的默认headers
        default_headers = config.get("headers", {})
        headers.update(default_headers)
        
        return headers
    
    def _build_request_params(self, config: Dict[str, Any], endpoint_params: Dict[str, Any] = None) -> Dict[str, str]:
        """构建请求参数"""
        params = {}
        
        # 添加API Key到参数（如果是query方式）
        auth_type = config.get("auth_type", "none")
        if auth_type == "api_key":
            auth_config = config.get("auth_config", {})
            key_location = auth_config.get("key_location", "query")
            if key_location == "query":
                key_param = auth_config.get("key_param", "api_key")
                api_key = auth_config.get("api_key", "")
                if api_key:
                    params[key_param] = api_key
        
        # 添加端点参数
        if endpoint_params:
            params.update(endpoint_params)
        
        return params
    
    def call_api(self, api_name: str, endpoint_name: str, params: Dict[str, Any] = None, 
                 data: Any = None, method: str = None) -> tuple[bool, Union[Dict, List, str], str]:
        """调用API端点"""
        try:
            # 获取配置
            config = self.config_manager.get_api_config(api_name)
            if not config:
                return False, None, f"API配置不存在: {api_name}"
            
            endpoint_config = self.config_manager.get_endpoint_config(api_name, endpoint_name)
            if not endpoint_config:
                return False, None, f"端点配置不存在: {api_name}.{endpoint_name}"
            
            # 检查域名权限
            base_url = config["base_url"]
            if not self.config_manager.is_domain_allowed(base_url):
                return False, None, f"域名不被允许访问: {urlparse(base_url).netloc}"
            
            # 构建请求URL
            endpoint_path = endpoint_config["path"]
            url = urljoin(base_url, endpoint_path)
            
            # 确定HTTP方法
            http_method = method or endpoint_config.get("method", "GET")
            
            # 构建请求头
            headers = self._build_auth_headers(config)
            
            # 处理API Key在header中的情况
            auth_type = config.get("auth_type", "none")
            if auth_type == "api_key":
                auth_config = config.get("auth_config", {})
                key_location = auth_config.get("key_location", "query")
                if key_location == "header":
                    key_param = auth_config.get("key_param", "X-API-Key")
                    api_key = auth_config.get("api_key", "")
                    if api_key:
                        headers[key_param] = api_key
            
            # 构建请求参数
            request_params = self._build_request_params(config, params)
            
            # 合并端点默认参数
            endpoint_default_params = endpoint_config.get("params", {})
            for key, value in endpoint_default_params.items():
                if key not in request_params:
                    request_params[key] = value
            
            # 发送请求
            response = self._send_request_with_retry(
                method=http_method,
                url=url,
                headers=headers,
                params=request_params,
                data=data,
                config=config
            )
            
            if not response:
                return False, None, "请求失败"
            
            # 检查响应大小
            security_config = self.config_manager.get_security_config()
            max_size = security_config.get("max_response_size_bytes", 10485760)
            if len(response.content) > max_size:
                return False, None, f"响应数据过大: {len(response.content)} bytes > {max_size} bytes"
            
            # 解析响应
            success, parsed_data, error_msg = self._parse_response(response, config)
            
            if success:
                return True, parsed_data, f"请求成功 (状态码: {response.status_code})"
            else:
                return False, None, error_msg
                
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return False, None, f"API调用失败: {str(e)}"
    
    def _send_request_with_retry(self, method: str, url: str, headers: Dict[str, str], 
                                params: Dict[str, Any], data: Any, config: Dict[str, Any]) -> Optional[requests.Response]:
        """带重试的请求发送"""
        default_settings = self.config_manager.get_default_settings()
        retry_attempts = config.get("retry_attempts", default_settings.get("retry_attempts", 3))
        retry_delay = config.get("retry_delay", default_settings.get("retry_delay", 1))
        timeout = config.get("timeout", default_settings.get("timeout", 30))
        
        for attempt in range(retry_attempts + 1):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, headers=headers, params=params, timeout=timeout)
                elif method.upper() == "POST":
                    if isinstance(data, dict):
                        response = self.session.post(url, headers=headers, params=params, json=data, timeout=timeout)
                    else:
                        response = self.session.post(url, headers=headers, params=params, data=data, timeout=timeout)
                elif method.upper() == "PUT":
                    if isinstance(data, dict):
                        response = self.session.put(url, headers=headers, params=params, json=data, timeout=timeout)
                    else:
                        response = self.session.put(url, headers=headers, params=params, data=data, timeout=timeout)
                elif method.upper() == "DELETE":
                    response = self.session.delete(url, headers=headers, params=params, timeout=timeout)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                # 检查状态码
                if response.status_code < 500:  # 4xx错误不重试
                    return response
                
                # 5xx错误重试
                if attempt < retry_attempts:
                    logger.warning(f"请求失败 (状态码: {response.status_code})，{retry_delay}秒后重试 (第{attempt + 1}次)")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    return response
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < retry_attempts:
                    logger.warning(f"网络错误: {e}，{retry_delay}秒后重试 (第{attempt + 1}次)")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"网络错误，重试次数已用完: {e}")
                    return None
            except Exception as e:
                logger.error(f"请求发送失败: {e}")
                return None
        
        return None
    
    def _parse_response(self, response: requests.Response, config: Dict[str, Any]) -> tuple[bool, Any, str]:
        """解析响应数据"""
        try:
            # 检查状态码
            if response.status_code >= 400:
                return False, None, f"HTTP错误: {response.status_code} - {response.text[:200]}"
            
            data_format = config.get("data_format", "json").lower()
            content_type = response.headers.get("content-type", "").lower()
            
            # 自动检测数据格式
            if "json" in content_type or data_format == "json":
                try:
                    data = response.json()
                    return True, data, "JSON解析成功"
                except json.JSONDecodeError as e:
                    return False, None, f"JSON解析失败: {e}"
            
            elif "xml" in content_type or data_format == "xml":
                if XML_PARSER_AVAILABLE:
                    try:
                        data = xmltodict.parse(response.text)
                        return True, data, "XML解析成功"
                    except Exception as e:
                        return False, None, f"XML解析失败: {e}"
                else:
                    # 使用内置XML解析器
                    try:
                        root = ET.fromstring(response.text)
                        data = self._xml_to_dict(root)
                        return True, data, "XML解析成功"
                    except ET.ParseError as e:
                        return False, None, f"XML解析失败: {e}"
            
            elif "csv" in content_type or data_format == "csv":
                try:
                    csv_reader = csv.DictReader(StringIO(response.text))
                    data = list(csv_reader)
                    return True, data, "CSV解析成功"
                except Exception as e:
                    return False, None, f"CSV解析失败: {e}"
            
            else:
                # 返回原始文本
                return True, response.text, "文本数据"
                
        except Exception as e:
            logger.error(f"响应解析失败: {e}")
            return False, None, f"响应解析失败: {str(e)}"
    
    def _xml_to_dict(self, element):
        """将XML元素转换为字典"""
        result = {}
        
        # 添加属性
        if element.attrib:
            result.update(element.attrib)
        
        # 处理子元素
        children = list(element)
        if children:
            child_dict = {}
            for child in children:
                child_data = self._xml_to_dict(child)
                if child.tag in child_dict:
                    # 如果标签重复，转换为列表
                    if not isinstance(child_dict[child.tag], list):
                        child_dict[child.tag] = [child_dict[child.tag]]
                    child_dict[child.tag].append(child_data)
                else:
                    child_dict[child.tag] = child_data
            result.update(child_dict)
        
        # 添加文本内容
        if element.text and element.text.strip():
            if result:
                result['_text'] = element.text.strip()
            else:
                return element.text.strip()
        
        return result
    
    def get_api_endpoints(self, api_name: str) -> Dict[str, Dict[str, Any]]:
        """获取API的所有端点信息"""
        config = self.config_manager.get_api_config(api_name)
        if not config:
            return {}
        
        endpoints = config.get("endpoints", {})
        result = {}
        
        for name, endpoint_config in endpoints.items():
            result[name] = {
                "path": endpoint_config.get("path", ""),
                "method": endpoint_config.get("method", "GET"),
                "description": endpoint_config.get("description", ""),
                "params": endpoint_config.get("params", {})
            }
        
        return result
    
    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()

# 创建全局实例
api_connector = APIConnector()