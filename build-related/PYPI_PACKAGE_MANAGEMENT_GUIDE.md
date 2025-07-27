# 📦 PyPI包管理完整指南

> **从零到一创建和维护PyPI包的完整流程** - 避免踩坑，一次搞定！

## 🎯 核心理念

**版本管理的黄金法则：所有版本号必须保持一致！**

## 📋 版本号管理清单

### ⚠️ 关键文件版本号检查

在发布新版本前，**必须**检查以下文件中的版本号：

1. **pyproject.toml** - `[project] version = "x.x.x"` ⭐ **最重要！**
2. **VERSION.md** - 版本历史记录
3. **setup.py** - 如果使用动态版本读取，确保函数正常工作
4. **README.md** - 文档中的版本引用

### 🔥 血泪教训

**pyproject.toml中的版本号是构建时的最终决定者！**
- 即使setup.py和VERSION.md都正确，如果pyproject.toml版本号不对，构建出来的包版本就是错的
- 现代Python包管理优先使用pyproject.toml配置

## 🚀 完整发布流程

### 1️⃣ 准备阶段

#### 环境检查
```bash
# 检查构建工具
python -m build --version
python -m twine --version

# 如果没有安装
pip install build twine
```

#### 项目结构确认
```
project/
├── pyproject.toml          # 主配置文件
├── setup.py                # 兼容性配置
├── VERSION.md              # 版本历史
├── README.md               # 项目说明
├── requirements.txt        # 依赖列表
├── your_package/           # 源代码包
│   ├── __init__.py
│   └── main.py
└── dist/                   # 构建输出目录
```

### 2️⃣ 版本更新

#### 更新版本号（按顺序执行）

1. **更新VERSION.md**
```markdown
## v1.0.3 (2025-01-24)

### 🐛 Bug修复
- 修复具体问题描述

### 🔧 技术改进
- 技术改进描述

### ✅ 验证结果
- ✅ 功能验证通过
```

2. **更新pyproject.toml** ⭐ **关键步骤**
```toml
[project]
name = "your-package-name"
version = "1.0.3"  # 更新这里！
```

3. **检查setup.py**（如果使用动态版本读取）
```python
def get_version():
    # 确保版本读取函数正常工作
    pass

version = get_version()  # 或直接硬编码版本号
```

### 3️⃣ 构建前清理

```bash
# 清理所有缓存文件（重要！）
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path build) { Remove-Item build -Recurse -Force }
Get-ChildItem *.egg-info -Recurse | Remove-Item -Recurse -Force
```

### 4️⃣ 构建包

```bash
# 构建包
python -m build

# 检查构建结果
ls dist/
# 应该看到：your-package-1.0.3-py3-none-any.whl 和 your-package-1.0.3.tar.gz
```

### 5️⃣ 验证构建

```bash
# 检查包信息
python -m twine check dist/*

# 确认版本号正确
ls dist/ | grep "1.0.3"
```

### 6️⃣ 发布到PyPI

```bash
# 发布到PyPI
python -m twine upload dist/*

# 输入API Token
# 等待上传完成
```

### 7️⃣ 代码管理

```bash
# 提交代码
git add .
git commit -m "Release v1.0.3: 描述主要更改"
git push origin master

# 创建标签（可选）
git tag v1.0.3
git push origin v1.0.3
```

## 🛠️ 常见问题解决

### 问题1：构建版本号不对

**症状**：构建出来的包版本是旧版本

**解决方案**：
1. 检查pyproject.toml中的版本号
2. 清理所有缓存文件
3. 重新构建

```bash
# 检查pyproject.toml
grep "version" pyproject.toml

# 清理缓存
rm -rf dist/ build/ *.egg-info

# 重新构建
python -m build
```

### 问题2：版本读取函数不工作

**症状**：setup.py中的get_version()函数返回错误版本

**解决方案**：
1. 临时使用硬编码版本号
2. 修复版本读取函数
3. 恢复动态版本读取

```python
# 临时方案
# version = get_version()
version = "1.0.3"  # 硬编码版本号

# 构建完成后恢复
version = get_version()
```

### 问题3：上传失败

**症状**：twine upload失败

**解决方案**：
1. 检查API Token
2. 检查网络连接
3. 确认版本号未重复

```bash
# 检查包信息
python -m twine check dist/*

# 使用测试PyPI（可选）
python -m twine upload --repository testpypi dist/*
```

## 📝 版本号规范

### 语义化版本控制

格式：`MAJOR.MINOR.PATCH`

- **MAJOR**：不兼容的API更改
- **MINOR**：向后兼容的功能添加
- **PATCH**：向后兼容的Bug修复

### 版本号示例

- `1.0.0` - 首个稳定版本
- `1.0.1` - Bug修复
- `1.1.0` - 新功能添加
- `2.0.0` - 重大更改，不向后兼容

## 🔧 自动化脚本

### 版本更新脚本

```python
#!/usr/bin/env python3
# update_version.py

import re
import sys
from pathlib import Path

def update_version(new_version):
    # 更新pyproject.toml
    toml_file = Path("pyproject.toml")
    content = toml_file.read_text()
    content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', content)
    toml_file.write_text(content)
    
    # 更新VERSION.md
    # ... 添加版本历史记录
    
    print(f"版本已更新为 {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python update_version.py 1.0.3")
        sys.exit(1)
    
    new_version = sys.argv[1]
    update_version(new_version)
```

### 发布脚本

```bash
#!/bin/bash
# release.sh

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "用法: ./release.sh 1.0.3"
    exit 1
fi

echo "🚀 开始发布版本 $VERSION"

# 更新版本号
python update_version.py $VERSION

# 清理缓存
echo "🧹 清理缓存文件"
rm -rf dist/ build/ *.egg-info

# 构建包
echo "📦 构建包"
python -m build

# 检查包
echo "✅ 检查包"
python -m twine check dist/*

# 上传到PyPI
echo "📤 上传到PyPI"
python -m twine upload dist/*

# 提交代码
echo "💾 提交代码"
git add .
git commit -m "Release v$VERSION"
git push origin master

echo "🎉 发布完成！"
echo "📦 PyPI链接: https://pypi.org/project/your-package-name/$VERSION/"
```

## 📚 参考资源

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI官方文档](https://pypi.org/help/)
- [Semantic Versioning](https://semver.org/)
- [Twine文档](https://twine.readthedocs.io/)

## 🎯 最佳实践

1. **版本号一致性**：所有文件中的版本号必须一致
2. **清理缓存**：每次构建前清理所有缓存文件
3. **验证构建**：上传前检查构建结果
4. **测试环境**：使用TestPyPI进行测试
5. **自动化**：使用脚本自动化发布流程
6. **文档更新**：及时更新版本历史和文档

## ⚠️ 注意事项

- PyPI不允许重复上传相同版本号的包
- 删除已发布的版本需要联系PyPI管理员
- API Token需要妥善保管，不要提交到代码仓库
- 大版本更新前建议先发布到TestPyPI测试

---

**记住：pyproject.toml中的版本号是王道！** 🔥

**最后更新**: 2025-01-24  
**版本**: v1.0.0