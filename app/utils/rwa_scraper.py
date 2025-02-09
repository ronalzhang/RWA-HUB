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
        
        # 记录 HTML 内容的一部分,用于调试
        logger.debug(f"HTML 内容片段: {response.text[:1000]}")
        
        # 提取数据
        stats = {}
        
        # 使用更精确的选择器
        selectors = {
            'total_rwa_onchain': ['div.total-rwa', 'div[data-testid="total-rwa"]', '.rwa-value', '.stat-value'],
            'total_holders': ['div.total-holders', 'div[data-testid="total-holders"]', '.holders-count', '.stat-value'],
            'total_issuers': ['div.total-issuers', 'div[data-testid="total-issuers"]', '.issuers-count', '.stat-value'],
            'total_stablecoin': ['div.total-stablecoin', 'div[data-testid="total-stablecoin"]', '.stablecoin-value', '.stat-value']
        }
        
        for field, selector_list in selectors.items():
            for selector in selector_list:
                element = soup.select_one(selector)
                if element:
                    logger.info(f"找到元素 {field} 使用选择器 {selector}: {element.text}")
                    # 提取数值
                    value = element.text.strip()
                    # 移除货币符号和逗号
                    value = re.sub(r'[^\d.]', '', value)
                    try:
                        stats[field] = float(value)
                        logger.info(f"成功提取 {field} 的值: {stats[field]}")
                        break
                    except ValueError:
                        logger.warning(f"无法将 {value} 转换为数值")
                else:
                    logger.debug(f"未找到元素 {field} 使用选择器 {selector}")
        
        # 尝试提取变化率
        change_selectors = ['.change-value', '.percent-change', '[data-testid="change-value"]']
        for selector in change_selectors:
            change_element = soup.select_one(selector)
            if change_element:
                logger.info(f"找到变化率元素使用选择器 {selector}: {change_element.text}")
                change_text = change_element.text.strip()
                try:
                    # 提取百分比数值
                    change_value = float(re.sub(r'[^\d.-]', '', change_text))
                    stats['total_rwa_change'] = change_value
                    logger.info(f"成功提取变化率: {change_value}%")
                    break
                except ValueError:
                    logger.warning(f"无法将变化率 {change_text} 转换为数值")
            else:
                logger.debug(f"未找到变化率元素使用选择器 {selector}")
        
        logger.info(f"HTML 解析结果: {stats}")
        
        # 使用默认值填充缺失字段
        for field in default_stats:
            if field not in stats or stats[field] is None:
                stats[field] = default_stats[field]
                logger.warning(f"字段 '{field}' 缺失或无效,使用默认值")
        
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