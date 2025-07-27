# 📚 DataMaster MCP 开发流程指南

## 🎯 开发流程概述

**推荐方式：本地持续开发 + 版本发布**

你**不需要**每次都下载包来更新！正确的开发流程是：
1. 在本地项目持续开发和测试
2. 版本稳定后统一发布到 PyPI
3. 用户通过 `pip install -U` 更新

## 🔄 完整开发工作流

### 阶段1：本地开发环境

```bash
# 1. 克隆或保持本地项目
git clone https://github.com/szqshan/DataMaster.git
cd DataMaster

# 2. 创建开发环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装开发依赖
pip install -r requirements.txt
pip install build twine  # 发布工具

# 4. 以开发模式安装（重要！）
pip install -e .  # 可编辑安装，代码修改立即生效
```

### 阶段2：日常开发循环

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发代码
# 编辑 datamaster_mcp/ 下的文件

# 3. 本地测试
python test_mcp_server.py  # 运行测试
python start_mcp_server.py  # 启动服务器测试

# 4. 提交更改
git add .
git commit -m "feat: 添加新功能"

# 5. 合并到主分支
git checkout master
git merge feature/new-feature
```

### 阶段3：版本发布流程

#### 3.1 版本号管理

```bash
# 更新版本号（三个地方）
# 1. setup.py 中的 version
# 2. pyproject.toml 中的 version  
# 3. datamaster_mcp/__init__.py 中的 __version__

# 版本号规则：
# 主版本.次版本.修订版本
# 1.0.1 -> 1.0.2 (bug修复)
# 1.0.1 -> 1.1.0 (新功能)
# 1.0.1 -> 2.0.0 (重大更改)
```

#### 3.2 发布前检查

```bash
# 1. 运行完整测试
python test_mcp_server.py

# 2. 检查包结构
python -c "import datamaster_mcp; print(datamaster_mcp.__version__)"

# 3. 构建包
python -m build

# 4. 检查构建结果
twine check dist/*
```

#### 3.3 发布到 PyPI

```bash
# 1. 测试发布（可选）
twine upload --repository testpypi dist/*

# 2. 正式发布
twine upload dist/*

# 3. 清理构建文件
rm -rf dist/ build/ *.egg-info/
```

#### 3.4 Git 标签和发布

```bash
# 1. 创建版本标签
git tag v1.0.2
git push origin v1.0.2

# 2. 推送代码
git push origin master

# 3. 在 GitHub 创建 Release（可选）
```

## 🛠️ 开发最佳实践

### 1. 开发环境配置

```bash
# .env 文件（不提交到 Git）
DEBUG=true
LOG_LEVEL=DEBUG
TEST_MODE=true
```

### 2. 代码质量检查

```bash
# 安装代码质量工具
pip install black flake8 pytest

# 代码格式化
black datamaster_mcp/

# 代码检查
flake8 datamaster_mcp/

# 运行测试
pytest tests/  # 如果有测试文件
```

### 3. 功能测试流程

```bash
# 1. 单元测试
python test_mcp_server.py

# 2. 集成测试
python start_mcp_server.py
# 在另一个终端测试 MCP 功能

# 3. Claude Desktop 测试
# 更新配置，重启 Claude，测试功能
```

## 📦 版本管理策略

### 版本号含义
- **1.0.x**: 稳定版本，bug 修复
- **1.x.0**: 新功能版本
- **x.0.0**: 重大更新，可能不兼容

### 发布频率建议
- **热修复**: 发现严重 bug 立即发布
- **功能更新**: 1-2周发布一次
- **大版本**: 1-3个月发布一次

### 分支策略
```
master (主分支，稳定版本)
├── develop (开发分支)
├── feature/xxx (功能分支)
├── hotfix/xxx (热修复分支)
└── release/x.x.x (发布分支)
```

## 🔧 常见开发场景

### 场景1：修复 Bug
```bash
# 1. 创建热修复分支
git checkout -b hotfix/fix-import-error

# 2. 修复代码
# 编辑相关文件

# 3. 测试修复
python test_mcp_server.py

# 4. 更新版本号（修订版本 +1）
# 1.0.1 -> 1.0.2

# 5. 提交并发布
git commit -m "fix: 修复导入错误"
git checkout master
git merge hotfix/fix-import-error
# 发布新版本...
```

### 场景2：添加新功能
```bash
# 1. 创建功能分支
git checkout -b feature/add-excel-export

# 2. 开发新功能
# 添加新的工具函数

# 3. 更新文档
# 更新 README.md, 用户使用手册.md

# 4. 测试功能
python test_mcp_server.py

# 5. 更新版本号（次版本 +1）
# 1.0.1 -> 1.1.0

# 6. 合并并发布
```

### 场景3：重构代码
```bash
# 1. 创建重构分支
git checkout -b refactor/optimize-database

# 2. 重构代码
# 保持 API 兼容性

# 3. 充分测试
# 确保所有功能正常

# 4. 更新版本号
# 如果兼容：1.0.1 -> 1.0.2
# 如果不兼容：1.0.1 -> 2.0.0
```

## 🎯 总结

**简单来说：**
1. **本地开发**：在你的项目里持续开发，用 `pip install -e .` 安装开发版本
2. **版本管理**：功能稳定后更新版本号，打 Git 标签
3. **发布流程**：构建包 -> 测试 -> 上传 PyPI -> 推送 Git
4. **用户更新**：用户通过 `pip install -U datamaster-mcp` 获取最新版本

**核心原则：** 本地开发 + 版本发布，而不是下载包来更新！

这样你就可以：
- 🔄 持续在本地开发和测试
- 📦 稳定后统一发布版本
- 🚀 用户轻松获取更新
- 📝 保持完整的版本历史

真nb！这个流程既专业又高效！🎉