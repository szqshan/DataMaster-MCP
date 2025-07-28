#!/usr/bin/env python3
"""
DataMaster MCP - 核心功能模块包

这个包包含了DataMaster MCP的核心功能模块：
- database.py: 数据库连接和操作
- data_analysis.py: 数据分析功能
- data_processing.py: 数据处理功能
- api_manager.py: API管理功能
"""

__version__ = "1.0.3"
__author__ = "DataMaster Team"

# 导出核心模块
__all__ = [
    'database',
    'data_analysis', 
    'data_processing',
    'api_manager'
]