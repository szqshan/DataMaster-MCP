# API数据提取功能优化方案

## 问题分析

当前API数据提取功能存在以下重复和冗余：

### 1. 功能重复问题

**重复功能对比**：
- **manage_api_storage(action="get_data")** ↔ **execute_sql()** 
  - 都提供数据查询功能
  - 都支持limit/offset分页
  - 都返回结构化数据

- **manage_api_storage(format_type="json|dataframe|excel")** ↔ **数据导出功能**
  - 都提供格式转换
  - 都支持多种输出格式
  - 功能高度重叠

- **manage_api_storage分页查询** ↔ **SQL LIMIT/OFFSET**
  - 都实现分页功能
  - SQL方式更灵活强大

### 2. 架构复杂性

- 用户需要学习多套API接口
- 维护成本高，功能分散
- 代码逻辑重复，增加bug风险

## 优化方案

### 核心思路
**简化API接口，统一数据访问方式，保留最强大和灵活的功能**

### 具体优化措施

#### 1. 移除重复功能

**移除以下manage_api_storage的action**：
- ❌ `get_data` - 用SQL查询替代
- ❌ `format_type` 参数 - 用数据导出替代
- ❌ `limit/offset` 参数 - 用SQL LIMIT/OFFSET替代

**保留核心功能**：
- ✅ `list_sessions` - 会话管理必需
- ✅ `delete_session` - 会话管理必需
- ✅ `export_data` - 数据导出核心功能
- ✅ `get_operations` - 操作历史查看

#### 2. 增强SQL查询功能

**新增API存储专用SQL查询支持**：
```python
# 新增函数：query_api_storage_data
def query_api_storage_data(
    session_id: str,
    sql_query: str,
    params: dict = None,
    limit: int = 1000
) -> str:
    """
    查询API存储数据
    
    Args:
        session_id: 存储会话ID
        sql_query: SQL查询语句
        params: 查询参数
        limit: 结果限制
    
    Returns:
        str: 查询结果
    """
```

**支持的查询类型**：
- 基础查询：`SELECT * FROM api_data`
- 条件筛选：`SELECT * FROM api_data WHERE json_extract(raw_data, '$.age') > 25`
- 分页查询：`SELECT * FROM api_data LIMIT 10 OFFSET 20`
- 聚合统计：`SELECT COUNT(*), AVG(json_extract(raw_data, '$.price')) FROM api_data`
- 时间范围：`SELECT * FROM api_data WHERE timestamp BETWEEN '2024-01-01' AND '2024-01-31'`

#### 3. 优化数据导出功能

**保留并增强export_data功能**：
- 支持基于SQL查询结果的导出
- 支持自定义导出路径和格式
- 支持批量导出多个会话

```python
# 增强的导出功能
manage_api_storage(
    action="export_data",
    session_id="session_id",
    export_format="excel",
    export_path="custom/path/data.xlsx",
    sql_filter="WHERE json_extract(raw_data, '$.status') = 'active'"  # 新增
)
```

## 优化后的使用流程

### 简化的数据提取方式

```python
# 1. 列出存储会话
sessions = manage_api_storage(action="list_sessions")

# 2. 使用SQL查询数据（替代get_data）
result = query_api_storage_data(
    session_id="session_id",
    sql_query="SELECT * FROM api_data WHERE json_extract(raw_data, '$.age') > 25 LIMIT 10"
)

# 3. 导出数据（保留并增强）
export_result = manage_api_storage(
    action="export_data",
    session_id="session_id",
    export_format="excel"
)

# 4. 查看操作历史（保留）
history = manage_api_storage(action="get_operations", session_id="session_id")

# 5. 删除会话（保留）
delete_result = manage_api_storage(action="delete_session", session_id="session_id")
```

## 优化收益

### 1. 简化用户体验
- 减少API接口数量：从5个action减少到4个
- 统一数据访问方式：全部使用SQL查询
- 降低学习成本：只需掌握SQL语法

### 2. 提升功能强大性
- SQL查询比固定的get_data更灵活
- 支持复杂的数据分析和聚合
- 支持JSON字段的深度查询

### 3. 减少维护成本
- 移除重复代码逻辑
- 统一错误处理机制
- 简化测试和调试

### 4. 保持向后兼容
- 保留核心的会话管理功能
- 保留数据导出功能
- 现有的存储数据结构不变

## 实施计划

### 阶段1：新增功能
1. 实现 `query_api_storage_data` 函数
2. 增强 `export_data` 功能，支持SQL过滤

### 阶段2：移除冗余
1. 从 `manage_api_storage` 中移除 `get_data` action
2. 移除 `format_type`、`limit`、`offset` 参数
3. 更新相关文档和示例

### 阶段3：测试验证
1. 测试新的查询功能
2. 验证导出功能增强
3. 确保向后兼容性

## 风险评估

### 低风险
- 核心存储机制不变
- 会话管理功能保持不变
- 数据导出功能得到增强

### 需要注意
- 用户需要学习SQL语法（但更通用）
- 需要更新使用文档和示例
- 需要逐步迁移现有使用方式

## 总结

通过移除重复功能，统一使用SQL查询和数据导出，可以：
- **简化架构**：减少功能重复，降低复杂性
- **提升能力**：SQL查询比固定接口更强大灵活
- **改善体验**：统一的数据访问方式，降低学习成本
- **便于维护**：减少代码重复，统一错误处理

这个优化方案既解决了当前的功能重复问题，又提升了整体的功能强大性和易用性。