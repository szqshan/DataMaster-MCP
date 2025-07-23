# API数据持久化存储使用示例

## 功能概述

本文档展示如何使用新增的API数据持久化存储功能，将API获取的数据存储到临时数据库中，并进行类似Excel的数据分析。

## 核心功能

### 1. 持久化存储选项

`fetch_api_data` 函数现在支持两个新参数：
- `persist_to_storage`: 是否将数据持久化存储到临时数据库
- `storage_session_id`: 存储会话ID（可选，如果不提供会自动创建）

### 2. 数据分析功能

`analyze_api_storage_data` 函数提供多种数据分析方式：
- **数据预览**: 查看数据的前几行
- **数据摘要**: 获取数据的基本统计信息
- **数据过滤**: 根据条件筛选数据
- **数据分组**: 按字段分组并进行聚合计算
- **统计分析**: 对数值字段进行详细统计分析

## 使用示例

### 示例1: 基本的数据持久化存储

```python
# 1. 创建存储会话
result = create_api_storage_session(
    session_name="用户数据分析",
    api_name="jsonplaceholder",
    endpoint_name="users",
    description="收集用户数据进行分析"
)

# 2. 获取API数据并持久化存储
result = fetch_api_data(
    api_name="jsonplaceholder",
    endpoint_name="users",
    persist_to_storage=True,
    storage_session_id="your-session-id"  # 从步骤1获取
)
```

### 示例2: 数据分析操作

```python
# 数据预览 - 查看前5行数据
result = analyze_api_storage_data(
    session_id="your-session-id",
    analysis_type="preview",
    limit=5
)

# 数据摘要 - 获取基本统计信息
result = analyze_api_storage_data(
    session_id="your-session-id",
    analysis_type="summary"
)

# 数据过滤 - 筛选特定条件的数据
result = analyze_api_storage_data(
    session_id="your-session-id",
    analysis_type="filter",
    filters={"age": ">25", "department": "技术部"},
    columns=["name", "age", "salary"]
)

# 数据分组 - 按部门统计平均工资
result = analyze_api_storage_data(
    session_id="your-session-id",
    analysis_type="group",
    group_by=["department"],
    aggregations={"salary": "avg", "age": "mean"}
)

# 统计分析 - 对数值字段进行详细分析
result = analyze_api_storage_data(
    session_id="your-session-id",
    analysis_type="stats",
    columns=["salary", "age"]
)
```

### 示例3: 完整的数据分析流程

```python
# 步骤1: 创建存储会话
session_result = create_api_storage_session(
    session_name="电商产品分析",
    api_name="ecommerce_api",
    endpoint_name="products",
    description="电商产品数据分析"
)

# 步骤2: 获取并存储数据
fetch_result = fetch_api_data(
    api_name="ecommerce_api",
    endpoint_name="products",
    params={"category": "electronics", "limit": 100},
    persist_to_storage=True,
    storage_session_id="session-id-from-step1"
)

# 步骤3: 数据预览
preview_result = analyze_api_storage_data(
    session_id="session-id-from-step1",
    analysis_type="preview",
    limit=10
)

# 步骤4: 按类别分组分析
group_result = analyze_api_storage_data(
    session_id="session-id-from-step1",
    analysis_type="group",
    group_by=["category", "brand"],
    aggregations={
        "price": "avg",
        "stock": "sum",
        "rating": "mean"
    }
)

# 步骤5: 价格统计分析
stats_result = analyze_api_storage_data(
    session_id="session-id-from-step1",
    analysis_type="stats",
    columns=["price", "rating", "stock"]
)

# 步骤6: 筛选高评分产品
filter_result = analyze_api_storage_data(
    session_id="session-id-from-step1",
    analysis_type="filter",
    filters={"rating": ">4.5", "price": "<1000"},
    columns=["name", "brand", "price", "rating"]
)
```

## 数据分析类型详解

### 1. 数据预览 (preview)
- **用途**: 快速查看数据的前几行
- **参数**: `limit` - 显示行数
- **返回**: 数据的前N行和基本信息

### 2. 数据摘要 (summary)
- **用途**: 获取数据的整体概况
- **返回**: 行数、列数、数据类型、缺失值统计等

### 3. 数据过滤 (filter)
- **用途**: 根据条件筛选数据
- **参数**: 
  - `filters` - 过滤条件字典
  - `columns` - 返回的列名列表
- **过滤条件格式**:
  - 等值: `{"column": "value"}`
  - 比较: `{"column": ">100"}`, `{"column": "<=50"}`
  - 包含: `{"column": "contains:keyword"}`

### 4. 数据分组 (group)
- **用途**: 按字段分组并进行聚合计算
- **参数**:
  - `group_by` - 分组字段列表
  - `aggregations` - 聚合函数字典
- **聚合函数**: `sum`, `avg`, `count`, `min`, `max`, `mean`, `std`

### 5. 统计分析 (stats)
- **用途**: 对数值字段进行详细统计分析
- **参数**: `columns` - 要分析的列名列表
- **返回**: 均值、中位数、标准差、分位数等统计指标

## 优势特点

### 🚀 性能优势
- **智能存储**: 大数据量时自动持久化，小数据量直接返回
- **去重机制**: 自动检测并避免重复数据存储
- **索引优化**: 数据库索引提升查询性能

### 📊 分析能力
- **类Excel体验**: 提供类似Excel的数据分析功能
- **多维分析**: 支持多字段分组和多种聚合函数
- **灵活过滤**: 支持多种过滤条件和比较操作

### 🔧 易用性
- **简单配置**: 只需设置 `persist_to_storage=True`
- **自动管理**: 自动创建和管理存储会话
- **统一接口**: 所有分析功能通过统一函数调用

### 💾 数据管理
- **会话隔离**: 不同API调用的数据独立存储
- **历史追踪**: 完整的操作历史记录
- **多格式导出**: 支持Excel、CSV、JSON等格式导出

## 最佳实践

### 1. 何时使用持久化存储
- ✅ **推荐使用**: 数据量大（>1000条记录）
- ✅ **推荐使用**: 需要多次分析同一数据集
- ✅ **推荐使用**: 需要复杂的数据分析操作
- ❌ **不推荐**: 简单的一次性数据查看

### 2. 分析操作建议
- 先使用 `preview` 了解数据结构
- 再使用 `summary` 获取整体概况
- 根据需要使用 `filter`、`group`、`stats` 进行深入分析

### 3. 性能优化
- 合理设置 `limit` 参数避免一次性加载过多数据
- 使用 `columns` 参数只返回需要的字段
- 定期清理不需要的存储会话

## 注意事项

1. **存储空间**: 持久化存储会占用磁盘空间，注意定期清理
2. **会话管理**: 记住存储会话ID，用于后续数据分析
3. **数据格式**: 确保API返回的数据格式适合进行分析
4. **错误处理**: 分析操作可能因数据格式问题失败，注意错误信息

通过这些功能，您可以像使用Excel一样对API数据进行灵活的分析和处理，为后续的AI数据分析奠定基础。