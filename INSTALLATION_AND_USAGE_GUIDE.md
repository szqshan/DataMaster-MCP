# 📊 DataMaster MCP 完整安装使用指南

> **超级数据分析MCP工具** - 为AI提供强大的数据分析能力的完整使用指南

## 🎯 什么是 DataMaster MCP？

**DataMaster MCP** 是一个专为 Claude Desktop 设计的数据分析工具，它让AI能够：
- 📁 连接各种数据源（Excel、CSV、数据库、API）
- 🔍 执行复杂的数据查询和分析
- 📊 进行统计分析和数据质量检查
- 🛠️ 处理和清洗数据
- 📤 导出分析结果

**核心理念：工具专注数据获取和计算，AI专注智能分析和洞察**

---

## 🚀 快速安装

### 方法一：pip 安装（推荐）

```bash
# 安装 DataMaster MCP
pip install datamaster-mcp

# 验证安装
pip show datamaster-mcp
```

### 方法二：开发者安装

```bash
# 1. 克隆项目
git clone https://github.com/szqshan/DataMaster.git
cd DataMaster

# 2. 自动设置开发环境
python scripts/setup_dev.py

# 3. 测试环境
python scripts/setup_dev.py --test-only
```

---

## ⚙️ Claude Desktop 配置

### 第一步：找到配置文件

**Windows 系统：**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS 系统：**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux 系统：**
```
~/.config/Claude/claude_desktop_config.json
```

### 第二步：配置 MCP 服务器

#### 🚀 推荐配置（使用 uvx）

首先安装 uv：
```bash
# Windows
scoop install uv
# 或者
pip install uv
```

然后在配置文件中添加：
```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "uvx",
      "args": [
        "datamaster-mcp"
      ]
    }
  }
}
```

#### 🔧 备用配置（使用模块路径）

```json
{
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
```

### 第三步：重启 Claude Desktop

配置完成后，完全关闭并重新启动 Claude Desktop 应用。

### 第四步：验证配置

在 Claude Desktop 中测试：
```
请帮我连接一个数据源
```

---

## 📚 基础使用教程

### 1. 数据导入

#### Excel 文件导入
```python
# 导入 Excel 文件
connect_data_source(
    source_type="excel",
    config={"file_path": "sales_data.xlsx"},
    target_table="sales"
)
```

#### CSV 文件导入
```python
# 导入 CSV 文件
connect_data_source(
    source_type="csv",
    config={"file_path": "customers.csv"},
    target_table="customers"
)
```

#### 数据库连接
```python
# 连接 MySQL 数据库
connect_data_source(
    source_type="mysql",
    config={
        "host": "localhost",
        "port": 3306,
        "database": "my_db",
        "user": "root",
        "password": "password"
    }
)
```

### 2. 数据查询

#### 基本查询
```python
# 查询本地数据
execute_sql("SELECT * FROM sales LIMIT 10")

# 带条件查询
execute_sql("SELECT * FROM sales WHERE amount > 1000")
```

#### 外部数据库查询
```python
# 查询外部数据库
query_external_database(
    database_name="my_mysql",
    query="SELECT COUNT(*) FROM users"
)
```

### 3. 数据分析

#### 基础统计
```python
# 基本统计信息
analyze_data(
    analysis_type="basic_stats",
    table_name="sales"
)
```

#### 相关性分析
```python
# 相关性分析
analyze_data(
    analysis_type="correlation",
    table_name="sales",
    columns=["amount", "quantity"]
)
```

#### 异常值检测
```python
# 异常值检测
analyze_data(
    analysis_type="outliers",
    table_name="sales",
    columns=["amount"]
)
```

### 4. 数据处理

#### 数据清洗
```python
# 去重和填充缺失值
process_data(
    operation_type="clean",
    data_source="customers",
    config={
        "remove_duplicates": True,
        "fill_missing": {
            "age": {"method": "mean"},
            "city": {"method": "mode"}
        }
    },
    target_table="customers_clean"
)
```

#### 数据筛选
```python
# 条件筛选
process_data(
    operation_type="filter",
    data_source="sales",
    config={
        "filter_condition": "amount > 1000",
        "select_columns": ["id", "amount", "date"]
    },
    target_table="high_value_sales"
)
```

### 5. 数据导出

```python
# 导出为 Excel
export_data(
    export_type="excel",
    data_source="sales",
    file_path="sales_report.xlsx"
)

# 导出查询结果
export_data(
    export_type="csv",
    data_source="SELECT * FROM sales WHERE amount > 1000"
)
```

---

## 🔧 高级功能

### API 数据获取

#### 配置 API
```python
# 添加 API 配置
manage_api_config(
    action="add",
    api_name="weather_api",
    config_data={
        "base_url": "https://api.openweathermap.org/data/2.5",
        "auth_type": "api_key",
        "auth_config": {
            "api_key": "your_api_key",
            "key_param": "appid",
            "key_location": "query"
        },
        "endpoints": {
            "current_weather": {
                "path": "/weather",
                "method": "GET"
            }
        }
    }
)
```

