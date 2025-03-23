from DrissionPage import ChromiumPage
from DataRecorder import Recorder
from datetime import datetime
import time
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
    打开小红书笔记详情页
    """
    page = ChromiumPage()
    page.get(f'{url}')
    time.sleep(3)  # 等待页面加载
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
        
        # 获取评论数据
        comments = get_comments(page)

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
            'comments': comments,
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

def get_comments(page, max_comments=50):
    """
    获取笔记评论，支持动态加载更多评论
    """
    comments = []
    try:
        # 等待评论区加载完成 (使用更通用的等待方式)
        try:
            page.wait(3)  # 先等待3秒
            comments_container = page.ele('xpath://div[@class="comments-container"]', timeout=10)
            if not comments_container:
                print("未找到评论容器元素")
                return comments
        except Exception as e:
            print(f"等待评论容器加载失败: {str(e)}")
            return comments
        
        # 获取评论总数
        total_comments_ele = page.ele('xpath://div[@class="total"]')
        total_comments_text = total_comments_ele.text if total_comments_ele else "0"
        total_comments_match = re.search(r'\d+', total_comments_text)
        total_comments = int(total_comments_match.group()) if total_comments_match else 0
        
        print(f"评论总数: {total_comments}")
        
        # 设置实际爬取的评论数量，不超过最大限制和实际评论总数
        comments_to_fetch = min(max_comments, total_comments)
        
        loaded_comments = 0
        max_scroll_attempts = 30  # 最大滚动尝试次数，防止无限循环
        
        for _ in range(max_scroll_attempts):
            # 获取当前已加载的评论元素
            comment_elements = page.eles('xpath://div[@class="parent-comment"]/div[@class="comment-item"]')
            loaded_comments = len(comment_elements)
            
            print(f"当前已加载评论数: {loaded_comments}/{comments_to_fetch}")
            
            # 如果已加载足够的评论或者没有更多评论，则停止滚动
            if loaded_comments >= comments_to_fetch:
                break
            
            # 尝试点击"展开更多回复"按钮
            try:
                more_buttons = page.eles('xpath://div[@class="show-more" and not(contains(@style, "display: none"))]')
                if more_buttons:
                    for btn in more_buttons:
                        page.scroll.to_element(btn)
                        btn.click()
                        time.sleep(1)  # 等待加载
            except Exception as e:
                print(f"点击展开更多回复按钮失败: {str(e)}")
            
            # 滚动到评论区底部，加载更多评论
            comments_container = page.ele('xpath://div[@class="comments-el"]')
            if comments_container:
                page.scroll.to_element(comments_container, position='bottom')
                time.sleep(2)  # 等待加载新评论
        
        # 获取所有已加载的评论
        comment_elements = page.eles('xpath://div[@class="parent-comment"]/div[@class="comment-item"]')
        
        print(f"最终加载评论数: {len(comment_elements)}")
        
        for i, comment_ele in enumerate(comment_elements):
            if i >= comments_to_fetch:
                break
                
            try:
                # 获取评论者信息
                commenter_ele = comment_ele.ele('xpath:.//a[contains(@class, "name")]')
                commenter_name = commenter_ele.text.strip() if commenter_ele else ''
                commenter_link = commenter_ele.attr('href') if commenter_ele else ''
                commenter_id = extract_id_from_url(commenter_link)
                
                # 获取评论内容
                content_ele = comment_ele.ele('xpath:.//span[@class="note-text"]')
                content = content_ele.text.strip() if content_ele else ''
                
                # 获取评论时间
                time_ele = comment_ele.ele('xpath:.//span[@class="date"]')
                comment_time = time_ele.text.strip() if time_ele else ''
                
                # 获取评论点赞数
                like_ele = comment_ele.ele('xpath:.//span[contains(@class, "like-wrapper")]//span[@class="count"]')
                like_count = like_ele.text.strip() if like_ele else '0'
                
                # 判断是否为作者评论
                is_author = bool(comment_ele.ele('xpath:.//span[@class="tag" and contains(text(), "作者")]'))
                
                # 获取评论ID
                comment_id = comment_ele.attr('id').replace('comment-', '') if comment_ele.attr('id') else ''
                
                # 获取评论下的回复
                replies = []
                try:
                    # 点击查看回复(如果有)
                    show_reply_btn = comment_ele.ele('xpath:.//following-sibling::div[@class="reply-container"]//div[@class="show-more"]')
                    if show_reply_btn:
                        page.scroll.to_element(show_reply_btn)
                        show_reply_btn.click()
                        time.sleep(1)  # 等待加载回复
                    
                    # 获取回复评论
                    reply_elements = comment_ele.eles('xpath:.//following-sibling::div[@class="reply-container"]//div[@class="comment-item comment-item-sub"]')
                    for reply_ele in reply_elements:
                        try:
                            # 获取回复者信息
                            reply_user_ele = reply_ele.ele('xpath:.//a[contains(@class, "name")]')
                            reply_user_name = reply_user_ele.text.strip() if reply_user_ele else ''
                            reply_user_link = reply_user_ele.attr('href') if reply_user_ele else ''
                            reply_user_id = extract_id_from_url(reply_user_link)
                            
                            # 获取回复内容
                            reply_content_ele = reply_ele.ele('xpath:.//span[@class="note-text"]')
                            reply_content = reply_content_ele.text.strip() if reply_content_ele else ''
                            
                            # 获取回复时间
                            reply_time_ele = reply_ele.ele('xpath:.//span[@class="date"]')
                            reply_time = reply_time_ele.text.strip() if reply_time_ele else ''
                            
                            # 判断是否为作者回复
                            reply_is_author = bool(reply_ele.ele('xpath:.//span[@class="tag" and contains(text(), "作者")]'))
                            
                            # 获取回复ID
                            reply_id = reply_ele.attr('id').replace('comment-', '') if reply_ele.attr('id') else ''
                            
                            replies.append({
                                'reply_id': reply_id,
                                'user_name': reply_user_name,
                                'user_id': reply_user_id,
                                'content': reply_content,
                                'time': reply_time,
                                'is_author': reply_is_author
                            })
                        except Exception as e:
                            print(f"解析回复失败: {str(e)}")
                            continue
                except Exception as e:
                    print(f"获取回复数据失败: {str(e)}")
                
                comments.append({
                    'comment_id': comment_id,
                    'commenter_name': commenter_name,
                    'commenter_id': commenter_id,
                    'content': content,
                    'time': comment_time,
                    'like_count': like_count,
                    'is_author': is_author,
                    'replies': replies
                })
            except Exception as e:
                print(f"解析评论失败: {str(e)}")
                continue
    except Exception as e:
        print(f"获取评论数据失败: {str(e)}")
    
    return comments

def save_to_json(data, filename):
    """
    将数据保存为JSON格式
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_note_page_info(url, save_json=True, max_comments=50):
    """
    获取笔记页面所有信息
    
    参数:
    - url: 笔记链接
    - save_json: 是否保存为JSON文件
    - max_comments: 最多爬取的评论数量
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

def test_single_url(url, max_comments=10):
    """
    测试单个URL的爬取功能
    """
    print(f"正在测试爬取: {url}")
    # 设置浏览器可视
    browser_page = ChromiumPage()  # 使用默认设置，无需headless参数
    browser_page.get(url)
    time.sleep(3)  # 等待页面加载
    
    try:
        # 获取笔记信息
        print("正在获取笔记基本信息...")
        
        # 获取标题
        title = browser_page.ele('xpath://div[@id="detail-title"]', timeout=5)
        title_text = title.text.strip() if title else '无标题'
        print(f"笔记标题: {title_text}")
        
        # 获取作者信息
        author_ele = browser_page.ele('xpath://div[contains(@class, "author-wrapper")]//a[contains(@class, "name")]', timeout=5)
        author_name = author_ele.text.strip() if author_ele else '未知作者'
        print(f"作者: {author_name}")
        
        # 获取交互数据
        like_count = get_interaction_count(browser_page, 'like-wrapper')
        collect_count = get_interaction_count(browser_page, 'collect-wrapper')
        comment_count = get_interaction_count(browser_page, 'chat-wrapper')
        print(f"点赞数: {like_count}, 收藏数: {collect_count}, 评论数: {comment_count}")
        
        # 获取评论
        print(f"开始获取评论(最多{max_comments}条)...")
        comments = get_comments(browser_page, max_comments=max_comments)
        print(f"成功获取 {len(comments)} 条评论")
        
        if comments:
            print("\n评论预览:")
            for i, comment in enumerate(comments[:3], 1):  # 只显示前3条评论预览
                print(f"{i}. {comment['commenter_name']}: {comment['content'][:30]}...")
                if 'replies' in comment and comment['replies']:
                    print(f"   - 有 {len(comment['replies'])} 条回复")
        
        # 将完整数据保存为JSON
        note_info = get_note_info(browser_page)
        json_dir = 'xiaohongshu_data'
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)
        
        filename = f"{json_dir}/test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_to_json(note_info, filename)
        print(f"\n完整数据已保存至: {filename}")
        
        return note_info
    
    except Exception as e:
        print(f"测试爬取失败: {str(e)}")
        import traceback
        traceback.print_exc()  # 打印完整错误堆栈
    
    finally:
        browser_page.quit()

if __name__ == '__main__':
    # 判断是否是测试单个URL
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试模式
        if len(sys.argv) > 2:
            # 使用命令行提供的URL
            test_url = sys.argv[2]
        else:
            # 手动输入URL
            test_url = input("请输入要测试的小红书笔记URL: ")
        
        max_comments = 10
        if len(sys.argv) > 3:
            try:
                max_comments = int(sys.argv[3])
            except:
                pass
        
        test_single_url(test_url, max_comments)
    
    else:
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

            # 设置最大爬取评论数
            max_comments = 50  # 每篇笔记最多爬取的评论数量
            print(f"每篇笔记最多爬取 {max_comments} 条评论")

            for note_url in note_urls:
                try:
                    print(f"正在爬取: {note_url}")
                    # 采集笔记详情
                    note_info = get_note_page_info(note_url, max_comments=max_comments)
                    
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
                        '评论数量': len(note_info['comments'])
                    }
                    
                    # 数据写入缓存
                    r.add_data(new_note_contents_dict)
                    
                    # 避免频繁请求
                    time.sleep(3)
                    
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