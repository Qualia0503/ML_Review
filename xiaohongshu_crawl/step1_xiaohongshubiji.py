import time
import random
import pandas as pd
import openpyxl
from tqdm import tqdm
from urllib.parse import quote, urlparse, parse_qs
from DrissionPage import ChromiumPage
import os

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

def craw(times):
    """循环爬取"""
    for i in tqdm(range(times)):
        retries = 2
        for attempt in range(retries):
            try:
                get_info()
                break
            except Exception as e:
                print(f"第 {attempt + 1} 次尝试失败，错误: {e}")
        page_scroll_down()

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
    keyword = "啤酒"
    total_batches = 2  # 总批次数
    current_batch = 1
    keyword_encoded = quote(quote(keyword.encode('utf-8')).encode('gb2312'))
    
    while current_batch <= total_batches:
        try:
            print(f"\n开始抓取第 {current_batch} 批次...")
            contents = []
            search(keyword_encoded)
            craw(1)  # 每批次抓取一页
            
            if contents:
                save_to_csv(contents, keyword)
            
            current_batch += 1
            time.sleep(random.uniform(2, 5))  
        except Exception as e:
            print(f"批次 {current_batch} 抓取失败: {e}")
            break
