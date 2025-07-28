#!/usr/bin/env python3
"""
DataMaster MCP - 超级数据分析工具
为AI提供强大的数据分析能力

核心理念：工具专注数据获取和计算，AI专注智能分析和洞察

模块化架构：
- core/database.py: 数据库管理和连接
- core/data_analysis.py: 数据分析和统计
- core/data_processing.py: 数据处理和导出
- core/api_manager.py: API管理和数据获取
"""

import json
import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataMaster_MCP")

# 导入核心模块
try:
    from .core.database import (
        connect_data_source_impl,
        execute_sql_impl,
        query_external_database_impl,
        list_data_sources_impl,
        manage_database_config_impl,
        init_database_module
    )
    from .core.data_analysis import (
        analyze_data_impl,
        get_data_info_impl,
        init_data_analysis_module
    )
    from .core.data_processing import (
        process_data_impl,
        export_data_impl,
        init_data_processing_module
    )
    from .core.api_manager import (
        manage_api_config_impl,
        fetch_api_data_impl,
        api_data_preview_impl,
        create_api_storage_session_impl,
        list_api_storage_sessions_impl,
        init_api_manager_module
    )
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    current_dir = Path(__file__).parent.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from datamaster_mcp.core.database import (
        connect_data_source_impl,
        execute_sql_impl,
        query_external_database_impl,
        list_data_sources_impl,
        manage_database_config_impl,
        init_database_module
    )
    from datamaster_mcp.core.data_analysis import (
        analyze_data_impl,
        get_data_info_impl,
        init_data_analysis_module
    )
    from datamaster_mcp.core.data_processing import (
        process_data_impl,
        export_data_impl,
        init_data_processing_module
    )
    from datamaster_mcp.core.api_manager import (
        manage_api_config_impl,
        fetch_api_data_impl,
        api_data_preview_impl,
        create_api_storage_session_impl,
        list_api_storage_sessions_impl,
        init_api_manager_module
    )

# ================================
# 配置和初始化
# ================================
TOOL_NAME = "DataMaster_MCP"
DATA_DIR = "data"
EXPORTS_DIR = "exports"

# 创建MCP服务器
mcp = FastMCP(TOOL_NAME)

# 确保目录存在
for directory in [DATA_DIR, EXPORTS_DIR]:
    Path(directory).mkdir(exist_ok=True)

# 初始化所有核心模块
try:
    init_database_module()
    init_data_analysis_module()
    init_data_processing_module()
    init_api_manager_module()
    logger.info("所有核心模块初始化完成")
except Exception as e:
    logger.error(f"模块初始化失败: {e}")

# ================================
# 数据库管理工具
# ================================

@mcp.tool()
def connect_data_source(
    source_type: str,
    config: dict,
    target_table: str = None,
    target_database: str = None
) -> str:
    """
    🔗 数据源连接路由器 - AI必读使用指南
    
    ⚠️ 重要：数据库连接采用"两步连接法"设计模式！
    
    📋 支持的数据源类型：
    - "excel" - Excel文件导入到数据库
    - "csv" - CSV文件导入到数据库
    - "json" - JSON文件导入到数据库（支持嵌套结构自动扁平化）
    - "sqlite" - SQLite数据库文件连接
    - "mysql" - MySQL数据库连接（第一步：创建临时配置）
    - "postgresql" - PostgreSQL数据库连接（第一步：创建临时配置）
    - "mongodb" - MongoDB数据库连接（第一步：创建临时配置）
    - "database_config" - 使用已有配置连接（第二步：实际连接）
    
    🎯 AI使用流程：
    1️⃣ 数据库连接第一步：
       connect_data_source(source_type="mysql", config={host, port, user, database, password})
       → 返回临时配置名称（如：temp_mysql_20250724_173102）
    
    2️⃣ 数据库连接第二步：
       connect_data_source(source_type="database_config", config={"database_name": "配置名称"})
       → 建立可查询的数据库连接
    
    3️⃣ 查询数据：
       使用 query_external_database(database_name="配置名称", query="SQL")
    
    💡 参数兼容性：
    - 支持 "user" 或 "username" 参数
    - 端口号使用数字类型（如：3306）
    - 密码使用字符串类型
    
    Args:
        source_type: 数据源类型，必须是上述支持的类型之一
        config: 配置参数字典，格式根据source_type不同
        target_table: 目标表名（文件导入时可选）
        target_database: 目标数据库名称（文件导入到外部数据库时可选）
    
    Returns:
        str: JSON格式的连接结果，包含状态、消息和配置信息
    
    ⚡ AI快速上手：
    记住"两步连接法"：先创建配置 → 再使用配置 → 最后查询数据
    """
    return connect_data_source_impl(source_type, config, target_table, target_database)

