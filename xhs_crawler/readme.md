第一步：
pip install -r requirements.txt

第二步：
初始化数据库的，如果不需要写入数据库，则可以跳过；

python main.py --mode init

第三步：抓取笔记的真正的链接以及点赞数，标题等第一层信息的；
keyword，即要查的关键词； batch，即抓取几轮， 一般建议10批次，热门的词可以20批次，超过20批次没有意义；
一般抓取200个笔记详情，需要大约1-2天的时间，提前去规划分配你的项目模块；

python main.py --mode search --keyword "万森男士" --batch 10
python main.py --mode search --keyword "尤司男士" --batch 10

第四步：抓取笔记深层信息的，如内容，点赞，收藏，转发等；
python main.py --mode detail --links "北京的美食_笔记链接_2025-04-07.txt"