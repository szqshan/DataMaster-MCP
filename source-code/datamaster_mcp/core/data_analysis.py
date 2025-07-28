#!/usr/bin/env python3
"""
DataMaster MCP - 数据分析核心模块

这个模块包含所有数据分析相关的工具函数：
- analyze_data: 执行各种统计分析和数据质量检查
- get_data_info: 获取数据库结构和统计信息

以及相关的分析辅助函数。
"""

import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
from scipy import stats

# 设置日志
logger = logging.getLogger("DataMaster_MCP.DataAnalysis")

# 导入配置管理器
try:
    from ..config.database_manager import database_manager
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent.parent.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from datamaster_mcp.config.database_manager import database_manager

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

# ================================
# 数据分析工具函数
# ================================

def analyze_data_impl(
    analysis_type: str,
    table_name: str,
    columns: list = None,
    options: dict = None
) -> str:
    """
    🔍 数据分析工具 - 执行各种统计分析和数据质量检查
    
    功能说明：
    - 提供5种核心数据分析功能
    - 支持指定列分析或全表分析
    - 自动处理数据类型和缺失值
    - 返回详细的分析结果和可视化建议
    
    Args:
        analysis_type: 分析类型
            - "basic_stats": 基础统计分析（均值、中位数、标准差等）
            - "correlation": 相关性分析（数值列之间的相关系数）
            - "outliers": 异常值检测（IQR、Z-score方法）
            - "missing_values": 缺失值分析（缺失率、分布模式）
            - "duplicates": 重复值检测（完全重复、部分重复）
        table_name: 要分析的数据表名
        columns: 分析的列名列表（可选）
            - None: 分析所有适用列
            - ["col1", "col2"]: 只分析指定列
        options: 分析选项（可选字典）
            - outliers: {"method": "iqr|zscore", "threshold": 1.5}
            - correlation: {"method": "pearson|spearman"}
            - basic_stats: {"percentiles": [25, 50, 75, 90, 95]}
    
    Returns:
        str: JSON格式的分析结果，包含统计数据、图表建议和洞察
    """
    try:
        # 验证表是否存在
        if not _table_exists(table_name):
            result = {
                "status": "error",
                "message": f"表 '{table_name}' 不存在"
            }
            return f"❌ 表不存在\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 路由到具体的分析函数
        analysis_map = {
            "basic_stats": _calculate_basic_stats,
            "correlation": _calculate_correlation,
            "outliers": _detect_outliers,
            "missing_values": _check_missing_values,
            "duplicates": _check_duplicates
        }
        
        if analysis_type not in analysis_map:
            result = {
                "status": "error",
                "message": f"不支持的分析类型: {analysis_type}",
                "supported_types": list(analysis_map.keys())
            }
            return f"❌ 分析类型错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 执行分析
        analysis_result = analysis_map[analysis_type](table_name, columns or [], options or {})
        
        if "error" in analysis_result:
            result = {
                "status": "error",
                "message": analysis_result["error"]
            }
            return f"❌ 分析失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 返回成功结果
        result = {
            "status": "success",
            "message": f"{analysis_type} 分析完成",
            "data": analysis_result,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "table_name": table_name,
                "analysis_type": analysis_type,
                "columns": columns or []
            }
        }
        
        return f"✅ 分析完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
    except Exception as e:
        logger.error(f"数据分析失败: {e}")
        result = {
            "status": "error",
            "message": f"数据分析失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 分析失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def get_data_info_impl(
    info_type: str = "tables",
    table_name: str = None,
    data_source: str = None
) -> str:
    """
    📊 数据信息获取工具 - 查看数据库结构和统计信息
    
    功能说明：
    - 获取数据库表列表、表结构、数据统计等信息
    - 支持本地SQLite和外部数据库
    - 提供详细的表结构和数据概览
    - 智能数据库清理管理功能
    
    Args:
        info_type: 信息类型
            - "tables": 获取所有表/集合列表（默认）
            - "schema": 获取指定表的结构信息（需要table_name）
            - "stats": 获取指定表的统计信息（需要table_name）
            - "cleanup": 智能检测过时数据和表，提供清理建议
        table_name: 表名（当info_type为schema或stats时必需）
        data_source: 数据源名称
            - None: 使用本地SQLite数据库（默认）
            - 配置名称: 使用外部数据库（需先通过manage_database_config创建配置）
    
    Returns:
        str: JSON格式的数据库信息，包含状态、数据和元数据
    """
    try:
        if data_source:
            # 使用外部数据库连接
            try:
                if info_type == "tables":
                    tables = database_manager.get_table_list(data_source)
                    
                    result = {
                        "status": "success",
                        "message": f"获取到 {len(tables)} 个表",
                        "data": {
                            "tables": tables,
                            "table_count": len(tables),
                            "data_source": data_source
                        },
                        "metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "info_type": info_type,
                            "data_source": data_source
                        }
                    }
                    return f"✅ 表列表获取成功（数据源: {data_source}）\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                elif info_type == "schema":
                    if not table_name:
                        raise ValueError("获取表结构需要指定table_name参数")
                    
                    schema = database_manager.get_table_schema(data_source, table_name)
                    
                    result = {
                        "status": "success",
                        "message": f"表 '{table_name}' 结构信息",
                        "data": {
                            "table_name": table_name,
                            "schema": schema,
                            "data_source": data_source
                        },
                        "metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "info_type": info_type,
                            "table_name": table_name,
                            "data_source": data_source
                        }
                    }
                    return f"✅ 表结构获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                elif info_type == "stats":
                    if not table_name:
                        raise ValueError("获取表统计需要指定table_name参数")
                    
                    stats = database_manager.get_table_stats(data_source, table_name)
                    
                    result = {
                        "status": "success",
                        "message": f"表 '{table_name}' 统计信息",
                        "data": {
                            "table_name": table_name,
                            "stats": stats,
                            "data_source": data_source
                        },
                        "metadata": {
                            "timestamp": datetime.now().isoformat(),
                            "info_type": info_type,
                            "table_name": table_name,
                            "data_source": data_source
                        }
                    }
                    return f"✅ 表统计获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                    
                else:
                    raise ValueError(f"外部数据库不支持 '{info_type}' 操作")
                    
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"外部数据库操作失败: {str(e)}",
                    "data_source": data_source
                }
                return f"❌ 外部数据库操作失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        else:
            # 使用本地SQLite数据库
            if info_type == "tables":
                return _get_local_tables()
            elif info_type == "schema":
                if not table_name:
                    raise ValueError("获取表结构需要指定table_name参数")
                return _get_table_schema(table_name)
            elif info_type == "stats":
                if not table_name:
                    raise ValueError("获取表统计需要指定table_name参数")
                return _get_table_stats(table_name)
            elif info_type == "cleanup":
                return _analyze_database_cleanup()
            else:
                result = {
                    "status": "error",
                    "message": f"不支持的信息类型: {info_type}",
                    "supported_types": ["tables", "schema", "stats", "cleanup"]
                }
                return f"❌ 信息类型错误\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                
    except Exception as e:
        logger.error(f"获取数据信息失败: {e}")
        result = {
            "status": "error",
            "message": f"获取数据信息失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 获取信息失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

# ================================
# 数据分析辅助函数
# ================================

def _calculate_basic_stats(table_name: str, columns: list, options: dict) -> dict:
    """计算基础统计信息 - 智能处理数值和文本列"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取列信息
            if columns:
                target_columns = columns
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                target_columns = [col[1] for col in cursor.fetchall()]
            
            if not target_columns:
                return {"error": "没有找到可分析的列"}
            
            # 分析每一列
            stats_result = {}
            numeric_columns = []
            text_columns = []
            
            for col in target_columns:
                escaped_col = _escape_identifier(col)
                
                # 检测列类型
                cursor = conn.execute(f"SELECT typeof({escaped_col}) FROM {escaped_table} WHERE {escaped_col} IS NOT NULL LIMIT 1")
                result = cursor.fetchone()
                col_type = result[0] if result else 'null'
                
                # 获取基本信息
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT({escaped_col}) as non_null_count,
                        COUNT(CASE WHEN {escaped_col} IS NULL THEN 1 END) as null_count
                    FROM {escaped_table}
                """)
                basic_info = cursor.fetchone()
                
                if col_type in ['integer', 'real']:
                    # 数值列统计
                    numeric_columns.append(col)
                    cursor = conn.execute(f"""
                        SELECT 
                            AVG({escaped_col}) as mean,
                            MIN({escaped_col}) as min_val,
                            MAX({escaped_col}) as max_val
                        FROM {escaped_table}
                        WHERE {escaped_col} IS NOT NULL
                    """)
                    numeric_stats = cursor.fetchone()
                    
                    # 计算中位数和标准差
                    cursor = conn.execute(f"SELECT {escaped_col} FROM {escaped_table} WHERE {escaped_col} IS NOT NULL ORDER BY {escaped_col}")
                    values = [row[0] for row in cursor.fetchall()]
                    
                    if values:
                        median = np.median(values)
                        std_dev = np.std(values)
                        q25 = np.percentile(values, 25)
                        q75 = np.percentile(values, 75)
                    else:
                        median = std_dev = q25 = q75 = None
                    
                    stats_result[col] = {
                        "column_type": "numeric",
                        "data_type": col_type,
                        "total_count": basic_info[0],
                        "non_null_count": basic_info[1],
                        "null_count": basic_info[2],
                        "null_percentage": round((basic_info[2] / basic_info[0]) * 100, 2) if basic_info[0] > 0 else 0,
                        "mean": round(numeric_stats[0], 4) if numeric_stats[0] else None,
                        "median": round(median, 4) if median is not None else None,
                        "std_dev": round(std_dev, 4) if std_dev is not None else None,
                        "min": numeric_stats[1],
                        "max": numeric_stats[2],
                        "q25": round(q25, 4) if q25 is not None else None,
                        "q75": round(q75, 4) if q75 is not None else None
                    }
                    
                else:
                    # 文本列统计
                    text_columns.append(col)
                    
                    # 获取唯一值数量
                    cursor = conn.execute(f"SELECT COUNT(DISTINCT {escaped_col}) FROM {escaped_table} WHERE {escaped_col} IS NOT NULL")
                    unique_count = cursor.fetchone()[0]
                    
                    # 获取最常见的值（前5个）
                    cursor = conn.execute(f"""
                        SELECT {escaped_col}, COUNT(*) as freq 
                        FROM {escaped_table} 
                        WHERE {escaped_col} IS NOT NULL 
                        GROUP BY {escaped_col} 
                        ORDER BY freq DESC 
                        LIMIT 5
                    """)
                    top_values = cursor.fetchall()
                    
                    # 计算字符串长度统计（如果是文本）
                    length_stats = None
                    if col_type == 'text':
                        cursor = conn.execute(f"""
                            SELECT 
                                AVG(LENGTH({escaped_col})) as avg_length,
                                MIN(LENGTH({escaped_col})) as min_length,
                                MAX(LENGTH({escaped_col})) as max_length
                            FROM {escaped_table}
                            WHERE {escaped_col} IS NOT NULL
                        """)
                        length_result = cursor.fetchone()
                        if length_result[0] is not None:
                            length_stats = {
                                "avg_length": round(length_result[0], 2),
                                "min_length": length_result[1],
                                "max_length": length_result[2]
                            }
                    
                    stats_result[col] = {
                        "column_type": "categorical",
                        "data_type": col_type,
                        "total_count": basic_info[0],
                        "non_null_count": basic_info[1],
                        "null_count": basic_info[2],
                        "null_percentage": round((basic_info[2] / basic_info[0]) * 100, 2) if basic_info[0] > 0 else 0,
                        "unique_count": unique_count,
                        "unique_percentage": round((unique_count / basic_info[1]) * 100, 2) if basic_info[1] > 0 else 0,
                        "top_values": [{
                            "value": str(val[0]),
                            "frequency": val[1],
                            "percentage": round((val[1] / basic_info[1]) * 100, 2) if basic_info[1] > 0 else 0
                        } for val in top_values],
                        "length_stats": length_stats
                    }
            
            # 添加汇总信息
            summary = {
                "total_columns": len(target_columns),
                "numeric_columns": len(numeric_columns),
                "categorical_columns": len(text_columns),
                "numeric_column_names": numeric_columns,
                "categorical_column_names": text_columns
            }
            
            return {
                "column_stats": stats_result,
                "summary": summary
            }
            
    except Exception as e:
        return {"error": f"计算统计信息失败: {str(e)}"}

