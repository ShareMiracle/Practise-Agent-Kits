# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
# -*- coding: utf-8 -*-
import copy
import csv
import os
import re
import pymysql
from datetime import datetime
from urllib.parse import unquote

import scrapy
from scrapy.exceptions import DropItem
from scrapy.pipelines.files import FilesPipeline
from scrapy.pipelines.images import ImagesPipeline
from scrapy.utils.project import get_project_settings

settings = get_project_settings()


class CsvPipeline(object):
    def process_item(self, item, spider):
        # 对关键词进行URL解码，还原为中文话题名称
        keyword = unquote(item['keyword'])
        base_dir = f'结果文件{os.sep}{keyword}'
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        file_path = f'{base_dir}{os.sep}{keyword}.csv'
        if not os.path.isfile(file_path):
            is_first_write = 1
        else:
            is_first_write = 0

        if item:
            with open(file_path, 'a', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                if is_first_write:
                    header = [
                        'id', 'bid', 'user_id', '用户昵称', '微博正文', '头条文章url',
                        '发布位置', '艾特用户', '话题', '转发数', '评论数', '点赞数', '发布时间',
                        '发布工具', '微博图片url', '微博视频url', 'retweet_id', 'ip', 'user_authentication',
                        '会员类型', '会员等级'
                    ]
                    writer.writerow(header)

                writer.writerow([
                    item['weibo'].get('id', ''),
                    item['weibo'].get('bid', ''),
                    item['weibo'].get('user_id', ''),
                    item['weibo'].get('screen_name', ''),
                    item['weibo'].get('text', ''),
                    item['weibo'].get('article_url', ''),
                    item['weibo'].get('location', ''),
                    item['weibo'].get('at_users', ''),
                    item['weibo'].get('topics', ''),
                    item['weibo'].get('reposts_count', ''),
                    item['weibo'].get('comments_count', ''),
                    item['weibo'].get('attitudes_count', ''),
                    item['weibo'].get('created_at', ''),
                    item['weibo'].get('source', ''),
                    ','.join(item['weibo'].get('pics', [])),
                    item['weibo'].get('video_url', ''),
                    item['weibo'].get('retweet_id', ''),
                    item['weibo'].get('ip', ''),
                    item['weibo'].get('user_authentication', ''),
                    item['weibo'].get('vip_type', ''),
                    item['weibo'].get('vip_level', 0)
                ])
        return item


class SQLitePipeline(object):
    def open_spider(self, spider):
        try:
            import sqlite3
            base_dir = '结果文件'
            if not os.path.isdir(base_dir):
                os.makedirs(base_dir)
            db_name = settings.get('SQLITE_DATABASE', 'weibo.db')
            self.conn = sqlite3.connect(os.path.join(base_dir, db_name))
            self.cursor = self.conn.cursor()
            sql = """
                  CREATE TABLE IF NOT EXISTS weibo
                  (
                      id
                      varchar
                  (
                      20
                  ) NOT NULL PRIMARY KEY,
                      bid varchar
                  (
                      12
                  ) NOT NULL,
                      user_id varchar
                  (
                      20
                  ),
                      screen_name varchar
                  (
                      30
                  ),
                      text varchar
                  (
                      2000
                  ),
                      article_url varchar
                  (
                      100
                  ),
                      topics varchar
                  (
                      200
                  ),
                      at_users varchar
                  (
                      1000
                  ),
                      pics varchar
                  (
                      3000
                  ),
                      video_url varchar
                  (
                      1000
                  ),
                      location varchar
                  (
                      100
                  ),
                      created_at DATETIME,
                      source varchar
                  (
                      30
                  ),
                      attitudes_count INTEGER,
                      comments_count INTEGER,
                      reposts_count INTEGER,
                      retweet_id varchar
                  (
                      20
                  ),
                      ip varchar
                  (
                      100
                  ),
                      user_authentication varchar
                  (
                      100
                  ),
                      vip_type varchar
                  (
                      50
                  ),
                      vip_level INTEGER
                      )"""
            self.cursor.execute(sql)
            self.conn.commit()
        except Exception as e:
            print(f"SQLite数据库创建失败: {e}")
            spider.sqlite_error = True

    def process_item(self, item, spider):
        data = dict(item['weibo'])
        data['pics'] = ','.join(data['pics'])
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f"""INSERT OR REPLACE INTO weibo ({keys}) 
                 VALUES ({placeholders})"""
        try:
            self.cursor.execute(sql, tuple(data.values()))
            self.conn.commit()
        except Exception as e:
            print(f"SQLite保存出错: {e}")
            spider.sqlite_error = True
            self.conn.rollback()

    def close_spider(self, spider):
        self.conn.close()


class MyImagesPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        """链接拼接逻辑不变（你手动测试有效，保留）"""
        if item['weibo'].get('pics') and len(item['weibo']['pics']) > 0:
            for img_idx, img_url in enumerate(item['weibo']['pics']):
                if not img_url.strip():
                    continue
                # 拼接百度下载接口（你验证过有效）
                baidu_download_url = f"https://image.baidu.com/search/down?url={img_url}"
                print(f"📤 发起图片下载请求：{baidu_download_url}")  # 新增日志，确认请求URL正确
                yield scrapy.Request(
                    url=baidu_download_url,
                    meta={
                        'item': item,
                        'img_idx': img_idx,
                        'original_img_url': img_url
                    },
                    dont_filter=True,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
                        'Referer': 'https://image.baidu.com/'
                    }
                )

    def file_path(self, request, response=None, info=None):
        """【强制修正】仅保留3个参数，绝对不添加item！"""
        # 新增日志：验证参数是否正确（无item参数）
        print(f"🔧 file_path 参数：request={request}, response={response}, info={info}")

        # 从request.meta提取item（唯一正确的方式）
        item = request.meta.get('item')
        img_idx = request.meta.get('img_idx', 0)
        original_img_url = request.meta.get('original_img_url')

        # 简化路径逻辑，减少出错点
        decoded_keyword = unquote(item['keyword'])
        clean_keyword = re.sub(r'[#@!$%^&*(){}[\];:"\'<>,.?\\/]', '_', decoded_keyword).strip('_')
        weibo_id = item['weibo']['id']

        # 提取后缀
        img_suffix = original_img_url.split('.')[-1] if '.' in original_img_url else 'jpg'
        img_suffix = img_suffix.split('?')[0]  # 彻底去除URL参数
        img_suffix = '.' + img_suffix if len(img_suffix) <= 5 else '.jpg'

        # 生成路径（用os.path.join确保跨系统兼容）
        save_path = os.path.join(
            '结果文件',
            clean_keyword,
            'images',
            f'{weibo_id}_{img_idx}{img_suffix}'
        )
        print(f"📁 图片存储路径：{save_path}")  # 新增日志，确认路径正确
        return save_path

    def item_completed(self, results, item, info):
        success_count = sum(1 for ok, _ in results if ok)
        fail_count = len(results) - success_count
        decoded_keyword = unquote(item['keyword'])
        print(f"📊 话题「{decoded_keyword}」图片下载结果：成功{success_count}张，失败{fail_count}张")
        return item


