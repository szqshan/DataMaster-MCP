# 🚀 DataMaster MCP 构建指南

## 📦 精简构建系统

这是一个**极简**的现代Python项目构建配置，删除了所有复杂的自动化脚本，只保留最核心的构建文件。

### 🎯 核心文件

- `pyproject.toml` - 现代Python项目配置（推荐使用）
- `requirements.txt` - 项目依赖列表
- `MANIFEST.in` - 打包文件清单

### ⚡ 快速构建命令

#### 1. 安装构建工具
```bash
pip install --upgrade build twine
```

#### 2. 构建包
```bash
# 使用现代构建工具（推荐）
python -m build

# 构建结果在 dist/ 目录
```

#### 3. 检查包质量
```bash
# 检查构建的包
twine check dist/*
```

#### 4. 发布到PyPI
```bash
# 发布到测试PyPI（可选）
twine upload --repository testpypi dist/*

# 发布到正式PyPI
twine upload dist/*
```

### 🔧 开发环境

#### 安装开发依赖
```bash
# 安装项目依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

#### 可选依赖安装
```bash
# MySQL支持
pip install datamaster-mcp[mysql]

# PostgreSQL支持
pip install datamaster-mcp[postgresql]

# 所有可选依赖
pip install datamaster-mcp[all]
```

### 📁 构建产物

构建完成后会生成：
- `dist/datamaster-mcp-*.tar.gz` - 源码包
- `dist/datamaster-mcp-*.whl` - 二进制包

### 🧹 清理构建文件

```bash
# Windows
Remove-Item -Recurse -Force dist, build, *.egg-info

# Linux/macOS
rm -rf dist/ build/ *.egg-info/
```

### 💡 为什么选择精简构建？

1. **简单直接** - 只用标准工具，没有复杂脚本
2. **易于维护** - 配置文件少，问题好排查
3. **标准兼容** - 完全符合Python打包标准
4. **学习友好** - 新手也能快速上手

### 🎯 一键构建流程

```bash
# 完整构建和发布流程
pip install --upgrade build twine
python -m build
twine check dist/*
twine upload dist/*
```

**就是这么简单！** 🚀

---

**提示**: 如果需要更复杂的自动化功能，可以考虑使用GitHub Actions或其他CI/CD工具。