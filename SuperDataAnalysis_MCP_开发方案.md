# SuperDataAnalysis MCP 完整开发方案

## 📋 项目概述

**项目名称：** SuperDataAnalysis MCP  
**项目目标：** 创建一个超级数据分析的MCP工具，为AI提供强大的数据分析能力  
**核心理念：** 工具专注数据获取和计算，AI专注智能分析和洞察  

## 🎯 设计原则

### 核心原则
1. **工具与智能分离**：工具只做数据处理，AI负责分析解读
2. **简化AI负担**：通过工具路由器减少AI需要处理的工具数量
3. **模块化设计**：功能模块化，易于维护和扩展
4. **标准化输出**：统一的数据返回格式
5. **错误友好**：完善的错误处理和用户提示

### 技术原则
- 基于FastMCP框架
- 使用SQLite作为主数据库
- 支持多种数据源接入
- 纯Python实现，跨平台兼容

## 🏗️ 系统架构

### 整体架构
```
SuperDataAnalysis_MCP/
├── main.py                    # 主MCP服务器
├── config/
│   ├── __init__.py
│   ├── database.py            # 数据库配置
│   └── settings.py            # 全局设置
├── core/
│   ├── __init__.py
│   ├── database_manager.py    # 数据库管理
│   ├── data_validator.py      # 数据验证
│   └── error_handler.py       # 错误处理
├── tools/
│   ├── __init__.py
│   ├── data_source.py         # 数据源工具
│   ├── data_analysis.py       # 数据分析工具
│   ├── data_export.py         # 数据导出工具
│   └── tool_router.py         # 工具路由器
├── utils/
│   ├── __init__.py
│   ├── file_handler.py        # 文件处理
│   ├── api_client.py          # API客户端
│   └── chart_generator.py     # 图表生成
├── data/                      # 数据存储目录
├── exports/                   # 导出文件目录
├── requirements.txt           # 依赖包
└── README.md                  # 项目说明
```

## 🔧 工具设计方案

### 工具路由器架构

**核心思想：** 将多个专业工具隐藏在路由器后面，AI只需要调用少数几个通用工具

**AI可见工具（5个）：**
1. `connect_data_source()` - 数据源连接路由器
2. `analyze_data()` - 数据分析路由器
3. `export_data()` - 数据导出路由器
4. `execute_sql()` - SQL执行工具
5. `get_data_info()` - 数据信息获取

### 🔧 核心工具代码实现

#### 1. 数据源连接工具 `connect_data_source()`

```python
@mcp.tool()
def connect_data_source(
    source_type: str,
    config: dict,
    target_table: str = None
) -> dict:
    """
    数据源连接路由器
    
    Args:
        source_type: 数据源类型 (mysql|mongodb|sqlite|excel|csv|api)
        config: 连接配置参数
        target_table: 目标表名（可选）
    
    Returns:
        dict: 连接结果和导入状态
    """
    try:
        # 路由到具体的连接函数
        if source_type == "mysql":
            return _connect_mysql(config, target_table)
        elif source_type == "mongodb":
            return _connect_mongodb(config, target_table)
        elif source_type == "sqlite":
            return _connect_sqlite(config, target_table)
        elif source_type == "excel":
            return _import_excel(config, target_table)
        elif source_type == "csv":
            return _import_csv(config, target_table)
        elif source_type == "api":
            return _call_api(config, target_table)
        else:
            return {
                "status": "error",
                "message": f"不支持的数据源类型: {source_type}",
                "supported_types": ["mysql", "mongodb", "sqlite", "excel", "csv", "api"]
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"数据源连接失败: {str(e)}",
            "error_type": type(e).__name__
        }
```

#### 2. 数据分析工具 `analyze_data()`

```python
@mcp.tool()
def analyze_data(
    analysis_type: str,
    table_name: str,
    columns: list = None,
    options: dict = None
) -> dict:
    """
    数据分析路由器
    
    Args:
        analysis_type: 分析类型 (basic_stats|correlation|outliers|trend等)
        table_name: 数据表名
        columns: 分析的列名列表
        options: 分析选项参数
    
    Returns:
        dict: 分析结果数据
    """
    try:
        # 验证表是否存在
        if not _table_exists(table_name):
            return {
                "status": "error",
                "message": f"表 '{table_name}' 不存在"
            }
        
        # 路由到具体的分析函数
        analysis_map = {
            "basic_stats": _calculate_basic_stats,
            "correlation": _calculate_correlation,
            "outliers": _detect_outliers,
            "trend": _trend_analysis,
            "group_stats": _group_by_stats,
            "missing_values": _check_missing_values,
            "duplicates": _check_duplicates,
            "percentiles": _calculate_percentiles,
            "moving_average": _calculate_moving_average,
            "normality_test": _test_normality
        }
        
        if analysis_type not in analysis_map:
            return {
                "status": "error",
                "message": f"不支持的分析类型: {analysis_type}",
                "supported_types": list(analysis_map.keys())
            }
        
        # 执行分析
        result = analysis_map[analysis_type](table_name, columns, options or {})
        
        return {
            "status": "success",
            "message": f"{analysis_type} 分析完成",
            "data": result,
            "metadata": {
                "analysis_type": analysis_type,
                "table_name": table_name,
                "columns": columns,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"数据分析失败: {str(e)}",
            "error_type": type(e).__name__
        }
```

