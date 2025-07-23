# API连接器功能使用指南

## 📋 概述

SuperDataAnalysis MCP 的 API连接器功能为AI提供了强大的API数据获取能力，支持多种认证方式、数据格式和转换选项。

## 🚀 核心功能

### 1. 支持的认证方式
- **API Key**: 支持Query参数和Header两种方式
- **Bearer Token**: OAuth 2.0 Bearer令牌认证
- **Basic认证**: 用户名/密码基础认证
- **自定义Header**: 灵活的自定义认证头
- **无认证**: 公开API接口

### 2. 支持的数据格式
- **JSON**: 标准JSON格式
- **XML**: XML格式（支持自动转换为字典）
- **CSV**: 逗号分隔值格式
- **纯文本**: 原始文本数据

### 3. 数据转换功能
- **格式转换**: JSON、CSV、Excel、DataFrame、Table
- **字段映射**: 重命名字段
- **字段过滤**: 包含/排除特定字段
- **类型转换**: 自动或手动数据类型转换
- **数据清洗**: 去除空白、HTML标签等

## 🛠️ MCP工具说明

### 1. manage_api_config - API配置管理

管理API配置，包括添加、删除、测试和查看API配置。

**参数:**
- `action`: 操作类型
  - `list`: 列出所有API配置
  - `test`: 测试API连接
  - `add`: 添加新的API配置
  - `remove`: 删除API配置
  - `reload`: 重新加载配置文件
  - `get_endpoints`: 获取API端点列表
- `api_name`: API名称（某些操作需要）
- `config_data`: API配置数据（添加操作需要）

**使用示例:**
```python
# 列出所有API配置
manage_api_config(action="list")

# 测试API连接
manage_api_config(action="test", api_name="weather_api")

# 添加新的API配置
manage_api_config(
    action="add",
    api_name="my_api",
    config_data={
        "base_url": "https://api.example.com",
        "auth_type": "api_key",
        "auth_config": {
            "api_key": "${MY_API_KEY}",
            "key_param": "apikey",
            "key_location": "query"
        },
        "endpoints": {
            "get_data": {
                "path": "/data",
                "method": "GET",
                "description": "获取数据"
            }
        }
    }
)

# 获取API端点
manage_api_config(action="get_endpoints", api_name="weather_api")
```

### 2. fetch_api_data - 获取API数据

从配置的API端点获取数据，支持多种输出格式和数据转换。

**参数:**
- `api_name`: API名称
- `endpoint_name`: 端点名称
- `params`: 请求参数（可选）
- `data`: 请求数据，用于POST/PUT（可选）
- `method`: HTTP方法（可选，默认使用端点配置）
- `output_format`: 输出格式（json|csv|excel|dataframe|table）
- `transform_config`: 数据转换配置（可选）

**使用示例:**
```python
# 基本API调用
fetch_api_data(
    api_name="weather_api",
    endpoint_name="current_weather",
    params={"city": "Beijing"}
)

# 带数据转换的API调用
fetch_api_data(
    api_name="rest_api",
    endpoint_name="users",
    output_format="table",
    transform_config={
        "field_mapping": {
            "user_id": "id",
            "user_name": "name"
        },
        "include_fields": ["id", "name", "email"],
        "type_conversions": {
            "id": "int",
            "created_at": "datetime"
        }
    }
)

# POST请求示例
fetch_api_data(
    api_name="rest_api",
    endpoint_name="create_user",
    method="POST",
    data={
        "name": "张三",
        "email": "zhangsan@example.com"
    }
)
```

### 3. api_data_preview - 预览API数据

快速预览API返回的数据结构和内容，用于数据探索。

**参数:**
- `api_name`: API名称
- `endpoint_name`: 端点名称
- `params`: 请求参数（可选）
- `max_rows`: 最大显示行数（默认10）
- `max_cols`: 最大显示列数（默认10）

**使用示例:**
```python
# 预览API数据
api_data_preview(
    api_name="weather_api",
    endpoint_name="current_weather",
    params={"city": "Shanghai"},
    max_rows=5
)

# 预览用户数据
api_data_preview(
    api_name="rest_api",
    endpoint_name="users",
    max_rows=10,
    max_cols=8
)
```

## ⚙️ 配置文件说明

### API配置文件结构 (config/api_config.json)

```json
{
  "apis": {
    "api_name": {
      "base_url": "https://api.example.com",
      "auth_type": "api_key|bearer_token|basic|custom_header|none",
      "auth_config": {
        // 认证配置，根据auth_type不同而不同
      },
      "data_format": "json|xml|csv|text",
      "headers": {
        // 默认请求头
      },
      "timeout": 30,
      "retry_attempts": 3,
      "endpoints": {
        "endpoint_name": {
          "path": "/api/path",
          "method": "GET|POST|PUT|DELETE",
          "description": "端点描述",
          "params": {
            // 默认参数
          }
        }
      }
    }
  },
  "default_settings": {
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1,
    "user_agent": "SuperDataAnalysis-MCP/1.0",
    "verify_ssl": true,
    "follow_redirects": true
  },
  "security": {
    "require_https": true,
    "domain_whitelist": [],
    "domain_blacklist": [],
    "max_response_size_bytes": 10485760,
    "max_redirects": 5
  },
  "data_processing": {
    "default_output_format": "json",
    "auto_detect_format": true,
    "max_preview_rows": 100,
    "max_preview_cols": 20
  }
}
```

