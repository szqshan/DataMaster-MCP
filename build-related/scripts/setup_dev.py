#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMaster MCP 开发环境设置脚本

这个脚本自动设置完整的开发环境：
1. 检查 Python 版本
2. 创建虚拟环境（可选）
3. 安装开发依赖
4. 以开发模式安装项目
5. 运行测试验证
6. 生成开发配置文件

用法:
    python scripts/setup_dev.py
    python scripts/setup_dev.py --venv  # 创建虚拟环境
    python scripts/setup_dev.py --test-only  # 仅运行测试
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    print("🔍 检查 Python 版本...")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (满足要求 >= 3.8)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (需要 >= 3.8)")
        return False

def run_command(cmd, description, check=True):
    """运行命令并处理结果"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check)
        if result.returncode == 0:
            print(f"✅ {description}成功")
            return True
        else:
            print(f"❌ {description}失败")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        return False
    except Exception as e:
        print(f"❌ {description}异常: {e}")
        return False

def create_virtual_env():
    """创建虚拟环境"""
    venv_path = Path('venv')
    
    if venv_path.exists():
        print("⚠️  虚拟环境已存在，跳过创建")
        return True
    
    if not run_command('python -m venv venv', '创建虚拟环境'):
        return False
    
    print("\n💡 激活虚拟环境:")
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\activate")
    else:  # Unix/Linux/macOS
        print("   source venv/bin/activate")
    
    return True

def install_dependencies():
    """安装依赖包"""
    dependencies = [
        ('pip install --upgrade pip', '升级 pip'),
        ('pip install -r requirements.txt', '安装项目依赖'),
        ('pip install build twine', '安装构建工具'),
        ('pip install black flake8 pytest', '安装开发工具'),
        ('pip install -e .', '以开发模式安装项目')
    ]
    
    for cmd, desc in dependencies:
        if not run_command(cmd, desc):
            return False
    
    return True

def create_dev_config():
    """创建开发配置文件"""
    print("🔄 创建开发配置文件...")
    
    # 创建 .env.dev 文件
    env_dev_content = """
# DataMaster MCP 开发环境配置
# 复制到 .env 文件中使用

# 调试模式
DEBUG=true
LOG_LEVEL=DEBUG
TEST_MODE=true

# 数据库配置（开发用）
DB_PATH=data/dev_analysis.db

# API 配置（开发用）
# WEATHER_API_KEY=your_dev_api_key
# CUSTOM_API_TOKEN=your_dev_token

# 其他开发配置
DATA_DIR=data
EXPORTS_DIR=exports
"""
    
    try:
        with open('.env.dev', 'w', encoding='utf-8') as f:
            f.write(env_dev_content.strip())
        print("✅ 创建 .env.dev 配置文件")
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False
    
    # 创建开发脚本快捷方式
    dev_scripts = {
        'dev_test.py': """
#!/usr/bin/env python3
# 快速测试脚本
import subprocess
import sys

def main():
    print("🧪 运行开发测试...")
    
    # 运行测试
    result1 = subprocess.run([sys.executable, 'test_mcp_server.py'])
    
    # 检查包导入
    result2 = subprocess.run([sys.executable, '-c', 'import datamaster_mcp; print(f"版本: {datamaster_mcp.__version__}")'])
    
    if result1.returncode == 0 and result2.returncode == 0:
        print("🎉 所有测试通过！")
    else:
        print("❌ 测试失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
""",
        'dev_start.py': """
#!/usr/bin/env python3
# 快速启动脚本
import subprocess
import sys

def main():
    print("🚀 启动开发服务器...")
    try:
        subprocess.run([sys.executable, 'start_mcp_server.py'])
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")

if __name__ == '__main__':
    main()
"""
    }
    
    for script_name, content in dev_scripts.items():
        try:
            with open(script_name, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            print(f"✅ 创建开发脚本 {script_name}")
        except Exception as e:
            print(f"❌ 创建 {script_name} 失败: {e}")
    
    return True

def run_tests():
    """运行测试验证环境"""
    print("\n🧪 验证开发环境...")
    
    if not run_command('python test_mcp_server.py', '运行完整测试'):
        return False
    
    # 测试包导入
    test_import_cmd = 'python -c "import datamaster_mcp; print(f\'✅ 包版本: {datamaster_mcp.__version__}\')"'
    if not run_command(test_import_cmd, '测试包导入'):
        return False
    
    return True

def print_next_steps():
    """打印后续步骤"""
    print("\n" + "=" * 60)
    print("🎉 开发环境设置完成！")
    print("\n📋 后续开发步骤:")
    
    print("\n1️⃣ 日常开发:")
    print("   python dev_test.py          # 快速测试")
    print("   python dev_start.py         # 启动服务器")
    print("   python start_mcp_server.py  # 完整启动")
    
    print("\n2️⃣ 代码质量:")
    print("   black datamaster_mcp/       # 代码格式化")
    print("   flake8 datamaster_mcp/      # 代码检查")
    
    print("\n3️⃣ 版本发布:")
    print("   python scripts/release.py 1.0.2        # 发布新版本")
    print("   python scripts/release.py 1.0.2 --test # 测试发布流程")
    
    print("\n4️⃣ 配置文件:")
    print("   .env.dev                    # 开发环境配置模板")
    print("   claude_desktop_config_example.json  # Claude 配置")
    
    print("\n📚 文档:")
    print("   DEVELOPMENT_WORKFLOW.md     # 完整开发流程")
    print("   LOCAL_TEST_GUIDE.md         # 本地测试指南")
    
    print("\n💡 提示:")
    print("   - 修改代码后会立即生效（开发模式安装）")
    print("   - 使用 Git 分支管理功能开发")
    print("   - 发布前务必运行完整测试")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DataMaster MCP 开发环境设置')
    parser.add_argument('--venv', action='store_true', help='创建虚拟环境')
    parser.add_argument('--test-only', action='store_true', help='仅运行测试')
    parser.add_argument('--skip-deps', action='store_true', help='跳过依赖安装')
    
    args = parser.parse_args()
    
    print("🛠️  DataMaster MCP 开发环境设置")
    print("=" * 50)
    
    # 仅测试模式
    if args.test_only:
        if run_tests():
            print("🎉 测试通过，开发环境正常！")
        else:
            print("❌ 测试失败，请检查环境配置")
            sys.exit(1)
        return
    
    # 1. 检查 Python 版本
    if not check_python_version():
        sys.exit(1)
    
    # 2. 创建虚拟环境（可选）
    if args.venv:
        if not create_virtual_env():
            sys.exit(1)
        print("\n⚠️  请先激活虚拟环境，然后重新运行此脚本")
        return
    
    # 3. 安装依赖
    if not args.skip_deps:
        if not install_dependencies():
            print("❌ 依赖安装失败")
            sys.exit(1)
    
    # 4. 创建开发配置
    if not create_dev_config():
        print("⚠️  配置文件创建失败，但不影响开发")
    
    # 5. 运行测试验证
    if not run_tests():
        print("❌ 环境验证失败")
        sys.exit(1)
    
    # 6. 打印后续步骤
    print_next_steps()

if __name__ == "__main__":
    # 确保在项目根目录运行
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    main()