#### 3. 数据导出工具 `export_data()`

```python
@mcp.tool()
def export_data(
    export_type: str,
    data_source: str,
    file_path: str = None,
    options: dict = None
) -> dict:
    """
    数据导出路由器
    
    Args:
        export_type: 导出类型 (excel|csv|json|pdf)
        data_source: 数据源（表名或SQL查询）
        file_path: 导出文件路径（可选，自动生成）
        options: 导出选项
    
    Returns:
        dict: 导出结果和文件路径
    """
    try:
        # 生成默认文件路径
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"exports/{data_source}_{timestamp}.{export_type}"
        
        # 路由到具体的导出函数
        export_map = {
            "excel": _export_to_excel,
            "csv": _export_to_csv,
            "json": _export_to_json,
            "pdf": _export_to_pdf
        }
        
        if export_type not in export_map:
            return {
                "status": "error",
                "message": f"不支持的导出类型: {export_type}",
                "supported_types": list(export_map.keys())
            }
        
        # 执行导出
        result = export_map[export_type](data_source, file_path, options or {})
        
        return {
            "status": "success",
            "message": f"数据导出完成",
            "data": {
                "file_path": file_path,
                "export_type": export_type,
                "file_size": result.get("file_size"),
                "record_count": result.get("record_count")
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "data_source": data_source
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"数据导出失败: {str(e)}",
            "error_type": type(e).__name__
        }
```

#### 4. SQL执行工具 `execute_sql()`

```python
@mcp.tool()
def execute_sql(
    query: str,
    params: dict = None,
    limit: int = 1000
) -> dict:
    """
    SQL执行工具
    
    Args:
        query: SQL查询语句
        params: 查询参数（防止SQL注入）
        limit: 结果限制行数
    
    Returns:
        dict: 查询结果
    """
    try:
        # SQL安全检查
        if not _is_safe_sql(query):
            return {
                "status": "error",
                "message": "检测到危险的SQL操作，已拦截",
                "blocked_operations": ["DROP", "DELETE", "UPDATE", "INSERT"]
            }
        
        # 添加LIMIT限制
        if "LIMIT" not in query.upper() and "SELECT" in query.upper():
            query = f"{query} LIMIT {limit}"
        
        # 执行查询
        with get_db_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            
            # 获取结果
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            # 转换为字典列表
            data = [dict(zip(columns, row)) for row in rows]
            
            return {
                "status": "success",
                "message": f"查询完成，返回 {len(data)} 条记录",
                "data": {
                    "columns": columns,
                    "rows": data,
                    "row_count": len(data)
                },
                "metadata": {
                    "query": query,
                    "execution_time": cursor.execution_time if hasattr(cursor, 'execution_time') else None,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"SQL执行失败: {str(e)}",
            "error_type": type(e).__name__,
            "query": query
        }
```

#### 5. 数据信息获取工具 `get_data_info()`

```python
@mcp.tool()
def get_data_info(
    info_type: str = "tables",
    table_name: str = None
) -> dict:
    """
    数据信息获取工具
    
    Args:
        info_type: 信息类型 (tables|schema|columns|stats)
        table_name: 表名（获取特定表信息时需要）
    
    Returns:
        dict: 数据库信息
    """
    try:
        with get_db_connection() as conn:
            if info_type == "tables":
                # 获取所有表名
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in cursor.fetchall()]
                
                return {
                    "status": "success",
                    "message": f"找到 {len(tables)} 个表",
                    "data": {
                        "tables": tables,
                        "table_count": len(tables)
                    }
                }
                
            elif info_type == "schema" and table_name:
                # 获取表结构
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                schema = []
                for col in columns:
                    schema.append({
                        "column_name": col[1],
                        "data_type": col[2],
                        "not_null": bool(col[3]),
                        "default_value": col[4],
                        "primary_key": bool(col[5])
                    })
                
                return {
                    "status": "success",
                    "message": f"表 '{table_name}' 结构信息",
                    "data": {
                        "table_name": table_name,
                        "columns": schema,
                        "column_count": len(schema)
                    }
                }
                
            elif info_type == "stats" and table_name:
                # 获取表统计信息
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                return {
                    "status": "success",
                    "message": f"表 '{table_name}' 统计信息",
                    "data": {
                        "table_name": table_name,
                        "row_count": row_count
                    }
                }
                
            else:
                return {
                    "status": "error",
                    "message": "无效的信息类型或缺少必要参数",
                    "supported_types": ["tables", "schema", "stats"]
                }
                
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取数据信息失败: {str(e)}",
            "error_type": type(e).__name__
        }
```



