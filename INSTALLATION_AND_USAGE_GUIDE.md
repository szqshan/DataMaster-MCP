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

## 📊 核心功能概览

### 🔗 数据源连接
- **Excel/CSV文件导入** - 支持多种格式和编码
- **数据库连接** - MySQL、PostgreSQL、MongoDB、SQLite
- **API数据获取** - RESTful API连接和数据提取

### 🔍 数据查询分析
- **SQL查询执行** - 本地和外部数据库查询
- **数据统计分析** - 基础统计、相关性、异常值检测
- **数据质量检查** - 缺失值、重复值分析

### 🛠️ 数据处理
- **数据清洗** - 去重、填充缺失值
- **数据转换** - 类型转换、格式化
- **数据聚合** - 分组统计、汇总

### 📤 数据导出
- **多格式导出** - Excel、CSV、JSON
- **查询结果导出** - 支持SQL查询结果导出

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

### 第三步：高级配置（可选）

如果需要设置环境变量或工作目录：

```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "python",
      "args": [
        "-m",
        "datamaster_mcp.main"
      ],
      "env": {
        "DATAMASTER_CONFIG_PATH": "C:\\path\\to\\your\\config"
      },
      "cwd": "C:\\path\\to\\working\\directory"
    }
  }
}
```

### 第四步：验证配置

在 Claude Desktop 中测试：
```
请帮我连接一个数据源
```

或者：
```
显示可用的数据分析工具
```

## 🚨 常见问题解决

### 问题 1：找不到模块

**错误信息：** `ModuleNotFoundError: No module named 'datamaster_mcp'`

**解决方案：**
1. 确认已正确安装：`pip show datamaster-mcp`
2. 检查 Python 路径是否正确
3. 尝试使用完整路径配置

### 问题 2：权限错误

**错误信息：** `Permission denied`

**解决方案：**
1. 确保 Python 有执行权限
2. 在 Windows 上可能需要管理员权限
3. 检查文件路径是否正确

### 问题 3：配置文件格式错误

**错误信息：** JSON 解析错误

**解决方案：**
1. 检查 JSON 格式是否正确（注意逗号、引号）
2. 使用 JSON 验证工具检查语法
3. 确保路径中的反斜杠正确转义（Windows）

## 💡 最佳实践

### 1. 使用模块路径
推荐使用 `-m datamaster_mcp.main` 方式，这样不依赖具体的安装路径。

### 2. 备份配置
在修改配置前，先备份原有的 `claude_desktop_config.json` 文件。

### 3. 逐步测试
先使用最简单的配置，确认能正常工作后再添加高级选项。

---

## 📚 基础使用教程

### 1. 数据库连接功能

#### 支持的数据库类型

- **MySQL** - 关系型数据库
- **PostgreSQL** - 关系型数据库  
- **MongoDB** - 文档型数据库
- **SQLite** - 轻量级关系型数据库

#### 连接方式

##### 方式一：配置文件连接（推荐）

1. **配置数据库信息**

编辑 `config/database_config.json`：

```json
{
  "databases": {
    "my_mysql": {
      "type": "mysql",
      "host": "localhost",
      "port": 3306,
      "database": "my_database",
      "username": "root",
      "password": "${MYSQL_PASSWORD}",
      "charset": "utf8mb4",
      "description": "我的MySQL数据库",
      "enabled": true
    },
    "my_postgres": {
      "type": "postgresql",
      "host": "localhost",
      "port": 5432,
      "database": "my_database",
      "username": "postgres",
      "password": "${POSTGRES_PASSWORD}",
      "schema": "public",
      "description": "我的PostgreSQL数据库",
      "enabled": true
    }
  }
}
```

2. **设置环境变量**

编辑 `.env` 文件：

```env
# 数据库密码
MYSQL_PASSWORD=your_mysql_password
POSTGRES_PASSWORD=your_postgres_password
MONGO_PASSWORD=your_mongo_password
```

