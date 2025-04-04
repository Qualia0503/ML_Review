

class Note:
    @staticmethod
    def extract_note_id_from_url(url):
        """从URL中提取笔记ID"""
        if "/explore/" in url:
            note_id = url.split("/explore/")[1].split("?")[0]
            return note_id
        elif "/note/" in url:
            note_id = url.split("/note/")[1].split("?")[0]
            return note_id
        return ""
    
    @staticmethod
    def parse_count(count_str):
        """解析数量字符串为整数"""
        if not count_str:
            return 0
            
        count_str = str(count_str).replace(',', '').strip()
        
        if count_str.endswith('万'):
            return int(float(count_str[:-1]) * 10000)
        if count_str.endswith('k') or count_str.endswith('K'):
            return int(float(count_str[:-1]) * 1000)
        
        try:
            return int(float(count_str))
        except:
            return 0
