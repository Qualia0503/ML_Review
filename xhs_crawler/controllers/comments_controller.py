# controllers/comments_controller.py
import logging
import time
import re
import json
from utils.browser_utils import random_sleep
from models.note import Note

class CommentsController:
    def __init__(self, browser_controller):
        """初始化评论控制器"""
        self.browser = browser_controller
    
    def get_comments(self, page, total_comment_count):
        """获取笔记评论数据
        
        参数:
            page: 浏览器页面对象
            total_comment_count: 评论总数
            
        返回:
            JSON字符串，包含所有评论数据
        """
        try:
            logging.info(f"开始获取评论数据，预计评论总数: {total_comment_count}")
            
            # 确保评论容器已加载
            comments_container = page.ele('xpath://div[contains(@class, "comments-container")]', timeout=5)
            if not comments_container:
                logging.warning("未找到评论容器")
                return json.dumps([])
            
            # 将评论计数转换为整数
            try:
                if isinstance(total_comment_count, str) and total_comment_count.isdigit():
                    total_count = int(total_comment_count)
                else:
                    # 尝试从评论容器中获取总数
                    total_ele = page.ele('xpath://div[contains(@class, "comments-container")]/div[contains(@class, "total")]')
                    if total_ele:
                        total_text = total_ele.text.strip()
                        # 从"共 14 条评论"中提取数字
                        match = re.search(r'\d+', total_text)
                        total_count = int(match.group()) if match else 0
                    else:
                        total_count = 0
            except Exception as e:
                logging.error(f"解析评论总数失败: {str(e)}")
                total_count = 10  # 默认值
            
            logging.info(f"实际评论总数: {total_count}")
            
            # 如果没有评论，直接返回空列表
            if total_count == 0:
                return json.dumps([])
            
            # 尝试加载更多评论
            self._try_load_more_comments(page, comments_container, total_count)
            
            # 收集所有评论
            comments = self._collect_all_comments(page)
            
            logging.info(f"成功获取 {len(comments)} 条评论数据，包含回复")
            return json.dumps(comments, ensure_ascii=False)
            
        except Exception as e:
            logging.error(f"获取评论数据失败: {str(e)}")
            return json.dumps([])


    def _try_load_more_comments(self, page, comments_container, total_count):
        """尝试通过多种方式加载更多评论"""
        try:
            # 先将焦点和鼠标位置移动到评论区
            self._focus_on_comments_container(page, comments_container)
            
            prev_comment_count = 0
            no_change_count = 0
            max_no_change = 10  # 增加允许无变化的次数
            max_scroll_attempts = 60
            
            logging.info(f"最多尝试滚动 {max_scroll_attempts} 次，直到出现结束标识或评论数不再增加")
            
            for i in range(max_scroll_attempts):
                # 先检查是否已加载完所有评论
                current_comments = page.eles('xpath://div[contains(@class, "parent-comment")]')
                loaded_comment_count = len(current_comments)
                
                # 检查"THE END"标识
                end_marker = page.ele('xpath://div[contains(@class, "end-container") and contains(text(), "THE END")]')
                if end_marker:
                    logging.info(f"发现结束标识'THE END'，评论加载完成，共 {loaded_comment_count} 条")
                    break
                
                # 检测评论数是否增加
                if loaded_comment_count == prev_comment_count:
                    no_change_count += 1
                    logging.info(f"第 {no_change_count} 次滚动后评论数未变化，仍为 {loaded_comment_count} 条")
                    
                    # 当连续无变化时，尝试查找并点击"查看更多"按钮
                    if no_change_count % 2 == 0:
                        load_more_btn = page.ele('xpath://div[contains(text(), "查看更多") or contains(text(), "加载更多")]')
                        if load_more_btn:
                            try:
                                logging.info("找到'查看更多'按钮，尝试点击")
                                load_more_btn.click()
                                time.sleep(2.0)  # 等待加载
                                no_change_count = 0  # 重置计数器
                            except Exception as e:
                                logging.warning(f"点击'查看更多'按钮失败: {str(e)}")
                    
                    if no_change_count >= max_no_change:
                        logging.info(f"连续 {max_no_change} 次滚动后评论数无变化，认为已加载完成")
                        break
                else:
                    no_change_count = 0
                    logging.info(f"第 {i+1} 次滚动后，评论数增加到 {loaded_comment_count} 条")
                
                prev_comment_count = loaded_comment_count
                
                # 模拟真实滚轮事件
                self._simulate_wheel_event(page, comments_container)
                
                # 等待新内容加载
                time.sleep(2.0)  # 增加等待时间
                
                # 尝试点击所有"显示更多"按钮
                self._click_all_show_more_buttons(page)
                
            logging.info(f"评论滚动加载完成，最终加载 {len(page.eles('xpath://div[contains(@class, \"parent-comment\")]'))} 条评论")

        except Exception as e:
            logging.error(f"尝试加载更多评论失败: {str(e)}")
            logging.info("将继续处理已加载的评论")


    def _focus_on_comments_container(self, page, comments_container):
        """将焦点和鼠标移动到评论容器上"""
        try:
            # 尝试滚动到评论容器可见位置
            page.run_js("""
                arguments[0].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            """, comments_container)
            
            time.sleep(0.5)
            
            # 尝试鼠标悬停在评论容器上
            try:
                comments_container.hover()
                logging.info("成功将鼠标悬停在评论容器上")
            except Exception as e:
                logging.warning(f"鼠标悬停失败: {str(e)}，但将继续尝试滚动加载")
            
            # 确保焦点在评论容器上
            page.run_js("arguments[0].focus();", comments_container)
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f"聚焦到评论容器失败: {str(e)}")
    
    
    def _wait_for_content_update(self, page, timeout=0.5):  # 默认等待时间改为0.5秒
        """等待内容更新完成"""
        try:
            time.sleep(timeout)
            return True
        except Exception as e:
            logging.error(f"等待内容更新失败: {str(e)}")
            return False
    
    # 修复_click_all_show_more_buttons方法中的错误
    def _click_all_show_more_buttons(self, page):
        """点击所有"显示更多"按钮以展开回复"""
        clicked = False
        try:
            show_more_btns = page.eles('xpath://div[contains(@class, "show-more")]')
            logging.info(f"找到 {len(show_more_btns)} 个'显示更多'按钮")
            
            for btn in show_more_btns:
                try:
                    # 简化判断，直接尝试点击
                    btn.click()
                    clicked = True
                    time.sleep(0.5)  # 增加等待时间
                    logging.info("成功点击了一个'显示更多'按钮")
                except Exception as e:
                    logging.warning(f"点击展开按钮失败: {str(e)}")
            
            if clicked:
                # 增加等待时间，确保子评论完全加载
                time.sleep(1.0)
                
            return clicked
        except Exception as e:
            logging.error(f"点击'显示更多'按钮过程出错: {str(e)}")
            return False

    # 改进滚动方法，尝试多种滚动策略
    def _simulate_wheel_event(self, page, element):
        """模拟鼠标滚轮事件，尝试多种滚动策略"""
        try:
            # 策略1：使用原生JavaScript滚动整个页面而非仅容器
            page.run_js("""
                window.scrollBy({
                    top: 500,
                    behavior: 'smooth'
                });
            """)
            
            time.sleep(0.5)
            
            # 策略2：直接滚动评论容器
            page.run_js("""
                arguments[0].scrollTop += 500;
            """, element)
            
            time.sleep(0.5)
            
            # 策略3：模拟真实wheel事件
            page.run_js("""
                try {
                    const rect = arguments[0].getBoundingClientRect();
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;
                    
                    const wheelEvent = new WheelEvent('wheel', {
                        deltaY: 300,
                        deltaMode: 0,
                        clientX: centerX,
                        clientY: centerY,
                        bubbles: true,
                        cancelable: true
                    });
                    arguments[0].dispatchEvent(wheelEvent);
                    return true;
                } catch (e) {
                    console.error(e);
                    return false;
                }
            """, element)
            
            return True
        except Exception as e:
            logging.error(f"模拟滚轮事件失败: {str(e)}")
            
            # 备用方法：直接使用键盘向下键
            try:
                page.keyboard.press('PageDown')
                return True
            except:
                return False

    def _collect_all_comments(self, page):
        """收集页面上的所有评论数据"""
        comments = []
        
        try:
            # 获取所有主评论
            parent_comments = page.eles('xpath://div[contains(@class, "parent-comment")]')
            logging.info(f"找到 {len(parent_comments)} 个主评论")
            
            for parent_idx, parent_div in enumerate(parent_comments):
                try:
                    comment_obj = self._parse_parent_comment(parent_div)
                    if comment_obj:
                        comments.append(comment_obj)
                        logging.info(f"成功解析第 {parent_idx + 1} 个主评论") # 添加更多日志
                except Exception as e:
                    logging.error(f"解析第 {parent_idx + 1} 个主评论失败: {str(e)}")
                    continue
            
            logging.info(f"评论收集完成，共解析 {len(comments)} 条评论") # 添加完成日志
            return comments
            
        except Exception as e:
            logging.error(f"收集评论过程中发生错误: {str(e)}")
            return comments
    
    def _parse_parent_comment(self, parent_div):
        """解析主评论数据"""
        try:
            # 获取主评论详情
            comment_item = parent_div.ele('xpath:.//div[contains(@class, "comment-item")]')
            
            comment_id = comment_item.attr('id').replace('comment-', '') if comment_item and comment_item.attr('id') else ''
            
            # 获取用户信息
            author_ele = comment_item.ele('xpath:.//a[contains(@class, "name")]')
            author_name = author_ele.text.strip() if author_ele else ''
            author_link = author_ele.attr('href') if author_ele else ''
            author_id = ''
            
            if author_link and '/profile/' in author_link:
                author_id = author_link.split('/profile/')[1].split('?')[0]
            
            # 获取用户头像
            avatar_ele = comment_item.ele('xpath:.//img[contains(@class, "avatar-item")]')
            avatar_url = avatar_ele.attr('src') if avatar_ele else ''
            
            # 获取评论内容
            content_ele = comment_item.ele('xpath:.//span[contains(@class, "note-text")]')
            content = ''
            
            if content_ele:
                # 处理文本节点
                text_nodes = content_ele.eles('xpath:.//span')
                if text_nodes:
                    content = ' '.join([node.text.strip() for node in text_nodes if node.text])
                else:
                    content = content_ele.text.strip()
                
                # 处理表情符号
                emoji_nodes = content_ele.eles('xpath:.//img[contains(@class, "note-content-emoji")]')
                emoji_urls = [node.attr('src') for node in emoji_nodes if node.attr('src')]
            
            # 获取评论时间和地点
            date_ele = comment_item.ele('xpath:.//span[contains(@class, "date")]')
            comment_date = date_ele.text.strip() if date_ele else ''
            
            location_ele = comment_item.ele('xpath:.//span[contains(@class, "location")]')
            location = location_ele.text.strip() if location_ele else ''
            
            # 获取点赞数
            like_count_ele = comment_item.ele('xpath:.//div[contains(@class, "like")]//span[contains(@class, "count")]')
            like_count = like_count_ele.text.strip() if like_count_ele else '0'
            # 如果点赞数只显示"赞"而没有数字，则视为0
            like_count = '0' if like_count == '赞' else like_count
            
            # 创建评论对象
            comment_obj = {
                'comment_id': comment_id,
                'author_name': author_name,
                'author_id': author_id,
                'author_avatar': avatar_url,
                'content': content,
                'date': comment_date,
                'location': location,
                'like_count': Note.parse_count(like_count),
                'is_reply': False,
                'replies': []
            }
            
            # 获取回复
            self._parse_reply_comments(parent_div, comment_obj, comment_id)
            
            return comment_obj
            
        except Exception as e:
            logging.error(f"解析评论详情失败: {str(e)}")
            return None
    
    def _parse_reply_comments(self, parent_div, comment_obj, comment_id):
        """解析回复评论数据"""
        try:
            # 尝试点击"显示更多回复"按钮，如果存在的话
            show_more = parent_div.ele('xpath:.//div[contains(@class, "show-more")]')
            if show_more:
                try:
                    show_more.click()
                    random_sleep(0.5, 1.0)
                except:
                    pass  # 忽略点击失败
                    
            # 获取回复容器和回复项
            reply_container = parent_div.ele('xpath:.//div[contains(@class, "reply-container")]')
            if not reply_container:
                return
                
            reply_items = reply_container.eles('xpath:.//div[contains(@class, "comment-item-sub")]')
            
            for reply_item in reply_items:
                try:
                    # 获取回复ID
                    reply_id = reply_item.attr('id').replace('comment-', '') if reply_item.attr('id') else ''
                    
                    # 获取回复者信息
                    reply_author_ele = reply_item.ele('xpath:.//a[contains(@class, "name")]')
                    reply_author_name = reply_author_ele.text.strip() if reply_author_ele else ''
                    reply_author_link = reply_author_ele.attr('href') if reply_author_ele else ''
                    reply_author_id = ''
                    
                    if reply_author_link and '/profile/' in reply_author_link:
                        reply_author_id = reply_author_link.split('/profile/')[1].split('?')[0]
                    
                    # 获取回复者头像
                    reply_avatar_ele = reply_item.ele('xpath:.//img[contains(@class, "avatar-item")]')
                    reply_avatar_url = reply_avatar_ele.attr('src') if reply_avatar_ele else ''
                    
                    # 获取回复内容
                    reply_content_ele = reply_item.ele('xpath:.//span[contains(@class, "note-text")]')
                    reply_content = ''
                    
                    if reply_content_ele:
                        # 处理文本节点
                        reply_text_nodes = reply_content_ele.eles('xpath:.//span')
                        if reply_text_nodes:
                            reply_content = ' '.join([node.text.strip() for node in reply_text_nodes if node.text])
                        else:
                            reply_content = reply_content_ele.text.strip()
                    
                    # 获取回复时间和地点
                    reply_date_ele = reply_item.ele('xpath:.//span[contains(@class, "date")]')
                    reply_date = reply_date_ele.text.strip() if reply_date_ele else ''
                    
                    reply_location_ele = reply_item.ele('xpath:.//span[contains(@class, "location")]')
                    reply_location = reply_location_ele.text.strip() if reply_location_ele else ''
                    
                    # 获取回复点赞数
                    reply_like_count_ele = reply_item.ele('xpath:.//div[contains(@class, "like")]//span[contains(@class, "count")]')
                    reply_like_count = reply_like_count_ele.text.strip() if reply_like_count_ele else '0'
                    # 如果点赞数只显示"赞"而没有数字，则视为0
                    reply_like_count = '0' if reply_like_count == '赞' else reply_like_count
                    
                    # 创建回复对象
                    reply_obj = {
                        'comment_id': reply_id,
                        'author_name': reply_author_name,
                        'author_id': reply_author_id,
                        'author_avatar': reply_avatar_url,
                        'content': reply_content,
                        'date': reply_date,
                        'location': reply_location,
                        'like_count': Note.parse_count(reply_like_count),
                        'is_reply': True,
                        'parent_comment_id': comment_id
                    }
                    
                    comment_obj['replies'].append(reply_obj)
                    
                except Exception as e:
                    logging.error(f"解析回复评论失败: {str(e)}")
                    continue
        except Exception as e:
            logging.error(f"解析回复评论过程出错: {str(e)}")
            pass