##### 方式二：直接连接

```python
# MySQL连接
connect_data_source(
    source_type="mysql",
    config={
        "host": "localhost",
        "port": 3306,
        "database": "test_db",
        "username": "root",  # 支持 user 或 username
        "password": "password"
    }
)

# PostgreSQL连接
connect_data_source(
    source_type="postgresql",
    config={
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "postgres",
        "password": "password"
    }
)
```

#### 数据库管理

```python
# 列出所有配置
manage_database_config(action="list")

# 测试连接
manage_database_config(
    action="test",
    config={"database_name": "my_mysql"}
)

# 添加新配置
manage_database_config(
    action="add",
    config={
        "database_name": "new_db",
        "database_config": {
            "type": "mysql",
            "host": "192.168.1.100",
            "port": 3306,
            "database": "test_db",
            "username": "user",
            "password": "pass"
        }
    }
)
```

### 2. 文件导入功能

#### Excel文件导入

```python
connect_data_source(
    source_type="excel",
    config={
        "file_path": "data/sales.xlsx",
        "sheet_name": "Sheet1"  # 可选，默认第一个工作表
    },
    target_table="sales_data"
)
```

#### CSV文件导入

```python
connect_data_source(
    source_type="csv",
    config={
        "file_path": "data/customers.csv",
        "encoding": "utf-8"  # 可选，自动检测
    },
    target_table="customers"
)
```

### 2. API连接器功能

#### 支持的认证方式

- **API Key认证** - 通过Header或Query参数
- **Bearer Token认证** - JWT等Token认证
- **Basic认证** - 用户名密码认证
- **OAuth 2.0** - 标准OAuth流程
- **自定义Header** - 灵活的认证方式

#### API配置管理

##### 配置API连接

编辑 `config/api_config.json`：

```json
{
  "apis": {
    "weather_api": {
      "base_url": "https://api.openweathermap.org/data/2.5",
      "auth_type": "api_key",
      "auth_config": {
        "key": "${WEATHER_API_KEY}",
        "location": "query",
        "param_name": "appid"
      },
      "description": "天气数据API",
      "enabled": true
    },
    "github_api": {
      "base_url": "https://api.github.com",
      "auth_type": "bearer",
      "auth_config": {
        "token": "${GITHUB_TOKEN}"
      },
      "description": "GitHub API",
      "enabled": true
    }
  }
}
```

#### API端点获取

```python
# 获取API端点信息
get_api_endpoints(
    api_name="weather_api",
    endpoint="/weather",
    params={"q": "Beijing", "units": "metric"}
)

# 获取GitHub仓库信息
get_api_endpoints(
    api_name="github_api",
    endpoint="/repos/owner/repo"
)
```

#### API数据获取与存储

```python
# 获取API数据并自动存储
get_api_data(
    api_name="weather_api",
    endpoint="/weather",
    params={"q": "Shanghai", "units": "metric"},
    store_data=True,
    table_name="weather_data"
)

# 批量获取数据
cities = ["Beijing", "Shanghai", "Guangzhou"]
for city in cities:
    get_api_data(
        api_name="weather_api",
        endpoint="/weather",
        params={"q": city, "units": "metric"},
        store_data=True,
        table_name="weather_data"
    )
```

##### 会话管理

- **自动存储** - API响应数据自动存储到本地数据库
- **数据持久化** - 支持跨会话数据查询
- **增量更新** - 支持数据增量获取和更新

### 3. 数据查询功能

#### 本地数据查询

```python
# 基本查询
execute_sql("SELECT * FROM sales LIMIT 10")

# 统计查询
execute_sql("SELECT COUNT(*) as total_sales FROM sales")

# 分组查询
execute_sql("""
    SELECT category, SUM(amount) as total_amount 
    FROM sales 
    GROUP BY category
    ORDER BY total_amount DESC
""")

# 复杂查询
execute_sql("""
    SELECT 
        DATE(order_date) as date,
        COUNT(*) as order_count,
        SUM(amount) as total_revenue,
        AVG(amount) as avg_order_value
    FROM sales 
    WHERE order_date >= '2024-01-01'
    GROUP BY DATE(order_date)
    ORDER BY date
""")
```