## 📊 详细工具列表

### 1. 数据源连接工具 `connect_data_source()`

**路由参数：** `source_type`

#### 内部实现的具体工具：
- `_connect_mysql()` - MySQL数据库连接
- `_connect_mongodb()` - MongoDB数据库连接
- `_connect_sqlite()` - SQLite数据库连接
- `_import_excel()` - Excel文件导入
- `_import_csv()` - CSV文件导入
- `_call_api()` - API数据获取
- `_batch_import()` - 批量文件导入

**使用示例：**
```python
# MySQL连接
connect_data_source(
    source_type="mysql",
    config={
        "host": "localhost",
        "database": "sales_db",
        "username": "user",
        "password": "pass"
    }
)

# Excel导入
connect_data_source(
    source_type="excel",
    config={
        "file_path": "sales_data.xlsx",
        "sheet_name": "Sheet1",
        "target_table": "sales"
    }
)
```

### 2. 数据分析工具 `analyze_data()`

**路由参数：** `analysis_type`

#### 内部实现的具体工具：

**基础统计分析：**
- `_calculate_basic_stats()` - 基础统计（均值、中位数、标准差等）
- `_calculate_percentiles()` - 百分位数计算
- `_calculate_mode()` - 众数计算
- `_calculate_range()` - 极差计算

**分组统计分析：**
- `_group_by_stats()` - 分组统计
- `_pivot_table()` - 数据透视表
- `_cross_tabulation()` - 交叉表统计
- `_frequency_distribution()` - 频率分布

**相关性分析：**
- `_calculate_correlation()` - 相关系数计算
- `_calculate_covariance()` - 协方差计算
- `_chi_square_test()` - 卡方检验
- `_t_test()` - t检验

**数据质量分析：**
- `_detect_outliers()` - 异常值检测
- `_check_missing_values()` - 缺失值检查
- `_check_duplicates()` - 重复值检查
- `_data_type_analysis()` - 数据类型分析

**时间序列分析：**
- `_calculate_moving_average()` - 移动平均
- `_calculate_growth_rate()` - 增长率计算
- `_seasonal_decompose()` - 季节性分解
- `_trend_analysis()` - 趋势分析

**分布分析：**
- `_test_normality()` - 正态性检验
- `_calculate_histogram()` - 直方图数据
- `_calculate_cumulative_distribution()` - 累积分布

**使用示例：**
```python
# 基础统计分析
analyze_data(
    analysis_type="basic_stats",
    table_name="sales",
    columns=["amount"]
)

# 异常值检测
analyze_data(
    analysis_type="outliers",
    table_name="sales",
    columns=["amount"],
    options={"method": "iqr"}
)

# 相关性分析
analyze_data(
    analysis_type="correlation",
    table_name="sales",
    columns=["price", "quantity"]
)
```

### 3. 数据导出工具 `export_data()`

**路由参数：** `export_type`

#### 内部实现的具体工具：
- `_export_to_excel()` - 导出到Excel
- `_export_to_csv()` - 导出到CSV
- `_export_to_json()` - 导出到JSON
- `_export_to_pdf()` - 导出到PDF报告
- `_save_chart()` - 保存图表文件

### 4. SQL执行工具 `execute_sql()`

**功能：** 直接执行SQL查询
**安全特性：**
- SQL注入防护
- 危险操作拦截（DROP、DELETE等）
- 查询结果限制

### 5. 数据信息获取工具 `get_data_info()`

**功能：**
- 获取表结构信息
- 获取数据库schema
- 获取表记录数
- 获取列信息和数据类型

### 6. 图表生成工具 `generate_chart()`

**支持的图表类型：**
- 柱状图（bar）
- 折线图（line）
- 散点图（scatter）
- 饼图（pie）
- 热力图（heatmap）
- 直方图（histogram）
- 箱线图（boxplot）

## 🔄 工作流程设计

### 典型使用场景

**场景1：Excel数据分析**
```
用户："分析一下这个Excel文件的销售数据趋势"

AI执行流程：
1. connect_data_source(source_type="excel", config={...})
2. get_data_info(table_name="sales")
3. analyze_data(analysis_type="trend", table_name="sales")
4. generate_chart(chart_type="line", data=trend_data)
5. AI基于结果生成分析报告
```

**场景2：数据库关联分析**
```
用户："分析价格和销量的关系"

AI执行流程：
1. get_data_info(table_name="products")
2. analyze_data(analysis_type="correlation", columns=["price", "quantity"])
3. generate_chart(chart_type="scatter", x="price", y="quantity")
4. AI解读相关性结果并给出建议
```

