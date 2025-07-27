#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

def get_version():
    """从 VERSION.md 文件中读取版本号"""
    version_file = Path("VERSION.md")
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        print("VERSION.md content (first 500 chars):")
        print(content[:500])
        print("\n" + "="*50 + "\n")
        
        # 查找版本号模式：## v1.0.3 (2025-01-24)
        pattern = r'^## v([0-9]+\.[0-9]+\.[0-9]+)'
        matches = re.findall(pattern, content, re.MULTILINE)
        print(f"All version matches found: {matches}")
        
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            version = match.group(1)
            print(f"First version found: {version}")
            return version
        
        # 如果没找到，返回默认版本
        print("No version found, returning default")
        return "1.0.2"
    except Exception as e:
        print(f"Error reading version: {e}")
        return "1.0.2"

if __name__ == "__main__":
    version = get_version()
    print(f"\nFinal version: {version}")