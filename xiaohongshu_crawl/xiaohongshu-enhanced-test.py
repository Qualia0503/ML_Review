from DrissionPage import ChromiumPage
import time
import re
import json
import os
from datetime import datetime

def extract_id_from_url(url):
    """
    从URL中提取ID
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
    match = re.search(r'explore/([^?]+)', url)
    return match.group(1) if match else ''

def save_to_json(data, filename):
    """
    将数据保存为JSON
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_basic_note_info(browser):
    """
    获取笔记基本信息
    """
    try:
        note_info = {}
        
        # 获取笔记ID
        note_info['note_id'] = extract_note_id_from_url(browser.url)
        
        # 获取标题
        title_ele = browser.ele('xpath://div[@id="detail-title"]')
        note_info['title'] = title_ele.text.strip() if title_ele else "无标题"
        
        # 获取作者信息
        author_ele = browser.ele('xpath://div[contains(@class, "author-wrapper")]//a[contains(@class, "name")]')
        note_info['author'] = author_ele.text.strip() if author_ele else "未知作者"
        author_link = author_ele.attr('href') if author_ele else ""
        note_info['author_id'] = extract_id_from_url(author_link)
        
        # 获取内容
        content_ele = browser.ele('xpath://div[@id="detail-desc"]//span[@class="note-text"]')
        note_info['content'] = content_ele.text.strip() if content_ele else "无内容"
        
        # 获取发布时间
        date_ele = browser.ele('xpath://span[@class="date"]')
        note_info['publish_date'] = date_ele.text.strip() if date_ele else "未知日期"
        
        # 获取交互数据
        like_ele = browser.ele('xpath://span[contains(@class, "like-wrapper")]//span[@class="count"]')
        note_info['like_count'] = like_ele.text.strip() if like_ele else "0"
        
        collect_ele = browser.ele('xpath://span[contains(@class, "collect-wrapper")]//span[@class="count"]')
        note_info['collect_count'] = collect_ele.text.strip() if collect_ele else "0"
        
        comment_ele = browser.ele('xpath://span[contains(@class, "chat-wrapper")]//span[@class="count"]')
        note_info['comment_count'] = comment_ele.text.strip() if comment_ele else "0"
        
        # 获取标签
        tags = []
        tag_elements = browser.eles('xpath://a[@id="hash-tag"]')
        for tag_ele in tag_elements:
            tags.append(tag_ele.text.replace('#', '').strip())
        note_info['tags'] = tags
        
        # 获取图片链接
        images = []
        img_elements = browser.eles('xpath://img[contains(@class, "note-slider-img")]')
        for img_ele in img_elements:
            img_url = img_ele.attr('src')
            if img_url and img_url not in images:
                images.append(img_url)
        note_info['images'] = images
        
        return note_info
    
    except Exception as e:
        print(f"获取笔记基本信息失败: {str(e)}")
        return {
            "note_id": extract_note_id_from_url(browser.url),
            "title": "获取失败",
            "author": "获取失败",
            "content": "获取失败",
            "publish_date": "获取失败"
        }