@mcp.tool()
def execute_sql(
    query: str,
    params: dict = None,
    limit: int = 1000,
    data_source: str = None
) -> str:
    """
    📊 SQL执行工具 - 本地数据库查询专用
    
    🎯 使用场景：
    - 查询本地SQLite数据库（默认）
    - 查询已导入的Excel/CSV数据
    - 查询指定的本地数据源
    
    ⚠️ 重要区别：
    - 本地数据查询 → 使用此工具 (execute_sql)
    - 外部数据库查询 → 使用 query_external_database
    
    🔒 安全特性：
    - 自动添加LIMIT限制防止大量数据返回
    - 支持参数化查询防止SQL注入
    - 只允许SELECT查询，拒绝危险操作
    
    Args:
        query: SQL查询语句（推荐使用SELECT语句）
        params: 查询参数字典，用于参数化查询（可选）
        limit: 结果行数限制，默认1000行（可选）
        data_source: 数据源名称，默认本地SQLite（可选）
    
    Returns:
        str: JSON格式查询结果，包含列名、数据行和统计信息
    
    💡 AI使用提示：
    - 查询本地数据时优先使用此工具
    - 查询外部数据库时使用 query_external_database
    - 使用 get_data_info 先了解表结构
    """
    return execute_sql_impl(query, params, limit, data_source)

@mcp.tool()
def query_external_database(
    database_name: str,
    query: str,
    limit: int = 1000
) -> str:
    """
    🌐 外部数据库查询工具 - 专门查询外部数据库
    
    🎯 使用场景：
    - 查询MySQL数据库
    - 查询PostgreSQL数据库
    - 查询MongoDB数据库
    - 查询所有通过connect_data_source连接的外部数据库
    
    ⚠️ 前置条件：
    必须先使用connect_data_source建立数据库连接并获得配置名称
    
    🔄 完整流程示例：
    1️⃣ connect_data_source(source_type="mysql", config={...}) → 获得配置名
    2️⃣ connect_data_source(source_type="database_config", config={"database_name": "配置名"}) → 建立连接
    3️⃣ query_external_database(database_name="配置名", query="SELECT * FROM table") → 查询数据
    
    💡 查询语法支持：
    - MySQL/PostgreSQL: 标准SQL语法
    - MongoDB: 支持多种查询格式（JSON、JavaScript风格等）
    
    Args:
        database_name: 数据库配置名称（从connect_data_source获得）
        query: 查询语句，SQL或MongoDB查询语法
        limit: 结果行数限制，默认1000行
    
    Returns:
        str: JSON格式查询结果，包含数据行、统计信息和元数据
    
    🚀 AI使用建议：
    - 这是查询外部数据库的首选工具
    - 使用list_data_sources查看可用的数据库配置
    - 配置名称通常格式为：temp_mysql_20250724_173102
    """
    return query_external_database_impl(database_name, query, limit)

@mcp.tool()
def list_data_sources() -> str:
    """
    📋 数据源列表工具 - 查看所有可用的数据源
    
    🎯 功能说明：
    - 显示本地SQLite数据库状态
    - 列出所有外部数据库配置
    - 显示每个数据源的连接状态和基本信息
    - 区分临时配置和永久配置
    
    📊 返回信息包括：
    - 数据源名称和类型
    - 连接状态（可用/已配置/已禁用）
    - 主机地址和数据库名
    - 是否为默认数据源
    - 配置创建时间（临时配置）
    
    💡 使用场景：
    - 不确定有哪些数据源时查看
    - 检查数据库连接状态
    - 查找临时配置名称
    - 了解可用的查询目标
    
    Returns:
        str: JSON格式的数据源列表，包含详细的配置信息
    
    🚀 AI使用建议：
    - 在查询数据前先调用此工具了解可用数据源
    - 用于获取正确的database_name参数
    - 检查临时配置是否还存在
    """
    return list_data_sources_impl()

