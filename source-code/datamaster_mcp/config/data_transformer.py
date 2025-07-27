#!/usr/bin/env python3
"""
数据转换器
负责API响应数据的格式化和转换
"""

import json
import pandas as pd
from typing import Dict, Any, List, Union, Optional
import logging
from datetime import datetime
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class DataTransformer:
    """数据转换器类"""
    
    def __init__(self):
        self.supported_formats = ["json", "csv", "excel", "dataframe", "table"]
    
    def transform_data(self, data: Any, output_format: str = "json", 
                      transform_config: Dict[str, Any] = None) -> tuple[bool, Any, str]:
        """转换数据格式"""
        try:
            if not data:
                return True, None, "数据为空"
            
            # 应用数据转换配置
            if transform_config:
                data = self._apply_transform_config(data, transform_config)
            
            # 根据输出格式转换数据
            if output_format.lower() == "json":
                return self._to_json(data)
            elif output_format.lower() == "csv":
                return self._to_csv(data)
            elif output_format.lower() == "excel":
                return self._to_excel(data)
            elif output_format.lower() == "dataframe":
                return self._to_dataframe(data)
            elif output_format.lower() == "table":
                return self._to_table(data)
            else:
                return False, None, f"不支持的输出格式: {output_format}"
                
        except Exception as e:
            logger.error(f"数据转换失败: {e}")
            return False, None, f"数据转换失败: {str(e)}"
    
    def _apply_transform_config(self, data: Any, config: Dict[str, Any]) -> Any:
        """应用数据转换配置"""
        try:
            # 字段映射
            field_mapping = config.get("field_mapping", {})
            if field_mapping and isinstance(data, (dict, list)):
                data = self._apply_field_mapping(data, field_mapping)
            
            # 字段过滤
            include_fields = config.get("include_fields", [])
            exclude_fields = config.get("exclude_fields", [])
            if (include_fields or exclude_fields) and isinstance(data, (dict, list)):
                data = self._apply_field_filter(data, include_fields, exclude_fields)
            
            # 数据类型转换
            type_conversions = config.get("type_conversions", {})
            if type_conversions and isinstance(data, (dict, list)):
                data = self._apply_type_conversions(data, type_conversions)
            
            # 数据清洗
            clean_config = config.get("data_cleaning", {})
            if clean_config:
                data = self._apply_data_cleaning(data, clean_config)
            
            return data
            
        except Exception as e:
            logger.warning(f"应用转换配置失败: {e}")
            return data
    
    def _apply_field_mapping(self, data: Any, mapping: Dict[str, str]) -> Any:
        """应用字段映射"""
        if isinstance(data, dict):
            new_data = {}
            for key, value in data.items():
                new_key = mapping.get(key, key)
                if isinstance(value, (dict, list)):
                    new_data[new_key] = self._apply_field_mapping(value, mapping)
                else:
                    new_data[new_key] = value
            return new_data
        elif isinstance(data, list):
            return [self._apply_field_mapping(item, mapping) for item in data]
        else:
            return data
    
    def _apply_field_filter(self, data: Any, include_fields: List[str], exclude_fields: List[str]) -> Any:
        """应用字段过滤"""
        if isinstance(data, dict):
            new_data = {}
            for key, value in data.items():
                # 检查是否应该包含此字段
                should_include = True
                
                if include_fields and key not in include_fields:
                    should_include = False
                
                if exclude_fields and key in exclude_fields:
                    should_include = False
                
                if should_include:
                    if isinstance(value, (dict, list)):
                        new_data[key] = self._apply_field_filter(value, include_fields, exclude_fields)
                    else:
                        new_data[key] = value
            return new_data
        elif isinstance(data, list):
            return [self._apply_field_filter(item, include_fields, exclude_fields) for item in data]
        else:
            return data
    
    def _apply_type_conversions(self, data: Any, conversions: Dict[str, str]) -> Any:
        """应用数据类型转换"""
        if isinstance(data, dict):
            new_data = {}
            for key, value in data.items():
                if key in conversions:
                    target_type = conversions[key]
                    new_data[key] = self._convert_value_type(value, target_type)
                elif isinstance(value, (dict, list)):
                    new_data[key] = self._apply_type_conversions(value, conversions)
                else:
                    new_data[key] = value
            return new_data
        elif isinstance(data, list):
            return [self._apply_type_conversions(item, conversions) for item in data]
        else:
            return data
    
    def _convert_value_type(self, value: Any, target_type: str) -> Any:
        """转换值的数据类型"""
        try:
            if target_type == "int":
                return int(float(str(value)))
            elif target_type == "float":
                return float(str(value))
            elif target_type == "str":
                return str(value)
            elif target_type == "bool":
                if isinstance(value, str):
                    return value.lower() in ["true", "1", "yes", "on"]
                return bool(value)
            elif target_type == "datetime":
                if isinstance(value, str):
                    # 尝试多种日期格式
                    formats = [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d",
                        "%Y/%m/%d %H:%M:%S",
                        "%Y/%m/%d",
                        "%d/%m/%Y",
                        "%d-%m-%Y"
                    ]
                    for fmt in formats:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                return value
            else:
                return value
        except Exception:
            return value
    
    def _apply_data_cleaning(self, data: Any, clean_config: Dict[str, Any]) -> Any:
        """应用数据清洗"""
        if isinstance(data, dict):
            new_data = {}
            for key, value in data.items():
                cleaned_value = self._clean_value(value, clean_config)
                if cleaned_value is not None or not clean_config.get("remove_null", False):
                    new_data[key] = cleaned_value
            return new_data
        elif isinstance(data, list):
            cleaned_list = []
            for item in data:
                cleaned_item = self._apply_data_cleaning(item, clean_config)
                if cleaned_item is not None or not clean_config.get("remove_null", False):
                    cleaned_list.append(cleaned_item)
            return cleaned_list
        else:
            return self._clean_value(data, clean_config)
    
    def _clean_value(self, value: Any, clean_config: Dict[str, Any]) -> Any:
        """清洗单个值"""
        if value is None:
            return None
        
        if isinstance(value, str):
            # 去除空白字符
            if clean_config.get("strip_whitespace", True):
                value = value.strip()
            
            # 移除HTML标签
            if clean_config.get("remove_html_tags", False):
                value = re.sub(r'<[^>]+>', '', value)
            
            # 标准化换行符
            if clean_config.get("normalize_newlines", False):
                value = re.sub(r'\r\n|\r', '\n', value)
            
            # 移除多余空格
            if clean_config.get("remove_extra_spaces", False):
                value = re.sub(r'\s+', ' ', value)
        
        return value
    
    def _to_json(self, data: Any) -> tuple[bool, str, str]:
        """转换为JSON格式"""
        try:
            json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            return True, json_str, "JSON格式转换成功"
        except Exception as e:
            return False, None, f"JSON转换失败: {e}"
    
    def _to_csv(self, data: Any) -> tuple[bool, str, str]:
        """转换为CSV格式"""
        try:
            # 转换为DataFrame
            success, df, message = self._to_dataframe(data)
            if not success:
                return False, None, message
            
            # 转换为CSV字符串
            csv_str = df.to_csv(index=False)
            return True, csv_str, "CSV格式转换成功"
        except Exception as e:
            return False, None, f"CSV转换失败: {e}"
    
    def _to_excel(self, data: Any) -> tuple[bool, bytes, str]:
        """转换为Excel格式"""
        try:
            # 转换为DataFrame
            success, df, message = self._to_dataframe(data)
            if not success:
                return False, None, message
            
            # 转换为Excel字节流
            from io import BytesIO
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            
            excel_bytes = excel_buffer.getvalue()
            return True, excel_bytes, "Excel格式转换成功"
        except Exception as e:
            return False, None, f"Excel转换失败: {e}"
    
    def _to_dataframe(self, data: Any) -> tuple[bool, pd.DataFrame, str]:
        """转换为DataFrame格式"""
        try:
            if isinstance(data, list):
                if not data:
                    return True, pd.DataFrame(), "空数据转换为DataFrame"
                
                # 检查是否为字典列表
                if all(isinstance(item, dict) for item in data):
                    df = pd.DataFrame(data)
                else:
                    # 简单列表转换为单列DataFrame
                    df = pd.DataFrame(data, columns=['value'])
            
            elif isinstance(data, dict):
                # 检查是否为嵌套字典结构
                if all(isinstance(value, (list, dict)) for value in data.values()):
                    # 尝试展平结构
                    flattened_data = self._flatten_dict(data)
                    df = pd.DataFrame([flattened_data])
                else:
                    # 简单字典转换为单行DataFrame
                    df = pd.DataFrame([data])
            
            else:
                # 其他类型转换为单值DataFrame
                df = pd.DataFrame([{'value': data}])
            
            return True, df, "DataFrame转换成功"
        except Exception as e:
            return False, None, f"DataFrame转换失败: {e}"
    
    def _to_table(self, data: Any) -> tuple[bool, str, str]:
        """转换为表格格式"""
        try:
            # 先转换为DataFrame
            success, df, message = self._to_dataframe(data)
            if not success:
                return False, None, message
            
            # 转换为表格字符串
            table_str = df.to_string(index=False)
            return True, table_str, "表格格式转换成功"
        except Exception as e:
            return False, None, f"表格转换失败: {e}"
    
    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """展平嵌套字典"""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # 处理字典列表，只取第一个元素进行展平
                items.extend(self._flatten_dict(value[0], new_key, sep=sep).items())
            else:
                items.append((new_key, value))
        
        return dict(items)
    
    def preview_data(self, data: Any, max_rows: int = 10, max_cols: int = 10) -> tuple[bool, str, str]:
        """预览数据"""
        try:
            if not data:
                return True, "数据为空", "数据预览"
            
            # 转换为DataFrame进行预览
            success, df, message = self._to_dataframe(data)
            if not success:
                # 如果无法转换为DataFrame，直接显示原始数据
                preview_str = str(data)[:1000]  # 限制显示长度
                if len(str(data)) > 1000:
                    preview_str += "...(数据已截断)"
                return True, preview_str, "原始数据预览"
            
            # 限制显示行数和列数
            if len(df) > max_rows:
                df_preview = df.head(max_rows)
                row_info = f"显示前{max_rows}行，共{len(df)}行"
            else:
                df_preview = df
                row_info = f"共{len(df)}行"
            
            if len(df.columns) > max_cols:
                df_preview = df_preview.iloc[:, :max_cols]
                col_info = f"显示前{max_cols}列，共{len(df.columns)}列"
            else:
                col_info = f"共{len(df.columns)}列"
            
            # 生成预览字符串
            preview_str = f"数据预览 ({row_info}, {col_info}):\n\n"
            preview_str += df_preview.to_string(index=False)
            
            # 添加数据类型信息
            if len(df.columns) <= max_cols:
                preview_str += "\n\n数据类型:\n"
                for col in df.columns:
                    preview_str += f"{col}: {df[col].dtype}\n"
            
            return True, preview_str, "数据预览成功"
            
        except Exception as e:
            logger.error(f"数据预览失败: {e}")
            return False, None, f"数据预览失败: {str(e)}"
    
    def get_data_summary(self, data: Any) -> tuple[bool, Dict[str, Any], str]:
        """获取数据摘要信息"""
        try:
            summary = {
                "data_type": type(data).__name__,
                "size": 0,
                "structure": {},
                "sample_data": None
            }
            
            if isinstance(data, list):
                summary["size"] = len(data)
                summary["structure"]["type"] = "list"
                summary["structure"]["length"] = len(data)
                
                if data:
                    first_item = data[0]
                    summary["structure"]["item_type"] = type(first_item).__name__
                    
                    if isinstance(first_item, dict):
                        summary["structure"]["fields"] = list(first_item.keys())
                    
                    # 样本数据（前3个元素）
                    summary["sample_data"] = data[:3]
            
            elif isinstance(data, dict):
                summary["size"] = len(data)
                summary["structure"]["type"] = "dict"
                summary["structure"]["keys"] = list(data.keys())
                summary["sample_data"] = {k: v for k, v in list(data.items())[:5]}  # 前5个键值对
            
            else:
                summary["size"] = 1
                summary["structure"]["type"] = "scalar"
                summary["sample_data"] = data
            
            return True, summary, "数据摘要生成成功"
            
        except Exception as e:
            logger.error(f"生成数据摘要失败: {e}")
            return False, None, f"生成数据摘要失败: {str(e)}"

# 创建全局实例
data_transformer = DataTransformer()