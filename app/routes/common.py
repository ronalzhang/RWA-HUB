from flask import request

def get_pagination_info():
    """
    从请求中获取分页信息
    返回: (页码, 每页数量)
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # 确保页码和每页数量合法
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 10
        if per_page > 100:
            per_page = 100  # 限制每页最大数量
            
        return page, per_page
    except (ValueError, TypeError):
        # 如果转换失败，返回默认值
        return 1, 10 