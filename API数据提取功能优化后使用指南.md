# API数据提取功能优化后使用指南

## 概述

经过优化，API数据提取功能已简化并增强，移除了重复功能，统一使用SQL查询和数据导出方式。

## 核心变化

### ✅ 新增功能
- **`query_api_storage_data`**: 新增专用SQL查询函数
- **增强的导出功能**: 支持SQL过滤的数据导出

### ❌ 移除功能
- **`manage_api_storage(action="get_data")`**: 已移除
- **`format_type`参数**: 已移除
- **`limit/offset`参数**: 已移除

### 🔄 保留功能
- **会话管理**: `list_sessions`, `delete_session`, `get_operations`
- **数据导出**: `export_data`（已增强）

## 新的使用方式

### 1. 数据查询（替代get_data）

**旧方式（已废弃）**：
```python
# ❌ 不再支持
result = manage_api_storage(
    action="get_data",
    session_id="session_id",
    format_type="json",
    limit=10,
    offset=0
)
```

**新方式（推荐）**：
```python
# ✅ 使用SQL查询
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT * FROM api_data LIMIT 10 OFFSET 0"
)
```

### 2. 复杂查询示例

#### 基础查询
```python
# 查询所有数据
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT * FROM api_data"
)

# 分页查询
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT * FROM api_data LIMIT 20 OFFSET 40"
)
```

#### JSON字段查询
```python
# 查询JSON字段中的特定值
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT * FROM api_data WHERE json_extract(raw_data, '$.age') > 25"
)

# 查询嵌套JSON字段
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT json_extract(raw_data, '$.name') as name, json_extract(raw_data, '$.email') as email FROM api_data"
)
```

#### 聚合查询
```python
# 统计查询
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT COUNT(*) as total_count, AVG(json_extract(raw_data, '$.price')) as avg_price FROM api_data"
)

# 分组统计
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT json_extract(raw_data, '$.category') as category, COUNT(*) as count FROM api_data GROUP BY category"
)
```

#### 时间范围查询
```python
# 查询特定时间范围的数据
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT * FROM api_data WHERE timestamp BETWEEN '2024-01-01' AND '2024-01-31'"
)
```

### 3. 增强的数据导出

#### 基础导出（无变化）
```python
# 导出所有数据
result = manage_api_storage(
    action="export_data",
    session_id="session_id",
    export_format="excel"
)
```

#### 过滤导出（新功能）
```python
# 使用WHERE条件过滤导出
result = manage_api_storage(
    action="export_data",
    session_id="session_id",
    export_format="excel",
    sql_filter="json_extract(raw_data, '$.status') = 'active'"
)

# 使用完整SQL语句过滤导出
result = manage_api_storage(
    action="export_data",
    session_id="session_id",
    export_format="csv",
    sql_filter="SELECT * FROM api_data WHERE json_extract(raw_data, '$.price') < 100 ORDER BY timestamp DESC"
)
```

### 4. 完整的工作流程

```python
# 1. 列出存储会话
sessions = manage_api_storage(action="list_sessions")

# 2. 数据预览
preview = query_api_storage_data(
    session_id="your_session_id",
    sql_query="SELECT * FROM api_data LIMIT 5"
)

# 3. 数据分析查询
analysis = query_api_storage_data(
    session_id="your_session_id",
    sql_query="""
        SELECT 
            json_extract(raw_data, '$.category') as category,
            COUNT(*) as count,
            AVG(json_extract(raw_data, '$.price')) as avg_price,
            MAX(json_extract(raw_data, '$.price')) as max_price
        FROM api_data 
        GROUP BY category 
        ORDER BY count DESC
    """
)

# 4. 过滤导出
export_result = manage_api_storage(
    action="export_data",
    session_id="your_session_id",
    export_format="excel",
    sql_filter="json_extract(raw_data, '$.price') > 50"
)

# 5. 查看操作历史
history = manage_api_storage(
    action="get_operations",
    session_id="your_session_id"
)
```

## 数据库表结构

