"""
推荐关系可视化服务
提供推荐关系的图形化展示和分析功能
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict, deque

from sqlalchemy import func, and_, or_
from app.extensions import db
from app.models.referral import UserReferral, CommissionRecord
from app.models.commission_config import UserCommissionBalance
from app.models.trade import Trade

logger = logging.getLogger(__name__)


class ReferralVisualization:
    """推荐关系可视化服务"""
    
    def __init__(self):
        self.max_depth = 10  # 最大显示深度
        self.max_nodes = 1000  # 最大节点数
    
    def generate_network_graph(self, root_address: str, max_depth: int = 5) -> Dict:
        """
        生成推荐网络图数据
        
        Args:
            root_address: 根节点地址
            max_depth: 最大深度
            
        Returns:
            Dict: 网络图数据（适用于D3.js、vis.js等）
        """
        try:
            nodes = []
            edges = []
            visited = set()
            node_stats = {}
            
            # 使用广度优先搜索构建网络图
            queue = deque([(root_address, 0, None)])  # (address, depth, parent)
            
            while queue and len(nodes) < self.max_nodes:
                current_address, depth, parent_address = queue.popleft()
                
                if current_address in visited or depth > max_depth:
                    continue
                
                visited.add(current_address)
                
                # 获取节点统计信息
                stats = self._get_node_statistics(current_address)
                node_stats[current_address] = stats
                
                # 创建节点
                node = {
                    'id': current_address,
                    'label': self._format_address_label(current_address),
                    'level': depth,
                    'size': self._calculate_node_size(stats),
                    'color': self._get_node_color(depth, stats),
                    'stats': stats,
                    'type': 'referrer' if depth == 0 else 'referee'
                }
                nodes.append(node)
                
                # 创建边（如果有父节点）
                if parent_address:
                    edge = {
                        'from': parent_address,
                        'to': current_address,
                        'label': f"L{depth}",
                        'weight': stats.get('total_commission', 0),
                        'color': self._get_edge_color(depth)
                    }
                    edges.append(edge)
                
                # 查找子节点
                if depth < max_depth:
                    children = UserReferral.query.filter_by(
                        referrer_address=current_address,
                        status='active'
                    ).all()
                    
                    for child in children:
                        if child.user_address not in visited:
                            queue.append((child.user_address, depth + 1, current_address))
            
            # 计算网络统计
            network_stats = self._calculate_network_statistics(nodes, edges, node_stats)
            
            return {
                'nodes': nodes,
                'edges': edges,
                'statistics': network_stats,
                'metadata': {
                    'root_address': root_address,
                    'max_depth': max_depth,
                    'total_nodes': len(nodes),
                    'total_edges': len(edges),
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"生成网络图失败: {e}")
            raise
    
    def _get_node_statistics(self, address: str) -> Dict:
        """获取节点统计信息"""
        try:
            # 直接下线数量
            direct_referrals = UserReferral.query.filter_by(
                referrer_address=address,
                status='active'
            ).count()
            
            # 总佣金收入
            total_commission = db.session.query(func.sum(CommissionRecord.amount))\
                .filter_by(recipient_address=address).scalar() or 0
            
            # 本月佣金收入
            current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_commission = db.session.query(func.sum(CommissionRecord.amount))\
                .filter(
                    CommissionRecord.recipient_address == address,
                    CommissionRecord.created_at >= current_month
                ).scalar() or 0
            
            # 用户余额
            balance = UserCommissionBalance.query.filter_by(user_address=address).first()
            available_balance = float(balance.available_balance) if balance else 0
            
            # 活跃度评分（基于最近30天的活动）
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_activity = CommissionRecord.query.filter(
                and_(
                    CommissionRecord.recipient_address == address,
                    CommissionRecord.created_at >= thirty_days_ago
                )
            ).count()
            
            activity_score = min(100, recent_activity * 10)  # 简单的活跃度评分
            
            return {
                'direct_referrals': direct_referrals,
                'total_commission': float(total_commission),
                'monthly_commission': float(monthly_commission),
                'available_balance': available_balance,
                'activity_score': activity_score,
                'performance_level': self._calculate_performance_level(
                    direct_referrals, float(total_commission), activity_score
                )
            }
            
        except Exception as e:
            logger.error(f"获取节点统计失败: {e}")
            return {
                'direct_referrals': 0,
                'total_commission': 0,
                'monthly_commission': 0,
                'available_balance': 0,
                'activity_score': 0,
                'performance_level': 'inactive'
            }
    
    def _format_address_label(self, address: str) -> str:
        """格式化地址标签"""
        if len(address) > 10:
            return f"{address[:6]}...{address[-4:]}"
        return address
    
    def _calculate_node_size(self, stats: Dict) -> int:
        """计算节点大小"""
        base_size = 20
        commission_factor = min(50, stats.get('total_commission', 0) / 100)
        referral_factor = min(30, stats.get('direct_referrals', 0) * 5)
        return int(base_size + commission_factor + referral_factor)
    
    def _get_node_color(self, depth: int, stats: Dict) -> str:
        """获取节点颜色"""
        performance_level = stats.get('performance_level', 'inactive')
        
        color_map = {
            'inactive': '#cccccc',
            'bronze': '#cd7f32',
            'silver': '#c0c0c0',
            'gold': '#ffd700',
            'platinum': '#e5e4e2',
            'diamond': '#b9f2ff'
        }
        
        return color_map.get(performance_level, '#cccccc')
    
    def _get_edge_color(self, depth: int) -> str:
        """获取边颜色"""
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', '#ff9ff3']
        return colors[depth % len(colors)]
    
    def _calculate_performance_level(self, referrals: int, commission: float, activity: int) -> str:
        """计算性能等级"""
        score = referrals * 10 + commission / 100 + activity / 10
        
        if score >= 100:
            return 'diamond'
        elif score >= 75:
            return 'platinum'
        elif score >= 50:
            return 'gold'
        elif score >= 25:
            return 'silver'
        elif score >= 10:
            return 'bronze'
        else:
            return 'inactive'
    
    def _calculate_network_statistics(self, nodes: List[Dict], edges: List[Dict], node_stats: Dict) -> Dict:
        """计算网络统计"""
        try:
            total_nodes = len(nodes)
            total_edges = len(edges)
            
            # 层级分布
            level_distribution = defaultdict(int)
            for node in nodes:
                level_distribution[node['level']] += 1
            
            # 性能分布
            performance_distribution = defaultdict(int)
            for node in nodes:
                performance_distribution[node['stats']['performance_level']] += 1
            
            # 总佣金和推荐数
            total_commission = sum(stats.get('total_commission', 0) for stats in node_stats.values())
            total_referrals = sum(stats.get('direct_referrals', 0) for stats in node_stats.values())
            
            # 网络密度（边数 / 最大可能边数）
            max_possible_edges = total_nodes * (total_nodes - 1) / 2
            network_density = total_edges / max_possible_edges if max_possible_edges > 0 else 0
            
            # 平均度数（每个节点的平均连接数）
            total_degree = sum(len([e for e in edges if e['from'] == node['id'] or e['to'] == node['id']]) 
                             for node in nodes)
            avg_degree = total_degree / total_nodes if total_nodes > 0 else 0
            
            return {
                'network_metrics': {
                    'total_nodes': total_nodes,
                    'total_edges': total_edges,
                    'network_density': round(network_density, 4),
                    'avg_degree': round(avg_degree, 2),
                    'max_depth': max(node['level'] for node in nodes) if nodes else 0
                },
                'business_metrics': {
                    'total_commission': round(total_commission, 2),
                    'total_referrals': total_referrals,
                    'avg_commission_per_node': round(total_commission / total_nodes, 2) if total_nodes > 0 else 0,
                    'avg_referrals_per_node': round(total_referrals / total_nodes, 2) if total_nodes > 0 else 0
                },
                'level_distribution': dict(level_distribution),
                'performance_distribution': dict(performance_distribution)
            }
            
        except Exception as e:
            logger.error(f"计算网络统计失败: {e}")
            return {}
    
    def generate_hierarchy_tree(self, root_address: str, max_depth: int = 5) -> Dict:
        """
        生成层级树结构
        
        Args:
            root_address: 根节点地址
            max_depth: 最大深度
            
        Returns:
            Dict: 树形结构数据
        """
        try:
            def build_tree_node(address: str, depth: int) -> Dict:
                if depth > max_depth:
                    return None
                
                # 获取节点信息
                stats = self._get_node_statistics(address)
                
                # 查找子节点
                children_data = []
                if depth < max_depth:
                    children = UserReferral.query.filter_by(
                        referrer_address=address,
                        status='active'
                    ).order_by(UserReferral.referral_time.desc()).all()
                    
                    for child in children:
                        child_node = build_tree_node(child.user_address, depth + 1)
                        if child_node:
                            child_node['referral_info'] = {
                                'referral_time': child.referral_time.isoformat() if child.referral_time else None,
                                'referral_code': child.referral_code,
                                'referral_level': child.referral_level
                            }
                            children_data.append(child_node)
                
                return {
                    'address': address,
                    'label': self._format_address_label(address),
                    'depth': depth,
                    'stats': stats,
                    'children': children_data,
                    'children_count': len(children_data),
                    'total_descendants': self._count_descendants(children_data)
                }
            
            tree = build_tree_node(root_address, 0)
            
            return {
                'tree': tree,
                'metadata': {
                    'root_address': root_address,
                    'max_depth': max_depth,
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"生成层级树失败: {e}")
            raise
    
    def _count_descendants(self, children: List[Dict]) -> int:
        """递归计算后代数量"""
        count = len(children)
        for child in children:
            count += child.get('total_descendants', 0)
        return count
    
    def generate_performance_heatmap(self, addresses: List[str] = None, 
                                   time_range_days: int = 30) -> Dict:
        """
        生成性能热力图数据
        
        Args:
            addresses: 地址列表（可选，为空则分析所有活跃用户）
            time_range_days: 时间范围（天）
            
        Returns:
            Dict: 热力图数据
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_range_days)
            
            # 如果没有指定地址，获取活跃的推荐人
            if not addresses:
                active_referrers = db.session.query(UserReferral.referrer_address)\
                    .filter_by(status='active')\
                    .distinct().limit(100).all()  # 限制数量避免过大
                addresses = [addr[0] for addr in active_referrers]
            
            heatmap_data = []
            
            for address in addresses:
                # 按天统计佣金收入
                daily_stats = db.session.query(
                    func.date(CommissionRecord.created_at).label('date'),
                    func.sum(CommissionRecord.amount).label('amount'),
                    func.count(CommissionRecord.id).label('count')
                ).filter(
                    and_(
                        CommissionRecord.recipient_address == address,
                        CommissionRecord.created_at >= start_date,
                        CommissionRecord.created_at <= end_date
                    )
                ).group_by(func.date(CommissionRecord.created_at)).all()
                
                # 填充每一天的数据
                current_date = start_date.date()
                daily_data = {}
                
                for stat in daily_stats:
                    daily_data[stat.date] = {
                        'amount': float(stat.amount or 0),
                        'count': stat.count
                    }
                
                # 生成完整的日期序列
                date_series = []
                while current_date <= end_date.date():
                    day_data = daily_data.get(current_date, {'amount': 0, 'count': 0})
                    date_series.append({
                        'date': current_date.isoformat(),
                        'amount': day_data['amount'],
                        'count': day_data['count'],
                        'intensity': min(100, day_data['amount'] / 10)  # 强度值，用于热力图颜色
                    })
                    current_date += timedelta(days=1)
                
                heatmap_data.append({
                    'address': address,
                    'label': self._format_address_label(address),
                    'daily_data': date_series,
                    'total_amount': sum(d['amount'] for d in date_series),
                    'total_count': sum(d['count'] for d in date_series),
                    'avg_daily_amount': sum(d['amount'] for d in date_series) / len(date_series)
                })
            
            # 排序（按总金额降序）
            heatmap_data.sort(key=lambda x: x['total_amount'], reverse=True)
            
            return {
                'heatmap_data': heatmap_data,
                'time_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': time_range_days
                },
                'summary': {
                    'total_addresses': len(heatmap_data),
                    'total_amount': sum(d['total_amount'] for d in heatmap_data),
                    'avg_amount_per_address': sum(d['total_amount'] for d in heatmap_data) / len(heatmap_data) if heatmap_data else 0
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成性能热力图失败: {e}")
            raise
    
    def generate_flow_diagram(self, root_address: str, max_depth: int = 3) -> Dict:
        """
        生成资金流向图
        
        Args:
            root_address: 根节点地址
            max_depth: 最大深度
            
        Returns:
            Dict: 流向图数据（Sankey图格式）
        """
        try:
            nodes = []
            links = []
            node_map = {}
            node_index = 0
            
            # 构建节点和链接
            def process_node(address: str, depth: int, parent_index: int = None):
                nonlocal node_index
                
                if depth > max_depth or address in node_map:
                    return node_map.get(address)
                
                # 创建节点
                stats = self._get_node_statistics(address)
                current_index = node_index
                node_map[address] = current_index
                
                nodes.append({
                    'id': current_index,
                    'name': self._format_address_label(address),
                    'address': address,
                    'level': depth,
                    'value': stats.get('total_commission', 0)
                })
                
                node_index += 1
                
                # 创建从父节点到当前节点的链接
                if parent_index is not None:
                    # 计算流向的金额（从父节点流向子节点的佣金）
                    flow_amount = self._calculate_flow_amount(
                        nodes[parent_index]['address'], address
                    )
                    
                    if flow_amount > 0:
                        links.append({
                            'source': parent_index,
                            'target': current_index,
                            'value': flow_amount,
                            'label': f"${flow_amount:.2f}"
                        })
                
                # 处理子节点
                if depth < max_depth:
                    children = UserReferral.query.filter_by(
                        referrer_address=address,
                        status='active'
                    ).all()
                    
                    for child in children:
                        process_node(child.user_address, depth + 1, current_index)
                
                return current_index
            
            # 从根节点开始处理
            process_node(root_address, 0)
            
            return {
                'nodes': nodes,
                'links': links,
                'metadata': {
                    'root_address': root_address,
                    'max_depth': max_depth,
                    'total_nodes': len(nodes),
                    'total_links': len(links),
                    'total_flow': sum(link['value'] for link in links),
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"生成流向图失败: {e}")
            raise
    
    def _calculate_flow_amount(self, from_address: str, to_address: str) -> float:
        """计算两个地址之间的资金流向金额"""
        try:
            # 查找从from_address推荐to_address产生的佣金
            referral = UserReferral.query.filter_by(
                user_address=to_address,
                referrer_address=from_address,
                status='active'
            ).first()
            
            if not referral:
                return 0
            
            # 计算to_address产生的交易给from_address带来的佣金
            total_commission = db.session.query(func.sum(CommissionRecord.amount))\
                .join(Trade, CommissionRecord.transaction_id == Trade.id)\
                .filter(
                    and_(
                        Trade.trader_address == to_address,
                        CommissionRecord.recipient_address == from_address
                    )
                ).scalar() or 0
            
            return float(total_commission)
            
        except Exception as e:
            logger.error(f"计算流向金额失败: {e}")
            return 0
    
    def export_visualization_data(self, root_address: str, format_type: str = 'json') -> str:
        """
        导出可视化数据
        
        Args:
            root_address: 根节点地址
            format_type: 导出格式（json, csv, etc.）
            
        Returns:
            str: 导出的数据
        """
        try:
            # 生成完整的可视化数据
            network_data = self.generate_network_graph(root_address)
            hierarchy_data = self.generate_hierarchy_tree(root_address)
            flow_data = self.generate_flow_diagram(root_address)
            
            export_data = {
                'network_graph': network_data,
                'hierarchy_tree': hierarchy_data,
                'flow_diagram': flow_data,
                'export_info': {
                    'root_address': root_address,
                    'format': format_type,
                    'exported_at': datetime.utcnow().isoformat()
                }
            }
            
            if format_type.lower() == 'json':
                return json.dumps(export_data, indent=2, ensure_ascii=False)
            else:
                # 可以扩展支持其他格式
                raise ValueError(f"不支持的导出格式: {format_type}")
                
        except Exception as e:
            logger.error(f"导出可视化数据失败: {e}")
            raise