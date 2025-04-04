# main.py
import os
import sys
import argparse
import logging
from datetime import datetime

# 导入控制器
from controllers.browser_controller import BrowserController
from controllers.search_controller import SearchController
from controllers.detail_controller import DetailController
from models.database import Database

def setup_logging():
    """设置日志"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_filename = os.path.join(log_dir, f"xhs_crawler_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def init_database():
    """初始化数据库"""
    try:
        db = Database()
        db.initialize_tables()
        print("数据库初始化成功")
        return True
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        return False

def search_mode(keyword, batch_count):
    """搜索模式"""
    print(f"=== 启动搜索模式，关键词: {keyword} ===")
    
    try:
        # 初始化浏览器
        browser = BrowserController()
        browser.init_browser()
        browser.login()
        
        # 初始化搜索控制器
        search_ctrl = SearchController(browser)
        
        # 运行搜索
        _, links_file = search_ctrl.run_search_batch(keyword, batch_count)
        
        # 自动进入详情采集模式
        if links_file and os.path.exists(links_file):
            print("\n=== 自动进入详情采集模式 ===")
            
            # 详情控制器
            detail_ctrl = DetailController(browser)
            detail_ctrl.process_from_file(links_file)
        
        # 关闭浏览器
        browser.close()
        
        return True
    except Exception as e:
        logging.error(f"搜索模式执行失败: {str(e)}")
        print(f"搜索失败: {str(e)}")
        return False

def detail_mode(links_file):
    """详情采集模式"""
    print("=== 启动详情采集模式 ===")
    
    try:
        # 初始化浏览器
        browser = BrowserController()
        browser.init_browser()
        browser.login()
        
        # 初始化详情控制器
        detail_ctrl = DetailController(browser)
        
        # 处理链接
        detail_ctrl.process_from_file(links_file)
        
        # 关闭浏览器
        browser.close()
        
        return True
    except Exception as e:
        logging.error(f"详情采集模式执行失败: {str(e)}")
        print(f"详情采集失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 设置日志
    setup_logging()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="小红书数据采集工具")
    parser.add_argument("--mode", choices=["search", "detail", "init"], required=True, 
                        help="运行模式：search - 搜索模式，detail - 详情采集模式，init - 初始化数据库")
    parser.add_argument("--keyword", help="搜索关键词")
    parser.add_argument("--batch", type=int, default=2, 
                        help="批次数")
    parser.add_argument("--links", help="链接文件路径")
    
    args = parser.parse_args()
    
    if args.mode == "init":
        # 初始化数据库
        init_database()
    elif args.mode == "search":
        if not args.keyword:
            parser.error("搜索模式需要提供 --keyword 参数")
        search_mode(args.keyword, args.batch)
    elif args.mode == "detail":
        if not args.links:
            parser.error("详情采集模式需要提供 --links 参数")
        detail_mode(args.links)

if __name__ == "__main__":
    main()