#### 外部数据库查询

```python
# 查询外部MySQL数据库
query_external_database(
    database_name="my_mysql",
    query="SELECT * FROM products WHERE price > 100"
)

# 查询外部PostgreSQL数据库
query_external_database(
    database_name="my_postgres",
    query="""
        SELECT p.name, p.price, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.created_at >= '2024-01-01'
    """
)
```

### 3. 数据分析功能

#### 基础统计分析

```python
# 获取数据基本统计信息
analyze_data(
    table_name="sales",
    analysis_type="basic_stats"
)

# 获取特定列的统计信息
analyze_data(
    table_name="sales",
    analysis_type="basic_stats",
    columns=["amount", "quantity"]
)

# 分组统计
analyze_data(
    table_name="sales",
    analysis_type="group_stats",
    group_by="category",
    agg_column="amount"
)
```

#### 数据质量检查

```python
# 检查缺失值
analyze_data(
    table_name="customers",
    analysis_type="missing_values"
)

# 检查重复值
analyze_data(
    table_name="customers",
    analysis_type="duplicates",
    columns=["email"]  # 检查邮箱重复
)

# 数据类型检查
analyze_data(
    table_name="sales",
    analysis_type="data_types"
)

# 数据范围检查
analyze_data(
    table_name="sales",
    analysis_type="value_ranges",
    columns=["amount", "quantity"]
)
```

#### 相关性分析

```python
# 分析数值列之间的相关性
analyze_data(
    table_name="sales",
    analysis_type="correlation",
    columns=["amount", "quantity", "price"]
)

# 计算特定列的相关系数
analyze_data(
    table_name="sales",
    analysis_type="correlation_matrix",
    columns=["amount", "quantity", "discount"]
)
```

#### 异常值检测

```python
# 使用IQR方法检测异常值
analyze_data(
    table_name="sales",
    analysis_type="outliers",
    column="amount",
    method="iqr"
)

# 使用Z-Score方法检测异常值
analyze_data(
    table_name="sales",
    analysis_type="outliers",
    column="amount",
    method="zscore",
    threshold=3
)
```

### 4. 数据处理功能

#### 数据清洗

```python
# 删除重复数据
process_data(
    table_name="customers",
    operation="remove_duplicates",
    columns=["email"]  # 基于邮箱去重
)

# 删除完全重复的行
process_data(
    table_name="sales",
    operation="remove_duplicates"
)

# 填充缺失值
process_data(
    table_name="sales",
    operation="fill_missing",
    column="amount",
    fill_value=0  # 用0填充
)

# 用平均值填充缺失值
process_data(
    table_name="sales",
    operation="fill_missing",
    column="price",
    fill_method="mean"
)

# 用中位数填充缺失值
process_data(
    table_name="sales",
    operation="fill_missing",
    column="quantity",
    fill_method="median"
)

# 删除包含缺失值的行
process_data(
    table_name="customers",
    operation="drop_missing",
    columns=["email", "phone"]  # 删除邮箱或电话为空的行
)
```

#### 数据转换

```python
# 数据类型转换
process_data(
    table_name="sales",
    operation="convert_type",
    column="order_date",
    target_type="datetime"
)

# 字符串格式化
process_data(
    table_name="customers",
    operation="format_string",
    column="phone",
    format_pattern="xxx-xxxx-xxxx"
)

# 数值标准化
process_data(
    table_name="sales",
    operation="normalize",
    column="amount",
    method="min_max"  # 或 "z_score"
)
```

#### 数据筛选

