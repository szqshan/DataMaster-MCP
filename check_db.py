#!/usr/bin/env python3
"""
检查数据库状态
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import get_db_connection
import sqlite3

def check_database():
    """检查数据库状态"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print('数据库中的表:', [t[0] for t in tables])
            
            # 如果有alarm_data_2025表，显示其内容
            if 'alarm_data_2025' in [t[0] for t in tables]:
                cursor = conn.execute('SELECT * FROM alarm_data_2025')
                rows = cursor.fetchall()
                print(f'\nalarm_data_2025表内容 ({len(rows)}行):')
                for row in rows:
                    print(row)
            else:
                print('\n❌ alarm_data_2025表不存在')
                
    except Exception as e:
        print(f"检查数据库失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()