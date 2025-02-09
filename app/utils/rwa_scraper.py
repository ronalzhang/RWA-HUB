import requests
from bs4 import BeautifulSoup
import re

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
    try:
        url = "https://app.rwa.xyz/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取数据
        stats = {}
        
        # 使用正则表达式匹配数字和符号
        def extract_value(text):
            if not text:
                return None
            value_match = re.search(r'\$?([\d,.]+)B?', text)
            change_match = re.search(r'([+-]?\d+\.?\d*)%', text)
            
            value = value_match.group(1) if value_match else None
            change = change_match.group(1) if change_match else None
            
            return value, change
        
        # 获取所有统计数据
        stat_elements = soup.find_all('div', class_='stat-item')
        for element in stat_elements:
            title = element.find('h4').text.strip()
            value = element.find('h3').text.strip()
            
            if 'Total RWA Onchain' in title:
                stats['total_rwa_onchain'], stats['total_rwa_change'] = extract_value(value)
            elif 'Total Asset Holders' in title:
                stats['total_holders'], stats['holders_change'] = extract_value(value)
            elif 'Total Asset Issuers' in title:
                stats['total_issuers'], _ = extract_value(value)
            elif 'Total Stablecoin Value' in title:
                stats['total_stablecoin'], _ = extract_value(value)
        
        return stats
    except Exception as e:
        print(f"Error fetching RWA stats: {str(e)}")
        return None 