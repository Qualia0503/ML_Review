from DrissionPage import ChromiumPage
from DataRecorder import Recorder
from datetime import datetime
import time
import random
import json
import re
import os

def sign_in():
    """
    首次运行需要登录小红书
    """
    sign_in_page = ChromiumPage()
    sign_in_page.get('https://www.xiaohongshu.com')
    print("请扫码登录")
    time.sleep(20)
    return sign_in_page

def read_urls_from_txt(path):
    """
    从txt文件中读取所有笔记链接
    """
    with open(path, 'r') as file:
        urls = [line.strip() for line in file.readlines()]
    return urls

def open_url(url):
    """
    打开小红书笔记详情页，包含随机等待时间和反爬虫措施
    """
    page = ChromiumPage()
    page.get(f'{url}')
    
    # 随机等待时间，更真实的浏览行为
    base_wait = random.uniform(1.0, 3.0)
    additional_wait = random.uniform(0.5, 1.5)
    total_wait = base_wait + additional_wait
    
    # 模拟人类行为：随机滚动页面
    for _ in range(random.randint(2, 4)):
        scroll_height = random.randint(300, 800)
        page.run_js(f'window.scrollBy(0, {scroll_height})')
        time.sleep(random.uniform(0.3, 0.8))
    
    # 最终等待页面加载
    time.sleep(total_wait)
    return page

def get_meta_content(page, meta_name):
    """
    获取指定meta标签的内容
    """
    try:
        meta = page.ele(f'xpath://meta[@name="{meta_name}"]', timeout=5)
        return meta.attr('content') if meta else ''
    except:
        return ''

