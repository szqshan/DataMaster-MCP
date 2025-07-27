# 📊 DataMaster MCP

> **超级数据分析MCP工具** - 为AI提供强大的数据分析能力

## 🎯 核心理念

**工具专注数据获取和计算，AI专注智能分析和洞察**

## 🚀 快速开始

### 一键安装

```bash
pip install datamaster-mcp
```

### Claude Desktop 配置

在 Claude Desktop 配置文件中添加：

```json
{
  "mcpServers": {
    "datamaster-mcp": {
      "command": "uvx",
      "args": ["datamaster-mcp"]
    }
  }
}
```

**备用配置：**
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

### 立即开始使用

重启 Claude Desktop，然后说：
```
请帮我连接一个数据源
```

## 📖 使用指南

### 🚀 快速上手
- **⚡ [5分钟快速开始](QUICK_START.md)** - 立即开始使用
- **📋 [完整安装使用指南](INSTALLATION_AND_USAGE_GUIDE.md)** - 详细功能说明

### 📚 详细文档
- **📚 [文档索引](DOCUMENTATION_INDEX.md)** - 所有文档导航
- **📖 [用户使用手册](用户使用手册.md)** - 完整功能指南
- **🛠️ [开发者文档](开发者文档.md)** - 技术文档
- **⚙️ [客户端配置指南](CLIENT_CONFIG_GUIDE.md)** - Claude Desktop 配置

## ✨ 核心功能

### 📁 数据导入导出
- **Excel/CSV文件导入** - 支持多种格式和编码
- **数据库连接** - MySQL、PostgreSQL、MongoDB、SQLite
- **API数据获取** - RESTful API连接和数据提取
- **多格式导出** - Excel、CSV、JSON格式导出

### 🔍 数据查询分析
- **SQL查询执行** - 本地和外部数据库查询
- **数据统计分析** - 基础统计、相关性、异常值检测
- **数据质量检查** - 缺失值、重复值分析

### 🛠️ 数据处理
- **数据清洗** - 去重、填充缺失值
- **数据转换** - 类型转换、格式化
- **数据聚合** - 分组统计、汇总

## 📚 文档

### 用户文档
- [用户使用手册](用户使用手册.md)
- [本地测试指南](LOCAL_TEST_GUIDE.md)

### 开发者文档
- [开发者文档](开发者文档.md)
- [开发流程指南](DEVELOPMENT_WORKFLOW.md) 🆕
- [项目结构说明](项目结构说明.md)
- [PyPI发布指南](PYPI_RELEASE_GUIDE.md)

### 快速开发
```bash
# 设置开发环境
python scripts/setup_dev.py

# 运行测试
python scripts/setup_dev.py --test-only

# 发布新版本
python scripts/release.py 1.0.2
```

### 版本信息
- **[更新日志](CHANGELOG.md)** - 版本更新记录
- **[版本信息](VERSION.md)** - 当前版本详情

## 🛡️ 安全特性

- SQL注入防护
- 危险操作拦截
- 查询结果限制
- 参数验证
- 环境变量管理敏感信息

## 📞 支持

- 📖 查看[用户使用手册](用户使用手册.md)获取详细使用说明
- 🛠️ 查看[开发者文档](开发者文档.md)了解技术细节
- 📁 查看[项目结构说明](项目结构说明.md)了解文件组织
- 🐛 提交Issue报告问题或建议

---

**版本**: v1.0.2 | **状态**: ✅ 稳定版 | **更新**: 2025-01-24