### 环境变量配置 (.env)

```bash
# API密钥
WEATHER_API_KEY=your_weather_api_key
BEARER_TOKEN=your_bearer_token

# Basic认证
API_USERNAME=your_username
API_PASSWORD=your_password

# 自定义认证
CUSTOM_API_KEY=your_custom_key
CLIENT_ID=your_client_id
```

## 🔒 安全特性

### 1. 域名控制
- **HTTPS要求**: 可配置是否强制使用HTTPS
- **域名白名单**: 只允许访问指定域名
- **域名黑名单**: 禁止访问特定域名

### 2. 请求限制
- **响应大小限制**: 防止过大响应占用内存
- **重定向限制**: 限制最大重定向次数
- **超时控制**: 防止长时间等待

### 3. 认证安全
- **环境变量**: 敏感信息通过环境变量管理
- **配置验证**: 自动验证配置完整性
- **SSL验证**: 支持SSL证书验证

## 📊 数据转换配置

### 字段映射
```json
{
  "field_mapping": {
    "old_field_name": "new_field_name",
    "user_id": "id",
    "user_name": "name"
  }
}
```

### 字段过滤
```json
{
  "include_fields": ["id", "name", "email"],
  "exclude_fields": ["password", "internal_id"]
}
```

### 类型转换
```json
{
  "type_conversions": {
    "id": "int",
    "price": "float",
    "active": "bool",
    "created_at": "datetime"
  }
}
```

### 数据清洗
```json
{
  "data_cleaning": {
    "strip_whitespace": true,
    "remove_html_tags": true,
    "normalize_newlines": true,
    "remove_extra_spaces": true,
    "remove_null": false
  }
}
```

## 🎯 使用场景示例

### 1. 天气数据分析
```python
# 获取多个城市的天气数据
cities = ["Beijing", "Shanghai", "Guangzhou"]
weather_data = []

for city in cities:
    result = fetch_api_data(
        api_name="weather_api",
        endpoint_name="current_weather",
        params={"city": city},
        output_format="json"
    )
    weather_data.append(result)
```

### 2. 社交媒体数据收集
```python
# 获取用户动态数据
user_posts = fetch_api_data(
    api_name="social_api",
    endpoint_name="user_posts",
    params={
        "user_id": "12345",
        "limit": 50
    },
    output_format="table",
    transform_config={
        "include_fields": ["id", "content", "created_at", "likes"],
        "type_conversions": {
            "created_at": "datetime",
            "likes": "int"
        }
    }
)
```

### 3. 电商数据分析
```python
# 获取产品销售数据
sales_data = fetch_api_data(
    api_name="ecommerce_api",
    endpoint_name="sales_report",
    params={
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    },
    output_format="csv",
    transform_config={
        "field_mapping": {
            "product_id": "id",
            "product_name": "name",
            "sale_amount": "amount"
        },
        "type_conversions": {
            "amount": "float",
            "quantity": "int"
        }
    }
)
```

## 🔧 故障排除

### 常见问题

1. **API连接失败**
   - 检查网络连接
   - 验证API URL和认证信息
   - 查看域名是否在白名单中

2. **认证失败**
   - 确认API密钥正确
   - 检查环境变量设置
   - 验证认证方式配置

3. **数据解析失败**
   - 检查API返回的数据格式
   - 确认data_format配置正确
   - 查看响应内容是否符合预期

4. **转换失败**
   - 检查transform_config配置
   - 确认字段名称正确
   - 验证数据类型转换规则

### 调试技巧

1. **使用预览功能**: 先用`api_data_preview`查看数据结构
2. **逐步测试**: 从简单的API调用开始，逐步添加转换配置
3. **检查日志**: 查看错误日志获取详细信息
4. **测试连接**: 使用`manage_api_config`的test功能验证连接

## 🚀 最佳实践

1. **配置管理**
   - 使用环境变量存储敏感信息
   - 定期更新API密钥
   - 备份重要的API配置

2. **性能优化**
   - 合理设置超时时间
   - 使用适当的重试策略
   - 限制响应数据大小

3. **安全考虑**
   - 启用HTTPS要求
   - 配置域名白名单
   - 定期检查安全配置

4. **数据处理**
   - 使用预览功能了解数据结构
   - 合理配置数据转换规则
   - 处理异常和错误情况

---

通过API连接器功能，SuperDataAnalysis MCP 为AI提供了强大的外部数据获取能力，支持各种API接口和数据格式，让数据分析更加全面和深入。