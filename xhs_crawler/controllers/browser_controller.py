# controllers/browser_controller.py
import time
import random
import logging
from DrissionPage import ChromiumPage
from utils.browser_utils import random_sleep

class BrowserController:
    def __init__(self):
        self.page = None
    
    def init_browser(self):
        """初始化浏览器"""
        try:
            self.page = ChromiumPage()
            logging.info("浏览器初始化成功")
            return True
        except Exception as e:
            logging.error(f"浏览器初始化失败: {str(e)}")
            return False
    
    def login(self):
        """登录小红书"""
        try:
            self.page.get('https://www.xiaohongshu.com')
            logging.info("请扫码登录并确保进入首页")
            print("请扫码登录小红书 (30秒)")
            time.sleep(30)  # 给用户足够时间登录
            
            return True
        except Exception as e:
            logging.error(f"登录过程发生错误: {str(e)}")
            return False
    
    def navigate_to(self, url):
        """导航到指定URL"""
        try:
            self.page.get(url)
            self.page.wait.doc_loaded()
            logging.info(f"成功导航到: {url}")
            return True
        except Exception as e:
            logging.error(f"导航到 {url} 失败: {str(e)}")
            raise
    
    def scroll_page(self, count=1):
        """滚动页面"""
        try:
            for _ in range(count):
                self.page.scroll.to_bottom()
                random_sleep(0.5, 1.5)
            
            logging.info(f"页面滚动 {count} 次")
            return True
        except Exception as e:
            logging.error(f"页面滚动失败: {str(e)}")
            return False
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.quit()
                logging.info("浏览器已关闭")
            return True
        except Exception as e:
            logging.error(f"关闭浏览器失败: {str(e)}")
            return False