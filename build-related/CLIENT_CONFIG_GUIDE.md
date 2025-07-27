# DataMaster MCP 客户端配置指南

## 🎯 概述

当你通过 `pip install datamaster-mcp` 安装完包后，需要配置 Claude Desktop 客户端来使用 DataMaster MCP 服务器。

## 📋 配置步骤

### ⚡ 快速步骤

1. **安装 uv**：`pip install uv` 或 `scoop install uv`
2. **找到配置文件**：下面的路径
3. **复制配置**：uvx 配置粘贴进去
4. **重启 Claude Desktop**
5. **开始使用**！

**备用方案（如果没有 uv）：**
1. **安装包**：`pip install datamaster-mcp`
2. **使用模块路径配置**：`python -m datamaster_mcp.main`

### 1. 找到 Claude Desktop 配置文件

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

### 2. 配置 JSON 文件

#### 🚀 推荐配置（使用 uvx - 最新潮流！）

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

**前置条件：** 需要安装 uv
```bash
# Windows
scoop install uv
# 或者
pip install uv
```

### 🔧 备用配置（使用模块路径）

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

#### 方法三：使用完整路径（不推荐）

首先找到安装路径：
```bash
python -c "import datamaster_mcp; print(datamaster_mcp.__file__)"
```

然后配置：
```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "python",
      "args": [
        "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\datamaster_mcp\\main.py"
      ]
    }
  }
}
```

### 3. 高级配置（可选）

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

## 🔧 验证配置

### 1. 重启 Claude Desktop

配置完成后，完全关闭并重新启动 Claude Desktop 应用。

### 2. 检查连接状态

在 Claude Desktop 中，你应该能看到 DataMaster MCP 工具可用。可以尝试以下命令来测试：

```
请帮我连接一个数据源
```

或者：

```
显示可用的数据分析工具
```

## 🚨 常见问题

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

## 📝 完整配置示例

```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "python",
      "args": [
        "-m",
        "datamaster_mcp.main"
      ]
    },
    "other-mcp-server": {
      "command": "node",
      "args": [
        "/path/to/other/server.js"
      ]
    }
  }
}
```

## 🎉 成功标志

配置成功后，你应该能在 Claude Desktop 中：

1. ✅ 看到 DataMaster MCP 工具可用
2. ✅ 能够连接数据源（Excel、CSV、数据库等）
3. ✅ 能够执行数据分析操作
4. ✅ 能够导出分析结果

## 📞 获取帮助

如果遇到问题，可以：

1. 检查 Claude Desktop 的日志文件
2. 在命令行中直接运行 `python -m datamaster_mcp.main` 测试
3. 查看项目的 GitHub Issues
4. 联系开发者获取支持

---

**祝你使用愉快！** 🚀