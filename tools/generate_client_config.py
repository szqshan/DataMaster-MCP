#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataMaster MCP 客户端配置生成器
自动生成 Claude Desktop 配置文件
"""

import json
import os
import sys
import platform
from pathlib import Path

def get_claude_config_path():
    """获取 Claude Desktop 配置文件路径"""
    system = platform.system().lower()
    
    if system == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif system == "darwin":  # macOS
        home = Path.home()
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "linux":
        home = Path.home()
        return home / ".config" / "Claude" / "claude_desktop_config.json"
    
    return None

def get_datamaster_path():
    """获取 DataMaster MCP 安装路径"""
    try:
        import datamaster_mcp
        return Path(datamaster_mcp.__file__).parent / "main.py"
    except ImportError:
        return None

def generate_config(use_module_path=True):
    """生成配置字典"""
    if use_module_path:
        # 推荐方式：使用模块路径
        config = {
            "mcpServers": {
                "datamaster-mcp": {
                    "command": "python",
                    "args": [
                        "-m",
                        "datamaster_mcp.main"
                    ]
                }
            }
        }
    else:
        # 备用方式：使用完整路径
        datamaster_path = get_datamaster_path()
        if not datamaster_path:
            raise Exception("无法找到 DataMaster MCP 安装路径，请确保已正确安装包")
        
        config = {
            "mcpServers": {
                "datamaster-mcp": {
                    "command": "python",
                    "args": [
                        str(datamaster_path)
                    ]
                }
            }
        }
    
    return config

def load_existing_config(config_path):
    """加载现有配置"""
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ 警告：无法解析现有配置文件: {e}")
            return {}
    return {}

def merge_config(existing_config, new_config):
    """合并配置"""
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    # 添加或更新 DataMaster MCP 配置
    existing_config["mcpServers"].update(new_config["mcpServers"])
    
    return existing_config

def save_config(config_path, config):
    """保存配置文件"""
    # 确保目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def main():
    """主函数"""
    print("🔧 DataMaster MCP 客户端配置生成器")
    print("=" * 50)
    
    # 检查是否安装了 DataMaster MCP
    try:
        import datamaster_mcp
        print(f"✅ 检测到 DataMaster MCP 版本: {datamaster_mcp.__version__}")
    except ImportError:
        print("❌ 错误：未检测到 DataMaster MCP 包")
        print("请先运行：pip install datamaster-mcp")
        return False
    
    # 获取配置文件路径
    config_path = get_claude_config_path()
    if not config_path:
        print("❌ 错误：无法确定 Claude Desktop 配置文件路径")
        print("请手动配置或联系开发者")
        return False
    
    print(f"📁 配置文件路径: {config_path}")
    
    # 询问用户配置方式
    print("\n🎯 选择配置方式:")
    print("1. 使用模块路径 (推荐)")
    print("2. 使用完整路径")
    
    while True:
        choice = input("\n请选择 (1/2) [默认: 1]: ").strip()
        if choice == "" or choice == "1":
            use_module_path = True
            break
        elif choice == "2":
            use_module_path = False
            break
        else:
            print("❌ 无效选择，请输入 1 或 2")
    
    try:
        # 生成新配置
        new_config = generate_config(use_module_path)
        print(f"\n✅ 生成配置 ({'模块路径' if use_module_path else '完整路径'})")
        
        # 加载现有配置
        existing_config = load_existing_config(config_path)
        
        # 合并配置
        final_config = merge_config(existing_config, new_config)
        
        # 显示配置预览
        print("\n📋 配置预览:")
        print(json.dumps(final_config, indent=2, ensure_ascii=False))
        
        # 询问是否保存
        save_choice = input("\n💾 是否保存配置? (y/N): ").strip().lower()
        if save_choice in ['y', 'yes', '是']:
            # 备份现有配置
            if config_path.exists():
                backup_path = config_path.with_suffix('.json.backup')
                import shutil
                shutil.copy2(config_path, backup_path)
                print(f"📦 已备份原配置到: {backup_path}")
            
            # 保存新配置
            save_config(config_path, final_config)
            print(f"✅ 配置已保存到: {config_path}")
            
            print("\n🎉 配置完成！")
            print("\n📋 下一步操作:")
            print("1. 重启 Claude Desktop 应用")
            print("2. 在 Claude 中测试 DataMaster MCP 功能")
            print("3. 尝试连接数据源进行分析")
            
            return True
        else:
            print("❌ 配置未保存")
            return False
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        sys.exit(1)