class MyVideoPipeline(FilesPipeline):
    def get_media_requests(self, item, info):
        if item['weibo']['video_url']:
            yield scrapy.Request(item['weibo']['video_url'],
                                 meta={'item': item})

    def file_path(self, request, response=None, info=None):
        item = request.meta['item']
        keyword = unquote(item['keyword'])  # 解码关键词为中文
        base_dir = f'结果文件{os.sep}{keyword}{os.sep}videos'
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        file_path = f'{base_dir}{os.sep}{item["weibo"]["id"]}.mp4'
        return file_path


class MongoPipeline(object):
    def open_spider(self, spider):
        try:
            from pymongo import MongoClient
            self.client = MongoClient(settings.get('MONGO_URI'))
            self.db = self.client['weibo']
            self.collection = self.db['weibo']
        except ModuleNotFoundError:
            spider.pymongo_error = True

    def process_item(self, item, spider):
        try:
            import pymongo
            new_item = copy.deepcopy(item)
            if not self.collection.find_one({'id': new_item['weibo']['id']}):
                self.collection.insert_one(dict(new_item['weibo']))
            else:
                self.collection.update_one({'id': new_item['weibo']['id']},
                                           {'$set': dict(new_item['weibo'])})
        except pymongo.errors.ServerSelectionTimeoutError:
            spider.mongo_error = True

    def close_spider(self, spider):
        try:
            self.client.close()
        except AttributeError:
            pass