def _calculate_correlation(table_name: str, columns: list, options: dict) -> dict:
    """计算相关系数"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取数值列
            if columns and len(columns) >= 2:
                numeric_columns = columns[:10]  # 限制最多10列
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                all_columns = cursor.fetchall()
                numeric_columns = [col[1] for col in all_columns if col[2] in ['INTEGER', 'REAL', 'NUMERIC']][:10]
            
            if len(numeric_columns) < 2:
                return {"error": "需要至少2个数值列来计算相关性"}
            
            # 获取数据
            escaped_columns = [_escape_identifier(col) for col in numeric_columns]
            columns_str = ", ".join(escaped_columns)
            df = pd.read_sql(f"SELECT {columns_str} FROM {escaped_table}", conn)
            
            # 重命名列为原始名称（去掉转义符号）
            df.columns = numeric_columns
            
            # 计算相关系数矩阵
            correlation_matrix = df.corr().round(4)
            
            # 转换为字典格式
            result = {}
            for i, col1 in enumerate(numeric_columns):
                result[col1] = {}
                for j, col2 in enumerate(numeric_columns):
                    result[col1][col2] = correlation_matrix.iloc[i, j]
            
            return {
                "correlation_matrix": result,
                "columns": numeric_columns,
                "method": "pearson"
            }
            
    except Exception as e:
        return {"error": f"计算相关性失败: {str(e)}"}

def _detect_outliers(table_name: str, columns: list, options: dict) -> dict:
    """检测异常值"""
    try:
        method = options.get("method", "iqr")  # iqr 或 zscore
        threshold = options.get("threshold", 1.5)
        
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取数值列
            if columns:
                numeric_columns = columns[:5]  # 限制最多5列
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                all_columns = cursor.fetchall()
                numeric_columns = [col[1] for col in all_columns if col[2] in ['INTEGER', 'REAL', 'NUMERIC']][:5]
            
            if not numeric_columns:
                return {"error": "没有找到数值列来检测异常值"}
            
            outliers_result = {}
            
            for col in numeric_columns:
                escaped_col = _escape_identifier(col)
                
                # 获取数据
                cursor = conn.execute(f"SELECT {escaped_col} FROM {escaped_table} WHERE {escaped_col} IS NOT NULL")
                values = [row[0] for row in cursor.fetchall()]
                
                if len(values) < 4:  # 需要足够的数据点
                    outliers_result[col] = {
                        "method": method,
                        "outliers": [],
                        "outlier_count": 0,
                        "total_count": len(values),
                        "note": "数据点太少，无法检测异常值"
                    }
                    continue
                
                outliers = []
                
                if method == "iqr":
                    # IQR方法
                    q1 = np.percentile(values, 25)
                    q3 = np.percentile(values, 75)
                    iqr = q3 - q1
                    lower_bound = q1 - threshold * iqr
                    upper_bound = q3 + threshold * iqr
                    
                    outliers = [v for v in values if v < lower_bound or v > upper_bound]
                    
                    outliers_result[col] = {
                        "method": "IQR",
                        "threshold": threshold,
                        "q1": round(q1, 4),
                        "q3": round(q3, 4),
                        "iqr": round(iqr, 4),
                        "lower_bound": round(lower_bound, 4),
                        "upper_bound": round(upper_bound, 4),
                        "outliers": sorted(set(outliers)),
                        "outlier_count": len(outliers),
                        "total_count": len(values),
                        "outlier_percentage": round((len(outliers) / len(values)) * 100, 2)
                    }
                    
                elif method == "zscore":
                    # Z-score方法
                    mean_val = np.mean(values)
                    std_val = np.std(values)
                    
                    if std_val == 0:
                        outliers_result[col] = {
                            "method": "Z-score",
                            "outliers": [],
                            "outlier_count": 0,
                            "total_count": len(values),
                            "note": "标准差为0，无法使用Z-score方法"
                        }
                        continue
                    
                    z_scores = [(v - mean_val) / std_val for v in values]
                    outliers = [values[i] for i, z in enumerate(z_scores) if abs(z) > threshold]
                    
                    outliers_result[col] = {
                        "method": "Z-score",
                        "threshold": threshold,
                        "mean": round(mean_val, 4),
                        "std": round(std_val, 4),
                        "outliers": sorted(set(outliers)),
                        "outlier_count": len(outliers),
                        "total_count": len(values),
                        "outlier_percentage": round((len(outliers) / len(values)) * 100, 2)
                    }
            
            return {
                "outliers_by_column": outliers_result,
                "columns_analyzed": numeric_columns,
                "method": method
            }
            
    except Exception as e:
        return {"error": f"异常值检测失败: {str(e)}"}

def _check_missing_values(table_name: str, columns: list, options: dict) -> dict:
    """检查缺失值"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取列信息
            if columns:
                target_columns = columns
            else:
                cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                target_columns = [col[1] for col in cursor.fetchall()]
            
            if not target_columns:
                return {"error": "没有找到可分析的列"}
            
            # 获取总行数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
            total_rows = cursor.fetchone()[0]
            
            missing_result = {}
            
            for col in target_columns:
                escaped_col = _escape_identifier(col)
                
                # 计算缺失值
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT({escaped_col}) as non_null,
                        COUNT(CASE WHEN {escaped_col} IS NULL THEN 1 END) as null_count
                    FROM {escaped_table}
                """)
                stats = cursor.fetchone()
                
                null_count = stats[2]
                null_percentage = (null_count / total_rows) * 100 if total_rows > 0 else 0
                
                missing_result[col] = {
                    "total_count": total_rows,
                    "non_null_count": stats[1],
                    "null_count": null_count,
                    "null_percentage": round(null_percentage, 2),
                    "completeness": round(100 - null_percentage, 2)
                }
            
            # 汇总统计
            total_missing = sum(col_data["null_count"] for col_data in missing_result.values())
            total_cells = total_rows * len(target_columns)
            overall_completeness = ((total_cells - total_missing) / total_cells) * 100 if total_cells > 0 else 0
            
            summary = {
                "total_rows": total_rows,
                "total_columns": len(target_columns),
                "total_cells": total_cells,
                "total_missing_cells": total_missing,
                "overall_completeness": round(overall_completeness, 2),
                "columns_with_missing": [col for col, data in missing_result.items() if data["null_count"] > 0],
                "complete_columns": [col for col, data in missing_result.items() if data["null_count"] == 0]
            }
            
            return {
                "missing_by_column": missing_result,
                "summary": summary
            }
            
    except Exception as e:
        return {"error": f"缺失值检查失败: {str(e)}"}

def _check_duplicates(table_name: str, columns: list, options: dict) -> dict:
    """检查重复值"""
    try:
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取总行数
            cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
            total_rows = cursor.fetchone()[0]
            
            if total_rows == 0:
                return {"error": "表为空，无法检查重复值"}
            
            # 检查完全重复的行
            if columns:
                # 检查指定列的重复
                escaped_columns = [_escape_identifier(col) for col in columns]
                columns_str = ", ".join(escaped_columns)
                
                cursor = conn.execute(f"""
                    SELECT COUNT(*) as unique_count
                    FROM (SELECT DISTINCT {columns_str} FROM {escaped_table})
                """)
                unique_rows = cursor.fetchone()[0]
                
                # 获取重复的组合
                cursor = conn.execute(f"""
                    SELECT {columns_str}, COUNT(*) as freq
                    FROM {escaped_table}
                    GROUP BY {columns_str}
                    HAVING COUNT(*) > 1
                    ORDER BY freq DESC
                    LIMIT 10
                """)
                duplicates = cursor.fetchall()
                
                duplicate_count = total_rows - unique_rows
                
                result = {
                    "check_type": "specified_columns",
                    "columns_checked": columns,
                    "total_rows": total_rows,
                    "unique_combinations": unique_rows,
                    "duplicate_rows": duplicate_count,
                    "duplicate_percentage": round((duplicate_count / total_rows) * 100, 2) if total_rows > 0 else 0,
                    "duplicate_groups": [{
                        "values": dict(zip(columns, dup[:-1])),
                        "frequency": dup[-1]
                    } for dup in duplicates]
                }
                
            else:
                # 检查完全重复的行（所有列）
                cursor = conn.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {escaped_table})")
                unique_rows = cursor.fetchone()[0]
                
                duplicate_count = total_rows - unique_rows
                
                result = {
                    "check_type": "complete_rows",
                    "total_rows": total_rows,
                    "unique_rows": unique_rows,
                    "duplicate_rows": duplicate_count,
                    "duplicate_percentage": round((duplicate_count / total_rows) * 100, 2) if total_rows > 0 else 0,
                    "note": "检查了所有列的完全重复"
                }
            
            return result
            
    except Exception as e:
        return {"error": f"重复值检查失败: {str(e)}"}

# ================================
# 数据信息获取辅助函数
# ================================

def _get_local_tables() -> str:
    """获取本地数据库表列表"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = cursor.fetchall()
            
            # 获取每个表的行数
            table_info = []
            for table_name, create_sql in tables:
                try:
                    escaped_table = _escape_identifier(table_name)
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
                    row_count = cursor.fetchone()[0]
                    
                    # 获取列数
                    cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
                    columns = cursor.fetchall()
                    column_count = len(columns)
                    
                    table_info.append({
                        "table_name": table_name,
                        "row_count": row_count,
                        "column_count": column_count,
                        "create_sql": create_sql
                    })
                except Exception as e:
                    table_info.append({
                        "table_name": table_name,
                        "row_count": "error",
                        "column_count": "error",
                        "error": str(e)
                    })
            
            result = {
                "status": "success",
                "message": f"找到 {len(table_info)} 个表",
                "data": {
                    "tables": table_info,
                    "table_count": len(table_info)
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "info_type": "tables",
                    "data_source": "本地SQLite"
                }
            }
            
            return f"✅ 表列表获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        result = {
            "status": "error",
            "message": f"获取表列表失败: {str(e)}"
        }
        return f"❌ 获取表列表失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _get_table_schema(table_name: str) -> str:
    """获取表结构信息"""
    try:
        if not _table_exists(table_name):
            result = {
                "status": "error",
                "message": f"表 '{table_name}' 不存在"
            }
            return f"❌ 表不存在\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取列信息
            cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
            columns = cursor.fetchall()
            
            # 获取索引信息
            cursor = conn.execute(f"PRAGMA index_list({escaped_table})")
            indexes = cursor.fetchall()
            
            # 获取外键信息
            cursor = conn.execute(f"PRAGMA foreign_key_list({escaped_table})")
            foreign_keys = cursor.fetchall()
            
            # 格式化列信息
            column_info = []
            for col in columns:
                column_info.append({
                    "column_id": col[0],
                    "name": col[1],
                    "type": col[2],
                    "not_null": bool(col[3]),
                    "default_value": col[4],
                    "primary_key": bool(col[5])
                })
            
            # 格式化索引信息
            index_info = []
            for idx in indexes:
                index_info.append({
                    "name": idx[1],
                    "unique": bool(idx[2]),
                    "origin": idx[3]
                })
            
            result = {
                "status": "success",
                "message": f"表 '{table_name}' 结构信息",
                "data": {
                    "table_name": table_name,
                    "columns": column_info,
                    "column_count": len(column_info),
                    "indexes": index_info,
                    "foreign_keys": [dict(zip(["id", "seq", "table", "from", "to", "on_update", "on_delete", "match"], fk)) for fk in foreign_keys]
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "info_type": "schema",
                    "table_name": table_name,
                    "data_source": "本地SQLite"
                }
            }
            
            return f"✅ 表结构获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"获取表结构失败: {e}")
        result = {
            "status": "error",
            "message": f"获取表结构失败: {str(e)}"
        }
        return f"❌ 获取表结构失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _get_table_stats(table_name: str) -> str:
    """获取表统计信息"""
    try:
        if not _table_exists(table_name):
            result = {
                "status": "error",
                "message": f"表 '{table_name}' 不存在"
            }
            return f"❌ 表不存在\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        escaped_table = _escape_identifier(table_name)
        
        with get_db_connection() as conn:
            # 获取基本统计
            cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
            row_count = cursor.fetchone()[0]
            
            # 获取列信息
            cursor = conn.execute(f"PRAGMA table_info({escaped_table})")
            columns = cursor.fetchall()
            column_count = len(columns)
            
            # 获取表大小（近似）
            cursor = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            
            # 简单的列类型统计
            column_types = {}
            for col in columns:
                col_type = col[2].upper()
                column_types[col_type] = column_types.get(col_type, 0) + 1
            
            result = {
                "status": "success",
                "message": f"表 '{table_name}' 统计信息",
                "data": {
                    "table_name": table_name,
                    "row_count": row_count,
                    "column_count": column_count,
                    "estimated_size_bytes": db_size,
                    "column_types": column_types,
                    "columns": [{
                        "name": col[1],
                        "type": col[2],
                        "nullable": not bool(col[3]),
                        "primary_key": bool(col[5])
                    } for col in columns]
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "info_type": "stats",
                    "table_name": table_name,
                    "data_source": "本地SQLite"
                }
            }
            
            return f"✅ 表统计获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"获取表统计失败: {e}")
        result = {
            "status": "error",
            "message": f"获取表统计失败: {str(e)}"
        }
        return f"❌ 获取表统计失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _analyze_database_cleanup() -> str:
    """分析数据库并提供清理建议"""
    try:
        with get_db_connection() as conn:
            # 获取所有表（排除元数据表）
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != '_metadata' AND name != 'data_metadata'"
            )
            all_tables = [row[0] for row in cursor.fetchall()]
            
            if not all_tables:
                result = {
                    "status": "success",
                    "message": "数据库中没有用户表",
                    "data": {
                        "total_tables": 0,
                        "cleanup_suggestions": []
                    }
                }
                return f"✅ 数据库清理分析完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            cleanup_suggestions = []
            empty_tables = []
            test_tables = []
            temp_tables = []
            
            for table_name in all_tables:
                try:
                    escaped_table = _escape_identifier(table_name)
                    
                    # 检查表是否为空
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {escaped_table}")
                    row_count = cursor.fetchone()[0]
                    
                    if row_count == 0:
                        empty_tables.append(table_name)
                    
                    # 检查是否是测试表或临时表
                    table_lower = table_name.lower()
                    if any(keyword in table_lower for keyword in ['test', 'temp', 'tmp', 'demo', 'sample']):
                        if 'test' in table_lower:
                            test_tables.append(table_name)
                        else:
                            temp_tables.append(table_name)
                    
                except Exception as e:
                    logger.warning(f"分析表 {table_name} 时出错: {e}")
            
            # 生成清理建议
            if empty_tables:
                cleanup_suggestions.append({
                    "type": "empty_tables",
                    "description": "发现空表，可以考虑删除",
                    "tables": empty_tables,
                    "count": len(empty_tables),
                    "risk_level": "low"
                })
            
            if test_tables:
                cleanup_suggestions.append({
                    "type": "test_tables",
                    "description": "发现测试表，可以考虑删除",
                    "tables": test_tables,
                    "count": len(test_tables),
                    "risk_level": "medium"
                })
            
            if temp_tables:
                cleanup_suggestions.append({
                    "type": "temp_tables",
                    "description": "发现临时表，可以考虑删除",
                    "tables": temp_tables,
                    "count": len(temp_tables),
                    "risk_level": "low"
                })
            
            result = {
                "status": "success",
                "message": f"数据库清理分析完成，发现 {len(cleanup_suggestions)} 类清理建议",
                "data": {
                    "total_tables": len(all_tables),
                    "cleanup_suggestions": cleanup_suggestions,
                    "summary": {
                        "empty_tables": len(empty_tables),
                        "test_tables": len(test_tables),
                        "temp_tables": len(temp_tables),
                        "total_suggested_for_cleanup": len(empty_tables) + len(test_tables) + len(temp_tables)
                    }
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "info_type": "cleanup",
                    "data_source": "本地SQLite"
                }
            }
            
            return f"✅ 数据库清理分析完成\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
    except Exception as e:
        logger.error(f"数据库清理分析失败: {e}")
        result = {
            "status": "error",
            "message": f"数据库清理分析失败: {str(e)}"
        }
        return f"❌ 数据库清理分析失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

# ================================
# 模块初始化函数
# ================================

def init_data_analysis_module():
    """初始化数据分析模块"""
    logger.info("数据分析模块初始化完成")
    return {
        "analyze_data_impl": analyze_data_impl,
        "get_data_info_impl": get_data_info_impl
    }