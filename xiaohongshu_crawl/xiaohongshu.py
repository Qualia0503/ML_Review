import time
import random
import pandas as pd
import openpyxl
from tqdm import tqdm
from urllib.parse import quote, urlparse, parse_qs
from DrissionPage import ChromiumPage
import os
import pymysql
from pymysql.cursors import DictCursor


# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rootroot',  # 请修改为你的实际密码
    'db': 'xiaohongshu',  # 请修改为你的实际数据库名
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def get_db_connection():
    """获取数据库连接"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("数据库连接成功")
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def ensure_table_exists(connection):
    """确保数据表存在，如不存在则创建"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS xiaohongshu_notes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        author VARCHAR(100) NOT NULL,
        full_link VARCHAR(500) NOT NULL,
        like_count VARCHAR(100),
        cover_pic VARCHAR(500),
        author_img VARCHAR(500),
        keyword VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(create_table_sql)
        connection.commit()
        print("表结构检查/创建完成")
        return True
    except Exception as e:
        print(f"表结构检查/创建失败: {e}")
        return False

def save_to_mysql(contents, keyword, connection):
    """保存数据到MySQL数据库，并处理重复项"""
    if not connection:
        print("数据库连接不可用，跳过MySQL保存")
        return False
    
    if not ensure_table_exists(connection):
        return False
    
    # 插入数据的SQL
    insert_sql = """
    INSERT INTO xiaohongshu_notes (title, author, full_link, like_count, cover_pic, author_img, keyword)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE 
    title = VALUES(title),
    author = VALUES(author),
    like_count = VALUES(like_count),
    cover_pic = VALUES(cover_pic),
    author_img = VALUES(author_img),
    keyword = VALUES(keyword);
    """
    
    inserted_count = 0
    try:
        with connection.cursor() as cursor:
            for item in contents:
                title, author, full_link, like_count, cover_pic, author_img = item
                
                # 尝试插入数据
                try:
                    cursor.execute(insert_sql, (
                        title, author, full_link, like_count, cover_pic, author_img, keyword
                    ))
                    inserted_count += 1
                except Exception as e:
                    print(f"插入记录失败: {e}, 链接: {full_link[:30]}...")
        
        # 提交事务
        connection.commit()
        print(f"成功保存到MySQL: {inserted_count}条记录")
        return True
    except Exception as e:
        print(f"保存到MySQL失败: {e}")
        connection.rollback()
        return False



def sign_in():
    """登录小红书"""
    sign_in_page = ChromiumPage()
    sign_in_page.get('https://www.xiaohongshu.com')
    print("请扫码登录并确保进入首页")
    time.sleep(30)
    # input("请确认已登录并回车继续...")

def search(keyword):
    """搜索指定关键词"""
    global page
    page = ChromiumPage()
    page.get(f'https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes')
    page.wait.doc_loaded()
    
    # 打印整个 HTML 页面
    # print("\n***** 页面 HTML *****\n")
    # print(page.html)
    # print("\n***** 结束 HTML *****\n")
    
    feeds = page.ele('.feeds-page')
    if not feeds:
        print("未找到内容区域")
        return
    print("搜索结果已加载")