#### 获取 API 数据
```python
# 获取天气数据
fetch_api_data(
    api_name="weather_api",
    endpoint_name="current_weather",
    params={"q": "Beijing", "units": "metric"}
)
```

### 数据库管理

```python
# 列出所有数据源
list_data_sources()

# 获取表信息
get_data_info(info_type="tables")

# 获取表结构
get_data_info(info_type="schema", table_name="sales")

# 获取统计信息
get_data_info(info_type="stats", table_name="sales")
```

---

## 🛡️ 安全特性

- **SQL注入防护** - 自动参数化查询
- **危险操作拦截** - 阻止 DROP、DELETE 等危险操作
- **查询结果限制** - 自动添加 LIMIT 防止大量数据返回
- **参数验证** - 严格的输入参数验证
- **环境变量管理** - 敏感信息通过环境变量管理

---

## 🚨 常见问题解决

### 问题 1：找不到模块
**错误：** `ModuleNotFoundError: No module named 'datamaster_mcp'`

**解决方案：**
1. 确认安装：`pip show datamaster-mcp`
2. 重新安装：`pip uninstall datamaster-mcp && pip install datamaster-mcp`
3. 检查 Python 环境

### 问题 2：数据库连接失败
**错误：** 连接超时或认证失败

**解决方案：**
1. 检查数据库服务是否运行
2. 验证连接参数（主机、端口、用户名、密码）
3. 检查防火墙设置
4. 确认数据库用户权限

### 问题 3：文件路径错误
**错误：** 找不到文件

**解决方案：**
1. 使用绝对路径
2. 检查文件是否存在
3. 确认文件权限
4. 注意路径分隔符（Windows 使用 `\\` 或 `/`）

### 问题 4：Claude Desktop 无法连接
**错误：** MCP 服务器无法启动

**解决方案：**
1. 检查配置文件 JSON 格式
2. 重启 Claude Desktop
3. 查看 Claude Desktop 日志
4. 尝试不同的配置方式

---

## 📖 实用示例

### 示例 1：销售数据分析

```python
# 1. 导入销售数据
connect_data_source(
    source_type="excel",
    config={"file_path": "sales_2024.xlsx"},
    target_table="sales_2024"
)

# 2. 基础统计分析
analyze_data(
    analysis_type="basic_stats",
    table_name="sales_2024"
)

# 3. 查找高价值客户
execute_sql("""
    SELECT customer_id, SUM(amount) as total_amount
    FROM sales_2024
    GROUP BY customer_id
    HAVING total_amount > 10000
    ORDER BY total_amount DESC
""")

# 4. 导出分析结果
export_data(
    export_type="excel",
    data_source="SELECT * FROM sales_2024 WHERE amount > 5000",
    file_path="high_value_sales.xlsx"
)
```

### 示例 2：多数据源整合分析

```python
# 1. 连接客户数据库
connect_data_source(
    source_type="mysql",
    config={
        "host": "localhost",
        "database": "crm",
        "user": "analyst",
        "password": "password"
    }
)

# 2. 导入订单数据
connect_data_source(
    source_type="csv",
    config={"file_path": "orders_2024.csv"},
    target_table="orders"
)

# 3. 关联分析
execute_sql("""
    SELECT c.customer_name, COUNT(o.order_id) as order_count,
           AVG(o.amount) as avg_order_value
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.customer_name
    ORDER BY order_count DESC
""")
```

---

## 📞 获取帮助

### 文档资源
- 📖 [用户使用手册](用户使用手册.md) - 详细功能说明
- 🛠️ [开发者文档](开发者文档.md) - 技术文档
- 📁 [项目结构说明](项目结构说明.md) - 文件组织
- 🔄 [更新日志](CHANGELOG.md) - 版本更新记录

### 支持渠道
- 🐛 [GitHub Issues](https://github.com/szqshan/DataMaster/issues) - 报告问题
- 💬 [讨论区](https://github.com/szqshan/DataMaster/discussions) - 交流讨论
- 📧 邮件支持 - 发送邮件获取帮助

---

## 🎉 开始使用

现在你已经掌握了 DataMaster MCP 的完整使用方法！

**快速开始步骤：**
1. ✅ 安装：`pip install datamaster-mcp`
2. ✅ 配置：添加到 Claude Desktop 配置文件
3. ✅ 重启：重启 Claude Desktop
4. ✅ 测试："请帮我连接一个数据源"
5. ✅ 使用：开始你的数据分析之旅！

**记住：工具专注数据获取和计算，AI专注智能分析和洞察！**

---

**版本**: v1.0.2 | **状态**: ✅ 稳定版 | **更新**: 2025-01-24