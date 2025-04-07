# controllers/detail_controller.py 修改版
import logging
import time
import random
import re
import json
from urllib.parse import urljoin
from datetime import datetime, timedelta
import threading
from models.database import Database
from models.note import Note
from utils.browser_utils import random_sleep, simulate_human_behavior
from utils.file_utils import read_links_from_txt, export_to_excel
from controllers.comments_controller import CommentsController

class DetailController:
    def __init__(self, browser_controller):
        self.browser = browser_controller
        self.db = Database()
        self.pause_flag = False
        self.resume_event = threading.Event()
        self.consecutive_empty_count = 0  # 连续空值计数器
        # 实例化评论控制器
        self.comments_controller = CommentsController(browser_controller)
    
    def get_note_detail(self, url):
        """获取笔记详情"""
        try:
            # 访问笔记页面
            self.browser.navigate_to(url)
            
            # 模拟人类行为，防止反爬
            simulate_human_behavior(self.browser.page)
            
            # 随机等待
            random_sleep(1.5, 3.0)
            
            page = self.browser.page
            
            # 提取笔记ID
            note_id = Note.extract_note_id_from_url(url)
            
            # 获取标题
            title_ele = page.ele('xpath://div[@id="detail-title"]', timeout=5)
            title = title_ele.text.strip() if title_ele else ''
            
            # 获取作者信息
            author_ele = page.ele('xpath://div[contains(@class, "author-wrapper")]//a[contains(@class, "name")]', timeout=5)
            author_name = author_ele.text.strip() if author_ele else ''
            author_link = author_ele.attr('href') if author_ele else ''
            
            # 从作者链接提取作者ID
            author_id = ""
            if author_link and '/profile/' in author_link:
                author_id = author_link.split('/profile/')[1].split('?')[0]
            
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
            like_count = self._get_interaction_count(page, 'like-wrapper')
            collect_count = self._get_interaction_count(page, 'collect-wrapper')
            comment_count = self._get_interaction_count(page, 'chat-wrapper')
            
            # 获取标签
            tags = []
            tag_elements = page.eles('xpath://a[@id="hash-tag"]')
            for tag_ele in tag_elements:
                tag_text = tag_ele.text.replace('#', '').strip()
                if tag_text:
                    tags.append(tag_text)
            
            # 获取所有图片链接
            image_links = []
            img_elements = page.eles('xpath://img[contains(@class, "note-slider-img")]')
            for img_ele in img_elements:
                img_url = img_ele.attr('src')
                if img_url and img_url not in image_links:
                    image_links.append(img_url)
            
            # 构建详情数据
            note_detail = {
                'note_id': note_id,
                'title': title,
                'content': content,
                'author_name': author_name,
                'author_id': author_id,
                'author_avatar': author_avatar,
                'author_link': urljoin("https://www.xiaohongshu.com", author_link) if author_link else '',
                'publish_time': publish_time,
                'like_count': Note.parse_count(like_count),
                'collect_count': Note.parse_count(collect_count),
                'comment_count': Note.parse_count(comment_count),
                'tags': tags,
                'image_links': image_links,
                'note_link': url
            }
            
            # 获取评论数据
            try:
                comments_json = self.comments_controller.get_comments(page, note_detail['comment_count'])
                note_detail['comments'] = comments_json
                logging.info(f"成功获取评论数据: {len(json.loads(comments_json))} 条")
            except Exception as e:
                logging.error(f"获取评论数据失败: {str(e)}")
                note_detail['comments'] = json.dumps([])
            
            # 检查是否所有重要字段都为空
            empty_fields = self._check_empty_fields(note_detail)
            if empty_fields:
                logging.warning(f"获取笔记详情异常: 所有重要字段为空，可能被平台拒绝请求")
                note_detail['_is_empty'] = True
                return note_detail
            
            logging.info(f"成功获取笔记详情: {note_id}")
            note_detail['_is_empty'] = False
            return note_detail
            
        except Exception as e:
            logging.error(f"获取笔记详情失败: {str(e)}")
            return {'note_id': note_id if 'note_id' in locals() else '', 'note_link': url, '_is_empty': True}
    
    def _check_empty_fields(self, note_detail):
        """检查笔记是否所有重要字段都为空"""
        important_fields = ['title', 'content', 'author_name', 'publish_time']
        empty_fields = []
        
        for field in important_fields:
            if not note_detail.get(field):
                empty_fields.append(field)
        
        return empty_fields
    
    def _get_interaction_count(self, page, class_name):
        """获取交互数据（点赞、收藏、评论数）"""
        try:
            element = page.ele(f'xpath://span[contains(@class, "{class_name}")]//span[@class="count"]')
            return element.text.strip() if element else '0'
        except:
            return '0'
    
    def _wait_and_resume(self, wait_hours=12):
        """等待指定小时数后自动恢复"""
        self.pause_flag = True
        resume_time = datetime.now() + timedelta(hours=wait_hours)
        
        print(f"\n检测到平台可能拒绝请求，将在 {wait_hours} 小时后自动恢复...")
        print(f"预计恢复时间: {resume_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 创建倒计时线程
        threading.Thread(target=self._countdown_timer, args=(wait_hours,), daemon=True).start()
        
        # 等待指定时间
        time.sleep(wait_hours * 3600)
        self.pause_flag = False
        print("\n自动恢复采集...")
        return True
    
    def _countdown_timer(self, wait_hours):
        """显示倒计时"""
        total_seconds = wait_hours * 3600
        for remaining in range(total_seconds, 0, -60):  # 每分钟更新一次
            hours, remainder = divmod(remaining, 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"\r等待恢复中... 剩余时间: {hours:02d}:{minutes:02d}", end="", flush=True)
            time.sleep(60)
    
    def _wait_for_user_input(self):
        """等待用户输入后继续"""
        self.pause_flag = True
        print("\n再次检测到平台拒绝请求，已暂停爬虫...")
        input("请处理完毕后，按回车键继续...")
        self.pause_flag = False
        print("继续采集...")
        return True
    
    def process_links(self, links, save_excel=True):
        """处理链接列表，每10个笔记休息一次"""
        processed_notes = []
        total_links = len(links)
        
        print(f"开始处理 {total_links} 个笔记链接")
        
        # 重置连续空值计数器
        self.consecutive_empty_count = 0
        
        index = 0
        while index < total_links:
            if self.pause_flag:
                time.sleep(1)  # 暂停状态下，轻松等待
                continue
                
            link = links[index]
            print(f"正在处理第 {index + 1}/{total_links} 个链接")
            
            try:
                # 获取笔记详情
                note_detail = self.get_note_detail(link)
                
                if note_detail:
                    # 检查是否为空数据
                    if note_detail.get('_is_empty', False):
                        self.consecutive_empty_count += 1
                        print(f"警告: 获取的笔记数据为空，可能被平台拒绝请求，这是连续第 {self.consecutive_empty_count} 次遇到这种情况")
                        
                        if self.consecutive_empty_count >= 5:
                            # 连续5次遇到空数据，等待12小时后自动重试
                            print(f"连续 {self.consecutive_empty_count} 次获取空数据，触发自动休眠")
                            self._wait_and_resume(wait_hours=12)
                            # 不增加索引，重试当前链接
                            self.consecutive_empty_count = 0  # 重置计数器
                            continue
                        else:
                            # 虽然是空数据，但是没有达到连续5次，继续下一个
                            index += 1
                            continue
                    else:
                        # 数据正常，重置连续空值计数
                        self.consecutive_empty_count = 0
                    
                    # 数据正常，保存到数据库
                    # 移除非数据库字段
                    if '_is_empty' in note_detail:
                        del note_detail['_is_empty']
                        
                    self.db.save_note_detail(note_detail)
                    processed_notes.append(note_detail)
                    print(f"成功获取并保存笔记: {note_detail.get('title', '')[:20]}...")
                    
                else:
                    print(f"获取笔记详情失败")
                    # 将失败也视为空值
                    self.consecutive_empty_count += 1
                    if self.consecutive_empty_count >= 5:
                        print(f"连续 {self.consecutive_empty_count} 次获取空数据，触发自动休眠")
                        self._wait_and_resume(wait_hours=12)
                        self.consecutive_empty_count = 0  # 重置计数器
                        # 不增加索引，重试当前链接
                        continue
                
                # 每处理10个链接休息一次，避免被反爬
                if (index + 1) % 10 == 0 and index < total_links - 1:
                    rest_time = random.uniform(5, 10)
                    print(f"已处理10个链接，休息 {rest_time:.1f} 秒，避免被反爬...")
                    time.sleep(rest_time)
                else:
                    # 正常随机等待
                    random_sleep(0.5, 2.0)
                
                # 处理下一个链接
                index += 1
                    
            except Exception as e:
                logging.error(f"处理链接 {link} 失败: {str(e)}")
                print(f"处理链接失败: {str(e)}")
                # 增加连续空值计数（异常也视为空值）
                self.consecutive_empty_count += 1
                if self.consecutive_empty_count >= 5:
                    print(f"连续 {self.consecutive_empty_count} 次获取空数据，触发自动休眠")
                    self._wait_and_resume(wait_hours=12)
                    self.consecutive_empty_count = 0  # 重置计数器
                    # 不增加索引，重试当前链接
                    continue
                # 跳过问题链接
                index += 1
        
        # 导出Excel
        if save_excel and processed_notes:
            current_date = datetime.now().strftime('%Y-%m-%d')
            excel_filename = f"笔记详情_{current_date}.xlsx"
            export_to_excel(processed_notes, excel_filename)
            print(f"详情数据已导出到Excel: {excel_filename}")
        
        print(f"处理完成，成功获取 {len(processed_notes)} 条笔记详情")
        return processed_notes
    
    def process_from_file(self, file_path, save_excel=True):
        """从文件读取链接并处理"""
        links = read_links_from_txt(file_path)
        
        if not links:
            print(f"文件 {file_path} 中没有找到链接")
            return []
        
        return self.process_links(links, save_excel)