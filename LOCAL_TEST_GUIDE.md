# 🧪 DataMaster MCP 本地测试指南

> **在不上传到 PyPI 之前，如何在本地测试 DataMaster MCP 工具**

---

## 🎯 测试目标

在本地环境中测试 DataMaster MCP 的完整功能，包括：
- MCP 服务器启动和运行
- 与 MCP 客户端（如 Claude Desktop）的连接
- 数据分析功能验证
- 配置文件和环境变量测试

---

## 📋 准备工作

### 1. 环境要求

```bash
# Python 版本要求
Python >= 3.8

# 必需的依赖包
pip install -r requirements.txt
```

### 2. 项目结构确认

确保你的项目结构如下：
```
DataMaster_MCP/
├── datamaster_mcp/           # 主包目录
│   ├── __init__.py
│   ├── main.py              # MCP 服务器主入口
│   └── config/              # 配置模块
│       ├── __init__.py
│       ├── *.py             # 各种管理器
│       └── *.json           # 配置文件
├── requirements.txt
├── .env.example
└── test_package.py          # 测试脚本
```

---

## 🚀 方法一：直接运行测试（推荐）

### 0. 自动化测试（推荐）
```bash
# 运行完整的自动化测试
python test_mcp_server.py

# 如果所有测试通过，直接启动服务器
python start_mcp_server.py
```

### 1. 安装依赖

```bash
# 进入项目目录
cd d:\MCP\SuperDataAnalysis_MCP

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行包测试

```bash
# 运行测试脚本，验证包功能
python test_package.py
```

### 3. 直接启动 MCP 服务器

```bash
# 方法1：直接运行主模块
python -m datamaster_mcp.main

# 方法2：运行 main.py
python datamaster_mcp/main.py
```

### 4. 验证服务器运行

如果看到类似输出，说明服务器启动成功：
```
INFO:DataMaster_MCP:启动 DataMaster_MCP
INFO:DataMaster_MCP:数据库初始化完成
# MCP 服务器开始监听...
```

---

## 🔧 方法二：开发模式安装

### 1. 开发模式安装包

```bash
# 在项目根目录执行
pip install -e .
```

这会将包安装到本地 Python 环境中，但仍然链接到源代码，方便开发和测试。

### 2. 验证安装

```bash
# 验证命令行工具
datamaster-mcp --help

# 或者直接启动
datamaster-mcp
```

### 3. Python 中导入测试

```python
# 测试包导入
import datamaster_mcp
print(f"版本: {datamaster_mcp.__version__}")
print(f"作者: {datamaster_mcp.__author__}")

# 测试主函数
from datamaster_mcp import main
# main()  # 启动 MCP 服务器
```

---

## 🖥️ 配置 MCP 客户端

### Claude Desktop 配置

#### 1. 找到配置文件

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

#### 2. 添加本地 MCP 服务器配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "python",
      "args": [
        "d:\\MCP\\SuperDataAnalysis_MCP\\datamaster_mcp\\main.py"
      ],
      "env": {
        "PYTHONPATH": "d:\\MCP\\SuperDataAnalysis_MCP"
      }
    }
  }
}
```

**注意：** 请将路径替换为你的实际项目路径。

#### 3. 使用开发模式安装的配置

如果你使用了 `pip install -e .` 安装，可以使用更简单的配置：

```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "datamaster-mcp"
    }
  }
}
```

---

## 🔧 环境配置

### 1. 创建环境变量文件

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入实际配置
notepad .env  # Windows
# 或
vim .env      # Linux/macOS
```

### 2. 配置数据库连接（可选）

编辑 `datamaster_mcp/config/database_config.json`：

```json
{
  "mysql_example": {
    "host": "localhost",
    "port": 3306,
    "database": "test_db",
    "username": "your_username",
    "password_env": "MYSQL_EXAMPLE_PASSWORD"
  },
  "postgresql_example": {
    "host": "localhost",
    "port": 5432,
    "database": "test_db",
    "username": "your_username",
    "password_env": "POSTGRES_EXAMPLE_PASSWORD"
  }
}
```

### 3. 配置 API 连接（可选）

编辑 `datamaster_mcp/config/api_config.json`：

```json
{
  "weather_api": {
    "base_url": "https://api.openweathermap.org/data/2.5",
    "auth": {
      "type": "api_key",
      "key_env": "WEATHER_API_KEY",
      "key_param": "appid"
    }
  }
}
```

---

## 🧪 功能测试

### 1. 基础功能测试

在 Claude Desktop 中测试以下功能：

```
# 测试数据导入
请帮我导入一个 Excel 文件到数据库中

# 测试数据查询
请查询数据库中的所有表

