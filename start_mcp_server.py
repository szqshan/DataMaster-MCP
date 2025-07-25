#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMaster MCP 服务器启动脚本

这个脚本用于直接启动 DataMaster MCP 服务器，方便本地测试和开发。

使用方法:
    python start_mcp_server.py

或者:
    python -m datamaster_mcp.main
"""

import sys
import os
from pathlib import Path

def main():
    """启动 MCP 服务器"""
    print("🚀 启动 DataMaster MCP 服务器...")
    print("=" * 50)
    
    # 确保当前目录在 Python 路径中
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    try:
        # 导入并启动 MCP 服务器
        from datamaster_mcp.main import main as mcp_main
        
        print("✅ DataMaster MCP 模块加载成功")
        print("📡 正在启动 MCP 服务器...")
        print("\n💡 提示: 按 Ctrl+C 停止服务器")
        print("=" * 50)
        
        # 启动服务器
        mcp_main()
        
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")
        sys.exit(0)
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("\n🔧 解决方案:")
        print("1. 确保在正确的项目目录中")
        print("2. 运行: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n🔧 请检查:")
        print("1. Python 版本 >= 3.8")
        print("2. 所有依赖包已安装")
        print("3. 项目文件完整")
        sys.exit(1)

if __name__ == "__main__":
    main()