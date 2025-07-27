#!/usr/bin/env python3
"""
测试脚本：验证 DataMaster MCP 包的基本功能
"""

import sys
import os

def test_import():
    """测试包导入"""
    try:
        import datamaster_mcp
        print(f"✅ 包导入成功")
        print(f"   版本: {datamaster_mcp.__version__}")
        print(f"   作者: {datamaster_mcp.__author__}")
        return True
    except ImportError as e:
        print(f"❌ 包导入失败: {e}")
        return False

def test_main_function():
    """测试主函数"""
    try:
        from datamaster_mcp import main
        print(f"✅ 主函数导入成功")
        return True
    except ImportError as e:
        print(f"❌ 主函数导入失败: {e}")
        return False

def test_config_modules():
    """测试配置模块"""
    try:
        from datamaster_mcp.config import database_manager
        from datamaster_mcp.config import config_manager
        from datamaster_mcp.config import api_config_manager
        print(f"✅ 配置模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 配置模块导入失败: {e}")
        return False

def test_dependencies():
    """测试核心依赖"""
    dependencies = [
        ('pandas', 'pd'),
        ('numpy', 'np'),
        ('openpyxl', None),
        ('scipy', None),
        ('requests', None),
    ]
    
    success_count = 0
    for dep_name, alias in dependencies:
        try:
            if alias:
                exec(f"import {dep_name} as {alias}")
            else:
                exec(f"import {dep_name}")
            print(f"✅ {dep_name} 导入成功")
            success_count += 1
        except ImportError as e:
            print(f"❌ {dep_name} 导入失败: {e}")
    
    return success_count == len(dependencies)

def main():
    """运行所有测试"""
    print("🧪 DataMaster MCP 包测试")
    print("=" * 50)
    
    tests = [
        ("包导入测试", test_import),
        ("主函数测试", test_main_function),
        ("配置模块测试", test_config_modules),
        ("依赖测试", test_dependencies),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"   测试失败")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！包已准备好发布。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查问题后再发布。")
        return 1

if __name__ == "__main__":
    sys.exit(main())