# 📊 DataMaster MCP

> **Super Data Analysis MCP Tool** - Providing powerful data analysis capabilities for AI

## 🎯 Core Philosophy

**Tools focus on data acquisition and computation, AI focuses on intelligent analysis and insights**

## 🚀 Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Start Service

```bash
python main.py
```

### Basic Usage

```python
# Import Excel data
connect_data_source(
    source_type="excel",
    config={"file_path": "data.xlsx"},
    target_table="my_data"
)

# Execute SQL query
execute_sql("SELECT * FROM my_data LIMIT 10")

# Data analysis
analyze_data(analysis_type="basic_stats", table_name="my_data")

# Export results
export_data(export_type="excel", data_source="my_data")
```

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

**Version**: v1.0.1 | **Status**: ✅ Stable | **Updated**: 2025-01-24