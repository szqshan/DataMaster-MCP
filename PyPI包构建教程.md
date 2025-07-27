# PyPI包构建教程 - 精简版

## 📦 概述

本教程将教你如何用最简单的方式构建一个标准的PyPI包。我们采用精简化的构建方式，只关注核心必需文件，让构建过程变得简单直接。

## 🎯 核心理念

**"最小可行构建"** - 只保留构建PyPI包的核心文件，去除所有非必需的复杂配置。

## 📁 项目结构

```
你的项目/
├── source-code/           # 源代码目录
│   └── 你的包名/
│       ├── __init__.py    # 包初始化文件（必需）
│       └── main.py        # 主要代码文件
└── build-related/         # 构建相关文件
    ├── pyproject.toml     # 核心配置文件（必需）
    ├── requirements.txt   # 依赖列表（必需）
    ├── MANIFEST.in        # 包含文件规则（可选但推荐）
    └── BUILD.md          # 构建说明文档
```

## 🔧 必需文件详解

### 1. `source-code/你的包名/__init__.py`

这是Python包的标识文件，告诉Python这是一个包。最简单的内容：

```python
"""你的包的简短描述"""

__version__ = "1.0.0"
__author__ = "你的名字"
__email__ = "你的邮箱"

# 导出主要功能（可选）
from .main import *
```

### 2. `build-related/pyproject.toml`

这是现代Python包构建的核心配置文件：

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "你的包名"
version = "1.0.0"
authors = [
    {name = "你的名字", email = "你的邮箱"}
]
description = "包的简短描述"
readme = "README.md"
requires-python = ">=3.8"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
keywords = ["关键词1", "关键词2"]
dependencies = [
    # 在这里列出你的依赖包
    # "requests>=2.25.0",
    # "pandas>=1.3.0",
]

[project.urls]
"Homepage" = "https://github.com/你的用户名/你的项目"
"Bug Reports" = "https://github.com/你的用户名/你的项目/issues"
"Source" = "https://github.com/你的用户名/你的项目"

[tool.setuptools.packages.find]
where = ["../source-code"]
include = ["你的包名*"]

[tool.setuptools.package-data]
"你的包名" = ["*.json", "*.yaml", "*.txt"]
```

### 3. `build-related/requirements.txt`

列出项目的所有依赖：

```
# 核心依赖
requests>=2.25.0
pandas>=1.3.0
numpy>=1.21.0

# 开发依赖（可选）
pytest>=6.0.0
black>=21.0.0
```

### 4. `build-related/MANIFEST.in`

指定哪些文件要包含在包中：

```
# 包含源代码
recursive-include source-code/你的包名 *.py
recursive-include source-code/你的包名 *.json
recursive-include source-code/你的包名 *.yaml
recursive-include source-code/你的包名 *.txt

# 包含文档
include README.md
include CHANGELOG.md
include LICENSE

# 排除不需要的文件
global-exclude *.pyc
global-exclude __pycache__
global-exclude .git*
global-exclude .DS_Store
```

## 🚀 构建步骤

### 前置条件

确保你已经安装了构建工具：

```bash
pip install build twine
```

### 四步构建法

1. **进入构建目录**
   ```bash
   cd build-related
   ```

2. **执行构建**
   ```bash
   python -m build
   ```

3. **检查构建结果**
   ```bash
   ls dist/
   # 应该看到：
   # 你的包名-版本号-py3-none-any.whl
   # 你的包名-版本号.tar.gz
   ```

4. **清理构建文件（可选）**
   ```bash
   # Windows PowerShell
   Remove-Item -Recurse -Force build, *.egg-info -ErrorAction SilentlyContinue
   
   # Linux/Mac
   rm -rf build *.egg-info
   ```

## 📤 发布到PyPI

### 测试发布（推荐先测试）

```bash
# 发布到测试PyPI
twine upload --repository testpypi dist/*

# 从测试PyPI安装验证
pip install --index-url https://test.pypi.org/simple/ 你的包名
```

### 正式发布

```bash
# 发布到正式PyPI
twine upload dist/*

# 安装验证
pip install 你的包名
```

## 🎯 关键理解点

### 为什么这么简单？

1. **现代化工具**：`pyproject.toml` + `python -m build` 是Python官方推荐的现代构建方式
2. **标准化配置**：所有配置都在一个文件中，清晰明了
3. **自动化处理**：构建工具会自动处理大部分复杂逻辑
4. **最小依赖**：只需要 `setuptools` 和 `wheel`，都是Python标准库

### 构建原理

```
源代码 + 配置文件 → 构建工具 → PyPI包
    ↓           ↓         ↓        ↓
你的.py文件  pyproject.toml  python -m build  .whl + .tar.gz
```

## 🔍 常见问题

### Q: 为什么要把构建文件单独放在 `build-related/` 目录？
A: 这样可以保持项目根目录整洁，构建相关的文件都集中管理，便于维护。

### Q: `__init__.py` 文件可以是空的吗？
A: 可以！空的 `__init__.py` 文件就足以让Python识别这是一个包。

### Q: 如何添加命令行工具？
A: 在 `pyproject.toml` 中添加：
```toml
[project.scripts]
你的命令名 = "你的包名.模块名:函数名"
```

### Q: 如何处理包的依赖？
A: 在 `pyproject.toml` 的 `dependencies` 列表中添加，格式：`"包名>=版本号"`

## 💡 最佳实践

1. **版本管理**：使用语义化版本号（如 1.0.0）
2. **测试先行**：先发布到测试PyPI验证
3. **文档完善**：写好 README.md 和代码注释
4. **依赖锁定**：指定依赖的最小版本号
5. **定期更新**：及时更新依赖和版本号

## 🎉 总结

恭喜！你现在掌握了最简单直接的PyPI包构建方法。记住核心要点：

- **4个核心文件**：`__init__.py`、`pyproject.toml`、`requirements.txt`、`MANIFEST.in`
- **1条构建命令**：`python -m build`
- **标准化流程**：现代Python包构建的最佳实践

现在你可以把任何Python代码打包成专业的PyPI包了！🚀

---

*本教程基于DataMaster MCP项目的实际构建经验总结，经过实战验证，简单可靠。*