import requests
from bs4 import BeautifulSoup
import re
import logging
import json

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
        logger.info("开始获取 RWA 统计数据")
        
        # 尝试从 API 获取数据
        api_url = "https://api.rwa.xyz/v1/stats"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://app.rwa.xyz/'
        }
        
        logger.info(f"尝试从 API 获取数据: {api_url}")
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"API 响应: {data}")
            
            if isinstance(data, dict):
                stats = {}
                stats['total_rwa_onchain'] = str(data.get('totalRWAOnchain', default_stats['total_rwa_onchain']))
                stats['total_rwa_change'] = str(data.get('rwaChange30d', default_stats['total_rwa_change']))
                stats['total_holders'] = str(data.get('totalHolders', default_stats['total_holders']))
                stats['holders_change'] = str(data.get('holdersChange30d', default_stats['holders_change']))
                stats['total_issuers'] = str(data.get('totalIssuers', default_stats['total_issuers']))
                stats['total_stablecoin'] = str(data.get('totalStablecoin', default_stats['total_stablecoin']))
                
                logger.info(f"成功从 API 获取数据: {stats}")
                return stats
        except Exception as e:
            logger.error(f"从 API 获取数据失败: {str(e)}")
        
        # 如果 API 获取失败,尝试从网页获取
        url = "https://app.rwa.xyz/"
        logger.info(f"尝试从网页获取数据: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        logger.info(f"获取到响应,状态码: {response.status_code}")
        logger.debug(f"响应内容: {response.text[:500]}...")
        
        # 尝试解析 JSON
        try:
            data = response.json()
            logger.info("成功解析 JSON 响应")
            
            # 提取所需数据
            stats = {}
            if isinstance(data, dict):
                stats['total_rwa_onchain'] = str(data.get('totalRWAOnchain', default_stats['total_rwa_onchain']))
                stats['total_rwa_change'] = str(data.get('rwaChange30d', default_stats['total_rwa_change']))
                stats['total_holders'] = str(data.get('totalHolders', default_stats['total_holders']))
                stats['holders_change'] = str(data.get('holdersChange30d', default_stats['holders_change']))
                stats['total_issuers'] = str(data.get('totalIssuers', default_stats['total_issuers']))
                stats['total_stablecoin'] = str(data.get('totalStablecoin', default_stats['total_stablecoin']))
                
                logger.info(f"成功提取数据: {stats}")
                return stats
                
        except json.JSONDecodeError:
            logger.info("响应不是 JSON 格式,尝试解析 HTML")
            
        # 如果不是 JSON,尝试解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("成功创建 BeautifulSoup 对象")
        
        # 提取数据
        stats = {}
        
        # 使用更灵活的选择器
        selectors = {
            'total_rwa_onchain': ['[data-testid="total-rwa"]', '.total-rwa', '.rwa-value', '.stat-value'],
            'total_holders': ['[data-testid="total-holders"]', '.total-holders', '.holders-count', '.stat-value'],
            'total_issuers': ['[data-testid="total-issuers"]', '.total-issuers', '.issuers-count', '.stat-value'],
            'total_stablecoin': ['[data-testid="total-stablecoin"]', '.total-stablecoin', '.stablecoin-value', '.stat-value']
        }
        
        def extract_value(text):
            if not text:
                return None, None
            try:
                # 改进的数值提取正则表达式
                value_match = re.search(r'\$?([\d,]+(?:\.\d+)?)[BM]?', text)
                change_match = re.search(r'([+-]?\d+(?:\.\d+)?)\s*%', text)
                
                value = value_match.group(1) if value_match else None
                change = change_match.group(1) if change_match else None
                
                logger.debug(f"从文本 '{text}' 提取的值: value={value}, change={change}")
                return value, change
            except Exception as e:
                logger.error(f"从文本 '{text}' 提取值时出错: {str(e)}")
                return None, None
        
        # 尝试使用不同的选择器查找数据
        for key, selector_list in selectors.items():
            for selector in selector_list:
                logger.debug(f"尝试使用选择器 '{selector}' 查找 {key}")
                element = soup.select_one(selector)
                if element:
                    logger.debug(f"找到元素: {element.text}")
                    value, change = extract_value(element.text)
                    if value:
                        stats[key] = value
                        if change and key in ['total_rwa_onchain', 'total_holders']:
                            stats[f"{key}_change"] = change
                        logger.info(f"成功提取 {key}: value={value}, change={change}")
                        break
                else:
                    logger.debug(f"未找到匹配的元素: {selector}")
        
        logger.info(f"HTML 解析结果: {stats}")
        
        # 使用默认值填充缺失字段
        for field in default_stats:
            if field not in stats or stats[field] is None:
                logger.warning(f"字段 '{field}' 缺失或无效,使用默认值")
                stats[field] = default_stats[field]
        
        return stats
        
    except requests.Timeout:
        logger.error("获取 RWA 统计数据超时")
        return default_stats
    except requests.RequestException as e:
        logger.error(f"获取 RWA 统计数据时发生网络错误: {str(e)}")
        return default_stats
    except Exception as e:
        logger.error(f"获取 RWA 统计数据时发生意外错误: {str(e)}")
        return default_stats