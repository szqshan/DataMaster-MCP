#!/usr/bin/env python3
"""
DataMaster MCP - API管理核心模块

这个模块包含所有API管理相关的工具函数：
- manage_api_config: API配置管理
- fetch_api_data: API数据获取并自动存储
- api_data_preview: API数据预览
- create_api_storage_session: 创建API存储会话
- list_api_storage_sessions: 列出API存储会话

以及相关的API管理辅助函数。
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# 设置日志
logger = logging.getLogger("DataMaster_MCP.APIManager")

# 导入API相关模块
try:
    from config.api_config_manager import APIConfigManager
    from config.api_connector import APIConnector
    from config.api_data_storage import APIDataStorage
    from config.data_transformer import DataTransformer
except ImportError as e:
    logger.warning(f"API模块导入失败: {e}")
    # 定义空的占位类
    class APIConfigManager:
        def list_apis(self): return {}
        def add_api_config(self, name, config): return False
        def remove_api_config(self, name): return False
        def reload_config(self): pass
    
    class APIConnector:
        def test_api_connection(self, name): return False, "API连接器未初始化"
        def get_api_endpoints(self, name): return []
        def call_api(self, **kwargs): return False, None, "API连接器未初始化"
    
    class APIDataStorage:
        def create_storage_session(self, **kwargs): return False, None, "API存储未初始化"
        def store_api_data(self, **kwargs): return False, 0, "API存储未初始化"
        def list_storage_sessions(self): return False, [], "API存储未初始化"
        def get_stored_data(self, **kwargs): return False, None, "API存储未初始化"
        def _get_session_info(self, session_id): return None
    
    class DataTransformer:
        def transform_data(self, **kwargs): return False, None, "数据转换器未初始化"
        def get_data_summary(self, data): return False, None, "数据转换器未初始化"

# 初始化API管理器
try:
    api_config_manager = APIConfigManager()
    api_connector = APIConnector()
    api_data_storage = APIDataStorage()
    data_transformer = DataTransformer()
except Exception as e:
    logger.warning(f"API管理器初始化失败: {e}")
    api_config_manager = APIConfigManager()
    api_connector = APIConnector()
    api_data_storage = APIDataStorage()
    data_transformer = DataTransformer()

# ================================
# API管理工具函数
# ================================

def manage_api_config_impl(
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

def fetch_api_data_impl(
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

def api_data_preview_impl(
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

def create_api_storage_session_impl(
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

def list_api_storage_sessions_impl() -> str:
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
        # 获取所有会话
        success, sessions, message = api_data_storage.list_storage_sessions()
        
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
                success_data, session_data, data_msg = api_data_storage.get_stored_data(session_id, format_type="dataframe")
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
        
    except Exception as e:
        logger.error(f"获取API存储会话列表失败: {e}")
        result = {
            "status": "error",
            "message": f"获取会话列表失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

# ================================
# API管理辅助函数
# ================================

def _format_user_friendly_error(error_type: str, error_message: str, context: dict) -> dict:
    """格式化用户友好的错误信息"""
    error_mappings = {
        "api_call_failed": {
            "friendly_message": "API调用失败",
            "solutions": [
                "检查API配置是否正确",
                "验证API密钥是否有效",
                "确认网络连接正常",
                "检查API端点是否可用",
                "验证请求参数格式"
            ]
        },
        "connection_timeout": {
            "friendly_message": "API连接超时",
            "solutions": [
                "检查网络连接",
                "稍后重试",
                "联系API服务提供商"
            ]
        },
        "authentication_failed": {
            "friendly_message": "API认证失败",
            "solutions": [
                "检查API密钥是否正确",
                "确认API密钥是否过期",
                "验证认证方式是否正确"
            ]
        }
    }
    
    error_info = error_mappings.get(error_type, {
        "friendly_message": "未知错误",
        "solutions": ["请联系技术支持"]
    })
    
    return {
        "error_type": error_type,
        "friendly_message": error_info["friendly_message"],
        "technical_message": error_message,
        "solutions": error_info["solutions"],
        "context": context
    }

def _generate_enhanced_preview(data, max_rows=10, max_cols=10, preview_fields=None, 
                             preview_depth=3, show_data_types=True, truncate_length=100) -> dict:
    """生成增强的数据预览"""
    try:
        import pandas as pd
        
        # 如果数据是字典或列表，尝试转换为DataFrame
        if isinstance(data, dict):
            if preview_fields:
                # 只预览指定字段
                filtered_data = {k: v for k, v in data.items() if k in preview_fields}
                df = pd.DataFrame([filtered_data])
            else:
                df = pd.DataFrame([data])
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                df = pd.DataFrame(data)
                if preview_fields:
                    available_fields = [f for f in preview_fields if f in df.columns]
                    if available_fields:
                        df = df[available_fields]
            else:
                df = pd.DataFrame(data, columns=['value'])
        else:
            # 其他类型数据
            df = pd.DataFrame([{'data': str(data)}])
        
        # 限制行数和列数
        df_preview = df.head(max_rows)
        if len(df.columns) > max_cols:
            df_preview = df_preview.iloc[:, :max_cols]
        
        # 截断长文本
        for col in df_preview.columns:
            if df_preview[col].dtype == 'object':
                df_preview[col] = df_preview[col].astype(str).apply(
                    lambda x: x[:truncate_length] + '...' if len(x) > truncate_length else x
                )
        
        # 生成预览文本
        preview_text = df_preview.to_string(index=False, max_rows=max_rows)
        
        # 生成结构信息
        structure_info = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "preview_rows": len(df_preview),
            "preview_columns": len(df_preview.columns),
            "column_names": list(df.columns),
            "data_types": df.dtypes.to_dict() if show_data_types else None
        }
        
        return {
            "preview_text": preview_text,
            "structure_info": structure_info
        }
        
    except Exception as e:
        return {
            "preview_text": f"预览生成失败: {str(e)}",
            "structure_info": {"error": str(e)}
        }

# ================================
# 模块初始化函数
# ================================

def init_api_manager_module():
    """初始化API管理模块"""
    logger.info("API管理模块已初始化")
    
    # 测试API管理器连接
    try:
        apis = api_config_manager.list_apis()
        logger.info(f"API配置管理器已连接，当前配置API数量: {len(apis)}")
    except Exception as e:
        logger.warning(f"API配置管理器连接失败: {e}")