## 📝 数据格式标准

### 统一返回格式
```json
{
  "status": "success|error|warning",
  "message": "操作描述",
  "data": {
    // 具体数据内容
  },
  "metadata": {
    "timestamp": "2024-12-15T10:30:00",
    "execution_time": "0.15s",
    "tool_name": "analyze_data",
    "parameters": {...}
  }
}
```

### 错误处理格式
```json
{
  "status": "error",
  "message": "数据库连接失败",
  "error_code": "DB_CONNECTION_ERROR",
  "suggestions": [
    "检查数据库连接参数",
    "确认数据库服务是否运行"
  ]
}
```

## 🛠️ 技术栈

### 核心依赖
```
# MCP框架
fastmcp>=0.1.0

# 数据处理
pandas>=2.0.0
numpy>=1.24.0
sqlalchemy>=2.0.0

# 数据库连接
sqlite3  # 内置
pymongo>=4.0.0
mysql-connector-python>=8.0.0

# 文件处理
openpyxl>=3.1.0
xlrd>=2.0.0

# 统计分析
scipy>=1.10.0
statsmodels>=0.14.0
scikit-learn>=1.3.0

# 可视化
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.15.0

# 报告生成
reportlab>=4.0.0
jinja2>=3.1.0

# API客户端
requests>=2.31.0
```

## 🚀 开发计划

### 第一阶段：基础框架（1-2周）
- [ ] 搭建项目结构
- [ ] 实现数据库管理模块
- [ ] 创建基础工具路由器
- [ ] 实现SQL执行工具
- [ ] 基础错误处理

### 第二阶段：数据源接入（1-2周）
- [ ] Excel/CSV文件导入
- [ ] MySQL数据库连接
- [ ] MongoDB数据库连接
- [ ] API数据获取
- [ ] 批量文件处理

### 第三阶段：数据分析工具（2-3周）
- [ ] 基础统计分析工具
- [ ] 相关性分析工具
- [ ] 时间序列分析工具
- [ ] 数据质量检查工具
- [ ] 异常值检测工具

### 第四阶段：可视化和导出（1-2周）
- [ ] 图表生成工具
- [ ] 数据导出功能
- [ ] 报告生成模板
- [ ] 文件管理功能

### 第五阶段：测试和优化（1周）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化
- [ ] 文档完善

## 📚 使用文档

### 快速开始
```bash
# 安装依赖
pip install -r requirements.txt

# 启动MCP服务
python main.py
```

### 配置说明
```python
# config/settings.py
DATABASE_PATH = "data/analysis.db"
MAX_QUERY_ROWS = 10000
CHART_OUTPUT_DIR = "exports/charts/"
REPORT_OUTPUT_DIR = "exports/reports/"
```

## 🔒 安全考虑

1. **SQL注入防护**：参数化查询，SQL语句验证
2. **文件安全**：文件路径验证，文件类型检查
3. **数据隐私**：敏感数据脱敏，访问权限控制
4. **资源限制**：查询结果大小限制，执行时间限制

## 📈 扩展计划

### 未来功能
- 机器学习模型集成
- 实时数据流处理
- 多用户权限管理
- 云数据库支持
- 自定义分析模板

## 📁 详细文件结构和内容

### 项目初始化文件

#### `requirements.txt`
```txt
# MCP框架
fastmcp>=0.1.0

# 数据处理核心
pandas>=2.0.0
numpy>=1.24.0
sqlalchemy>=2.0.0

# 数据库连接
pymongo>=4.0.0
mysql-connector-python>=8.0.0
psycopg2-binary>=2.9.0  # PostgreSQL支持

# 文件处理
openpyxl>=3.1.0
xlrd>=2.0.0
chardet>=5.0.0  # 编码检测

# 统计分析
scipy>=1.10.0
statsmodels>=0.14.0
scikit-learn>=1.3.0

# 可视化
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.15.0
kaleido>=0.2.1  # plotly静态图导出

# 报告生成
reportlab>=4.0.0
jinja2>=3.1.0
markdown>=3.4.0

# API和网络
requests>=2.31.0
aiohttp>=3.8.0

# 工具库
python-dateutil>=2.8.0
pytz>=2023.3
loguru>=0.7.0  # 日志管理
pydantic>=2.0.0  # 数据验证
```