@mcp.tool()
def manage_database_config(
    action: str,
    config: dict = None
) -> str:
    """
    ⚙️ 数据库配置管理工具 - 管理所有数据库连接配置
    
    🎯 支持的操作类型：
    - "list" - 列出所有数据库配置（包括临时和永久）
    - "test" - 测试指定配置的连接状态
    - "add" - 添加永久数据库配置
    - "remove" - 删除指定配置
    - "reload" - 重新加载配置文件
    - "list_temp" - 仅列出临时配置
    - "cleanup_temp" - 清理所有临时配置
    
    📋 常用操作示例：
    
    1️⃣ 查看所有配置：
       manage_database_config(action="list")
    
    2️⃣ 测试连接：
       manage_database_config(action="test", config={"database_name": "配置名"})
    
    3️⃣ 添加永久配置：
       manage_database_config(action="add", config={
           "database_name": "my_mysql",
           "database_config": {
               "host": "localhost",
               "port": 3306,
               "type": "mysql",
               "user": "root",
               "database": "test_db",
               "password": "password"
           }
       })
    
    4️⃣ 清理临时配置：
       manage_database_config(action="cleanup_temp")
    
    Args:
        action: 操作类型，必须是上述支持的操作之一
        config: 配置参数字典，根据action类型提供不同参数
    
    Returns:
        str: JSON格式操作结果，包含状态、消息和相关数据
    
    💡 AI使用建议：
    - 不确定有哪些配置时，先用action="list"查看
    - 连接问题时，用action="test"检查配置状态
    - 临时配置过多时，用action="cleanup_temp"清理
    """
    return manage_database_config_impl(action, config)

# ================================
# 数据分析工具
# ================================

@mcp.tool()
def get_data_info(
    info_type: str = "tables",
    table_name: str = None,
    data_source: str = None
) -> str:
    """
    📊 数据信息获取工具 - 查看数据库结构和统计信息
    
    功能说明：
    - 获取数据库表列表、表结构、数据统计等信息
    - 支持本地SQLite和外部数据库
    - 提供详细的表结构和数据概览
    - 智能数据库清理管理功能
    
    Args:
        info_type: 信息类型
            - "tables": 获取所有表/集合列表（默认）
            - "schema": 获取指定表的结构信息（需要table_name）
            - "stats": 获取指定表的统计信息（需要table_name）
            - "cleanup": 智能检测过时数据和表，提供清理建议
        table_name: 表名（当info_type为schema或stats时必需）
        data_source: 数据源名称
            - None: 使用本地SQLite数据库（默认）
            - 配置名称: 使用外部数据库（需先通过manage_database_config创建配置）
    
    Returns:
        str: JSON格式的数据库信息，包含状态、数据和元数据
    
    🤖 AI使用建议：
    1. 数据探索：先用info_type="tables"查看所有表
    2. 结构分析：用info_type="schema"了解表结构
    3. 数据概览：用info_type="stats"获取统计信息
    4. 数据库维护：用info_type="cleanup"检测并清理过时数据
    5. 外部数据库：确保data_source配置已存在
    
    💡 最佳实践：
    - 在查询数据前先了解表结构
    - 使用stats了解数据分布和质量
    - 定期使用cleanup功能维护数据库整洁
    - 结合analyze_data工具进行深度分析
    
    ⚠️ 常见错误避免：
    - schema和stats必须指定table_name
    - 外部数据库需要有效的data_source配置
    - 表名区分大小写
    - cleanup功能仅适用于本地SQLite数据库
    
    📈 高效使用流程：
    1. get_data_info(info_type="tables") → 查看所有表
    2. get_data_info(info_type="schema", table_name="表名") → 了解结构
    3. get_data_info(info_type="stats", table_name="表名") → 查看统计
    4. get_data_info(info_type="cleanup") → 检测过时数据
    5. analyze_data() → 深度分析
    
    🎯 关键理解点：
    - 这是数据探索的第一步工具
    - 为后续分析提供基础信息
    - 支持本地和远程数据源
    - 智能维护数据库整洁性
    
    🧹 数据库清理功能（info_type="cleanup"）：
    - 自动检测测试表、临时表、过时表
    - 识别空表和重复表
    - 分析表的创建时间和最后访问时间
    - 提供智能清理建议，询问用户是否执行清理
    - 支持批量清理和选择性清理
    """
    return get_data_info_impl(info_type, table_name, data_source)

