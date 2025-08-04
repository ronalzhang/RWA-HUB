#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步任务处理器
实现后台任务处理，提升系统响应性能
"""

import threading
import queue
import time
import logging
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import traceback

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AsyncTask:
    """异步任务数据类"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 5  # 1-10, 1为最高优先级
    max_retries: int = 3
    retry_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class AsyncTaskProcessor:
    """异步任务处理器"""
    
    def __init__(self, max_workers: int = 5, max_queue_size: int = 1000):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.task_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.workers = []
        self.tasks = {}  # task_id -> AsyncTask
        self.running = False
        self._task_counter = 0
        self._lock = threading.Lock()
        
    def start(self):
        """启动任务处理器"""
        if self.running:
            logger.warning("任务处理器已经在运行")
            return
        
        self.running = True
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"AsyncTaskWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"异步任务处理器已启动，工作线程数: {self.max_workers}")
    
    def stop(self):
        """停止任务处理器"""
        self.running = False
        
        # 向队列添加停止信号
        for _ in range(self.max_workers):
            try:
                self.task_queue.put((0, None), timeout=1)
            except queue.Full:
                pass
        
        # 等待工作线程结束
        for worker in self.workers:
            worker.join(timeout=5)
        
        logger.info("异步任务处理器已停止")
    
    def submit_task(self, func: Callable, *args, priority: int = 5, 
                   max_retries: int = 3, **kwargs) -> str:
        """提交异步任务"""
        if not self.running:
            raise RuntimeError("任务处理器未启动")
        
        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}_{int(time.time())}"
        
        task = AsyncTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries
        )
        
        try:
            # 优先级队列：数字越小优先级越高
            self.task_queue.put((priority, task), timeout=1)
            
            with self._lock:
                self.tasks[task_id] = task
            
            logger.debug(f"任务已提交: {task_id}")
            return task_id
            
        except queue.Full:
            logger.error("任务队列已满，无法提交新任务")
            raise RuntimeError("任务队列已满")
    
    def get_task_status(self, task_id: str) -> Optional[AsyncTask]:
        """获取任务状态"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        with self._lock:
            status_counts = {}
            for task in self.tasks.values():
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'queue_size': self.task_queue.qsize(),
            'max_queue_size': self.max_queue_size,
            'total_tasks': len(self.tasks),
            'status_counts': status_counts,
            'workers': self.max_workers,
            'running': self.running
        }
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的旧任务"""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        with self._lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                    and task.created_at.timestamp() < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            logger.info(f"清理了 {len(tasks_to_remove)} 个旧任务")
    
    def _worker_loop(self):
        """工作线程主循环"""
        worker_name = threading.current_thread().name
        logger.info(f"工作线程 {worker_name} 已启动")
        
        while self.running:
            try:
                # 获取任务（阻塞等待）
                priority, task = self.task_queue.get(timeout=1)
                
                # 检查停止信号
                if task is None:
                    break
                
                # 检查任务是否被取消
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                # 执行任务
                self._execute_task(task, worker_name)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程 {worker_name} 发生错误: {e}")
        
        logger.info(f"工作线程 {worker_name} 已停止")
    
    def _execute_task(self, task: AsyncTask, worker_name: str):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        logger.debug(f"工作线程 {worker_name} 开始执行任务 {task.task_id}")
        
        try:
            # 执行任务函数
            result = task.func(*task.args, **task.kwargs)
            
            # 任务成功完成
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            
            logger.debug(f"任务 {task.task_id} 执行成功")
            
        except Exception as e:
            # 任务执行失败
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            task.error = error_msg
            task.retry_count += 1
            
            logger.error(f"任务 {task.task_id} 执行失败 (重试 {task.retry_count}/{task.max_retries}): {e}")
            
            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                # 重新提交任务
                task.status = TaskStatus.PENDING
                try:
                    self.task_queue.put((task.priority, task), timeout=1)
                    logger.info(f"任务 {task.task_id} 已重新提交重试")
                except queue.Full:
                    task.status = TaskStatus.FAILED
                    logger.error(f"任务 {task.task_id} 重试失败：队列已满")
            else:
                # 重试次数用完，标记为失败
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()

# 全局任务处理器实例
_task_processor_instance = None

def get_task_processor() -> AsyncTaskProcessor:
    """获取全局任务处理器实例"""
    global _task_processor_instance
    if _task_processor_instance is None:
        _task_processor_instance = AsyncTaskProcessor()
        _task_processor_instance.start()
    return _task_processor_instance

def async_task(priority: int = 5, max_retries: int = 3):
    """异步任务装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            processor = get_task_processor()
            return processor.submit_task(func, *args, priority=priority, 
                                       max_retries=max_retries, **kwargs)
        
        # 保留原函数的同步调用能力
        wrapper.sync = func
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        return wrapper
    return decorator

# 常用的异步任务函数
@async_task(priority=3)
def async_send_notification(user_address: str, message: str, notification_type: str = 'info'):
    """异步发送通知"""
    try:
        # 这里可以实现实际的通知发送逻辑
        logger.info(f"发送通知给 {user_address}: {message} (类型: {notification_type})")
        time.sleep(0.1)  # 模拟网络延迟
        return True
    except Exception as e:
        logger.error(f"发送通知失败: {e}")
        raise

@async_task(priority=4)
def async_update_cache(cache_key: str, data: Any, timeout: int = 300):
    """异步更新缓存"""
    try:
        from app.services.cache_service import get_cache
        cache = get_cache()
        return cache.set(cache_key, data, timeout)
    except Exception as e:
        logger.error(f"异步更新缓存失败: {e}")
        raise

@async_task(priority=2)
def async_blockchain_sync(asset_id: int):
    """异步区块链同步"""
    try:
        from app.services.blockchain_sync_service import get_sync_service
        sync_service = get_sync_service()
        return sync_service.sync_asset_data(asset_id)
    except Exception as e:
        logger.error(f"异步区块链同步失败: {e}")
        raise

@async_task(priority=5)
def async_log_analytics(event_type: str, data: Dict[str, Any]):
    """异步记录分析数据"""
    try:
        # 这里可以实现分析数据记录逻辑
        logger.info(f"记录分析事件: {event_type}, 数据: {data}")
        return True
    except Exception as e:
        logger.error(f"记录分析数据失败: {e}")
        raise