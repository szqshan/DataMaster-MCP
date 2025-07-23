# API数据存储功能使用指南

## 功能概述

API数据存储功能允许您将通过API获取的数据存储到临时的SQLite数据库文件中，类似于Excel文件的存储方式。这个功能提供了完整的数据管理能力，包括创建存储会话、存储数据、查询数据、导出数据等。

## 核心特性

- 🗂️ **会话管理**: 创建和管理多个数据存储会话
- 💾 **数据存储**: 自动存储API响应数据，支持去重
- 📊 **多格式支持**: 支持JSON、DataFrame、Excel等多种数据格式
- 📁 **数据导出**: 支持导出为Excel、CSV、JSON格式
- 📜 **操作历史**: 记录所有数据操作的历史记录
- 🔍 **数据查询**: 支持分页查询和数据筛选

## 工具函数说明

### 1. create_api_storage_session

创建一个新的API数据存储会话。

**参数:**
- `session_name` (str): 存储会话名称
- `api_name` (str): API名称
- `endpoint_name` (str): 端点名称
- `description` (str, 可选): 会话描述

**示例:**
```python
result = create_api_storage_session(
    session_name="用户数据收集",
    api_name="jsonplaceholder",
    endpoint_name="users",
    description="收集用户基本信息数据"
)
```

### 2. store_api_data_to_session

获取API数据并存储到指定会话中。

**参数:**
- `session_id` (str): 存储会话ID
- `api_name` (str): API名称
- `endpoint_name` (str): 端点名称
- `params` (dict, 可选): 请求参数
- `data` (dict, 可选): 请求数据（POST/PUT）
- `method` (str, 可选): HTTP方法
- `transform_config` (dict, 可选): 数据转换配置

**示例:**
```python
result = store_api_data_to_session(
    session_id="your-session-id",
    api_name="jsonplaceholder",
    endpoint_name="users",
    params={"page": 1, "limit": 10}
)
```

### 3. manage_api_storage

管理API数据存储的综合工具函数。

**参数:**
- `action` (str): 操作类型
  - `list_sessions`: 列出存储会话
  - `get_data`: 获取存储的数据
  - `delete_session`: 删除存储会话
  - `export_data`: 导出数据
  - `get_operations`: 获取操作历史
- `session_id` (str, 可选): 存储会话ID
- `api_name` (str, 可选): API名称（用于筛选会话）
- `limit` (int, 可选): 数据限制数量
- `offset` (int, 可选): 数据偏移量
- `format_type` (str, 可选): 数据格式 (json|dataframe|excel)
- `export_path` (str, 可选): 导出路径
- `export_format` (str, 可选): 导出格式 (excel|csv|json)

## 使用流程示例

### 完整的数据收集和管理流程

```python
# 1. 创建存储会话
session_result = create_api_storage_session(
    session_name="GitHub用户数据分析",
    api_name="github",
    endpoint_name="users",
    description="收集GitHub用户数据进行分析"
)

# 从结果中提取session_id
import json
session_data = json.loads(session_result.split('\n\n')[1])
session_id = session_data['data']['session_id']

# 2. 存储API数据
store_result = store_api_data_to_session(
    session_id=session_id,
    api_name="github",
    endpoint_name="users",
    params={"since": 0, "per_page": 30}
)

# 3. 获取存储的数据
data_result = manage_api_storage(
    action="get_data",
    session_id=session_id,
    format_type="json",
    limit=10
)

# 4. 导出数据到Excel
export_result = manage_api_storage(
    action="export_data",
    session_id=session_id,
    export_format="excel"
)

# 5. 查看操作历史
history_result = manage_api_storage(
    action="get_operations",
    session_id=session_id
)

# 6. 列出所有会话
sessions_result = manage_api_storage(
    action="list_sessions"
)
```

## 数据格式说明

### JSON格式
返回完整的数据记录，包含原始数据、处理后数据、源参数和时间戳。

### DataFrame格式
将数据转换为pandas DataFrame，便于数据分析和处理。

### Excel格式
生成Excel二进制数据，可直接保存为.xlsx文件。

## 数据转换配置

可以在存储数据时应用数据转换配置：

```python
transform_config = {
    "field_mapping": {
        "login": "username",
        "avatar_url": "avatar"
    },
    "field_filter": ["id", "username", "avatar", "type"],
    "data_types": {
        "id": "int",
        "username": "str"
    }
}

store_result = store_api_data_to_session(
    session_id=session_id,
    api_name="github",
    endpoint_name="users",
    transform_config=transform_config
)
```

## 文件存储结构

```
data/
├── api_storage/
│   ├── metadata.db              # 元数据数据库
│   └── sessions/
│       ├── session_1.db         # 会话1的数据文件
│       ├── session_2.db         # 会话2的数据文件
│       └── ...
└── exports/                     # 导出文件目录
    ├── api_data_20250123.xlsx
    ├── api_data_20250123.csv
    └── ...
```

## 注意事项

1. **数据去重**: 系统会自动对相同的API响应数据进行去重处理
2. **存储限制**: 每个会话的数据存储在独立的SQLite文件中，理论上没有大小限制
3. **数据安全**: 存储的数据仅在本地，不会上传到任何外部服务
4. **会话管理**: 删除会话会同时删除对应的数据文件
5. **导出路径**: 如果不指定导出路径，系统会自动生成带时间戳的文件名

## 错误处理

所有工具函数都会返回详细的错误信息，包括：
- 错误状态和消息
- 错误类型
- 相关的会话或操作信息

## 性能优化建议

1. **批量存储**: 对于大量数据，建议分批次存储而不是一次性存储
2. **定期清理**: 定期删除不需要的存储会话以节省磁盘空间
3. **合理分页**: 获取数据时使用合理的limit和offset参数
4. **选择合适格式**: 根据使用场景选择合适的数据格式（JSON用于查看，DataFrame用于分析）

## 常见问题

**Q: 如何查看某个API的所有存储会话？**
A: 使用 `manage_api_storage(action="list_sessions", api_name="your_api_name")`

**Q: 如何备份存储的数据？**
A: 使用导出功能将数据导出为Excel或CSV格式进行备份

**Q: 存储会话被删除后能否恢复？**
A: 删除操作是不可逆的，建议在删除前先导出重要数据

**Q: 如何处理大量数据的存储？**
A: 建议分批次调用 `store_api_data_to_session`，每次处理适量数据