# PyPI 发布指南

本文档详细说明如何将 DataMaster MCP 发布到 PyPI。

## 📋 准备工作清单

### ✅ 已完成的准备工作

1. **项目结构重构** ✅
   - 创建了 `datamaster_mcp` 包目录
   - 移动了 `main.py` 到包目录
   - 移动了 `config` 目录到包内
   - 修复了导入路径（使用相对导入）

2. **核心配置文件** ✅
   - `setup.py` - 传统的安装配置
   - `pyproject.toml` - 现代Python项目配置
   - `MANIFEST.in` - 指定包含的文件
   - `LICENSE` - MIT许可证
   - `requirements.txt` - 依赖列表

3. **文档文件** ✅
   - `README.md` - 中文文档
   - `README_EN.md` - 英文文档
   - `CHANGELOG.md` - 变更日志
   - `VERSION.md` - 版本信息

4. **包结构** ✅
   ```
   datamaster_mcp/
   ├── __init__.py          # 包初始化文件
   ├── main.py              # 主程序文件
   └── config/              # 配置模块
       ├── __init__.py
       ├── *.py             # 各种配置管理器
       └── *.json           # 配置文件
   ```

### 🔧 需要完成的准备工作

1. **PyPI 账户设置**
   - 注册 PyPI 账户：https://pypi.org/account/register/
   - 注册 TestPyPI 账户（测试用）：https://test.pypi.org/account/register/
   - 启用双因素认证（推荐）

2. **API Token 配置**
   - 在 PyPI 中创建 API Token
   - 配置本地认证信息

3. **安装发布工具**
   ```bash
   pip install --upgrade pip setuptools wheel twine build
   ```

4. **邮箱验证**
   - 确保在 setup.py 中更新正确的邮箱地址
   - 当前设置为：`your.email@example.com`（需要更新）

## 🚀 发布步骤

### 1. 安装发布工具

```bash
# 安装必要的发布工具
pip install --upgrade pip setuptools wheel twine build
```

### 2. 更新邮箱地址

编辑 `setup.py` 和 `pyproject.toml`，将邮箱地址更新为你的真实邮箱：

```python
# setup.py 中
author_email="your.real.email@example.com"

# pyproject.toml 中
authors = [
    {name = "szqshan", email = "your.real.email@example.com"},
]
```

### 3. 构建包

```bash
# 清理之前的构建文件
rm -rf build/ dist/ *.egg-info/

# 构建包
python -m build
```

这将创建：
- `dist/datamaster_mcp-1.0.1.tar.gz` (源码包)
- `dist/datamaster_mcp-1.0.1-py3-none-any.whl` (wheel包)

### 4. 检查包

```bash
# 检查包的完整性
twine check dist/*
```

### 5. 测试发布（推荐）

先发布到 TestPyPI 进行测试：

```bash
# 发布到 TestPyPI
twine upload --repository testpypi dist/*
```

然后测试安装：

```bash
# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ datamaster-mcp
```

### 6. 正式发布

如果测试成功，发布到正式 PyPI：

```bash
# 发布到 PyPI
twine upload dist/*
```

### 7. 验证发布

```bash
# 安装验证
pip install datamaster-mcp

# 测试运行
datamaster-mcp --help
```

## 🔐 认证配置

### 方法1：使用 API Token（推荐）

1. 在 PyPI 中创建 API Token
2. 创建 `~/.pypirc` 文件：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token-here
```

### 方法2：交互式认证

如果没有配置 API Token，twine 会提示输入用户名和密码。

## 📦 包信息

- **包名**: `datamaster-mcp`
- **版本**: `1.0.1`
- **Python 要求**: `>=3.8`
- **许可证**: MIT
- **主页**: https://github.com/szqshan/DataMaster

## 🎯 安装方式

发布后，用户可以通过以下方式安装：

```bash
# 基础安装
pip install datamaster-mcp

# 包含 MySQL 支持
pip install datamaster-mcp[mysql]

# 包含 PostgreSQL 支持
pip install datamaster-mcp[postgresql]

# 包含 MongoDB 支持
pip install datamaster-mcp[mongodb]

# 包含所有可选依赖
pip install datamaster-mcp[all]
```

## 🔄 版本更新流程

1. 更新版本号：
   - `VERSION.md`
   - `setup.py`
   - `pyproject.toml`
   - `datamaster_mcp/__init__.py`

2. 更新 `CHANGELOG.md`

3. 提交到 Git：
   ```bash
   git add .
   git commit -m "Release v1.0.2"
   git tag v1.0.2
   git push origin master --tags
   ```

4. 重新构建和发布：
   ```bash
   rm -rf build/ dist/ *.egg-info/
   python -m build
   twine upload dist/*
   ```

## ⚠️ 注意事项

1. **版本号不可重复**：一旦发布某个版本到 PyPI，就不能再次发布相同版本号

2. **包名唯一性**：确保包名在 PyPI 上是唯一的

3. **依赖管理**：仔细管理依赖版本，避免冲突

4. **文档完整性**：确保 README 和文档完整准确

5. **测试覆盖**：建议先在 TestPyPI 测试

6. **安全性**：
   - 不要在代码中包含敏感信息
   - 使用 API Token 而不是密码
   - 启用双因素认证

## 🆘 常见问题

### Q: 构建失败怎么办？
A: 检查 `setup.py` 和 `pyproject.toml` 的语法，确保所有依赖都正确安装。

### Q: 上传失败怎么办？
A: 检查网络连接、认证信息和版本号是否重复。

### Q: 包安装后无法运行？
A: 检查入口点配置和依赖是否正确安装。

### Q: 如何删除已发布的版本？
A: PyPI 不允许删除版本，只能发布新版本。

## 📞 支持

如果遇到问题，可以：
1. 查看 PyPI 官方文档：https://packaging.python.org/
2. 在项目 GitHub 仓库提交 Issue
3. 联系项目维护者