#### `config/settings.py`
```python
"""
全局配置文件
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据库配置
DATABASE_CONFIG = {
    "sqlite": {
        "path": PROJECT_ROOT / "data" / "analysis.db",
        "timeout": 30
    },
    "mysql": {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "charset": "utf8mb4"
    },
    "mongodb": {
        "host": os.getenv("MONGO_HOST", "localhost"),
        "port": int(os.getenv("MONGO_PORT", 27017))
    }
}

# 文件路径配置
PATH_CONFIG = {
    "data_dir": PROJECT_ROOT / "data",
    "exports_dir": PROJECT_ROOT / "exports",
    "charts_dir": PROJECT_ROOT / "exports" / "charts",
    "reports_dir": PROJECT_ROOT / "exports" / "reports",
    "temp_dir": PROJECT_ROOT / "temp",
    "logs_dir": PROJECT_ROOT / "logs"
}

# 安全配置
SECURITY_CONFIG = {
    "max_query_rows": 10000,
    "max_file_size_mb": 100,
    "allowed_file_types": [".xlsx", ".xls", ".csv", ".json"],
    "blocked_sql_keywords": ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"],
    "query_timeout_seconds": 60
}

# 图表配置
CHART_CONFIG = {
    "default_figsize": (10, 6),
    "default_dpi": 300,
    "supported_formats": ["png", "jpg", "svg", "pdf"],
    "color_palette": "viridis",
    "font_size": 12
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    "rotation": "1 day",
    "retention": "30 days"
}

# API配置
API_CONFIG = {
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1
}
```

#### `config/database.py`
```python
"""
数据库连接管理
"""
import sqlite3
import contextlib
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .settings import DATABASE_CONFIG, PATH_CONFIG
from loguru import logger

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.sqlite_path = DATABASE_CONFIG["sqlite"]["path"]
        self._ensure_directories()
        self._init_sqlite()
    
    def _ensure_directories(self):
        """确保必要目录存在"""
        for path in PATH_CONFIG.values():
            path.mkdir(parents=True, exist_ok=True)
    
    def _init_sqlite(self):
        """初始化SQLite数据库"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                # 启用外键约束
                conn.execute("PRAGMA foreign_keys = ON")
                # 设置WAL模式提高并发性能
                conn.execute("PRAGMA journal_mode = WAL")
                logger.info(f"SQLite数据库初始化完成: {self.sqlite_path}")
        except Exception as e:
            logger.error(f"SQLite数据库初始化失败: {e}")
            raise
    
    @contextlib.contextmanager
    def get_sqlite_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """获取SQLite连接"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.sqlite_path,
                timeout=DATABASE_CONFIG["sqlite"]["timeout"]
            )
            conn.row_factory = sqlite3.Row  # 启用字典式访问
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"SQLite连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_mysql_engine(self, config: dict):
        """创建MySQL引擎"""
        try:
            connection_string = (
                f"mysql+mysqlconnector://{config['username']}:{config['password']}"
                f"@{config['host']}:{config.get('port', 3306)}/{config['database']}"
                f"?charset={DATABASE_CONFIG['mysql']['charset']}"
            )
            engine = create_engine(connection_string, echo=False)
            logger.info(f"MySQL连接创建成功: {config['host']}:{config['database']}")
            return engine
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            raise
    
    def test_connection(self, db_type: str, config: dict) -> bool:
        """测试数据库连接"""
        try:
            if db_type == "sqlite":
                with self.get_sqlite_connection() as conn:
                    conn.execute("SELECT 1")
            elif db_type == "mysql":
                engine = self.create_mysql_engine(config)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"{db_type}连接测试失败: {e}")
            return False

# 全局数据库管理器实例
db_manager = DatabaseManager()

def get_db_connection():
    """获取默认数据库连接"""
    return db_manager.get_sqlite_connection()
```

### 核心模块实现

#### `core/data_validator.py`
```python
"""
数据验证模块
"""
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, validator
from .settings import SECURITY_CONFIG
from loguru import logger

class DataSourceConfig(BaseModel):
    """数据源配置验证"""
    source_type: str
    config: Dict[str, Any]
    target_table: Optional[str] = None
    
    @validator('source_type')
    def validate_source_type(cls, v):
        allowed_types = ['mysql', 'mongodb', 'sqlite', 'excel', 'csv', 'api']
        if v not in allowed_types:
            raise ValueError(f'不支持的数据源类型: {v}')
        return v

class SQLValidator:
    """SQL安全验证器"""
    
    @staticmethod
    def is_safe_sql(query: str) -> bool:
        """检查SQL查询是否安全"""
        query_upper = query.upper().strip()
        
        # 检查危险关键词
        for keyword in SECURITY_CONFIG["blocked_sql_keywords"]:
            if keyword in query_upper:
                logger.warning(f"检测到危险SQL关键词: {keyword}")
                return False
        
        # 检查是否为SELECT查询
        if not query_upper.startswith('SELECT'):
            logger.warning("只允许SELECT查询")
            return False
        
        # 检查注释注入
        if '--' in query or '/*' in query:
            logger.warning("检测到SQL注释，可能存在注入风险")
            return False
        
        return True
    
    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """验证表名是否合法"""
        # 只允许字母、数字、下划线
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, table_name))
    
    @staticmethod
    def validate_column_name(column_name: str) -> bool:
        """验证列名是否合法"""
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, column_name))

class FileValidator:
    """文件验证器"""
    
    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """验证文件路径是否安全"""
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False
            
            # 检查文件大小
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > SECURITY_CONFIG["max_file_size_mb"]:
                logger.error(f"文件过大: {file_size_mb:.2f}MB")
                return False
            
            # 检查文件扩展名
            if path.suffix.lower() not in SECURITY_CONFIG["allowed_file_types"]:
                logger.error(f"不支持的文件类型: {path.suffix}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return False
    
    @staticmethod
    def detect_file_encoding(file_path: str) -> str:
        """检测文件编码"""
        import chardet
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # 读取前10KB检测编码
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                logger.info(f"文件编码检测: {encoding} (置信度: {confidence:.2f})")
                return encoding or 'utf-8'
        except Exception as e:
            logger.warning(f"编码检测失败，使用默认编码: {e}")
            return 'utf-8'
```

