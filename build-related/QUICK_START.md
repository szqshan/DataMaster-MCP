# ⚡ DataMaster MCP 快速开始

> **5分钟上手指南** - 最快速度开始使用 DataMaster MCP

## 🎯 三步开始

### 第一步：安装
```bash
pip install datamaster-mcp
```

### 第二步：配置 Claude Desktop

找到配置文件：
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

添加配置：
```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "python",
      "args": ["-m", "datamaster_mcp.main"]
    }
  }
}
```

### 第三步：重启 Claude Desktop

完全关闭并重新启动 Claude Desktop。

## 🚀 立即测试

在 Claude Desktop 中输入：
```
请帮我连接一个数据源
```

## 📊 第一个数据分析

### 导入 Excel 文件
```
请帮我导入这个Excel文件：sales_data.xlsx
```

### 查看数据
```
显示前10行数据
```

### 基础分析
```
对这个数据做基础统计分析
```

### 导出结果
```
把分析结果导出为Excel文件
```

## 🎉 完成！

恭喜！你已经成功使用 DataMaster MCP 完成了第一个数据分析。

## 📖 下一步

- 📋 [完整安装使用指南](INSTALLATION_AND_USAGE_GUIDE.md) - 详细功能说明
- 📚 [用户使用手册](用户使用手册.md) - 高级功能
- 🛠️ [开发者文档](开发者文档.md) - 技术细节

## 🚨 遇到问题？

### 常见问题快速解决

**问题：找不到模块**
```bash
pip show datamaster-mcp
pip install --upgrade datamaster-mcp
```

**问题：Claude Desktop 无法连接**
1. 检查 JSON 格式是否正确
2. 重启 Claude Desktop
3. 尝试备用配置

**问题：文件路径错误**
- 使用绝对路径
- 检查文件是否存在
- 注意路径分隔符

---

**记住：工具专注数据获取和计算，AI专注智能分析和洞察！**