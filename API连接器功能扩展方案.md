# API连接器功能扩展方案

## 需求分析

用户希望为 SuperDataAnalysis MCP 增加通用API连接器功能，能够：
- 兼容各种API接口获取数据
- 支持配置文件方式管理API连接信息
- 支持直接传递API调用方式和API Key
- 通过API获取数据并集成到现有数据分析流程

## 技术架构设计

### 1. 核心组件

#### API配置管理器 (APIConfigManager)
- 管理API连接配置信息
- 支持多种认证方式（API Key、OAuth、Bearer Token等）
- 环境变量保护敏感信息
- 配置验证和测试功能

#### API连接器 (APIConnector)
- 统一的API调用接口
- 支持多种HTTP方法（GET、POST、PUT、DELETE等）
- 自动处理认证和请求头
- 响应数据解析和转换
- 错误处理和重试机制

#### 数据转换器 (DataTransformer)
- JSON/XML/CSV等格式数据解析
- 数据结构扁平化处理
- 自动类型推断和转换
- 分页数据合并处理

### 2. 配置文件结构

```json
{
  "apis": {
    "weather_api": {
      "name": "天气API",
      "base_url": "https://api.openweathermap.org/data/2.5",
      "auth_type": "api_key",
      "auth_config": {
        "api_key": "${WEATHER_API_KEY}",
        "key_param": "appid"
      },
      "endpoints": {
        "current_weather": {
          "path": "/weather",
          "method": "GET",
          "params": {
            "q": "city_name",
            "units": "metric"
          }
        }
      },
      "rate_limit": {
        "requests_per_minute": 60,
        "requests_per_day": 1000
      },
      "data_format": "json",
      "description": "OpenWeatherMap API",
      "enabled": true
    },
    "rest_api_example": {
      "name": "REST API示例",
      "base_url": "https://jsonplaceholder.typicode.com",
      "auth_type": "bearer_token",
      "auth_config": {
        "token": "${API_BEARER_TOKEN}"
      },
      "endpoints": {
        "users": {
          "path": "/users",
          "method": "GET"
        },
        "posts": {
          "path": "/posts",
          "method": "GET",
          "params": {
            "userId": "user_id"
          }
        }
      },
      "headers": {
        "Content-Type": "application/json",
        "User-Agent": "SuperDataAnalysis-MCP/1.0"
      },
      "timeout": 30,
      "retry_attempts": 3,
      "data_format": "json",
      "enabled": true
    }
  },
  "default_settings": {
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1,
    "max_response_size": "10MB",
    "follow_redirects": true,
    "verify_ssl": true
  },
  "security": {
    "allowed_domains": [],
    "blocked_domains": [],
    "require_https": false,
    "max_redirects": 5
  }
}
```

### 3. 支持的认证方式

#### API Key认证
- URL参数方式：`?api_key=xxx`
- Header方式：`X-API-Key: xxx`
- 自定义参数名和位置

#### Bearer Token认证
- Authorization Header：`Authorization: Bearer xxx`
- 支持JWT Token

#### OAuth 2.0认证
- Client Credentials流程
- Authorization Code流程（需要用户授权）

#### Basic认证
- 用户名密码Base64编码
- Authorization Header：`Authorization: Basic xxx`

#### 自定义Header认证
- 灵活的自定义认证头配置

### 4. 新增MCP工具

#### manage_api_config
- 列出所有API配置
- 测试API连接
- 添加/删除/更新API配置
- 重新加载配置

#### connect_api_source
- 连接API数据源
- 支持配置文件方式和直接传递方式
- 获取API端点列表和文档

#### fetch_api_data
- 调用API获取数据
- 支持参数化查询
- 自动处理分页数据
- 数据格式转换和导入

#### api_data_preview
- 预览API返回数据结构
- 数据类型分析
- 字段映射建议

### 5. 数据处理流程

```
1. API配置验证
   ↓
2. 构建请求（URL、Headers、参数）
   ↓
3. 发送HTTP请求
   ↓
4. 响应数据解析
   ↓
5. 数据格式转换
   ↓
6. 导入到SQLite数据库
   ↓
7. 更新元数据信息
```

