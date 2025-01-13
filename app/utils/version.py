import os

def get_version():
    """获取当前系统版本"""
    try:
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'VERSION')
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.readline().strip()
        return version
    except Exception as e:
        return "未知版本"

def get_version_info():
    """获取完整的版本信息"""
    try:
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'VERSION')
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return "无法读取版本信息" 