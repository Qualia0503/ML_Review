
import os
import pandas as pd
from datetime import datetime
import logging

def ensure_dir(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def export_to_excel(data, filename):
    """导出数据到Excel文件"""
    try:
        # 确保目录存在
        dir_path = os.path.dirname(filename)
        if dir_path:
            ensure_dir(dir_path)
        
        # 创建DataFrame并导出
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        
        logging.info(f"数据已导出到Excel: {filename}")
        return True
    except Exception as e:
        logging.error(f"导出Excel失败: {str(e)}")
        return False

def export_links_to_txt(links, filename):
    """导出链接到文本文件"""
    try:
        # 确保目录存在
        dir_path = os.path.dirname(filename)
        if dir_path:
            ensure_dir(dir_path)
        
        # 写入链接
        with open(filename, 'w', encoding='utf-8') as f:
            for link in links:
                f.write(f"{link}\n")
        
        logging.info(f"链接已导出到文件: {filename}")
        return True
    except Exception as e:
        logging.error(f"导出链接文件失败: {str(e)}")
        return False

def read_links_from_txt(filename):
    """从文本文件读取链接"""
    try:
        if not os.path.exists(filename):
            logging.error(f"文件不存在: {filename}")
            return []
        
        with open(filename, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
        
        logging.info(f"从文件 {filename} 读取了 {len(links)} 个链接")
        return links
    except Exception as e:
        logging.error(f"读取链接文件失败: {str(e)}")
        return []
