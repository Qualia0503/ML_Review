# controllers/search_controller.py
import logging
import time
import random
from urllib.parse import quote
from datetime import datetime
from models.database import Database
from models.note import Note
from utils.browser_utils import random_sleep
from utils.file_utils import export_to_excel, export_links_to_txt
from config.settings import SEARCH_URL_TEMPLATE, EXCEL_FILENAME_TEMPLATE, LINKS_FILENAME_TEMPLATE

class SearchController:
    def __init__(self, browser_controller):
        self.browser = browser_controller
        self.db = Database()
    
    def search_keyword(self, keyword):
        """搜索关键词"""
        encoded_keyword = quote(quote(keyword.encode('utf-8')).encode('gb2312'))
        search_url = SEARCH_URL_TEMPLATE.format(keyword=encoded_keyword)
        
        try:
            self.browser.navigate_to(search_url)
            logging.info(f"搜索关键词: {keyword}")
            return True
        except Exception as e:
            logging.error(f"搜索关键词 {keyword} 失败: {str(e)}")
            return False
    
    def extract_notes_from_current_page(self):
        """从当前页面提取笔记信息"""
        notes = []
        page = self.browser.page
        
        try:
            sections = page.eles('.note-item')
            if not sections:
                logging.warning("没有找到任何笔记项")
                return notes
            
            print(f"找到 {len(sections)} 条笔记")
            
            for section in sections:
                try:
                    # 提取标题
                    title_ele = section.ele('.title') or section.ele('.content')
                    title = title_ele.text if title_ele else ""
                    
                    # 提取作者
                    author_ele = section.ele('.author') or section.ele('.user-name')
                    author = author_ele.text if author_ele else ""
                    
                    # 提取点赞数
                    count_ele = section.ele('.count')
                    count = count_ele.text if count_ele else "0"
                    like_count = Note.parse_count(count)
                    
                    # 提取封面图
                    coverurl_ele = section.ele('xpath://img[@data-xhs-img and not(@class="author-avatar")]')
                    coverurl = coverurl_ele.attr('src') if coverurl_ele else ""
                    
                    # 提取作者头像
                    avatarurl_ele = section.ele('xpath://img[@class="author-avatar"]')
                    avatarurl = avatarurl_ele.attr('src') if avatarurl_ele else ""
                    
                    # 提取链接信息
                    section_html = section.html
                    
                    # 提取第一个链接（explore）
                    note_link_1_start = section_html.find('/explore/')
                    if note_link_1_start == -1:
                        continue
                        
                    note_link_1_end = section_html.find('"', note_link_1_start)
                    base_url = section_html[note_link_1_start:note_link_1_end]
                    
                    # 提取第二个链接（search_result）
                    note_link_2_start = section_html.find('/search_result/')
                    note_link_2_end = section_html.find('"', note_link_2_start) if note_link_2_start != -1 else -1
                    
                    if note_link_2_start != -1 and note_link_2_end != -1:
                        full_url = section_html[note_link_2_start:note_link_2_end]
                        
                        # 拼接完整链接
                        full_link = f"https://www.xiaohongshu.com{base_url}"
                        
                        if '?xsec_token=' in full_url:
                            xsec_token_start = full_url.find('?xsec_token=')
                            xsec_token_end = full_url.find('&', xsec_token_start)
                            if xsec_token_end == -1:
                                xsec_token_end = len(full_url)
                                
                            xsec_token = full_url[xsec_token_start + 12:xsec_token_end]
                            full_link = f"{full_link}?xsec_token={xsec_token}&xsec_source=pc_search"
                        else:
                            full_link = f"{full_link}&xsec_source=pc_search"
                    else:
                        # 备用方案，直接使用base_url
                        full_link = f"https://www.xiaohongshu.com{base_url}"
                    
                    # 从链接中提取笔记ID
                    note_id = Note.extract_note_id_from_url(full_link)
                    
                    # 创建笔记数据
                    note_data = {
                        'note_id': note_id,
                        'title': title,
                        'author': author,
                        'note_link': full_link,
                        'like_count': like_count,
                        'cover_pic': coverurl,
                        'author_avatar': avatarurl
                    }
                    
                    notes.append(note_data)
                    logging.info(f"成功提取笔记: {title[:20]}...")
                    
                except Exception as e:
                    logging.error(f"处理笔记时出错: {str(e)}")
            
            return notes
            
        except Exception as e:
            logging.error(f"提取笔记信息时发生错误: {str(e)}")
            return notes
    
    def run_search_batch(self, keyword, batch_count=2):
        """运行搜索批次"""
        all_notes = []
        all_links = []
        
        print(f"开始搜索关键词: {keyword}")
        search_success = self.search_keyword(keyword)
        
        if not search_success:
            print("搜索失败，请检查网络或登录状态")
            return all_notes, all_links
        
        # 等待页面加载
        random_sleep(1.0, 2.0)
        
        for batch in range(batch_count):
            print(f"正在处理第 {batch + 1}/{batch_count} 批次...")
            
            # 提取当前页面的笔记
            batch_notes = self.extract_notes_from_current_page()
            all_notes.extend(batch_notes)
            
            # 收集链接
            batch_links = [note['note_link'] for note in batch_notes if 'note_link' in note]
            all_links.extend(batch_links)
            
            # 保存到数据库
            for note in batch_notes:
                try:
                    self.db.save_note(note)
                except Exception as e:
                    logging.error(f"保存笔记 {note.get('note_id', '')} 失败: {str(e)}")
            
            # 滚动页面加载更多内容
            if batch < batch_count - 1:  # 如果不是最后一批
                print("滚动页面加载更多内容...")
                self.browser.scroll_page()
                random_sleep(1.0, 3.0)  # 等待新内容加载
        
        # 生成Excel文件和链接文件
        current_date = datetime.now().strftime('%Y-%m-%d')
        excel_filename = EXCEL_FILENAME_TEMPLATE.format(keyword=keyword, date=current_date)
        links_filename = LINKS_FILENAME_TEMPLATE.format(keyword=keyword, date=current_date)
        
        export_to_excel(all_notes, excel_filename)
        export_links_to_txt(all_links, links_filename)
        
        print(f"搜索完成，共获取 {len(all_notes)} 条笔记")
        print(f"Excel文件已保存: {excel_filename}")
        print(f"链接文件已保存: {links_filename}")
        
        return all_notes, links_filename