#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMaster MCP 自动发布脚本

这个脚本自动化版本发布流程：
1. 更新所有文件中的版本号
2. 运行测试确保代码质量
3. 构建和检查包
4. 创建 Git 提交和标签
5. 提供发布指导

用法:
    python scripts/release.py 1.0.2
    python scripts/release.py 1.1.0 --test  # 仅测试，不实际发布
"""

import sys
import os
import subprocess
import re
import argparse
from pathlib import Path

def update_version_in_file(file_path, pattern, replacement):
    """更新单个文件中的版本号"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 更新 {file_path} 中的版本号")
            return True
        else:
            print(f"⚠️  在 {file_path} 中未找到版本号模式")
            return False
    except Exception as e:
        print(f"❌ 更新 {file_path} 失败: {e}")
        return False

def update_version(new_version):
    """更新所有文件中的版本号"""
    print(f"🔄 更新版本号到 {new_version}...")
    
    files_to_update = [
        ('setup.py', r'version = "[^"]+"', f'version = "{new_version}"'),  # setup.py 中的 fallback version
        ('pyproject.toml', r'version = "[^"]+"', f'version = "{new_version}"'),
        ('datamaster_mcp/__init__.py', r'__version__ = "[^"]+"', f'__version__ = "{new_version}"')
    ]
    
    success_count = 0
    for file_path, pattern, replacement in files_to_update:
        if update_version_in_file(file_path, pattern, replacement):
            success_count += 1
    
    if success_count == len(files_to_update):
        print(f"🎉 所有文件版本号更新成功！")
        return True
    else:
        print(f"⚠️  只有 {success_count}/{len(files_to_update)} 个文件更新成功")
        return False

def run_command(cmd, description, check=True):
    """运行命令并处理结果"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description}成功")
            return True
        else:
            print(f"❌ {description}失败: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        return False
    except Exception as e:
        print(f"❌ {description}异常: {e}")
        return False

def validate_version(version):
    """验证版本号格式"""
    pattern = r'^\d+\.\d+\.\d+$'
    if re.match(pattern, version):
        return True
    else:
        print(f"❌ 版本号格式错误: {version}")
        print("   正确格式: x.y.z (如 1.0.2)")
        return False

def check_git_status():
    """检查 Git 状态"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout.strip():
            print("⚠️  工作目录有未提交的更改:")
            print(result.stdout)
            return False
        return True
    except Exception as e:
        print(f"❌ 检查 Git 状态失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DataMaster MCP 自动发布脚本')
    parser.add_argument('version', help='新版本号 (格式: x.y.z)')
    parser.add_argument('--test', action='store_true', help='仅测试，不实际发布')
    parser.add_argument('--skip-git-check', action='store_true', help='跳过 Git 状态检查')
    
    args = parser.parse_args()
    new_version = args.version
    
    print("🚀 DataMaster MCP 自动发布脚本")
    print("=" * 50)
    
    # 1. 验证版本号
    if not validate_version(new_version):
        sys.exit(1)
    
    # 2. 检查 Git 状态（可选）
    if not args.skip_git_check and not check_git_status():
        print("\n💡 提示: 请先提交或暂存当前更改，或使用 --skip-git-check 跳过检查")
        sys.exit(1)
    
    # 3. 更新版本号
    if not update_version(new_version):
        print("❌ 版本号更新失败")
        sys.exit(1)
    
    # 4. 运行测试
    if not run_command('python test_mcp_server.py', '运行测试'):
        print("❌ 测试失败，请修复后重试")
        sys.exit(1)
    
    # 5. 构建包
    if not run_command('python -m build', '构建包'):
        print("❌ 包构建失败")
        sys.exit(1)
    
    # 6. 检查包
    if not run_command('twine check dist/*', '检查包'):
        print("❌ 包检查失败")
        sys.exit(1)
    
    if args.test:
        print("\n🧪 测试模式完成，未实际发布")
        print("如需正式发布，请移除 --test 参数")
        return
    
    # 7. Git 操作
    print("\n📝 准备 Git 提交...")
    
    if not run_command('git add .', '添加文件到暂存区'):
        sys.exit(1)
    
    commit_msg = f'chore: 发布版本 {new_version}'
    if not run_command(f'git commit -m "{commit_msg}"', '创建提交'):
        sys.exit(1)
    
    tag_name = f'v{new_version}'
    if not run_command(f'git tag {tag_name}', f'创建标签 {tag_name}'):
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print(f"🎉 版本 {new_version} 准备完成！")
    print("\n📋 下一步手动操作:")
    print(f"1. 推送代码: git push origin master")
    print(f"2. 推送标签: git push origin {tag_name}")
    print(f"3. 发布到 PyPI: twine upload dist/*")
    print(f"4. 清理构建文件: rm -rf dist/ build/ *.egg-info/")
    
    print("\n💡 或者运行以下命令一键完成:")
    print(f"git push origin master && git push origin {tag_name} && twine upload dist/*")
    
    print("\n🔗 相关链接:")
    print(f"- GitHub: https://github.com/szqshan/DataMaster/releases/tag/{tag_name}")
    print(f"- PyPI: https://pypi.org/project/datamaster-mcp/{new_version}/")

if __name__ == "__main__":
    # 确保在项目根目录运行
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    main()