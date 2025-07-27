#!/usr/bin/env python3
"""
DataMaster MCP 服务器测试脚本
用于验证 MCP 服务器是否能正常启动和运行
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path

def test_imports():
    """测试包导入"""
    print("🔍 测试包导入...")
    try:
        # 添加当前目录到 Python 路径
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))
        
        import datamaster_mcp
        print(f"✅ datamaster_mcp 导入成功")
        print(f"   版本: {datamaster_mcp.__version__}")
        print(f"   作者: {datamaster_mcp.__author__}")
        
        from datamaster_mcp import main
        print(f"✅ main 模块导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 包导入失败: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n🔍 测试依赖包...")
    dependencies = [
        ('mcp', 'MCP 框架'),
        ('pandas', '数据处理'),
        ('numpy', '数值计算'),
        ('openpyxl', 'Excel 支持'),
        ('scipy', '科学计算'),
        ('requests', 'HTTP 请求')
    ]
    
    success_count = 0
    for package, description in dependencies:
        try:
            __import__(package)
            print(f"✅ {package} ({description}) 导入成功")
            success_count += 1
        except ImportError as e:
            print(f"❌ {package} ({description}) 导入失败: {e}")
    
    print(f"\n📊 依赖包测试结果: {success_count}/{len(dependencies)} 通过")
    return success_count == len(dependencies)

def test_config_files():
    """测试配置文件"""
    print("\n🔍 测试配置文件...")
    
    config_files = [
        'datamaster_mcp/config/database_config.json',
        'datamaster_mcp/config/api_config.json'
    ]
    
    success = True
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"✅ {config_file} 格式正确")
            except json.JSONDecodeError as e:
                print(f"❌ {config_file} JSON 格式错误: {e}")
                success = False
        else:
            print(f"⚠️  {config_file} 不存在（可选文件）")
    
    return success

def test_directory_structure():
    """测试目录结构"""
    print("\n🔍 测试目录结构...")
    
    required_paths = [
        'datamaster_mcp/__init__.py',
        'datamaster_mcp/main.py',
        'datamaster_mcp/config/__init__.py',
        'requirements.txt'
    ]
    
    missing_files = []
    for path in required_paths:
        if os.path.exists(path):
            print(f"✅ {path} 存在")
        else:
            print(f"❌ {path} 缺失")
            missing_files.append(path)
    
    if missing_files:
        print(f"\n⚠️  缺失文件: {missing_files}")
        return False
    return True

def test_mcp_server_startup():
    """测试 MCP 服务器启动（非阻塞）"""
    print("\n🔍 测试 MCP 服务器启动...")
    
    try:
        # 尝试导入并初始化（不实际启动服务器）
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))
        
        from datamaster_mcp.main import init_database, mcp
        
        # 测试数据库初始化
        init_database()
        print("✅ 数据库初始化成功")
        
        # 检查 MCP 服务器对象
        if hasattr(mcp, 'tools'):
            tool_count = len(mcp.tools)
            print(f"✅ MCP 服务器初始化成功，注册了 {tool_count} 个工具")
        else:
            print("✅ MCP 服务器对象创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP 服务器启动测试失败: {e}")
        return False

def create_test_data():
    """创建测试数据文件"""
    print("\n🔍 创建测试数据...")
    
    try:
        import pandas as pd
        
        # 创建测试数据
        data = {
            'name': ['张三', '李四', '王五', '赵六', '钱七'],
            'age': [25, 30, 35, 28, 32],
            'salary': [5000, 8000, 12000, 6500, 9500],
            'department': ['IT', 'HR', 'Finance', 'IT', 'Marketing']
        }
        
        df = pd.DataFrame(data)
        
        # 确保目录存在
        os.makedirs('test_data', exist_ok=True)
        
        # 保存为 Excel 文件
        excel_file = 'test_data/sample_data.xlsx'
        df.to_excel(excel_file, index=False)
        print(f"✅ 测试 Excel 文件已创建: {excel_file}")
        
        # 保存为 CSV 文件
        csv_file = 'test_data/sample_data.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"✅ 测试 CSV 文件已创建: {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建测试数据失败: {e}")
        return False

def generate_claude_config():
    """生成 Claude Desktop 配置示例"""
    print("\n🔍 生成 Claude Desktop 配置...")
    
    current_path = os.path.abspath('.')
    main_py_path = os.path.join(current_path, 'datamaster_mcp', 'main.py')
    
    config = {
        "mcpServers": {
            "datamaster-mcp": {
                "command": "python",
                "args": [main_py_path.replace('\\', '\\\\')],
                "env": {
                    "PYTHONPATH": current_path.replace('\\', '\\\\')
                }
            }
        }
    }
    
    config_file = 'claude_desktop_config_example.json'
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Claude Desktop 配置示例已生成: {config_file}")
        print(f"   请将此配置复制到 Claude Desktop 的配置文件中")
        return True
    except Exception as e:
        print(f"❌ 生成配置失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 DataMaster MCP 服务器测试")
    print("=" * 50)
    
    tests = [
        ("目录结构", test_directory_structure),
        ("包导入", test_imports),
        ("依赖包", test_dependencies),
        ("配置文件", test_config_files),
        ("MCP服务器", test_mcp_server_startup),
        ("测试数据", create_test_data),
        ("Claude配置", generate_claude_config)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！MCP 服务器准备就绪！")
        print("\n🚀 下一步操作:")
        print("1. 将 claude_desktop_config_example.json 中的配置复制到 Claude Desktop")
        print("2. 重启 Claude Desktop")
        print("3. 在 Claude 中测试 DataMaster MCP 功能")
        print("\n💡 或者直接运行: python -m datamaster_mcp.main")
    else:
        print("⚠️  部分测试失败，请检查上述错误信息")
        print("\n🔧 常见解决方案:")
        print("1. 运行: pip install -r requirements.txt")
        print("2. 确保在正确的项目目录中")
        print("3. 检查 Python 版本 >= 3.8")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)