#!/usr/bin/env python3
"""
DataMaster MCP - 超级数据分析工具
为AI提供强大的数据分析能力

核心理念：工具专注数据获取和计算，AI专注智能分析和洞察
"""

__version__ = "1.0.2"
__author__ = "Shan (学习AI1000天)"

# 导出主要接口
from .main import main

# 导出版本信息
__all__ = ["main", "__version__", "__author__"]