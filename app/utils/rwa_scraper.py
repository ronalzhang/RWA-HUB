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
        logger.info(f"HTML 内容片段: {response.text[:2000]}")
        
        # 提取数据
        stats = {}
        
        # 使用更简单的选择器
        try:
            # 找到所有 stat-item 元素
            stat_items = soup.find_all('div', class_='stat-item')
            logger.info(f"找到 {len(stat_items)} 个 stat-item 元素")
            
            # 记录所有找到的 stat-item 元素的内容
            for i, item in enumerate(stat_items):
                logger.info(f"stat-item {i + 1} 内容: {item}")
            
            for item in stat_items:
                # 获取标题和值
                title = item.find('h6', class_='text-white-75')
                value = item.find('h4', class_='text-gradient')
                change = item.find('small', class_='text-white-75')
                
                if title and value:
                    title_text = title.text.strip()
                    value_text = value.text.strip()
                    logger.info(f"找到统计项: {title_text} = {value_text}")
                    
                    if 'Total RWA Onchain' in title_text:
                        # 提取数值
                        value_match = re.search(r'\$?([\d.]+)B', value_text)
                        if value_match:
                            stats['total_rwa_onchain'] = float(value_match.group(1))
                            logger.info(f"提取 total_rwa_onchain: {stats['total_rwa_onchain']}")
                            
                            # 提取变化率
                            if change:
                                change_text = change.text.strip()
                                logger.info(f"变化率文本: {change_text}")
                                change_match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                                if change_match:
                                    stats['total_rwa_change'] = float(change_match.group(1))
                                    logger.info(f"提取 total_rwa_change: {stats['total_rwa_change']}")
                                else:
                                    logger.warning(f"无法从文本 '{change_text}' 提取变化率")
                    
                    elif 'Total Asset Holders' in title_text:
                        # 提取数值
                        value_match = re.search(r'([\d,]+)', value_text)
                        if value_match:
                            stats['total_holders'] = float(value_match.group(1).replace(',', ''))
                            logger.info(f"提取 total_holders: {stats['total_holders']}")
                            
                            # 提取变化率
                            if change:
                                change_text = change.text.strip()
                                logger.info(f"变化率文本: {change_text}")
                                change_match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                                if change_match:
                                    stats['holders_change'] = float(change_match.group(1))
                                    logger.info(f"提取 holders_change: {stats['holders_change']}")
                                else:
                                    logger.warning(f"无法从文本 '{change_text}' 提取变化率")
                    
                    elif 'Total Asset Issuers' in title_text:
                        # 提取数值
                        value_match = re.search(r'(\d+)', value_text)
                        if value_match:
                            stats['total_issuers'] = float(value_match.group(1))
                            logger.info(f"提取 total_issuers: {stats['total_issuers']}")
                    
                    elif 'Total Stablecoin Value' in title_text:
                        # 提取数值
                        value_match = re.search(r'\$?([\d.]+)B', value_text)
                        if value_match:
                            stats['total_stablecoin'] = float(value_match.group(1))
                            logger.info(f"提取 total_stablecoin: {stats['total_stablecoin']}")
                else:
                    if not title:
                        logger.warning("未找到标题元素")
                    if not value:
                        logger.warning("未找到值元素")
        
        except Exception as e:
            logger.error(f"解析统计数据时出错: {str(e)}")
            logger.exception(e)  # 记录完整的异常堆栈
        
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