### 6. 错误处理机制

- **网络错误**：自动重试，指数退避
- **认证错误**：详细错误信息，配置验证建议
- **限流错误**：自动等待，遵守API限制
- **数据格式错误**：容错解析，部分数据保存
- **超时错误**：可配置超时时间，连接池管理

### 7. 安全特性

- **敏感信息保护**：API Key等通过环境变量管理
- **域名白名单**：限制可访问的API域名
- **HTTPS强制**：可配置要求HTTPS连接
- **请求大小限制**：防止过大响应数据
- **速率限制**：遵守API提供商的限制

## 实施计划

### 第一阶段：基础架构
1. 创建API配置管理模块
2. 实现基础HTTP客户端
3. 添加认证机制支持
4. 创建配置文件模板

### 第二阶段：数据处理
1. 实现数据解析和转换
2. 添加分页数据处理
3. 集成到现有数据流程
4. 错误处理和重试机制

### 第三阶段：MCP工具集成
1. 实现API管理工具
2. 实现数据获取工具
3. 扩展现有connect_data_source工具
4. 添加数据预览功能

### 第四阶段：测试和优化
1. 功能测试和验证
2. 性能优化
3. 文档编写
4. 示例和最佳实践

## 依赖包需求

```
# HTTP客户端和请求处理
requests>=2.31.0
httpx>=0.25.0  # 异步HTTP客户端（可选）

# 数据处理
xmltodict>=0.13.0  # XML解析
pandas>=2.0.0  # 数据处理（已有）

# 认证和安全
cryptography>=41.0.0  # 加密和JWT处理
requests-oauthlib>=1.3.1  # OAuth支持

# 配置和环境
python-dotenv>=1.0.0  # 环境变量（已有）
pyyaml>=6.0  # YAML配置支持（可选）
```

## 使用场景示例

### 场景1：天气数据分析
```python
# 配置天气API
manage_api_config(
    action="add",
    config={
        "api_name": "weather_api",
        "base_url": "https://api.openweathermap.org/data/2.5",
        "auth_type": "api_key",
        "api_key": "your_api_key"
    }
)

# 获取多个城市的天气数据
fetch_api_data(
    api_name="weather_api",
    endpoint="current_weather",
    params_list=[
        {"q": "Beijing"},
        {"q": "Shanghai"},
        {"q": "Guangzhou"}
    ]
)

# 分析天气数据
analyze_data(analysis_type="comparison", table_name="weather_data")
```

### 场景2：社交媒体数据
```python
# 直接连接API（无需预配置）
connect_api_source(
    source_type="api_direct",
    config={
        "base_url": "https://api.twitter.com/2",
        "auth_type": "bearer_token",
        "token": "your_bearer_token",
        "endpoints": {
            "tweets": "/tweets/search/recent"
        }
    }
)

# 获取推文数据
fetch_api_data(
    api_name="twitter_api",
    endpoint="tweets",
    params={"query": "#AI", "max_results": 100}
)
```

### 场景3：电商数据分析
```python
# 获取产品数据
fetch_api_data(
    api_name="ecommerce_api",
    endpoint="products",
    params={"category": "electronics", "limit": 1000}
)

# 获取销售数据
fetch_api_data(
    api_name="ecommerce_api",
    endpoint="sales",
    params={"date_range": "2024-01-01,2024-12-31"}
)

# 关联分析
analyze_data(analysis_type="correlation", table_name="sales_products")
```

## 优势特点

1. **通用性强**：支持各种REST API和数据格式
2. **配置灵活**：支持配置文件和直接传递两种方式
3. **安全可靠**：完善的认证和安全机制
4. **易于使用**：简单的配置和调用方式
5. **高度集成**：与现有数据分析流程无缝集成
6. **错误容错**：完善的错误处理和重试机制
7. **性能优化**：支持并发请求和数据缓存

这个API连接器将大大扩展SuperDataAnalysis MCP的数据源支持能力，让AI能够便捷地获取各种在线数据进行分析。