#### `core/error_handler.py`
```python
"""
错误处理模块
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from loguru import logger
import traceback

class ErrorCode(Enum):
    """错误代码枚举"""
    # 数据库错误
    DB_CONNECTION_ERROR = "DB_CONNECTION_ERROR"
    DB_QUERY_ERROR = "DB_QUERY_ERROR"
    DB_TABLE_NOT_FOUND = "DB_TABLE_NOT_FOUND"
    
    # 文件错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_FORMAT_ERROR = "FILE_FORMAT_ERROR"
    FILE_SIZE_ERROR = "FILE_SIZE_ERROR"
    
    # 数据错误
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    DATA_TYPE_ERROR = "DATA_TYPE_ERROR"
    DATA_EMPTY_ERROR = "DATA_EMPTY_ERROR"
    
    # 安全错误
    SQL_INJECTION_ERROR = "SQL_INJECTION_ERROR"
    UNSAFE_OPERATION_ERROR = "UNSAFE_OPERATION_ERROR"
    
    # 系统错误
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    MEMORY_ERROR = "MEMORY_ERROR"

class MCPError(Exception):
    """MCP自定义异常"""
    
    def __init__(self, 
                 message: str, 
                 error_code: ErrorCode, 
                 suggestions: Optional[List[str]] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.suggestions = suggestions or []
        self.details = details or {}
        super().__init__(self.message)

class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_exception(e: Exception, context: str = "") -> Dict[str, Any]:
        """处理异常并返回标准错误格式"""
        if isinstance(e, MCPError):
            return ErrorHandler._format_mcp_error(e)
        else:
            return ErrorHandler._format_system_error(e, context)
    
    @staticmethod
    def _format_mcp_error(error: MCPError) -> Dict[str, Any]:
        """格式化MCP错误"""
        logger.error(f"MCP错误: {error.error_code.value} - {error.message}")
        
        return {
            "status": "error",
            "message": error.message,
            "error_code": error.error_code.value,
            "suggestions": error.suggestions,
            "details": error.details
        }
    
    @staticmethod
    def _format_system_error(error: Exception, context: str) -> Dict[str, Any]:
        """格式化系统错误"""
        error_msg = str(error)
        error_type = type(error).__name__
        
        logger.error(f"系统错误 [{context}]: {error_type} - {error_msg}")
        logger.debug(f"错误堆栈: {traceback.format_exc()}")
        
        # 根据异常类型提供建议
        suggestions = ErrorHandler._get_error_suggestions(error_type)
        
        return {
            "status": "error",
            "message": f"{context}: {error_msg}" if context else error_msg,
            "error_code": ErrorCode.SYSTEM_ERROR.value,
            "error_type": error_type,
            "suggestions": suggestions
        }
    
    @staticmethod
    def _get_error_suggestions(error_type: str) -> List[str]:
        """根据错误类型获取建议"""
        suggestions_map = {
            "FileNotFoundError": [
                "检查文件路径是否正确",
                "确认文件是否存在",
                "检查文件权限"
            ],
            "PermissionError": [
                "检查文件访问权限",
                "确认程序有足够的权限",
                "尝试以管理员身份运行"
            ],
            "ConnectionError": [
                "检查网络连接",
                "确认服务器地址正确",
                "检查防火墙设置"
            ],
            "TimeoutError": [
                "增加超时时间",
                "检查网络状况",
                "减少数据量"
            ],
            "MemoryError": [
                "减少数据处理量",
                "分批处理数据",
                "增加系统内存"
            ]
        }
        
        return suggestions_map.get(error_type, ["请检查输入参数和系统状态"])
```

### 工具实现细节

