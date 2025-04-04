
import time
import random
import logging

def random_sleep(min_time=0.5, max_time=2.0):
    """随机等待一段时间"""
    sleep_time = random.uniform(min_time, max_time)
    time.sleep(sleep_time)
    return sleep_time

def simulate_human_behavior(page):
    """模拟人类行为"""
    try:
        # 随机滚动页面
        for _ in range(random.randint(2, 4)):
            scroll_height = random.randint(300, 800)
            page.run_js(f'window.scrollBy(0, {scroll_height})')
            time.sleep(random.uniform(0.3, 0.8))
        
        # 随机等待
        random_sleep(0.5, 1.0)
        
        return True
    except Exception as e:
        logging.error(f"模拟人类行为失败: {str(e)}")
        return False
