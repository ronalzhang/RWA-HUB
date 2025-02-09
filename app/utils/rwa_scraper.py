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
        
        # 提取数据
        stats = {}
        
        # 使用正则表达式匹配数字和符号
        def extract_value(text):
            if not text:
                return None, None
            try:
                value_match = re.search(r'\$?([\d,.]+)B?', text)
                change_match = re.search(r'([+-]?\d+\.?\d*)%', text)
                
                value = value_match.group(1) if value_match else None
                change = change_match.group(1) if change_match else None
                
                return value, change
            except Exception as e:
                logger.error(f"Error extracting value from text '{text}': {str(e)}")
                return None, None
        
        # 获取所有统计数据
        stat_elements = soup.find_all('div', class_='stat-item')
        if not stat_elements:
            logger.warning("No stat elements found, using default values")
            return default_stats
            
        for element in stat_elements:
            try:
                title = element.find('h4')
                value = element.find('h3')
                
                if not title or not value:
                    continue
                    
                title = title.text.strip()
                value = value.text.strip()
                
                if 'Total RWA Onchain' in title:
                    stats['total_rwa_onchain'], stats['total_rwa_change'] = extract_value(value)
                elif 'Total Asset Holders' in title:
                    stats['total_holders'], stats['holders_change'] = extract_value(value)
                elif 'Total Asset Issuers' in title:
                    stats['total_issuers'], _ = extract_value(value)
                elif 'Total Stablecoin Value' in title:
                    stats['total_stablecoin'], _ = extract_value(value)
            except Exception as e:
                logger.error(f"Error processing stat element: {str(e)}")
                continue
        
        # 验证所有必需的字段是否存在
        required_fields = ['total_rwa_onchain', 'total_rwa_change', 'total_holders', 
                         'holders_change', 'total_issuers', 'total_stablecoin']
        
        # 如果缺少任何必需字段，使用默认值填充
        for field in required_fields:
            if field not in stats or stats[field] is None:
                logger.warning(f"Missing or invalid field '{field}', using default value")
                stats[field] = default_stats[field]
            
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