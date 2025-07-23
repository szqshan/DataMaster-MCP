#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd

# 查看数据库中的表
conn = sqlite3.connect('data_analysis.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("数据库中的表:")
for table in tables:
    print(f"- {table[0]}")

# 创建一个简单的测试表
print("\n创建测试表...")
test_data = {
    '姓名': ['张三', '李四', '王五'],
    '部门': ['技术部', '销售部', '人事部'],
    '工资': [8000, 6000, 7000]
}

df = pd.DataFrame(test_data)
df.to_sql('编码测试', conn, if_exists='replace', index=False)
print("测试表'编码测试'已创建")

# 验证表是否创建成功
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("\n更新后的表列表:")
for table in tables:
    print(f"- {table[0]}")

# 查看表内容
print("\n表内容:")
df_read = pd.read_sql('SELECT * FROM "编码测试"', conn)
print(df_read)

conn.close()