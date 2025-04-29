#!/usr/bin/env python3
import os
import time
import requests
import sys
from pathlib import Path

# 确保vendor目录存在
VENDOR_DIR = Path("app/static/vendor")
VENDOR_DIR.mkdir(parents=True, exist_ok=True)

# webfonts目录
WEBFONTS_DIR = VENDOR_DIR / "webfonts"
WEBFONTS_DIR.mkdir(exist_ok=True)

# 缓存URL映射，将外部URL映射到本地文件
VENDOR_MAPPING = {
    # Solana相关库
    'solana-web3.js': 'https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js',
    'solana-web3-stable.js': 'https://unpkg.com/@solana/web3.js@1.98.0/lib/index.iife.min.js',
    'solana-spl-token.js': 'https://unpkg.com/@solana/spl-token@0.3.8/dist/index.iife.js',
    
    # Web3和区块链相关
    'web3.min.js': 'https://unpkg.com/web3@1.5.2/dist/web3.min.js',
    'ethereumjs-tx-1.3.7.min.js': 'https://cdn.jsdelivr.net/npm/ethereumjs-tx@1.3.7/dist/index.min.js',
    'ethers.umd.min.js': 'https://cdn.ethers.io/lib/ethers-5.2.umd.min.js',
    
    # 基础库
    'jquery.min.js': 'https://code.jquery.com/jquery-3.6.0.min.js',
    'jquery-ui.min.js': 'https://code.jquery.com/ui/1.13.2/jquery-ui.min.js',
    'jquery-ui.min.css': 'https://code.jquery.com/ui/1.13.2/themes/base/jquery-ui.min.css',
    
    # Bootstrap
    'bootstrap.min.css': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'bootstrap.bundle.min.js': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    
    # Font Awesome
    'all.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    
    # Animations
    'aos.css': 'https://unpkg.com/aos@2.3.1/dist/aos.css',
    'aos.js': 'https://unpkg.com/aos@2.3.1/dist/aos.js',
    'animate.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css',
    
    # 图表库
    'chart.min.js': 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
    
    # 工具库
    'moment.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js',
    'lodash.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.min.js',
    'axios.min.js': 'https://cdn.jsdelivr.net/npm/axios@1.6.2/dist/axios.min.js',
    
    # 数据表格
    'datatables.min.js': 'https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js',
    'datatables.min.css': 'https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css',
    
    # 表单验证
    'validate.min.js': 'https://cdn.jsdelivr.net/npm/jquery-validation@1.19.5/dist/jquery.validate.min.js',
}

# 字体文件
FONT_AWESOME_WEBFONTS = [
    'fa-brands-400.ttf',
    'fa-brands-400.woff2',
    'fa-regular-400.ttf',
    'fa-regular-400.woff2',
    'fa-solid-900.ttf',
    'fa-solid-900.woff2',
    'fa-v4compatibility.ttf',
    'fa-v4compatibility.woff2'
]

def download_file(url, filepath):
    """下载文件到指定路径"""
    print(f"正在下载 {url} 到 {filepath}")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"下载完成: {filepath}")
            return True
        else:
            print(f"下载失败 ({response.status_code}): {url}")
            return False
    except Exception as e:
        print(f"下载出错: {url}, 原因: {str(e)}")
        return False

def main():
    """主函数，处理下载和符号链接"""
    print(f"开始下载第三方库到 {VENDOR_DIR}")
    
    # 下载所有库
    for filename, url in VENDOR_MAPPING.items():
        filepath = VENDOR_DIR / filename
        if not filepath.exists():
            download_file(url, filepath)
        else:
            print(f"文件已存在，跳过: {filepath}")
    
    # 下载Font Awesome webfonts
    base_webfonts_url = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/"
    for font_file in FONT_AWESOME_WEBFONTS:
        webfont_url = base_webfonts_url + font_file
        webfont_path = WEBFONTS_DIR / font_file
        if not webfont_path.exists():
            download_file(webfont_url, webfont_path)
        else:
            print(f"字体文件已存在，跳过: {webfont_path}")
    
    # 创建符号链接
    print("创建符号链接...")
    try:
        solana_web3_min_js = VENDOR_DIR / "solana-web3.js"
        if solana_web3_min_js.exists():
            # 创建链接到solana-web3-stable.js
            stable_link = VENDOR_DIR / "solana-web3-stable.js"
            if not stable_link.exists():
                os.symlink(solana_web3_min_js, stable_link)
                print(f"创建符号链接: {stable_link} -> {solana_web3_min_js}")
    except Exception as e:
        print(f"创建符号链接失败: {str(e)}")
    
    print("所有文件下载完成！")

if __name__ == "__main__":
    main() 