class MysqlPipeline(object):
    def __init__(self):
        self.db = None
        self.cursor = None
        self.today_db = datetime.now().strftime('weibo_%Y_%m_%d')  # 当天日期数据库名

    def clean_topic_name(self, topic):
        """清洗话题名称为合法MySQL表名"""
        clean_name = re.sub(r'[#@!$%^&*(){}[\];:"\'<>,.?\\/]', '_', topic).strip('_')
        clean_name = clean_name[:50] if clean_name else 'default_topic'
        return clean_name

    def create_date_database(self, mysql_config):
        """创建当天的日期数据库（若不存在）"""
        try:
            server_config = mysql_config.copy()
            server_config.pop('db', None)  # 不指定具体数据库，仅连接服务器
            db_server = pymysql.connect(**server_config)
            cursor_server = db_server.cursor()

            sql = f"""CREATE DATABASE IF NOT EXISTS `{self.today_db}` 
                      DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"""
            cursor_server.execute(sql)
            print(f"✅ 日期数据库`{self.today_db}`创建成功（或已存在）")

            cursor_server.close()
            db_server.close()
        except Exception as e:
            print(f"❌ 创建日期数据库失败：{e}")
            raise

    def create_topic_table(self, table_name):
        """创建单个话题的表（若不存在）"""
        sql = f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                id varchar(20) NOT NULL,
                bid varchar(12) NOT NULL,
                user_id varchar(20),
                screen_name varchar(30),
                text TEXT NOT NULL,
                article_url varchar(100),
                topics varchar(500),
                at_users varchar(1000),
                pics varchar(3000),
                video_url varchar(1000),
                location varchar(100),
                created_at DATETIME,
                source varchar(30),
                attitudes_count INT,
                comments_count INT,
                reposts_count INT,
                retweet_id varchar(20),
                ip varchar(100),
                user_authentication varchar(100),
                vip_type varchar(50),
                vip_level INT,
                PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.cursor.execute(sql)
        print(f"✅ 话题表`{table_name}`创建成功（或已存在）")

    def open_spider(self, spider):
        """初始化数据库连接，创建日期数据库"""
        try:
            from scrapy.utils.project import get_project_settings
            settings = get_project_settings()
            mysql_config = {
                'host': settings.get('MYSQL_HOST', 'localhost'),
                'port': settings.get('MYSQL_PORT', 3306),
                'user': settings.get('MYSQL_USER', 'root'),
                'password': settings.get('MYSQL_PASSWORD', '123456'),
                'charset': 'utf8mb4',
                'connect_timeout': 10
            }

            # 1. 创建当天的日期数据库
            self.create_date_database(mysql_config)

            # 2. 连接日期数据库
            mysql_config['db'] = self.today_db
            self.db = pymysql.connect(**mysql_config)
            self.cursor = self.db.cursor()
            print(f"✅ MySQL日期数据库`{self.today_db}`连接成功")

        except ImportError:
            spider.pymysql_error = True
            print("❌ 未安装pymysql，请执行：pip install pymysql")
        except pymysql.OperationalError as e:
            spider.mysql_error = True
            print(f"❌ MySQL连接失败：{e}")

    def process_item(self, item, spider):
        if not self.db or not self.cursor:
            return item

        # 1. 清洗并生成话题表名
        raw_topic = unquote(item['keyword'])
        clean_topic = self.clean_topic_name(raw_topic)
        topic_table_name = clean_topic

        # 2. 确保话题表存在
        self.create_topic_table(topic_table_name)

        # 3. 插入/更新数据
        data = dict(item['weibo'])
        data['pics'] = ','.join(data['pics'])
        keys = ', '.join([f'`{k}`' for k in data.keys()])
        values = ', '.join(['%s'] * len(data))

        sql = f"""
            INSERT INTO `{topic_table_name}` ({keys}) 
            VALUES ({values}) 
            ON DUPLICATE KEY UPDATE 
            {', '.join([f'`{k}` = %s' for k in data.keys()])}
        """
        try:
            self.cursor.execute(sql, tuple(data.values()) * 2)
            self.db.commit()
            print(f"✅ 成功存储微博（库：{self.today_db}，表：{topic_table_name}，ID：{data['id']}）")
        except Exception as e:
            self.db.rollback()
            print(f"❌ 数据存储失败（库：{self.today_db}，表：{topic_table_name}，ID：{data.get('id', '未知')}）：{e}")
        return item

    def close_spider(self, spider):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
            print(f"✅ MySQL日期数据库`{self.today_db}`连接已关闭")


class DuplicatesPipeline(object):
    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        if item['weibo']['id'] in self.ids_seen:
            raise DropItem("过滤重复微博: %s" % item)
        else:
            self.ids_seen.add(item['weibo']['id'])
            return item
