"""
佣金自动化处理定时任务
每分钟运行一次，处理佣金计算和取现申请
"""

import logging
import time
from datetime import datetime
from flask import current_app
from app import create_app
from app.services.auto_commission_service import AutoCommissionService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_commission_automation():
    """运行佣金自动化处理"""
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("开始运行佣金自动化处理任务")
            
            # 运行完整的自动化周期
            result = AutoCommissionService.run_automation_cycle()
            
            if result.get('success'):
                logger.info(f"自动化处理成功完成:")
                logger.info(f"  - 更新佣金: {result['commission_update']['updated_count']} 用户")
                logger.info(f"  - 处理取现: {result['withdrawal_process']['processed_count']} 笔")
                logger.info(f"  - 取现金额: ${result['withdrawal_process']['total_amount']}")
            else:
                logger.error(f"自动化处理失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"佣金自动化任务执行异常: {str(e)}", exc_info=True)


def start_automation_scheduler():
    """启动自动化调度器"""
    logger.info("启动佣金自动化调度器")
    
    while True:
        try:
            run_commission_automation()
            
            # 等待1分钟
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("收到停止信号，退出自动化调度器")
            break
        except Exception as e:
            logger.error(f"调度器异常: {str(e)}", exc_info=True)
            # 等待10秒后重试
            time.sleep(10)


if __name__ == '__main__':
    # 可以直接运行此脚本来启动自动化调度器
    start_automation_scheduler() 