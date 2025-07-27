#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMaster MCP PyPI 发布验证脚本
用于验证 PyPI 发布是否成功
"""

import subprocess
import sys
import tempfile
import os

def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def verify_pypi_release():
    """验证 PyPI 发布"""
    print("🔍 开始验证 DataMaster MCP PyPI 发布...")
    print("=" * 50)
    
    # 创建临时目录进行测试
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 创建临时测试目录: {temp_dir}")
        
        # 1. 测试包安装
        print("\n1️⃣ 测试包安装...")
        success, stdout, stderr = run_command(
            "pip install datamaster-mcp --force-reinstall", 
            cwd=temp_dir
        )
        
        if success:
            print("✅ 包安装成功")
        else:
            print("❌ 包安装失败")
            print(f"错误: {stderr}")
            return False
        
        # 2. 测试包导入
        print("\n2️⃣ 测试包导入...")
        success, stdout, stderr = run_command(
            'python -c "import datamaster_mcp; print(f\'Version: {datamaster_mcp.__version__}\')"',
            cwd=temp_dir
        )
        
        if success:
            print("✅ 包导入成功")
            print(f"📦 {stdout.strip()}")
        else:
            print("❌ 包导入失败")
            print(f"错误: {stderr}")
            return False
        
        # 3. 测试 MCP 服务器启动
        print("\n3️⃣ 测试 MCP 服务器...")
        success, stdout, stderr = run_command(
            'python -c "from datamaster_mcp.main import main; print(\'MCP 服务器模块加载成功\')"',
            cwd=temp_dir
        )
        
        if success:
            print("✅ MCP 服务器模块加载成功")
        else:
            print("❌ MCP 服务器模块加载失败")
            print(f"错误: {stderr}")
            return False
        
        # 4. 检查 PyPI 页面
        print("\n4️⃣ PyPI 页面信息...")
        print("🌐 PyPI 页面: https://pypi.org/project/datamaster-mcp/")
        print("📚 项目文档: https://pypi.org/project/datamaster-mcp/1.0.1/")
        
        print("\n🎉 所有验证测试通过！")
        print("=" * 50)
        print("✨ DataMaster MCP 已成功发布到 PyPI！")
        print("\n📋 用户安装命令:")
        print("   pip install datamaster-mcp")
        print("\n🔄 用户更新命令:")
        print("   pip install -U datamaster-mcp")
        
        return True

if __name__ == "__main__":
    try:
        success = verify_pypi_release()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        sys.exit(1)