#### `tools/data_source.py` - 数据源工具实现
```python
"""
数据源连接工具实现
"""
import pandas as pd
import mysql.connector
from pymongo import MongoClient
from typing import Dict, Any, Optional
from pathlib import Path
from core.database_manager import db_manager
from core.data_validator import FileValidator, DataSourceConfig
from core.error_handler import ErrorHandler, MCPError, ErrorCode
from loguru import logger

def _connect_mysql(config: Dict[str, Any], target_table: Optional[str] = None) -> Dict[str, Any]:
    """MySQL数据库连接和数据导入"""
    try:
        # 验证配置
        required_keys = ['host', 'database', 'username', 'password']
        for key in required_keys:
            if key not in config:
                raise MCPError(
                    f"MySQL配置缺少必要参数: {key}",
                    ErrorCode.DATA_VALIDATION_ERROR,
                    [f"请提供{key}参数"]
                )
        
        # 创建MySQL连接
        engine = db_manager.create_mysql_engine(config)
        
        # 如果指定了目标表，则导入数据
        if target_table:
            source_table = config.get('source_table', target_table)
            
            # 从MySQL读取数据
            query = f"SELECT * FROM {source_table}"
            if 'limit' in config:
                query += f" LIMIT {config['limit']}"
            
            df = pd.read_sql(query, engine)
            
            # 导入到SQLite
            with db_manager.get_sqlite_connection() as conn:
                df.to_sql(target_table, conn, if_exists='replace', index=False)
            
            logger.info(f"MySQL数据导入完成: {len(df)}条记录 -> {target_table}")
            
            return {
                "status": "success",
                "message": f"MySQL数据导入完成",
                "data": {
                    "source_table": source_table,
                    "target_table": target_table,
                    "record_count": len(df),
                    "columns": list(df.columns)
                }
            }
        else:
            # 仅测试连接
            with engine.connect():
                pass
            
            return {
                "status": "success",
                "message": "MySQL连接成功",
                "data": {
                    "host": config['host'],
                    "database": config['database']
                }
            }
            
    except Exception as e:
        return ErrorHandler.handle_exception(e, "MySQL连接")

def _import_excel(config: Dict[str, Any], target_table: Optional[str] = None) -> Dict[str, Any]:
    """Excel文件导入"""
    try:
        file_path = config.get('file_path')
        if not file_path:
            raise MCPError(
                "Excel导入缺少file_path参数",
                ErrorCode.DATA_VALIDATION_ERROR,
                ["请提供Excel文件路径"]
            )
        
        # 验证文件
        if not FileValidator.validate_file_path(file_path):
            raise MCPError(
                "Excel文件验证失败",
                ErrorCode.FILE_FORMAT_ERROR,
                ["检查文件路径和格式"]
            )
        
        # 读取Excel文件
        sheet_name = config.get('sheet_name', 0)
        skiprows = config.get('skiprows', 0)
        nrows = config.get('nrows', None)
        
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            skiprows=skiprows,
            nrows=nrows
        )
        
        if df.empty:
            raise MCPError(
                "Excel文件为空",
                ErrorCode.DATA_EMPTY_ERROR,
                ["检查Excel文件内容"]
            )
        
        # 数据清理
        df = df.dropna(how='all')  # 删除全空行
        df.columns = df.columns.astype(str)  # 确保列名为字符串
        
        # 导入到数据库
        table_name = target_table or Path(file_path).stem
        
        with db_manager.get_sqlite_connection() as conn:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        logger.info(f"Excel导入完成: {file_path} -> {table_name} ({len(df)}条记录)")
        
        return {
            "status": "success",
            "message": f"Excel文件导入完成",
            "data": {
                "file_path": file_path,
                "table_name": table_name,
                "record_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns)
            }
        }
        
    except Exception as e:
        return ErrorHandler.handle_exception(e, "Excel导入")

def _import_csv(config: Dict[str, Any], target_table: Optional[str] = None) -> Dict[str, Any]:
    """CSV文件导入"""
    try:
        file_path = config.get('file_path')
        if not file_path:
            raise MCPError(
                "CSV导入缺少file_path参数",
                ErrorCode.DATA_VALIDATION_ERROR,
                ["请提供CSV文件路径"]
            )
        
        # 验证文件
        if not FileValidator.validate_file_path(file_path):
            raise MCPError(
                "CSV文件验证失败",
                ErrorCode.FILE_FORMAT_ERROR,
                ["检查文件路径和格式"]
            )
        
        # 检测编码
        encoding = config.get('encoding') or FileValidator.detect_file_encoding(file_path)
        
        # 读取CSV文件
        separator = config.get('separator', ',')
        skiprows = config.get('skiprows', 0)
        nrows = config.get('nrows', None)
        
        df = pd.read_csv(
            file_path,
            sep=separator,
            encoding=encoding,
            skiprows=skiprows,
            nrows=nrows
        )
        
        if df.empty:
            raise MCPError(
                "CSV文件为空",
                ErrorCode.DATA_EMPTY_ERROR,
                ["检查CSV文件内容"]
            )
        
        # 数据清理
        df = df.dropna(how='all')
        df.columns = df.columns.astype(str)
        
        # 导入到数据库
        table_name = target_table or Path(file_path).stem
        
        with db_manager.get_sqlite_connection() as conn:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        logger.info(f"CSV导入完成: {file_path} -> {table_name} ({len(df)}条记录)")
        
        return {
            "status": "success",
            "message": f"CSV文件导入完成",
            "data": {
                "file_path": file_path,
                "table_name": table_name,
                "record_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "encoding": encoding
            }
        }
        
    except Exception as e:
        return ErrorHandler.handle_exception(e, "CSV导入")
```

