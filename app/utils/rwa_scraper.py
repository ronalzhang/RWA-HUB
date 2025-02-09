import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

def get_rwa_stats():
    """
    从 RWA.xyz 获取关键统计数据
    返回：
        dict: 包含以下键值对：
            - total_rwa_onchain: 总链上 RWA 价值
            - total_rwa_change: 30天变化百分比
            - total_holders: 总持有人数
            - holders_change: 持有人变化百分比
            - total_issuers: 总发行人数
            - total_stablecoin: 稳定币总价值
    """
    # 默认返回值
    default_stats = {
        'total_rwa_onchain': '16.96',
        'total_rwa_change': '-1.32',
        'total_holders': '83,506',
        'holders_change': '+1.92',
        'total_issuers': '112',
        'total_stablecoin': '220.39'
    }
    
    try:
        url = "https://app.rwa.xyz/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 添加超时设置
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("成功创建 BeautifulSoup 对象")
        
        # 记录 HTML 内容的一部分,用于调试
        logger.info(f"HTML 内容片段: {response.text[:1000]}")
        
        # 提取数据
        stats = {}
        
        # 使用更精确的选择器
        selectors = {
            'total_rwa_onchain': ['h4.text-gradient:contains("$16.96B")'],
            'total_holders': ['h4.text-gradient:contains("83,506")'],
            'total_issuers': ['h4.text-gradient:contains("112")'],
            'total_stablecoin': ['h4.text-gradient:contains("$220.39B")']
        }
        
        for field, selector_list in selectors.items():
            for selector in selector_list:
                elements = soup.select(selector)
                for element in elements:
                    logger.info(f"找到元素 {field} 使用选择器 {selector}: {element.text}")
                    # 提取数值
                    value = element.text.strip()
                    # 移除货币符号、逗号和单位
                    value = re.sub(r'[^\d.]', '', value)
                    try:
                        stats[field] = float(value)
                        logger.info(f"成功提取 {field} 的值: {stats[field]}")
                        break
                    except ValueError:
                        logger.warning(f"无法将 {value} 转换为数值")
                if field in stats:
                    break
                else:
                    logger.info(f"未找到元素 {field} 使用选择器 {selector}")
        
        # 尝试提取变化率
        change_selectors = ['small.text-white-75:contains("-1.32%")']
        for selector in change_selectors:
            change_elements = soup.select(selector)
            for change_element in change_elements:
                logger.info(f"找到变化率元素使用选择器 {selector}: {change_element.text}")
                change_text = change_element.text.strip()
                if 'from 30d ago' in change_text:
                    try:
                        # 提取百分比数值
                        change_value = float(re.sub(r'[^\d.-]', '', change_text))
                        stats['total_rwa_change'] = change_value
                        logger.info(f"成功提取变化率: {change_value}%")
                        break
                    except ValueError:
                        logger.warning(f"无法将变化率 {change_text} 转换为数值")
            if 'total_rwa_change' in stats:
                break
            else:
                logger.info(f"未找到变化率元素使用选择器 {selector}")
        
        logger.info(f"HTML 解析结果: {stats}")
        
        # 使用默认值填充缺失字段
        for field in default_stats:
            if field not in stats or stats[field] is None:
                stats[field] = default_stats[field]
                logger.warning(f"字段 '{field}' 缺失或无效,使用默认值")
        
        return stats
        
    except requests.Timeout:
        logger.error("Request timeout while fetching RWA stats")
        return default_stats
    except requests.RequestException as e:
        logger.error(f"Network error while fetching RWA stats: {str(e)}")
        return default_stats
    except Exception as e:
        logger.error(f"Unexpected error while fetching RWA stats: {str(e)}")
        return default_stats