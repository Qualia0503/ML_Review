
import mysql.connector
import logging
from datetime import datetime
import time
import random
from config.settings import DB_CONFIG

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            try:
                cls._instance.conn = mysql.connector.connect(**DB_CONFIG)
                logging.info("数据库连接成功")
            except Exception as e:
                logging.error(f"数据库连接失败: {str(e)}")
                cls._instance.conn = None  # 设置为None而不是抛出异常
        return cls._instance
    
    def get_connection(self):
        """获取数据库连接"""
        if self.conn is None:
            try:
                self.conn = mysql.connector.connect(**DB_CONFIG)
            except Exception as e:
                logging.error(f"尝试重新连接数据库失败: {str(e)}")
                return None
        # 如果连接已关闭，重新连接
        elif not self.conn.is_connected():
            try:
                self.conn = mysql.connector.connect(**DB_CONFIG)
            except Exception as e:
                logging.error(f"尝试重新连接数据库失败: {str(e)}")
                return None
        return self.conn
    
    def initialize_tables(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建笔记表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                note_id VARCHAR(50) PRIMARY KEY,
                title VARCHAR(255),
                author VARCHAR(100),
                note_link VARCHAR(255) NOT NULL,
                like_count INT DEFAULT 0,
                cover_pic VARCHAR(255),
                author_avatar VARCHAR(255),
                crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 创建笔记详情表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_details (
                note_id VARCHAR(50) PRIMARY KEY,
                content TEXT,
                author_id VARCHAR(50),
                publish_time VARCHAR(50),
                like_count INT DEFAULT 0,
                collect_count INT DEFAULT 0,
                comment_count INT DEFAULT 0,
                tags TEXT,
                crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes(note_id)
            )
            """)
            
            # 创建图片链接表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                note_id VARCHAR(50),
                image_url VARCHAR(255) NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(note_id)
            )
            """)
            
            conn.commit()
            logging.info("数据库表初始化成功")
            
        except Exception as e:
            conn.rollback()
            logging.error(f"数据库表初始化失败: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def save_note(self, note):
        """保存搜索阶段获取的笔记基础信息"""
        conn = self.get_connection()
        if conn is None:
            logging.error("数据库连接不可用，无法保存笔记信息")
            return False
        
        
        try:
            cursor = conn.cursor()
            query = """
            INSERT INTO notes (note_id, title, author, note_link, like_count, cover_pic, author_avatar)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            author = VALUES(author),
            note_link = VALUES(note_link),
            like_count = VALUES(like_count),
            cover_pic = VALUES(cover_pic),
            author_avatar = VALUES(author_avatar)
            """
            
            values = (
                note['note_id'],
                note['title'],
                note['author'],
                note['note_link'],
                note['like_count'],
                note.get('cover_pic', ''),
                note.get('author_avatar', '')
            )
            
            cursor.execute(query, values)
            conn.commit()
            
            return True
            
        except Exception as e:
            conn.rollback()
            logging.error(f"保存笔记信息失败: {str(e)}")
            return False
        finally:
            cursor.close()
    
    def save_note_detail(self, note_detail):
        """保存笔记详情信息"""
        conn = self.get_connection()
        if conn is None:
            logging.error("数据库连接不可用，无法保存笔记详情信息")
            return False
        
        
        try:
            # 保存笔记详情
            cursor = conn.cursor()
            detail_query = """
            INSERT INTO note_details (note_id, content, author_id, publish_time, like_count, collect_count, comment_count, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            content = VALUES(content),
            author_id = VALUES(author_id),
            publish_time = VALUES(publish_time),
            like_count = VALUES(like_count),
            collect_count = VALUES(collect_count),
            comment_count = VALUES(comment_count),
            tags = VALUES(tags)
            """
            
            # 将标签列表转换为字符串
            tags_str = ','.join(note_detail.get('tags', []))
            
            detail_values = (
                note_detail['note_id'],
                note_detail['content'],
                note_detail.get('author_id', ''),
                note_detail.get('publish_time', ''),
                note_detail.get('like_count', 0),
                note_detail.get('collect_count', 0),
                note_detail.get('comment_count', 0),
                tags_str
            )
            
            cursor.execute(detail_query, detail_values)
            
            # 保存图片链接
            if 'image_links' in note_detail and note_detail['image_links']:
                # 先删除旧的图片链接
                cursor.execute("DELETE FROM images WHERE note_id = %s", (note_detail['note_id'],))
                
                # 插入新的图片链接
                for image_url in note_detail['image_links']:
                    image_query = """
                    INSERT INTO images (note_id, image_url) VALUES (%s, %s)
                    """
                    cursor.execute(image_query, (note_detail['note_id'], image_url))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            logging.error(f"保存笔记详情失败: {str(e)}")
            return False
        finally:
            cursor.close()
    
    def get_all_note_links(self, limit=100):
        """获取所有笔记链接，用于更新详情"""
        conn = self.get_connection()
        if conn is None:
            logging.error("数据库连接不可用，无法获取笔记链接")
            return False
        
        
        try:
            cursor = conn.cursor()
            query = """
            SELECT note_id, note_link FROM notes
            ORDER BY crawl_time DESC
            LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            return [(note_id, note_link) for note_id, note_link in results]
            
        except Exception as e:
            logging.error(f"获取笔记链接失败: {str(e)}")
            return []
        finally:
            cursor.close()