### 测试框架

#### `tests/test_tools.py`
```python
"""
工具测试模块
"""
import pytest
import pandas as pd
import tempfile
from pathlib import Path
from tools.data_source import _import_excel, _import_csv
from core.database_manager import db_manager

class TestDataSourceTools:
    """数据源工具测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def test_excel_import_success(self):
        """测试Excel导入成功"""
        # 创建测试Excel文件
        test_data = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'salary': [50000, 60000, 70000]
        })
        
        excel_path = self.temp_dir / "test_data.xlsx"
        test_data.to_excel(excel_path, index=False)
        
        # 测试导入
        config = {
            'file_path': str(excel_path),
            'sheet_name': 0
        }
        
        result = _import_excel(config, "test_table")
        
        assert result['status'] == 'success'
        assert result['data']['record_count'] == 3
        assert 'name' in result['data']['columns']
    
    def test_csv_import_with_encoding(self):
        """测试CSV导入（含编码检测）"""
        # 创建测试CSV文件
        test_data = pd.DataFrame({
            '姓名': ['张三', '李四', '王五'],
            '年龄': [25, 30, 35]
        })
        
        csv_path = self.temp_dir / "test_data.csv"
        test_data.to_csv(csv_path, index=False, encoding='utf-8')
        
        config = {
            'file_path': str(csv_path)
        }
        
        result = _import_csv(config, "test_csv_table")
        
        assert result['status'] == 'success'
        assert result['data']['encoding'] == 'utf-8'
    
    def test_file_not_found_error(self):
        """测试文件不存在错误"""
        config = {
            'file_path': '/nonexistent/file.xlsx'
        }
        
        result = _import_excel(config)
        
        assert result['status'] == 'error'
        assert 'FILE_NOT_FOUND' in result.get('error_code', '')
```

### 部署和运行脚本

#### `scripts/setup.py`
```python
"""
项目初始化脚本
"""
import os
import sys
from pathlib import Path
from loguru import logger

def setup_project():
    """初始化项目环境"""
    project_root = Path(__file__).parent.parent
    
    # 创建必要目录
    directories = [
        'data',
        'exports',
        'exports/charts',
        'exports/reports',
        'temp',
        'logs'
    ]
    
    for dir_name in directories:
        dir_path = project_root / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {dir_path}")
    
    # 创建.gitignore文件
    gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 虚拟环境
venv/
env/
ENV/

# 数据文件
data/*.db
data/*.sqlite
data/*.sqlite3

# 导出文件
exports/
temp/
logs/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 系统文件
.DS_Store
Thumbs.db

# 环境变量
.env
.env.local
    """
    
    gitignore_path = project_root / '.gitignore'
    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write(gitignore_content.strip())
    
    logger.info("项目初始化完成！")
    logger.info("下一步：")
    logger.info("1. pip install -r requirements.txt")
    logger.info("2. python main.py")

if __name__ == "__main__":
    setup_project()
```

#### `scripts/run_tests.py`
```python
"""
测试运行脚本
"""
import subprocess
import sys
from pathlib import Path

def run_tests():
    """运行所有测试"""
    project_root = Path(__file__).parent.parent
    
    # 运行pytest
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--cov=tools',
        '--cov=core',
        '--cov-report=html',
        '--cov-report=term'
    ]
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("\n✅ 所有测试通过！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 测试失败，退出码: {e.returncode}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
```

---

**项目状态：** 设计完成，准备开发  
**预计完成时间：** 6-8周  
**维护计划：** 持续更新和功能扩展

## 📝 开发检查清单

### 第一阶段检查项
- [ ] 项目结构创建完成
- [ ] 依赖包安装成功
- [ ] 数据库连接测试通过
- [ ] 基础配置文件就位
- [ ] 日志系统正常工作
- [ ] 错误处理机制测试

### 代码质量标准
- [ ] 所有函数都有类型注解
- [ ] 所有模块都有文档字符串
- [ ] 错误处理覆盖率 > 90%
- [ ] 单元测试覆盖率 > 80%
- [ ] 代码符合PEP8规范
- [ ] 安全检查通过

### 性能要求
- [ ] 单次查询响应时间 < 5秒
- [ ] 文件导入速度 > 1000行/秒
- [ ] 内存使用 < 500MB
- [ ] 支持并发连接数 > 10