```python
# 基于条件筛选数据
process_data(
    table_name="sales",
    operation="filter",
    condition="amount > 1000 AND category = 'Electronics'"
)

# 基于日期范围筛选
process_data(
    table_name="sales",
    operation="filter",
    condition="order_date >= '2024-01-01' AND order_date < '2024-02-01'"
)

# 筛选前N条记录
process_data(
    table_name="sales",
    operation="limit",
    limit=100
)
```

#### 数据聚合

```python
# 按类别聚合销售数据
process_data(
    table_name="sales",
    operation="aggregate",
    group_by=["category"],
    aggregations={
        "amount": ["sum", "avg", "count"],
        "quantity": ["sum", "max"]
    }
)

# 按日期聚合
process_data(
    table_name="sales",
    operation="aggregate",
    group_by=["DATE(order_date)"],
    aggregations={
        "amount": ["sum"],
        "order_id": ["count"]
    }
)
```

### 5. 数据导出功能

#### Excel导出

```python
# 导出完整表格到Excel
export_data(
    table_name="sales",
    export_format="excel",
    file_path="reports/sales_report.xlsx"
)

# 导出查询结果到Excel
export_data(
    query="SELECT * FROM sales WHERE amount > 1000",
    export_format="excel",
    file_path="reports/high_value_sales.xlsx",
    sheet_name="高价值销售"
)

# 导出多个工作表
export_data(
    tables={
        "销售数据": "sales",
        "客户数据": "customers",
        "产品数据": "products"
    },
    export_format="excel",
    file_path="reports/complete_report.xlsx"
)
```

#### CSV导出

```python
# 导出为CSV文件
export_data(
    table_name="customers",
    export_format="csv",
    file_path="exports/customers.csv",
    encoding="utf-8"  # 指定编码
)

# 导出查询结果为CSV
export_data(
    query="""
        SELECT customer_id, name, email, total_orders
        FROM customers 
        WHERE total_orders > 5
        ORDER BY total_orders DESC
    """,
    export_format="csv",
    file_path="exports/vip_customers.csv"
)
```

#### JSON导出

```python
# 导出为JSON格式
export_data(
    table_name="products",
    export_format="json",
    file_path="exports/products.json"
)

# 导出嵌套JSON结构
export_data(
    query="""
        SELECT 
            category,
            JSON_GROUP_ARRAY(
                JSON_OBJECT(
                    'name', name,
                    'price', price,
                    'stock', stock
                )
            ) as products
        FROM products 
        GROUP BY category
    """,
    export_format="json",
    file_path="exports/products_by_category.json"
)
```

#### 数据信息查询

```python
# 查看表结构
get_data_info(
    table_name="sales",
    info_type="schema"
)

# 查看数据样本
get_data_info(
    table_name="customers",
    info_type="sample",
    limit=10
)

# 查看表统计信息
get_data_info(
    table_name="sales",
    info_type="stats"
)

# 列出所有表
get_data_info(info_type="tables")
```

### 6. 最佳实践

#### 数据导入最佳实践

```python
# 1. 大文件分批导入
connect_data_source(
    source_type="csv",
    config={
        "file_path": "large_dataset.csv",
        "chunk_size": 10000,  # 分批处理
        "encoding": "utf-8"
    },
    target_table="large_data"
)

# 2. 数据验证导入
connect_data_source(
    source_type="excel",
    config={
        "file_path": "sales.xlsx",
        "validate_schema": True,  # 验证数据结构
        "skip_errors": False     # 遇到错误停止
    },
    target_table="sales"
)
```

#### 查询性能优化

```python
# 1. 使用索引优化查询
execute_sql("""
    CREATE INDEX idx_sales_date ON sales(order_date);
    CREATE INDEX idx_sales_customer ON sales(customer_id);
""")

# 2. 分页查询大数据集
execute_sql("""
    SELECT * FROM sales 
    ORDER BY order_date DESC 
    LIMIT 1000 OFFSET 0
""")

# 3. 使用聚合减少数据传输
execute_sql("""
    SELECT 
        DATE(order_date) as date,
        COUNT(*) as orders,
        SUM(amount) as revenue
    FROM sales 
    WHERE order_date >= '2024-01-01'
    GROUP BY DATE(order_date)
""")
```