def extract_comments(browser, max_comments=758):
    """
    提取评论，包括回复
    """
    comments = []
    
    try:
        # 等待评论区加载
        browser.wait(1.0)
        
        # 获取评论总数
        total_ele = browser.ele('xpath://div[@class="total"]')
        if not total_ele:
            print("未找到评论总数元素")
            return comments
        
        total_text = total_ele.text
        print(f"评论区标题: {total_text}")
        match = re.search(r'\d+', total_text)
        total_comments = int(match.group()) if match else 0
        print(f"评论总数: {total_comments}")
        
        # 限制要爬取的评论数量
        comments_to_fetch = min(max_comments, total_comments)
        print(f"计划爬取前 {comments_to_fetch} 条评论")
        
        # 滚动加载评论
        current_comments = 0
        max_scroll_attempts = 1000
        
        for i in range(max_scroll_attempts):
            # 检查当前已加载的评论数量
            comment_elements = browser.eles('xpath://div[@class="parent-comment"]/div[@class="comment-item"]')
            current_comments = len(comment_elements)
            print(f"当前已加载评论: {current_comments}/{comments_to_fetch}")
            
            if current_comments >= comments_to_fetch:
                break
            
            # 滚动到评论区底部
            comments_container = browser.ele('xpath://div[@class="comments-el"]')
            if comments_container:
                browser.run_js('arguments[0].scrollIntoView({block: "end"});', comments_container)
                time.sleep(0.5)
            
            # 尝试点击"展开更多回复"按钮
            more_buttons = browser.eles('xpath://div[@class="show-more" and not(contains(@style, "display: none"))]')
            for btn in more_buttons:
                try:
                    print("点击'展开更多回复'按钮")
                    browser.run_js('arguments[0].scrollIntoView({block: "center"});', btn)
                    time.sleep(0.5)
                    btn.click()
                    time.sleep(0.6)
                except Exception as e:
                    print(f"点击按钮失败: {str(e)}")
        
        # 最终获取评论
        comment_elements = browser.eles('xpath://div[@class="parent-comment"]/div[@class="comment-item"]')
        print(f"找到 {len(comment_elements)} 条评论")
        
        # 处理评论
        for i, comment_ele in enumerate(comment_elements):
            if i >= comments_to_fetch:
                break
            
            try:
                # 评论ID
                comment_id = comment_ele.attr('id')
                if comment_id:
                    comment_id = comment_id.replace('comment-', '')
                
                # 评论者信息
                commenter_ele = comment_ele.ele('xpath:.//a[contains(@class, "name")]')
                commenter_name = commenter_ele.text.strip() if commenter_ele else '未知用户'
                commenter_link = commenter_ele.attr('href') if commenter_ele else ''
                commenter_id = extract_id_from_url(commenter_link)
                
                # 评论内容
                content_ele = comment_ele.ele('xpath:.//span[@class="note-text"]')
                content = content_ele.text.strip() if content_ele else '无内容'
                
                # 评论时间 - 改进了时间的提取
                # time_ele = comment_ele.ele('xpath:.//div[@class="info"]//span[@class="date"]')
                time_ele = comment_ele.ele('xpath:.//div[@class="date"]/span[1]')
                comment_time = time_ele.text.strip() if time_ele else '未知时间'
                
                # 评论位置
                location_ele = comment_ele.ele('xpath:.//span[@class="location"]')
                location = location_ele.text.strip() if location_ele else ''
                
                # 是否作者评论
                is_author = bool(comment_ele.ele('xpath:.//span[@class="tag" and contains(text(), "作者")]'))
                
                # 评论点赞数
                like_ele = comment_ele.ele('xpath:.//span[contains(@class, "like-wrapper")]//span[@class="count"]')
                like_count = like_ele.text.strip() if like_ele else '0'
                if like_count == '赞':  # 处理没有点赞的情况
                    like_count = '0'
                
                print(f"评论 {i+1}: {commenter_name} - {comment_time}")
                print(f"内容: {content[:50]}..." + ("" if len(content) <= 50 else "..."))
                
                # 提取回复
                replies = []
                reply_container = browser.ele(f'xpath://div[@id="comment-{comment_id}"]/following-sibling::div[@class="reply-container"]')
                
                if reply_container:
                    # 先确保展开所有回复
                    show_more_btn = reply_container.ele('xpath:.//div[@class="show-more"]')
                    if show_more_btn:
                        try:
                            browser.run_js('arguments[0].scrollIntoView({block: "center"});', show_more_btn)
                            time.sleep(0.5)
                            show_more_btn.click()
                            time.sleep(1.5)
                        except:
                            pass
                    
                    # 获取所有回复
                    reply_elements = reply_container.eles('xpath:.//div[@class="comment-item comment-item-sub"]')
                    print(f"  - 找到 {len(reply_elements)} 条回复")
                    
                    for reply_ele in reply_elements:
                        try:
                            # 回复ID
                            reply_id = reply_ele.attr('id')
                            if reply_id:
                                reply_id = reply_id.replace('comment-', '')
                            
                            # 回复者信息
                            replier_ele = reply_ele.ele('xpath:.//a[contains(@class, "name")]')
                            replier_name = replier_ele.text.strip() if replier_ele else '未知用户'
                            replier_link = replier_ele.attr('href') if replier_ele else ''
                            replier_id = extract_id_from_url(replier_link)
                            
                            # 回复内容
                            reply_content_ele = reply_ele.ele('xpath:.//span[@class="note-text"]')
                            reply_content = reply_content_ele.text.strip() if reply_content_ele else '无内容'
                            
                            # 回复时间
                            # reply_time_ele = reply_ele.ele('xpath:.//div[@class="info"]//span[@class="date"]')
                            reply_time_ele = reply_ele.ele('xpath:.//div[@class="date"]/span[1]')
                            reply_time = reply_time_ele.text.strip() if reply_time_ele else '未知时间'
                            
                            # 回复位置
                            reply_location_ele = reply_ele.ele('xpath:.//span[@class="location"]')
                            reply_location = reply_location_ele.text.strip() if reply_location_ele else ''
                            
                            # 是否作者回复
                            reply_is_author = bool(reply_ele.ele('xpath:.//span[@class="tag" and contains(text(), "作者")]'))
                            
                            # 回复点赞数
                            reply_like_ele = reply_ele.ele('xpath:.//span[contains(@class, "like-wrapper")]//span[@class="count"]')
                            reply_like_count = reply_like_ele.text.strip() if reply_like_ele else '0'
                            if reply_like_count == '赞':  # 处理没有点赞的情况
                                reply_like_count = '0'
                            
                            replies.append({
                                'reply_id': reply_id,
                                'user_name': replier_name,
                                'user_id': replier_id, 
                                'content': reply_content,
                                'time': reply_time,
                                'location': reply_location,
                                'is_author': reply_is_author,
                                'like_count': reply_like_count
                            })
                            
                        except Exception as e:
                            print(f"解析回复失败: {str(e)}")
                
                comments.append({
                    'comment_id': comment_id,
                    'user_name': commenter_name,
                    'user_id': commenter_id,
                    'content': content,
                    'time': comment_time,
                    'location': location,
                    'is_author': is_author,
                    'like_count': like_count,
                    'replies': replies
                })
                
            except Exception as e:
                print(f"处理评论 {i+1} 失败: {str(e)}")
        
        return comments
    
    except Exception as e:
        print(f"提取评论过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return comments

def test_scrape(url, max_comments=758):
    """
    进行完整的爬取测试
    """
    print(f"正在测试爬取: {url}")
    # 创建浏览器实例
    browser = ChromiumPage()
    browser.get(url)
    time.sleep(1.5)  # 等待页面加载
    
    try:
        # 获取笔记基本信息
        print("\n=== 获取笔记基本信息 ===")
        note_info = get_basic_note_info(browser)
        print(f"标题: {note_info['title']}")
        print(f"作者: {note_info['author']}")
        print(f"点赞: {note_info['like_count']}, 收藏: {note_info['collect_count']}, 评论: {note_info['comment_count']}")
        print(f"标签: {', '.join(note_info['tags'])}")
        print(f"发布日期: {note_info['publish_date']}")
        print(f"图片数量: {len(note_info['images'])}")
        
        # 获取评论
        print("\n=== 获取评论 ===")
        comments = extract_comments(browser, max_comments)
        print(f"\n成功获取 {len(comments)} 条评论")
        
        # 组合结果
        result = {
            'note_info': note_info,
            'comments': comments,
            'scrape_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 创建保存目录
        os.makedirs('test_results', exist_ok=True)
        
        # 保存结果
        note_id = note_info['note_id']
        filename = f"test_results/{note_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_to_json(result, filename)
        print(f"\n完整数据已保存至: {filename}")
        
        # # 等待用户确认
        # input("\n测试完成，按Enter键退出浏览器...")
        
        return result
    
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    # finally:
    #     browser.quit()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("请输入小红书笔记URL: ")
    
    max_comments = 758
    if len(sys.argv) > 2:
        try:
            max_comments = int(sys.argv[2])
        except:
            pass
    
    test_scrape(url, max_comments)