def get_info():
    """提取笔记信息"""
    global contents
    # contents = []
    try:
        sections = page.eles('.note-item')
        if not sections:
            print("没有找到任何笔记项")
            return
        
        print(f"找到 {len(sections)} 条笔记")
        for section in sections:
            try:
                title_ele = section.ele('.title') or section.ele('.content')
                author_ele = section.ele('.author') or section.ele('.user-name')
                count_ele = section.ele('.count')
                coverurl_ele = section.ele('xpath://img[@data-xhs-img and not(@class="author-avatar")]').attr('src')
                avatarurl_ele = section.ele('xpath://img[@class="author-avatar"]').attr('src')
                
                # 提取 href 信息
                section_html = section.html
                # 提取第一个 href 链接（explore）
                note_link_1_start = section_html.find('/explore/')
                # print(note_link_1_start)
                note_link_1_end = section_html.find('"', note_link_1_start)
                # print(note_link_1_end)
                base_url = section_html[note_link_1_start:note_link_1_end]
                # print(base_url)

                # 提取第二个 href 链接（search_result）
                note_link_2_start = section_html.find('/search_result/')
                # print(note_link_2_start)
                note_link_2_end = section_html.find('"', note_link_2_start)
                # print(note_link_2_end)
                full_url = section_html[note_link_2_start:note_link_2_end]
                # print(full_url)
                
                # 拼接完整链接
                full_link = f"https://www.xiaohongshu.com{base_url}"
                # print(full_link)
                if '?xsec_token=' in full_url:
                    xsec_token_start = full_url.find('?xsec_token=')
                    xsec_token_end = full_url.find('&', xsec_token_start)
                    xsec_token = full_url[xsec_token_start + 12:xsec_token_end]
                    full_link = f"{full_link}?xsec_token={xsec_token}&xsec_source=pc_search"
                    print(full_link)
                else:
                    full_link = f"{full_link}&xsec_source=pc_search"
                    print(full_link)
                
                # 获取标题和作者
                if title_ele and author_ele and full_link:
                    title = title_ele.text
                    author = author_ele.text
                    count = count_ele.text
                    coverurl = coverurl_ele
                    avatarurl = avatarurl_ele
                    
                    # 添加数据到内容列表
                    contents.append([title, author, full_link, count, coverurl, avatarurl])
                    print(f"成功添加笔记: {title[:20]}...")
                else:
                    print("跳过缺失必要元素的笔记")
            except Exception as e:
                print(f"处理笔记时出错: {str(e)}")
    except Exception as e:
        print(f"获取信息时发生错误: {str(e)}")
    finally:
        print(f"\n总共处理笔记数: {len(sections)}")
        print(f"成功获取笔记数: {len(contents)}")


def page_scroll_down():
    """模拟用户滑动页面"""
    print("********下滑页面********")
    time.sleep(random.uniform(0.5, 1.5))
    page.scroll.to_bottom()

# def craw(times):
#     """循环爬取"""
#     for i in tqdm(range(times)):
#         retries = 2
#         for attempt in range(retries):
#             try:
#                 get_info()
#                 break
#             except Exception as e:
#                 print(f"第 {attempt + 1} 次尝试失败，错误: {e}")
#         page_scroll_down()

def adaptive_craw(max_scrolls=20, min_new_items=5):
    """自适应爬取：如果新内容足够多就继续滚动，否则停止"""
    scroll_count = 0
    previous_count = 0
    
    while scroll_count < max_scrolls:
        try:
            current_count = len(contents)
            new_items = current_count - previous_count
            
            print(f"滚动 {scroll_count+1}: 新增 {new_items} 条内容")
            
            # 如果新增内容太少，可能已经到底了
            if new_items < min_new_items and scroll_count > 2:
                print("新增内容减少，可能已到底部，停止滚动")
                break
                
            previous_count = current_count
            get_info()
            page_scroll_down()
            scroll_count += 1
            time.sleep(random.uniform(1, 2))  # 随机等待时间
            
        except Exception as e:
            print(f"滚动过程中出错: {e}")
            break

def save_to_csv(contents, keyword):
    """追加模式保存数据到CSV，并去重"""
    filename = f'{keyword}_data.csv'
    name = ['title', 'author', 'full_link','like_count', 'cover_pic', 'author_img']
    
    new_df = pd.DataFrame(columns=name, data=contents)
    
    # 如果CSV文件存在，读取已有数据并合并去重
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename, encoding='utf-8-sig')
        combined_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates()
    else:
        combined_df = new_df.drop_duplicates()
    
    combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"数据已去重并保存至 {filename}，总条数: {len(combined_df)}")

if __name__ == '__main__':
    contents = []
    keyword = "猫"
    total_batches = 20  # 总批次数
    current_batch = 1
    keyword_encoded = quote(quote(keyword.encode('utf-8')).encode('gb2312'))
    
    # 建立数据库连接
    db_connection = get_db_connection()

    try:
        while current_batch <= total_batches:
            try:
                print(f"\n开始抓取第 {current_batch} 批次...")
                contents = []
                search(keyword_encoded)
                # craw(1)  # 每批次抓取一页
                adaptive_craw()
                
                if contents:
                    save_to_csv(contents, keyword)

                # 同时保存到MySQL
                if db_connection:
                    save_to_mysql(contents, keyword, db_connection)
            
                current_batch += 1
                time.sleep(random.uniform(2, 5))  
            except Exception as e:
                print(f"批次 {current_batch} 抓取失败: {e}")
                break
    finally:
    # 关闭数据库连接
        if db_connection:
            db_connection.close()
            print("数据库连接已关闭")