#### 数据安全实践

```python
# 1. 使用环境变量存储敏感信息
connect_data_source(
    source_type="mysql",
    config={
        "host": "${DB_HOST}",
        "database": "${DB_NAME}",
        "username": "${DB_USER}",
        "password": "${DB_PASSWORD}"
    }
)

# 2. 限制查询结果数量
execute_sql(
    "SELECT * FROM sensitive_data",
    limit=100  # 自动添加LIMIT
)

# 3. 数据脱敏处理
execute_sql("""
    SELECT 
        customer_id,
        SUBSTR(email, 1, 3) || '***@' || SUBSTR(email, INSTR(email, '@')+1) as masked_email,
        amount
    FROM customers
""")
```

#### 错误处理和日志

```python
# 1. 带错误处理的数据导入
try:
    connect_data_source(
        source_type="csv",
        config={"file_path": "data.csv"},
        target_table="import_data"
    )
except Exception as e:
    print(f"导入失败: {e}")
    # 记录错误日志

# 2. 查询结果验证
result = execute_sql("SELECT COUNT(*) FROM sales")
if result and len(result) > 0:
    print(f"查询成功，返回 {len(result)} 条记录")
else:
    print("查询无结果")
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

# 数据库连接池管理
manage_database_config(
    action="optimize",
    config={
        "max_connections": 10,
        "connection_timeout": 30,
        "retry_attempts": 3
    }
)

# 数据库备份
manage_database_config(
    action="backup",
    config={
        "database_name": "my_mysql",
        "backup_path": "backups/",
        "include_data": True
    }
)
```

### 自动化工作流

```python
# 定义数据处理流水线
def daily_sales_report():
    # 1. 导入最新数据
    connect_data_source(
        source_type="csv",
        config={"file_path": "daily_sales.csv"},
        target_table="daily_sales"
    )
    
    # 2. 数据清洗
    process_data(
        table_name="daily_sales",
        operation="remove_duplicates"
    )
    
    # 3. 生成报告
    report_data = execute_sql("""
        SELECT 
            category,
            SUM(amount) as total_sales,
            COUNT(*) as order_count
        FROM daily_sales
        GROUP BY category
        ORDER BY total_sales DESC
    """)
    
    # 4. 导出报告
    export_data(
        query="SELECT * FROM daily_sales",
        export_format="excel",
        file_path=f"reports/daily_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )
    
    return report_data

# 执行工作流
daily_report = daily_sales_report()
```

---

## 🛡️ 安全特性

- **SQL注入防护** - 自动参数化查询
- **危险操作拦截** - 阻止 DROP、DELETE 等危险操作
- **查询结果限制** - 自动添加 LIMIT 防止大量数据返回
- **参数验证** - 严格的输入参数验证
- **环境变量管理** - 敏感信息通过环境变量管理

---

## ⚠️ 注意事项

### 安全性注意事项

- **敏感数据保护**：不要在配置文件中直接存储密码，使用环境变量
- **访问权限控制**：为数据库用户设置最小必要权限
- **数据备份**：定期备份重要数据，避免数据丢失
- **网络安全**：在生产环境中使用SSL/TLS加密连接

### 性能优化建议

- **大文件处理**：对于大型CSV/Excel文件，建议分批导入
- **查询优化**：使用适当的索引和LIMIT子句
- **内存管理**：避免一次性加载过大的数据集
- **连接池**：合理配置数据库连接池参数

### 数据质量保证

- **数据验证**：导入前检查数据格式和完整性
- **编码处理**：确保文件编码正确（推荐UTF-8）
- **类型匹配**：注意数据类型的一致性
- **异常处理**：建立完善的错误处理机制

---

## ❓ 常见问题解决

### 安装和配置问题

