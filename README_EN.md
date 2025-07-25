# 📊 DataMaster MCP

> **Super Data Analysis MCP Tool** - Providing powerful data analysis capabilities for AI

## 🎯 Core Philosophy

**Tools focus on data acquisition and computation, AI focuses on intelligent analysis and insights**

## 🚀 Quick Start

### One-Click Installation

```bash
pip install datamaster-mcp
```

### Claude Desktop Configuration

Add to Claude Desktop config file:

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

**Alternative Configuration:**
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

### Start Using Immediately

Restart Claude Desktop, then say:
```
Please help me connect to a data source
```

## 📖 Complete Usage Guide

**🎯 Must-read for new users:** [📋 Complete Installation & Usage Guide](INSTALLATION_AND_USAGE_GUIDE.md)

This guide includes:
- ✅ Detailed installation steps
- ⚙️ Claude Desktop configuration
- 📚 Basic usage tutorials
- 🔧 Advanced features
- 🚨 Troubleshooting
- 📖 Practical examples

## ✨ Core Features

### 📁 Data Import & Export
- **Excel/CSV File Import** - Support multiple formats and encodings
- **Database Connection** - MySQL, PostgreSQL, MongoDB, SQLite
- **API Data Fetching** - RESTful API connection and data extraction
- **Multi-format Export** - Excel, CSV, JSON format export

### 🔍 Data Query & Analysis
- **SQL Query Execution** - Local and external database queries
- **Statistical Analysis** - Basic statistics, correlation, outlier detection
- **Data Quality Check** - Missing values, duplicate analysis

### 🛠️ Data Processing
- **Data Cleaning** - Deduplication, missing value filling
- **Data Transformation** - Type conversion, formatting
- **Data Aggregation** - Group statistics, summarization

## 📚 Documentation

- **[User Manual](用户使用手册.md)** - Complete feature usage guide
- **[Developer Documentation](开发者文档.md)** - Technical documentation and AI usage guide
- **[Project Structure](项目结构说明.md)** - Directory structure and file descriptions
- **[Changelog](CHANGELOG.md)** - Version update records
- **[Version Info](VERSION.md)** - Current version details

## 🛡️ Security Features

- SQL injection protection
- Dangerous operation interception
- Query result limitations
- Parameter validation
- Environment variable management for sensitive information

## 📞 Support

- 📖 Check [User Manual](用户使用手册.md) for detailed usage instructions
- 🛠️ Check [Developer Documentation](开发者文档.md) for technical details
- 📁 Check [Project Structure](项目结构说明.md) for file organization
- 🐛 Submit Issues to report problems or suggestions

---

**Version**: v1.0.2 | **Status**: ✅ Stable | **Updated**: 2025-01-24