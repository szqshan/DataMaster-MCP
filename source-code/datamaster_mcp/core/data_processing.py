#!/usr/bin/env python3
"""
DataMaster MCP - 数据处理核心模块

这个模块包含所有数据处理相关的工具函数：
- process_data: 执行数据清洗、转换、筛选等操作
- export_data: 将数据导出为各种格式文件

以及相关的处理辅助函数。
"""

import json
import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

# 设置日志
logger = logging.getLogger("DataMaster_MCP.DataProcessing")

# 导入数据库相关函数
try:
    from .database import get_db_connection, _escape_identifier, _table_exists
except ImportError:
    # 如果相对导入失败，定义本地版本
    def get_db_connection():
        """获取数据库连接"""
        import sqlite3
        conn = sqlite3.connect("data/analysis.db")
        conn.row_factory = sqlite3.Row
        return conn
    
    def _escape_identifier(identifier: str) -> str:
        """转义SQL标识符"""
        return '"' + identifier.replace('"', '""') + '"'
    
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

# 确保导出目录存在
EXPORTS_DIR = "exports"
if not os.path.exists(EXPORTS_DIR):
    os.makedirs(EXPORTS_DIR)

# ================================
# 数据处理工具函数
# ================================

def process_data_impl(
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
        target_table: 目标表名（可选）
            - None: 覆盖原表（默认）
            - 表名: 保存到新表
    
    Returns:
        str: JSON格式的处理结果，包含操作详情、影响行数和新表信息
    """
    try:
        # 路由映射
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
                "supported_types": list(processors.keys())
            }
            return f"❌ 操作类型错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 路由到对应处理器
        process_result = processors[operation_type](data_source, config, target_table)
        
        if "error" in process_result:
            result = {
                "status": "error",
                "message": process_result["error"]
            }
            return f"❌ 处理失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
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
                "processing_category": "data_processing"
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

def export_data_impl(
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
            file_path = f"{EXPORTS_DIR}/{source_name}_{timestamp}.{extension}"
        
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
        
        if "error" in export_result:
            result = {
                "status": "error",
                "message": export_result["error"]
            }
            return f"❌ 导出失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
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
# 数据处理辅助函数
# ================================

def _process_clean(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据清洗处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
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
                            mode_val = df[column].mode()
                            if not mode_val.empty:
                                df[column] = df[column].fillna(mode_val.iloc[0])
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
                
                for col in columns:
                    if col in df.columns and df[col].dtype in ['int64', 'float64']:
                        before_count = len(df)
                        
                        if method == 'iqr':
                            Q1 = df[col].quantile(0.25)
                            Q3 = df[col].quantile(0.75)
                            IQR = Q3 - Q1
                            lower_bound = Q1 - threshold * IQR
                            upper_bound = Q3 + threshold * IQR
                            df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
                        elif method == 'zscore':
                            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                            df = df[z_scores <= threshold]
                        
                        removed_count = before_count - len(df)
                        operations_performed.append(f"移除异常值 {col}: {removed_count}行")
            
            # 保存结果
            final_table = target_table or data_source
            if not data_source.upper().startswith('SELECT'):
                # 如果是表名，保存到目标表
                df.to_sql(final_table, conn, if_exists='replace', index=False)
            else:
                # 如果是查询，必须指定目标表
                if not target_table:
                    return {"error": "处理查询结果时必须指定target_table"}
                df.to_sql(target_table, conn, if_exists='replace', index=False)
            
            return {
                "target_table": final_table,
                "processed_rows": len(df),
                "original_rows": original_count,
                "operations": operations_performed,
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"数据清洗失败: {str(e)}"}

def _process_transform(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据转换处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            operations_performed = []
            
            # 列重命名
            if 'rename_columns' in config:
                rename_map = config['rename_columns']
                df = df.rename(columns=rename_map)
                operations_performed.append(f"重命名列: {list(rename_map.keys())} -> {list(rename_map.values())}")
            
            # 数据标准化
            if 'normalize' in config:
                normalize_config = config['normalize']
                columns = normalize_config.get('columns', [])
                method = normalize_config.get('method', 'minmax')  # minmax, zscore
                
                for col in columns:
                    if col in df.columns and df[col].dtype in ['int64', 'float64']:
                        if method == 'minmax':
                            df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
                        elif method == 'zscore':
                            df[col] = (df[col] - df[col].mean()) / df[col].std()
                        
                        operations_performed.append(f"标准化列 {col} (方法: {method})")
            
            # 新列计算
            if 'add_columns' in config:
                add_config = config['add_columns']
                for new_col, formula in add_config.items():
                    try:
                        # 简单的公式计算（安全性考虑，只支持基本运算）
                        df[new_col] = df.eval(formula)
                        operations_performed.append(f"添加新列 {new_col}: {formula}")
                    except Exception as e:
                        operations_performed.append(f"添加新列 {new_col} 失败: {str(e)}")
            
            # 数据类型转换
            if 'convert_types' in config:
                type_config = config['convert_types']
                for col, new_type in type_config.items():
                    if col in df.columns:
                        try:
                            if new_type == 'int':
                                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                            elif new_type == 'float':
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                            elif new_type == 'str':
                                df[col] = df[col].astype(str)
                            elif new_type == 'datetime':
                                df[col] = pd.to_datetime(df[col], errors='coerce')
                            
                            operations_performed.append(f"转换列类型 {col} -> {new_type}")
                        except Exception as e:
                            operations_performed.append(f"转换列类型 {col} 失败: {str(e)}")
            
            # 保存结果
            final_table = target_table or data_source
            if not data_source.upper().startswith('SELECT'):
                df.to_sql(final_table, conn, if_exists='replace', index=False)
            else:
                if not target_table:
                    return {"error": "处理查询结果时必须指定target_table"}
                df.to_sql(target_table, conn, if_exists='replace', index=False)
            
            return {
                "target_table": final_table,
                "processed_rows": len(df),
                "operations": operations_performed,
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"数据转换失败: {str(e)}"}

def _process_filter(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据筛选处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            original_count = len(df)
            operations_performed = []
            
            # 条件筛选
            if 'filter_condition' in config:
                condition = config['filter_condition']
                try:
                    df = df.query(condition)
                    operations_performed.append(f"条件筛选: {condition}")
                except Exception as e:
                    return {"error": f"筛选条件错误: {str(e)}"}
            
            # 列选择
            if 'select_columns' in config:
                columns = config['select_columns']
                available_columns = [col for col in columns if col in df.columns]
                if available_columns:
                    df = df[available_columns]
                    operations_performed.append(f"选择列: {available_columns}")
                else:
                    return {"error": "指定的列都不存在"}
            
            # 数据采样
            if 'sample' in config:
                sample_config = config['sample']
                sample_type = sample_config.get('type', 'random')  # random, head, tail
                sample_size = sample_config.get('size', 1000)
                
                if sample_type == 'random':
                    if sample_size < len(df):
                        df = df.sample(n=sample_size, random_state=42)
                        operations_performed.append(f"随机采样: {sample_size}行")
                elif sample_type == 'head':
                    df = df.head(sample_size)
                    operations_performed.append(f"头部采样: {sample_size}行")
                elif sample_type == 'tail':
                    df = df.tail(sample_size)
                    operations_performed.append(f"尾部采样: {sample_size}行")
            
            # 保存结果
            final_table = target_table or data_source
            if not data_source.upper().startswith('SELECT'):
                df.to_sql(final_table, conn, if_exists='replace', index=False)
            else:
                if not target_table:
                    return {"error": "处理查询结果时必须指定target_table"}
                df.to_sql(target_table, conn, if_exists='replace', index=False)
            
            return {
                "target_table": final_table,
                "filtered_rows": len(df),
                "original_rows": original_count,
                "operations": operations_performed,
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"数据筛选失败: {str(e)}"}

def _process_aggregate(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据聚合处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            operations_performed = []
            
            # 分组聚合
            if 'group_by' in config:
                group_config = config['group_by']
                group_columns = group_config.get('columns', [])
                agg_config = group_config.get('agg', {})
                
                if not group_columns:
                    return {"error": "分组聚合需要指定group_by列"}
                
                # 检查分组列是否存在
                missing_cols = [col for col in group_columns if col not in df.columns]
                if missing_cols:
                    return {"error": f"分组列不存在: {missing_cols}"}
                
                # 执行分组聚合
                try:
                    if agg_config:
                        df = df.groupby(group_columns).agg(agg_config).reset_index()
                        # 扁平化多级列名
                        df.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in df.columns]
                    else:
                        # 默认计数
                        df = df.groupby(group_columns).size().reset_index(name='count')
                    
                    operations_performed.append(f"分组聚合: {group_columns} -> {list(agg_config.keys()) if agg_config else ['count']}")
                except Exception as e:
                    return {"error": f"分组聚合失败: {str(e)}"}
            
            # 保存结果
            final_table = target_table or f"{data_source}_aggregated"
            if data_source.upper().startswith('SELECT') and not target_table:
                final_table = "query_aggregated"
            
            df.to_sql(final_table, conn, if_exists='replace', index=False)
            
            return {
                "target_table": final_table,
                "processed_rows": len(df),
                "operations": operations_performed,
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"数据聚合失败: {str(e)}"}

def _process_merge(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据合并处理器"""
    try:
        with get_db_connection() as conn:
            # 获取左表数据
            if data_source.upper().startswith('SELECT'):
                left_df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                left_df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            # 获取右表数据
            right_table = config.get('right_table')
            if not right_table:
                return {"error": "合并操作需要指定right_table"}
            
            if not _table_exists(right_table):
                return {"error": f"右表 '{right_table}' 不存在"}
            
            escaped_right = _escape_identifier(right_table)
            right_df = pd.read_sql(f'SELECT * FROM {escaped_right}', conn)
            
            # 合并参数
            on_columns = config.get('on', [])
            how = config.get('how', 'inner')  # inner, left, right, outer
            
            if not on_columns:
                return {"error": "合并操作需要指定on参数（关联列）"}
            
            # 检查关联列是否存在
            missing_left = [col for col in on_columns if col not in left_df.columns]
            missing_right = [col for col in on_columns if col not in right_df.columns]
            
            if missing_left:
                return {"error": f"左表缺少关联列: {missing_left}"}
            if missing_right:
                return {"error": f"右表缺少关联列: {missing_right}"}
            
            # 执行合并
            try:
                merged_df = pd.merge(left_df, right_df, on=on_columns, how=how, suffixes=('_left', '_right'))
                operations_performed = [f"表合并: {data_source} {how} join {right_table} on {on_columns}"]
            except Exception as e:
                return {"error": f"表合并失败: {str(e)}"}
            
            # 保存结果
            final_table = target_table or f"{data_source}_merged"
            if data_source.upper().startswith('SELECT') and not target_table:
                final_table = "query_merged"
            
            merged_df.to_sql(final_table, conn, if_exists='replace', index=False)
            
            return {
                "target_table": final_table,
                "processed_rows": len(merged_df),
                "operations": operations_performed,
                "columns": list(merged_df.columns)
            }
            
    except Exception as e:
        return {"error": f"数据合并失败: {str(e)}"}

def _process_reshape(data_source: str, config: dict, target_table: str = None) -> dict:
    """数据重塑处理器"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            operations_performed = []
            
            # 透视表
            if 'pivot' in config:
                pivot_config = config['pivot']
                index = pivot_config.get('index')
                columns = pivot_config.get('columns')
                values = pivot_config.get('values')
                
                if not all([index, columns, values]):
                    return {"error": "透视表需要指定index, columns, values参数"}
                
                # 检查列是否存在
                missing_cols = [col for col in [index, columns, values] if col not in df.columns]
                if missing_cols:
                    return {"error": f"透视表列不存在: {missing_cols}"}
                
                try:
                    df = df.pivot_table(index=index, columns=columns, values=values, aggfunc='mean').reset_index()
                    df.columns.name = None  # 移除列名
                    operations_performed.append(f"透视表: index={index}, columns={columns}, values={values}")
                except Exception as e:
                    return {"error": f"透视表操作失败: {str(e)}"}
            
            # 宽表转长表
            elif 'melt' in config:
                melt_config = config['melt']
                id_vars = melt_config.get('id_vars', [])
                value_vars = melt_config.get('value_vars', [])
                var_name = melt_config.get('var_name', 'variable')
                value_name = melt_config.get('value_name', 'value')
                
                try:
                    df = pd.melt(df, id_vars=id_vars, value_vars=value_vars, 
                               var_name=var_name, value_name=value_name)
                    operations_performed.append(f"宽表转长表: id_vars={id_vars}, value_vars={value_vars}")
                except Exception as e:
                    return {"error": f"宽表转长表失败: {str(e)}"}
            
            else:
                return {"error": "重塑操作需要指定pivot或melt配置"}
            
            # 保存结果
            final_table = target_table or f"{data_source}_reshaped"
            if data_source.upper().startswith('SELECT') and not target_table:
                final_table = "query_reshaped"
            
            df.to_sql(final_table, conn, if_exists='replace', index=False)
            
            return {
                "target_table": final_table,
                "processed_rows": len(df),
                "operations": operations_performed,
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"数据重塑失败: {str(e)}"}

# ================================
# 数据导出辅助函数
# ================================

def _export_to_excel(data_source: str, file_path: str, options: dict) -> dict:
    """导出到Excel文件"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 导出选项
            sheet_name = options.get('sheet_name', 'Sheet1')
            auto_adjust = options.get('auto_adjust_columns', True)
            
            # 导出到Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 自动调整列宽
                if auto_adjust:
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
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            return {
                "file_size": file_size,
                "record_count": len(df),
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"Excel导出失败: {str(e)}"}

def _export_to_csv(data_source: str, file_path: str, options: dict) -> dict:
    """导出到CSV文件"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 导出选项
            encoding = options.get('encoding', 'utf-8')
            separator = options.get('separator', ',')
            
            # 导出到CSV
            df.to_csv(file_path, index=False, encoding=encoding, sep=separator)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            return {
                "file_size": file_size,
                "record_count": len(df),
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"CSV导出失败: {str(e)}"}

def _export_to_json(data_source: str, file_path: str, options: dict) -> dict:
    """导出到JSON文件"""
    try:
        with get_db_connection() as conn:
            # 获取数据
            if data_source.upper().startswith('SELECT'):
                df = pd.read_sql(data_source, conn)
            else:
                if not _table_exists(data_source):
                    return {"error": f"表 '{data_source}' 不存在"}
                escaped_table = _escape_identifier(data_source)
                df = pd.read_sql(f'SELECT * FROM {escaped_table}', conn)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 导出选项
            orient = options.get('orient', 'records')  # records, index, values, split, table
            indent = options.get('indent', 2)
            
            # 导出到JSON
            df.to_json(file_path, orient=orient, indent=indent, force_ascii=False)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            return {
                "file_size": file_size,
                "record_count": len(df),
                "columns": list(df.columns)
            }
            
    except Exception as e:
        return {"error": f"JSON导出失败: {str(e)}"}

# ================================
# 模块初始化函数
# ================================

def init_data_processing_module():
    """初始化数据处理模块"""
    logger.info("数据处理模块已初始化")
    
    # 确保导出目录存在
    if not os.path.exists(EXPORTS_DIR):
        os.makedirs(EXPORTS_DIR)
        logger.info(f"创建导出目录: {EXPORTS_DIR}")