# 测试数据分析
请对某个表进行基础统计分析

# 测试数据导出
请将查询结果导出为 Excel 文件
```

### 2. 创建测试数据

```python
# 创建测试 Excel 文件
import pandas as pd

# 创建测试数据
data = {
    'name': ['张三', '李四', '王五', '赵六'],
    'age': [25, 30, 35, 28],
    'salary': [5000, 8000, 12000, 6500],
    'department': ['IT', 'HR', 'Finance', 'IT']
}

df = pd.DataFrame(data)
df.to_excel('test_data.xlsx', index=False)
print("测试数据文件已创建：test_data.xlsx")
```

### 3. 测试脚本验证

```bash
# 运行完整测试
python test_package.py

# 预期输出
🧪 DataMaster MCP 包测试
🔍 包导入测试:
✅ 包导入成功
   版本: 1.0.1
   作者: Shan (学习AI1000天)
🔍 主函数测试:
🔍 配置模块测试:
🔍 依赖测试:
✅ pandas 导入成功
✅ numpy 导入成功
✅ openpyxl 导入成功
✅ scipy 导入成功
✅ requests 导入成功

==================================================
📊 测试结果: 4/4 通过
🎉 所有测试通过！包已准备好发布。
```

---

## 🐛 常见问题排查

### 1. 导入错误

**问题：** `ModuleNotFoundError: No module named 'datamaster_mcp'`

**解决：**
```bash
# 确保在正确的目录
cd d:\MCP\SuperDataAnalysis_MCP

# 设置 Python 路径
export PYTHONPATH=$PYTHONPATH:$(pwd)  # Linux/macOS
set PYTHONPATH=%PYTHONPATH%;%cd%      # Windows

# 或使用模块方式运行
python -m datamaster_mcp.main
```

### 1.1. 相对导入错误（已修复）

**问题：** `ImportError: attempted relative import with no known parent package`

**解决：** 这个问题已经在最新版本中完美修复！现在 MCP 服务器支持多种启动方式：

```bash
# 方法1：直接运行（推荐）
python datamaster_mcp/main.py

# 方法2：模块运行
python -m datamaster_mcp.main

# 方法3：使用启动脚本
python start_mcp_server.py
```

所有导入都已改为绝对导入，无论哪种方式启动都不会有导入问题！

### 2. 依赖包问题

**问题：** 某些依赖包安装失败

**解决：**
```bash
# 升级 pip
pip install --upgrade pip

# 分别安装核心依赖
pip install mcp>=1.0.0
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install openpyxl>=3.1.0
```

### 3. MCP 连接问题

**问题：** Claude Desktop 无法连接到 MCP 服务器

**解决：**
1. 检查配置文件路径是否正确
2. 确保 Python 路径正确
3. 查看 Claude Desktop 的错误日志
4. 尝试手动启动 MCP 服务器验证

### 4. 权限问题

**问题：** 文件读写权限错误

**解决：**
```bash
# 确保目录权限
chmod 755 datamaster_mcp/  # Linux/macOS

# 创建必要的目录
mkdir -p data exports
```

---

## 📊 测试检查清单

### ✅ 基础功能
- [ ] 包导入成功
- [ ] MCP 服务器启动
- [ ] 依赖包正常加载
- [ ] 配置文件读取正常

### ✅ 数据功能
- [ ] Excel 文件导入
- [ ] CSV 文件导入
- [ ] SQL 查询执行
- [ ] 数据统计分析
- [ ] 数据导出功能

### ✅ 客户端连接
- [ ] Claude Desktop 配置正确
- [ ] MCP 连接建立成功
- [ ] 工具调用正常
- [ ] 错误处理正常

---

## 🎉 测试成功标志

当你看到以下情况时，说明本地测试成功：

1. **包测试通过**：`python test_package.py` 显示 4/4 通过
2. **服务器启动**：MCP 服务器正常启动并监听
3. **客户端连接**：Claude Desktop 能够识别并连接到 DataMaster MCP
4. **功能正常**：能够在 Claude 中调用数据分析功能
5. **数据处理**：能够导入、查询、分析和导出数据

---

## 💡 下一步

本地测试成功后，你可以：

1. **继续开发**：添加新功能或修复问题
2. **准备发布**：按照 `PYPI_RELEASE_GUIDE.md` 发布到 PyPI
3. **分享使用**：将配置方法分享给其他用户
4. **文档完善**：根据测试结果完善文档

---

**真nb！** 现在你可以在本地完整测试 DataMaster MCP 的所有功能了！🚀

**简单来说**：就是先装好依赖包，然后直接运行 Python 脚本启动服务器，再在 Claude Desktop 里配置一下路径，就能愉快地测试数据分析功能了！