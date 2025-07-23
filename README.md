# SuperDataAnalysis MCP

超级数据分析MCP工具 - 为AI提供强大的数据分析能力

## 🎯 核心理念

**工具专注数据获取和计算，AI专注智能分析和洞察**

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

### 3. 核心功能

#### 📊 导入Excel数据

```python
connect_data_source(
    source_type="excel",
    config={
        "file_path": "data/sales.xlsx",
        "sheet_name": "Sheet1"
    },
    target_table="sales_data"
)
```

#### 🔍 执行SQL查询

```python
execute_sql(
    query="SELECT * FROM sales_data WHERE amount > 1000",
    limit=100
)
```

#### 📋 获取数据信息

```python
# 获取所有表
get_data_info(info_type="tables")

# 获取表结构
get_data_info(info_type="schema", table_name="sales_data")

# 获取表统计
get_data_info(info_type="stats", table_name="sales_data")
```

## 🔧 当前功能

- ✅ Excel文件导入
- ✅ CSV文件导入
- ✅ SQL查询执行
- ✅ 数据信息获取
- ✅ 安全SQL检查
- ✅ 自动数据库管理

## 📁 项目结构

```
SuperDataAnalysis_MCP/
├── main.py                    # 主MCP服务器
├── requirements.txt           # 依赖包
├── README.md                  # 项目说明
├── data/                      # 数据存储目录
│   └── analysis.db           # SQLite数据库
└── exports/                   # 导出文件目录
```

## 🛡️ 安全特性

- SQL注入防护
- 危险操作拦截（DROP、DELETE等）
- 查询结果限制
- 参数验证

## 📝 返回格式

所有工具返回统一的JSON格式：

```json
{
  "status": "success|error|info",
  "message": "操作描述",
  "data": {
    // 具体数据
  },
  "metadata": {
    "timestamp": "2024-01-01T12:00:00",
    // 其他元数据
  }
}
```

## 🔄 开发计划

- [ ] 数据分析工具（统计、相关性、异常值检测）
- [ ] 图表生成工具
- [ ] 数据导出工具
- [ ] MySQL/MongoDB支持
- [ ] API数据获取
- [ ] 批量文件处理

## 📞 支持

如有问题或建议，请提交Issue或联系开发团队。