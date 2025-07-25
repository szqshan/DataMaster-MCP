# 更新日志

本文档记录了DataMaster_MCP的所有重要更改。

## [1.0.1] - 2025-01-24

### 🐛 Bug修复

#### Excel导出功能修复
- **修复自动生成文件路径的扩展名错误**
  - 解决了当不指定`file_path`参数时，Excel导出失败的问题
  - 错误信息：`Invalid extension for engine 'excel': 'excel'`
  - 根本原因：自动生成的文件路径使用了错误的扩展名（`.excel`而非`.xlsx`）

- **添加文件扩展名映射表**
  - 在`export_data`函数中添加`extension_map`字典
  - 映射关系：`{"excel": "xlsx", "csv": "csv", "json": "json"}`
  - 确保所有导出格式使用正确的文件扩展名

- **优化文件路径生成逻辑**
  - 修复前：`f"exports/{source_name}_{timestamp}.{export_type}"`
  - 修复后：`f"exports/{source_name}_{timestamp}.{extension}"`
  - 其中`extension = extension_map.get(export_type, export_type)`

### 🔧 技术改进

- **保持向后兼容性**：指定路径的导出功能不受影响
- **增强错误处理**：改进了导出失败时的错误信息提示
- **代码可维护性**：使用映射表方式便于后续扩展新的导出格式

### ✅ 验证测试

- ✅ 自动生成路径Excel导出：`exports/test_employees_*.xlsx`
- ✅ 指定路径Excel导出：`final_test.xlsx` (5449 bytes)
- ✅ CSV导出功能：`final_test.csv` (308 bytes)
- ✅ 文件完整性：所有导出文件包含完整的8条记录
- ✅ 多次导出测试：连续导出功能正常

### 📁 影响文件

- `main.py`: 修复`export_data`函数的文件路径生成逻辑

---

## [1.0.0] - 2025-01-24

### 🎉 首次正式发布

这是DataMaster_MCP的第一个正式版本，提供完整的数据分析和处理功能。

### ✨ 新增功能

#### 数据导入导出
- 添加CSV文件导入功能，支持自动编码检测
- 添加Excel文件导入功能，支持多工作表
- 添加数据导出功能，支持Excel、CSV、JSON格式
- 实现文件路径验证和错误处理

#### 数据库连接
- 实现MySQL数据库连接和查询
- 实现PostgreSQL数据库支持
- 实现MongoDB NoSQL数据库支持
- 实现SQLite本地数据库支持
- 添加数据库配置管理系统
- 实现连接池和事务管理

#### 数据分析功能
- 实现基本统计分析（均值、中位数、标准差等）
- 添加相关性分析功能
- 实现异常值检测算法
- 添加缺失值分析功能
- 实现重复值检测功能

#### 数据处理功能
- 实现数据过滤和条件查询
- 添加数据类型转换功能
- 实现数据聚合和分组统计
- 添加数据清洗和去重功能
- 实现数据重塑和透视表功能

#### API数据连接
- 实现RESTful API连接器
- 添加API配置管理系统
- 实现数据转换和格式化
- 添加API数据持久化存储
- 实现API数据预览功能

#### 配置管理
- 实现统一的配置管理系统
- 添加数据库连接配置
- 实现API端点配置管理
- 添加环境变量支持

### 🔧 技术改进

- 实现模块化架构设计
- 添加完整的错误处理机制
- 实现日志记录系统
- 添加数据验证和类型检查
- 优化内存使用和性能

### 📚 文档

- 添加完整的使用指南文档
- 创建API连接器使用说明
- 编写数据库连接配置指南
- 提供功能扩展方案文档

### 🧪 测试验证

- 完成CSV导入功能测试
- 验证数据查询和分析功能
- 测试数据导出功能
- 验证数据处理和过滤功能
- 完成SQLite数据库操作测试

### 📦 依赖更新

- 添加pandas数据处理库
- 集成SQLAlchemy数据库ORM
- 添加pymongo MongoDB驱动
- 集成psycopg2 PostgreSQL驱动
- 添加pymysql MySQL驱动
- 集成openpyxl Excel处理库

### 🐛 修复问题

- 修复CSV文件编码识别问题
- 解决数据库连接超时问题
- 修复数据类型转换错误
- 解决内存泄漏问题
- 修复配置文件读取错误

---

## 版本说明

- **[主版本]**: 不兼容的API更改
- **[次版本]**: 向后兼容的功能添加
- **[修订版本]**: 向后兼容的错误修复

## 贡献指南

如果您想为此项目做出贡献，请：

1. Fork 此仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。