@mcp.tool()
def analyze_data(
    analysis_type: str,
    table_name: str,
    columns: list = None,
    options: dict = None
) -> str:
    """
    🔍 数据分析工具 - 执行各种统计分析和数据质量检查
    
    功能说明：
    - 提供5种核心数据分析功能
    - 支持指定列分析或全表分析
    - 自动处理数据类型和缺失值
    - 返回详细的分析结果和可视化建议
    
    Args:
        analysis_type: 分析类型
            - "basic_stats": 基础统计分析（均值、中位数、标准差等）
            - "correlation": 相关性分析（数值列之间的相关系数）
            - "outliers": 异常值检测（IQR、Z-score方法）
            - "missing_values": 缺失值分析（缺失率、分布模式）
            - "duplicates": 重复值检测（完全重复、部分重复）
        table_name: 要分析的数据表名
        columns: 分析的列名列表（可选）
            - None: 分析所有适用列
            - ["col1", "col2"]: 只分析指定列
        options: 分析选项（可选字典）
            - outliers: {"method": "iqr|zscore", "threshold": 1.5}
            - correlation: {"method": "pearson|spearman"}
            - basic_stats: {"percentiles": [25, 50, 75, 90, 95]}
    
    Returns:
        str: JSON格式的分析结果，包含统计数据、图表建议和洞察
    
    🤖 AI使用建议：
    1. 数据概览：先用"basic_stats"了解数据分布
    2. 质量检查：用"missing_values"和"duplicates"检查数据质量
    3. 关系探索：用"correlation"发现变量关系
    4. 异常检测：用"outliers"识别异常数据
    5. 逐步深入：从基础统计到高级分析
    
    💡 最佳实践：
    - 先进行basic_stats了解数据概况
    - 数值列用correlation分析关系
    - 大数据集指定columns提高效率
    - 结合get_data_info了解表结构
    
    ⚠️ 常见错误避免：
    - 确保table_name存在
    - correlation只适用于数值列
    - columns名称必须准确匹配
    - 空表或单列表某些分析会失败
    
    📈 高效使用流程：
    1. get_data_info() → 了解表结构
    2. analyze_data("basic_stats") → 基础统计
    3. analyze_data("missing_values") → 质量检查
    4. analyze_data("correlation") → 关系分析
    5. analyze_data("outliers") → 异常检测
    
    🎯 关键理解点：
    - 每种分析类型有特定适用场景
    - 结果包含统计数据和业务洞察
    - 支持参数化定制分析行为
    """
    return analyze_data_impl(analysis_type, table_name, columns, options)

# ================================
# 数据处理工具
# ================================

@mcp.tool()
def process_data(
    operation_type: str,
    data_source: str,
    config: dict,
    target_table: str = None
) -> str:
    """
    ⚙️ 数据处理工具 - 执行数据清洗、转换、筛选等操作
    
    功能说明：
    - 提供6种核心数据处理功能
    - 支持表和SQL查询作为数据源
    - 灵活的配置参数系统
    - 可指定目标表或覆盖原表
    
    Args:
        operation_type: 处理操作类型
            - "clean": 数据清洗（去重、填充缺失值、数据类型转换）
            - "transform": 数据转换（列重命名、标准化、新列计算）
            - "filter": 数据筛选（条件过滤、列选择、数据采样）
            - "aggregate": 数据聚合（分组统计、汇总计算）
            - "merge": 数据合并（表连接、数据拼接）
            - "reshape": 数据重塑（透视表、宽长转换）
        data_source: 数据源
            - 表名: 处理整个表
            - SQL查询: 处理查询结果
        config: 操作配置字典（必需）
            - clean: {"remove_duplicates": True, "fill_missing": {"col": {"method": "mean"}}}
            - transform: {"rename_columns": {"old": "new"}, "normalize": {"columns": ["col1"]}}
            - filter: {"filter_condition": "age > 18", "select_columns": ["name", "age"]}
            - aggregate: {"group_by": {"columns": ["dept"], "agg": {"salary": "mean"}}}
            - merge: {"right_table": "table2", "on": "id", "how": "inner"}
            - reshape: {"pivot": {"index": "date", "columns": "product", "values": "sales"}}
        target_table: 目标表名（可选）
            - None: 覆盖原表（默认）
            - 表名: 保存到新表
    
    Returns:
        str: JSON格式的处理结果，包含操作详情、影响行数和新表信息
    
    🤖 AI使用建议：
    1. 数据清洗：先用"clean"处理数据质量问题
    2. 数据转换：用"transform"标准化和计算新字段
    3. 数据筛选：用"filter"获取目标数据子集
    4. 数据聚合：用"aggregate"生成汇总报表
    5. 数据合并：用"merge"关联多个数据源
    6. 数据重塑：用"reshape"改变数据结构
    
    💡 最佳实践：
    - 处理前先备份重要数据
    - 使用target_table避免覆盖原数据
    - 复杂操作分步骤执行
    - 结合analyze_data验证处理结果
    
    ⚠️ 常见错误避免：
    - config参数必须符合operation_type要求
    - 确保引用的列名存在
    - merge操作需要确保关联键存在
    - 大数据量操作注意性能
    
    📈 高效使用流程：
    1. analyze_data() → 了解数据质量
    2. process_data("clean") → 清洗数据
    3. process_data("transform") → 转换数据
    4. process_data("filter") → 筛选数据
    5. analyze_data() → 验证处理结果
    
    🎯 关键理解点：
    - 每种操作类型有特定的config格式
    - 支持链式处理（上一步输出作为下一步输入）
    - 提供详细的操作日志和统计信息
    
    📋 配置示例：
    ```python
    # 数据清洗
    config = {
        "remove_duplicates": True,
        "fill_missing": {
            "age": {"method": "mean"},
            "name": {"method": "mode"}
        }
    }
    
    # 数据筛选
    config = {
        "filter_condition": "age > 18 and salary > 5000",
        "select_columns": ["name", "age", "department"]
    }
    
    # 数据聚合
    config = {
        "group_by": {
            "columns": ["department"],
            "agg": {
                "salary": "mean",
                "age": "count"
            }
        }
    }
    ```
    """
    return process_data_impl(operation_type, data_source, config, target_table)