API存储数据表结构：
```sql
CREATE TABLE api_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hash TEXT UNIQUE,
    raw_data TEXT,           -- 原始API响应数据（JSON格式）
    processed_data TEXT,     -- 处理后的数据（JSON格式）
    source_params TEXT,      -- 请求参数（JSON格式）
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 常用SQL查询模式

### 1. 数据探索
```sql
-- 查看表结构
PRAGMA table_info(api_data);

-- 查看数据总数
SELECT COUNT(*) FROM api_data;

-- 查看最新数据
SELECT * FROM api_data ORDER BY timestamp DESC LIMIT 10;
```

### 2. JSON数据查询
```sql
-- 提取JSON字段
SELECT 
    json_extract(raw_data, '$.id') as id,
    json_extract(raw_data, '$.name') as name,
    json_extract(raw_data, '$.email') as email
FROM api_data;

-- JSON数组查询
SELECT 
    json_extract(raw_data, '$.tags[0]') as first_tag,
    json_array_length(raw_data, '$.tags') as tag_count
FROM api_data;
```

### 3. 数据过滤
```sql
-- 数值比较
SELECT * FROM api_data 
WHERE CAST(json_extract(raw_data, '$.age') AS INTEGER) > 25;

-- 字符串匹配
SELECT * FROM api_data 
WHERE json_extract(raw_data, '$.name') LIKE '%John%';

-- 日期范围
SELECT * FROM api_data 
WHERE timestamp BETWEEN '2024-01-01' AND '2024-12-31';
```

## 优化收益

### 1. 功能统一
- 所有数据查询统一使用SQL
- 减少API接口复杂性
- 降低学习成本

### 2. 功能增强
- SQL查询比固定接口更灵活
- 支持复杂的数据分析
- 支持JSON字段深度查询
- 导出功能支持SQL过滤

### 3. 性能提升
- 直接SQL查询，性能更好
- 减少数据传输量
- 支持数据库级别的优化

### 4. 维护简化
- 移除重复代码
- 统一错误处理
- 简化测试和调试

## 迁移指南

### 从旧版本迁移

1. **替换get_data调用**：
   ```python
   # 旧版本
   manage_api_storage(action="get_data", session_id="xxx", limit=10)
   
   # 新版本
   query_api_storage_data(session_id="xxx", sql_query="SELECT * FROM api_data LIMIT 10")
   ```

2. **替换格式转换**：
   ```python
   # 旧版本
   manage_api_storage(action="get_data", format_type="json")
   
   # 新版本
   query_api_storage_data(sql_query="SELECT * FROM api_data")  # 默认返回JSON格式
   ```

3. **替换分页查询**：
   ```python
   # 旧版本
   manage_api_storage(action="get_data", limit=20, offset=40)
   
   # 新版本
   query_api_storage_data(sql_query="SELECT * FROM api_data LIMIT 20 OFFSET 40")
   ```

## 最佳实践

1. **使用参数化查询**：
   ```python
   query_api_storage_data(
       session_id="xxx",
       sql_query="SELECT * FROM api_data WHERE json_extract(raw_data, '$.age') > ?",
       params={"age": 25}
   )
   ```

2. **合理使用LIMIT**：
   ```python
   # 大数据集查询时总是使用LIMIT
   query_api_storage_data(
       session_id="xxx",
       sql_query="SELECT * FROM api_data ORDER BY timestamp DESC LIMIT 100"
   )
   ```

3. **利用索引优化**：
   ```sql
   -- 为常用查询字段创建索引
   CREATE INDEX idx_timestamp ON api_data(timestamp);
   CREATE INDEX idx_json_field ON api_data(json_extract(raw_data, '$.category'));
   ```

4. **导出大数据集时使用过滤**：
   ```python
   # 避免导出全部数据，使用过滤条件
   manage_api_storage(
       action="export_data",
       sql_filter="timestamp >= '2024-01-01'"
   )
   ```

## 总结

优化后的API数据提取功能：
- **更简洁**：减少了重复功能和复杂参数
- **更强大**：SQL查询比固定接口更灵活
- **更高效**：直接数据库查询，性能更好
- **更易用**：统一的数据访问方式

通过这次优化，用户可以享受到更强大、更灵活的数据查询和导出功能，同时降低了学习和使用成本。