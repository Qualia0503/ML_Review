# 基础配置
BASE_URL = "https://www.xiaohongshu.com"
SEARCH_URL_TEMPLATE = "https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "rootroot",  # 请修改为您的MySQL密码
    "database": "xhs_crawler",
    "charset": "utf8mb4"
}

# 浏览器配置
WAIT_TIME_MIN = 0.5
WAIT_TIME_MAX = 3.0
PAGE_LOAD_TIMEOUT = 10

# 批次配置
DEFAULT_BATCH_COUNT = 2
SCROLL_COUNT_PER_BATCH = 3

# 文件配置
DEFAULT_OUTPUT_DIR = "output"
EXCEL_FILENAME_TEMPLATE = "{keyword}_笔记列表_{date}.xlsx"
LINKS_FILENAME_TEMPLATE = "{keyword}_笔记链接_{date}.txt"