@mcp.tool()
def export_data(
    export_type: str,
    data_source: str,
    file_path: str = None,
    options: dict = None
) -> str:
    """
    📤 数据导出工具 - 将数据导出为各种格式文件
    
    功能说明：
    - 支持多种导出格式：Excel、CSV、JSON
    - 可导出表数据或SQL查询结果
    - 自动生成文件路径或使用指定路径
    - 支持导出选项自定义
    
    Args:
        export_type: 导出格式类型
            - "excel": Excel文件(.xlsx)
            - "csv": CSV文件(.csv)
            - "json": JSON文件(.json)
        data_source: 数据源
            - 表名: 直接导出整个表
            - SQL查询: 导出查询结果（以SELECT开头）
        file_path: 导出文件路径（可选）
            - None: 自动生成路径到exports/目录
            - 指定路径: 使用自定义路径
        options: 导出选项（可选字典）
            - Excel: {"sheet_name": "工作表名", "auto_adjust_columns": True}
            - CSV: {"encoding": "utf-8", "separator": ","}
            - JSON: {"orient": "records", "indent": 2}
    
    Returns:
        str: JSON格式的导出结果，包含文件路径、大小、记录数等信息
    
    🤖 AI使用建议：
    1. 表导出：export_data("excel", "table_name")
    2. 查询导出：export_data("csv", "SELECT * FROM table WHERE condition")
    3. 自定义格式：使用options参数调整导出格式
    4. 批量导出：结合循环导出多个表或查询
    
    💡 最佳实践：
    - Excel适合报表和可视化
    - CSV适合数据交换和导入其他系统
    - JSON适合API和程序处理
    - 大数据量优先使用CSV
    
    ⚠️ 常见错误避免：
    - 确保data_source存在（表名）或语法正确（SQL）
    - 文件路径目录必须存在或可创建
    - 注意文件权限和磁盘空间
    
    📈 高效使用流程：
    1. 确定导出需求（格式、内容）
    2. 选择合适的export_type
    3. 准备data_source（表名或SQL）
    4. 设置options（如需要）
    5. 执行导出并检查结果
    
    🎯 关键理解点：
    - 支持表和查询两种数据源
    - 自动处理文件路径和格式
    - 提供详细的导出统计信息
    """
    return export_data_impl(export_type, data_source, file_path, options)

# ================================
# API管理工具
# ================================

@mcp.tool()
def manage_api_config(
    action: str,
    api_name: str = None,
    config_data: dict = None
) -> str:
    """
    管理API配置
    
    Args:
        action: 操作类型 (list|test|add|remove|reload|get_endpoints)
        api_name: API名称
        config_data: API配置数据
    
    Returns:
        str: 操作结果
    """
    return manage_api_config_impl(action, api_name, config_data)