**Q: pip安装失败怎么办？**
```bash
# 解决方案：
# 1. 更新pip
pip install --upgrade pip

# 2. 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ datamaster-mcp

# 3. 清除缓存重试
pip cache purge
pip install datamaster-mcp
```

**Q: Claude Desktop无法识别MCP服务器？**
```json
解决步骤：
1. 检查配置文件位置是否正确
2. 验证JSON格式是否有效
3. 确认Python路径正确
4. 重启Claude Desktop
5. 查看Claude Desktop日志
```

**Q: 配置文件在哪里？**
```
Windows: %APPDATA%\Claude\claude_desktop_config.json
macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
Linux: ~/.config/claude/claude_desktop_config.json
```

### 数据连接问题

**Q: 无法连接到数据库？**
```python
# 解决方案：
# 1. 测试连接
manage_database_config(
    action="test",
    config={"database_name": "my_db"}
)

# 2. 检查配置
# - 主机地址和端口
# - 用户名和密码
# - 数据库名称
# - 网络连接

# 3. 查看错误日志
# 检查具体的错误信息
```

**Q: API连接失败？**
```python
# 解决方案：
# 1. 验证API密钥
# 2. 检查网络连接
# 3. 确认API端点正确
# 4. 查看API限制和配额

# 测试API连接
get_api_endpoints(
    api_name="your_api",
    endpoint="/test"
)
```

### 数据处理问题

**Q: 导入的数据乱码？**
```python
# 解决方案：
connect_data_source(
    source_type="csv",
    config={
        "file_path": "data.csv",
        "encoding": "utf-8"  # 或 "gbk", "gb2312"
    },
    target_table="data"
)
```

**Q: Excel文件导入失败？**
```python
# 解决方案：
# 1. 检查文件是否损坏
# 2. 确认工作表名称
# 3. 处理合并单元格

connect_data_source(
    source_type="excel",
    config={
        "file_path": "data.xlsx",
        "sheet_name": "Sheet1",  # 指定工作表
        "header_row": 0         # 指定标题行
    },
    target_table="data"
)
```

**Q: 查询结果为空？**
```sql
-- 解决方案：
-- 1. 检查表是否存在
SELECT name FROM sqlite_master WHERE type='table';

-- 2. 检查数据是否存在
SELECT COUNT(*) FROM your_table;

-- 3. 验证查询条件
SELECT * FROM your_table LIMIT 5;
```

### 性能问题

**Q: 查询速度很慢？**
```sql
-- 解决方案：
-- 1. 添加索引
CREATE INDEX idx_column ON table_name(column_name);

-- 2. 使用LIMIT限制结果
SELECT * FROM large_table LIMIT 1000;

-- 3. 优化查询条件
SELECT * FROM table WHERE indexed_column = 'value';
```

**Q: 内存不足？**
```python
# 解决方案：
# 1. 分批处理大文件
connect_data_source(
    source_type="csv",
    config={
        "file_path": "large_file.csv",
        "chunk_size": 10000  # 分批处理
    },
    target_table="data"
)

# 2. 使用流式查询
query_data(
    "SELECT * FROM large_table",
    stream=True,
    batch_size=1000
)
```

### 错误代码说明

| 错误代码 | 说明 | 解决方案 |
|---------|------|----------|
| DB_001 | 数据库连接失败 | 检查连接参数和网络 |
| DB_002 | 认证失败 | 验证用户名和密码 |
| API_001 | API密钥无效 | 检查API密钥配置 |
| API_002 | API限制超出 | 等待或升级API计划 |
| FILE_001 | 文件不存在 | 检查文件路径 |
| FILE_002 | 文件格式错误 | 确认文件格式和编码 |

### 获取帮助

如果遇到其他问题：

1. **查看日志**：检查详细的错误信息
2. **文档参考**：查阅完整的API文档
3. **社区支持**：在GitHub Issues中提问
4. **联系支持**：发送邮件获取技术支持

---

---

## 📞 获取帮助

### 文档资源
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