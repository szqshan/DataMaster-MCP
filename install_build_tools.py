#!/usr/bin/env python3
"""
安装 PyPI 发布工具脚本
"""

import subprocess
import sys
import os

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ {description} 成功")
        if result.stdout.strip():
            print(f"   输出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败")
        print(f"   错误: {e.stderr.strip() if e.stderr else str(e)}")
        return False

def check_tool_installed(tool_name):
    """检查工具是否已安装"""
    try:
        result = subprocess.run(
            f"{tool_name} --version", 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ {tool_name} 已安装: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {tool_name} 未安装")
        return False

def main():
    """主函数"""
    print("🚀 PyPI 发布工具安装脚本")
    print("=" * 50)
    
    # 检查 Python 版本
    python_version = sys.version_info
    print(f"🐍 Python 版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("⚠️  警告: Python 版本低于 3.8，可能不兼容")
    
    print("\n🔍 检查已安装的工具:")
    
    # 检查已安装的工具
    tools = ['pip', 'twine', 'build']
    installed_tools = []
    
    for tool in tools:
        if check_tool_installed(tool):
            installed_tools.append(tool)
    
    # 安装缺失的工具
    missing_tools = set(tools) - set(installed_tools)
    
    if missing_tools:
        print(f"\n📦 需要安装的工具: {', '.join(missing_tools)}")
        
        # 升级 pip
        if not run_command(
            "python -m pip install --upgrade pip", 
            "升级 pip"
        ):
            print("⚠️  pip 升级失败，继续安装其他工具...")
        
        # 安装发布工具
        install_command = "python -m pip install --upgrade setuptools wheel twine build"
        if run_command(install_command, "安装发布工具"):
            print("\n🎉 发布工具安装完成！")
        else:
            print("\n❌ 发布工具安装失败")
            return 1
    else:
        print("\n✅ 所有必需工具已安装")
    
    print("\n" + "=" * 50)
    print("📋 下一步操作:")
    print("1. 注册 PyPI 账户: https://pypi.org/account/register/")
    print("2. 注册 TestPyPI 账户: https://test.pypi.org/account/register/")
    print("3. 创建 API Token")
    print("4. 更新 setup.py 中的邮箱地址")
    print("5. 运行构建命令: python -m build")
    print("6. 运行发布命令: twine upload dist/*")
    print("\n📖 详细说明请查看: PYPI_RELEASE_GUIDE.md")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())