@mcp.tool()
def fetch_api_data(
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    data: dict = None,
    method: str = None,
    transform_config: dict = None,
    storage_session_id: str = None
) -> str:
    """
    从API获取数据并自动存储到数据库（方式二：自动持久化流程）
    
    注意：已删除方式一（手动流程），所有API数据默认直接存储到数据库
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        data: 请求数据（POST/PUT）
        method: HTTP方法
        transform_config: 数据转换配置
        storage_session_id: 存储会话ID（可选，不提供时自动创建）
    
    Returns:
        str: 数据存储结果和会话信息
    """
    return fetch_api_data_impl(api_name, endpoint_name, params, data, method, transform_config, storage_session_id)

@mcp.tool()
def api_data_preview(
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    max_rows: int = 10,
    max_cols: int = 10,
    preview_fields: list = None,
    preview_depth: int = 3,
    show_data_types: bool = True,
    show_summary: bool = True,
    truncate_length: int = 100
) -> str:
    """
    🔍 API数据预览工具 - 灵活预览API返回数据
    
    功能说明：
    - 支持灵活的数据预览配置
    - 可指定预览字段和深度
    - 提供数据类型和摘要信息
    - 避免数据截断问题
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        max_rows: 最大显示行数 (默认10)
        max_cols: 最大显示列数 (默认10)
        preview_fields: 指定预览的字段列表 (可选)
        preview_depth: JSON嵌套预览深度 (默认3)
        show_data_types: 是否显示数据类型信息 (默认True)
        show_summary: 是否显示数据摘要 (默认True)
        truncate_length: 字段值截断长度 (默认100)
    
    Returns:
        str: 数据预览结果
        
    📋 使用示例：
    ```python
    # 基本预览
    api_data_preview(
        api_name="alpha_vantage",
        endpoint_name="news_sentiment",
        params={"topics": "technology"}
    )
    
    # 指定字段预览
    api_data_preview(
        api_name="alpha_vantage",
        endpoint_name="news_sentiment",
        params={"topics": "technology"},
        preview_fields=["title", "summary", "sentiment_score"],
        max_rows=5
    )
    
    # 深度预览嵌套数据
    api_data_preview(
        api_name="complex_api",
        endpoint_name="nested_data",
        preview_depth=5,
        truncate_length=200
    )
    ```
    
    🎯 关键理解点：
    - preview_fields可以精确控制显示内容
    - preview_depth控制JSON嵌套显示层级
    - truncate_length避免超长字段影响显示
    - 提供完整的数据结构分析
    """
    return api_data_preview_impl(api_name, endpoint_name, params, max_rows, max_cols, preview_fields, preview_depth, show_data_types, show_summary, truncate_length)

@mcp.tool()
def create_api_storage_session(
    session_name: str,
    api_name: str,
    endpoint_name: str,
    description: str = None
) -> str:
    """
    创建API数据存储会话
    
    Args:
        session_name: 存储会话名称
        api_name: API名称
        endpoint_name: 端点名称
        description: 会话描述
    
    Returns:
        str: 创建结果
    """
    return create_api_storage_session_impl(session_name, api_name, endpoint_name, description)

@mcp.tool()
def list_api_storage_sessions() -> str:
    """
    📋 API存储会话列表工具 - 查看所有API数据存储会话
    
    功能说明：
    - 列出所有API数据存储会话
    - 显示会话详细信息和数据统计
    - 为API数据导入提供会话选择
    
    Returns:
        str: JSON格式的会话列表，包含会话信息和数据统计
    
    🤖 AI使用建议：
    - 在导入API数据前先查看可用会话
    - 选择合适的会话进行数据导入
    - 了解每个会话的数据量和结构
    """
    return list_api_storage_sessions_impl()

# ================================
# 服务器启动
# ================================

def main():
    """主函数 - 启动MCP服务器"""
    logger.info("DataMaster MCP 服务器启动中...")
    logger.info("模块化架构已加载：")
    logger.info("  - core/database.py: 数据库管理")
    logger.info("  - core/data_analysis.py: 数据分析")
    logger.info("  - core/data_processing.py: 数据处理")
    logger.info("  - core/api_manager.py: API管理")
    mcp.run()

if __name__ == "__main__":
    main()