def get_note_info(page):
    """
    从页面获取笔记信息
    """
    try:
        # 获取标题
        title = page.ele('xpath://div[@id="detail-title"]', timeout=5)
        title_text = title.text.strip() if title else ''

        # 获取作者信息
        author_ele = page.ele('xpath://div[contains(@class, "author-wrapper")]//a[contains(@class, "name")]', timeout=5)
        author_name = author_ele.text.strip() if author_ele else ''
        author_link = author_ele.attr('href') if author_ele else ''
        author_id = extract_id_from_url(author_link)
        
        # 获取作者头像
        author_avatar_ele = page.ele('xpath://img[contains(@class, "avatar-item")]', timeout=5)
        author_avatar = author_avatar_ele.attr('src') if author_avatar_ele else ''

        # 获取笔记内容
        content_ele = page.ele('xpath://div[@id="detail-desc"]', timeout=5)
        content = content_ele.text.strip() if content_ele else ''
        
        # 获取发布时间
        time_ele = page.ele('xpath://span[@class="date"]', timeout=5)
        publish_time = time_ele.text.strip() if time_ele else ''
        
        # 获取交互数据
        like_count = get_interaction_count(page, 'like-wrapper')
        collect_count = get_interaction_count(page, 'collect-wrapper')
        comment_count = get_interaction_count(page, 'chat-wrapper')
        
        # 获取标签
        tags = []
        tag_elements = page.eles('xpath://a[@id="hash-tag"]')
        for tag_ele in tag_elements:
            tags.append(tag_ele.text.replace('#', '').strip())
        
        # 获取所有图片链接
        image_links = []
        img_elements = page.eles('xpath://img[contains(@class, "note-slider-img")]')
        for img_ele in img_elements:
            img_url = img_ele.attr('src')
            if img_url and img_url not in image_links:
                image_links.append(img_url)
        
        # 获取笔记ID
        note_id = extract_note_id_from_url(page.url)

        info = {
            'note_id': note_id,
            'title': title_text,
            'content': content,
            'author_name': author_name,
            'author_id': author_id,
            'author_avatar': author_avatar,
            'author_link': author_link,
            'publish_time': publish_time,
            'like_count': like_count,
            'collect_count': collect_count,
            'comment_count': comment_count,
            'tags': tags,
            'image_links': image_links,
            'comments': [],  # 不再获取评论详细内容
            'note_link': page.url,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        return info
    except Exception as e:
        print(f"获取笔记信息失败: {str(e)}")
        return {
            'note_id': '',
            'title': '',
            'content': '',
            'author_name': '',
            'author_id': '',
            'author_avatar': '',
            'author_link': '',
            'publish_time': '',
            'like_count': '0',
            'collect_count': '0',
            'comment_count': '0',
            'tags': [],
            'image_links': [],
            'comments': [],
            'note_link': page.url,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def get_interaction_count(page, class_name):
    """
    获取交互数据（点赞、收藏、评论数）
    """
    try:
        element = page.ele(f'xpath://span[contains(@class, "{class_name}")]//span[@class="count"]')
        return element.text.strip() if element else '0'
    except:
        return '0'

def extract_id_from_url(url):
    """
    从URL中提取用户ID
    """
    if not url:
        return ''
    match = re.search(r'profile/([^?]+)', url)
    return match.group(1) if match else ''

def extract_note_id_from_url(url):
    """
    从URL中提取笔记ID
    """
    if not url:
        return ''
    match = re.search(r'note/([^?]+)', url)
    return match.group(1) if match else ''

def save_to_json(data, filename):
    """
    将数据保存为JSON格式
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_note_page_info(url, save_json=True):
    """
    获取笔记页面所有信息
    
    参数:
    - url: 笔记链接
    - save_json: 是否保存为JSON文件
    """
    # 访问url
    page = open_url(url)
    
    # 获取笔记信息
    note_info = get_note_info(page)
    
    # 保存为JSON文件(可选)
    if save_json and note_info.get('note_id'):
        json_dir = 'xiaohongshu_data'
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)
        save_to_json(note_info, f'{json_dir}/{note_info["note_id"]}.json')
    
    return note_info

if __name__ == '__main__':
    try:
        # 第1次运行需要登录，后面不用登录，可以注释掉
        browser = sign_in()

        # 获取当前日期
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # 创建输出文件名
        output_file = f'采集输出-小红书笔记详情-{current_date}.xlsx'

        # 新建一个excel表格，用来保存数据
        r = Recorder(path=output_file, cache_size=20)

        # 设置要采集的笔记链接
        note_urls_file_path = '需要采集的笔记链接（每行放1个链接）.txt'

        # 从txt文件读取urls
        note_urls = read_urls_from_txt(note_urls_file_path)

        # 创建文件夹保存详细数据（JSON格式）
        json_dir = 'xiaohongshu_data'
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)

        print("开始采集数据，不获取评论详细内容")

        for note_url in note_urls:
            try:
                print(f"正在爬取: {note_url}")
                # 采集笔记详情
                note_info = get_note_page_info(note_url)
                
                # 整理数据格式 (Excel表格中展示的关键字段)
                new_note_contents_dict = {
                    '采集日期': current_date,
                    '笔记ID': note_info['note_id'],
                    '作者': note_info['author_name'],
                    '作者ID': note_info['author_id'],
                    '笔记标题': note_info['title'],
                    '发布日期': note_info['publish_time'],
                    'IP属地': '',  # 暂时无法从页面直接获取
                    '点赞数': note_info['like_count'],
                    '收藏数': note_info['collect_count'],
                    '评论数': note_info['comment_count'],
                    '笔记链接': note_url,
                    '作者链接': note_info['author_link'],
                    '标签': ', '.join(note_info['tags']),
                    '笔记内容': note_info['content'],
                    '图片数量': len(note_info['image_links']),
                    '评论数量': 0  # 不再获取评论详细内容
                }
                
                # 数据写入缓存
                r.add_data(new_note_contents_dict)
                
                # 避免频繁请求
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"处理笔记 {note_url} 时出错: {str(e)}")
                continue

        # 保存excel文件
        r.record()
        print("数据采集完成！")
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        # 确保数据被保存
        try:
            r.record()
        except:
            pass