
#!/usr/bin/env python3
"""
MySQL驱动自动修复脚本
"""

import subprocess
import sys

def install_mysql_drivers():
    """安装MySQL驱动"""
    drivers_to_install = [
        'pymysql>=1.0.0',
        'mysql-connector-python>=8.0.0'
    ]
    
    for driver in drivers_to_install:
        try:
            print(f"安装 {driver}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', driver])
            print(f"✅ {driver} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ {driver} 安装失败: {e}")

if __name__ == "__main__":
    install_mysql_drivers()
