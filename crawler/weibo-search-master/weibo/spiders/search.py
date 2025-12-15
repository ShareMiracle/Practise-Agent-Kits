# -*- coding: utf-8 -*-
import os
import re
import sys
from datetime import datetime, timedelta
from urllib.parse import unquote

import requests
import scrapy
from scrapy.utils.project import get_project_settings

import weibo.utils.util as util
from scrapy.exceptions import CloseSpider
from weibo.items import WeiboItem


class SearchSpider(scrapy.Spider):
    name = 'search'
    allowed_domains = ['weibo.com']
    settings = get_project_settings()

    def __init__(self, keywords=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keyword_list = []
        # 从爬虫参数接收关键词（优先级最高）
        if keywords:
            self.keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
            print(f"📌 从爬虫参数读取到关键词：{self.keyword_list}")
        # 兼容原Settings配置（临时测试用）
        else:
            keyword_list = self.settings.get('KEYWORD_LIST', [])
            if not isinstance(keyword_list, list):
                if not os.path.isabs(keyword_list):
                    keyword_list = os.getcwd() + os.sep + keyword_list
                if not os.path.isfile(keyword_list):
                    sys.exit(f'❌ 不存在关键词文件：{keyword_list}')
                keyword_list = util.get_keyword_list(keyword_list)
            self.keyword_list = keyword_list
            print(f"📌 从Settings读取到关键词：{self.keyword_list}")

        # 关键词URL编码
        for i, keyword in enumerate(self.keyword_list):
            if len(keyword) > 2 and keyword[0] == '#' and keyword[-1] == '#':
                self.keyword_list[i] = '%23' + keyword[1:-1] + '%23'
            else:
                self.keyword_list[i] = requests.utils.quote(keyword, safe='')

        self.weibo_type = util.convert_weibo_type(self.settings.get('WEIBO_TYPE'))
        self.contain_type = util.convert_contain_type(self.settings.get('CONTAIN_TYPE'))
        self.regions = util.get_regions(self.settings.get('REGION'))
        self.base_url = 'https://s.weibo.com'
        self.start_date = self.settings.get('START_DATE', datetime.now().strftime('%Y-%m-%d'))
        self.end_date = self.settings.get('END_DATE', datetime.now().strftime('%Y-%m-%d'))

        if util.str_to_time(self.start_date) > util.str_to_time(self.end_date):
            sys.exit('❌ settings配置错误：START_DATE应早于或等于END_DATE')

        self.further_threshold = self.settings.get('FURTHER_THRESHOLD', 46)
        self.limit_result = self.settings.get('LIMIT_RESULT', 0)
        self.result_count = 0
        self.mongo_error = False
        self.pymongo_error = False
        self.mysql_error = False
        self.pymysql_error = False
        self.sqlite3_error = False

        self.max_items_per_keyword = self.settings.get('MAX_ITEMS_PER_KEYWORD', 10)
        self.item_counter = {keyword: 0 for keyword in self.keyword_list}
        print(f"✅ 爬虫初始化完成：关键词{len(self.keyword_list)}个，每个关键词限爬{self.max_items_per_keyword}条")

    def check_limit(self):
        if self.limit_result > 0 and self.result_count >= self.limit_result:
            print(f'🔚 已达总爬取限制：{self.limit_result}条')
            raise CloseSpider('总条数限制')
        return False

    def check_keyword_limit(self, keyword):
        if self.item_counter[keyword] >= self.max_items_per_keyword:
            self.logger.info(f'🔚 关键词「{keyword}」已达{self.max_items_per_keyword}条限制')
            return True
        return False

    async def start(self):
        if not self.keyword_list:
            print('❌ 无有效关键词，爬虫关闭')
            return

        start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d') + timedelta(days=1)
        start_str = start_date.strftime('%Y-%m-%d') + '-0'
        end_str = end_date.strftime('%Y-%m-%d') + '-0'

        for keyword in self.keyword_list:
            if self.check_keyword_limit(keyword):
                continue

            if not self.settings.get('REGION') or '全部' in self.settings.get('REGION'):
                base_url = f'https://s.weibo.com/weibo?q={keyword}'
                url = f'{base_url}{self.weibo_type}{self.contain_type}&timescope=custom:{start_str}:{end_str}'
                print(f"🚀 发起请求：{url}")
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta={'base_url': base_url, 'keyword': keyword},
                    dont_filter=True
                )
            else:
                for region in self.regions.values():
                    base_url = f'https://s.weibo.com/weibo?q={keyword}&region=custom:{region["code"]}:1000'
                    url = f'{base_url}{self.weibo_type}{self.contain_type}&timescope=custom:{start_str}:{end_str}'
                    print(f"🚀 发起请求（地区：{region['name']}）：{url}")
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse,
                        meta={'base_url': base_url, 'keyword': keyword, 'province': region},
                        dont_filter=True
                    )

    def check_environment(self):
        if self.pymongo_error:
            print('❌ 请安装pymongo：pip install pymongo')
            raise CloseSpider()
        if self.mongo_error:
            print('❌ 请安装/启动MongoDB')
            raise CloseSpider()
        if self.pymysql_error:
            print('❌ 请安装pymysql：pip install pymysql')
            raise CloseSpider()
        if self.mysql_error:
            print('❌ 请安装/配置MySQL')
            raise CloseSpider()
        if self.sqlite3_error:
            print('❌ 请安装sqlite3：pip install sqlite3')
            raise CloseSpider()

    def parse(self, response):
        base_url = response.meta.get('base_url')
        keyword = response.meta.get('keyword')
        province = response.meta.get('province')

        print(f"📥 接收响应：{response.url}（状态码：{response.status}）")

        if self.check_keyword_limit(keyword):
            return

        is_empty = response.xpath('//div[@class="card card-no-result s-pt20b40"]')
        page_count = len(response.xpath('//ul[@class="s-scroll"]/li'))

        if is_empty:
            print(f"📭 关键词「{keyword}」当前页面无结果")
            return
        elif page_count < self.further_threshold:
            for weibo in self.parse_weibo(response):
                self.check_environment()
                if self.check_limit():
                    return
                yield weibo
            if not self.check_keyword_limit(keyword):
                next_url = response.xpath('//a[@class="next"]/@href').extract_first()
                if next_url:
                    next_url = self.base_url + next_url
                    print(f"🚀 发起下一页请求：{next_url}")
                    yield scrapy.Request(
                        url=next_url,
                        callback=self.parse_page,
                        meta={'keyword': keyword},
                        dont_filter=True
                    )
        else:
            start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
            while start_date <= end_date:
                if self.check_keyword_limit(keyword):
                    break
                start_str = start_date.strftime('%Y-%m-%d') + '-0'
                start_date += timedelta(days=1)
                end_str = start_date.strftime('%Y-%m-%d') + '-0'
                url = f'{base_url}{self.weibo_type}{self.contain_type}&timescope=custom:{start_str}:{end_str}&page=1'
                print(f"🚀 按天拆分请求：{url}")
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_by_day,
                    meta={'base_url': base_url, 'keyword': keyword, 'province': province, 'date': start_str[:-2]},
                    dont_filter=True
                )

    def parse_by_day(self, response):
        base_url = response.meta.get('base_url')
        keyword = response.meta.get('keyword')
        province = response.meta.get('province')

        if self.check_keyword_limit(keyword):
            return

        is_empty = response.xpath('//div[@class="card card-no-result s-pt20b40"]')
        date = response.meta.get('date')
        page_count = len(response.xpath('//ul[@class="s-scroll"]/li'))

        print(f"📥 接收按天响应（日期：{date}）：{response.url}")

        if is_empty:
            print(f"📭 关键词「{keyword}」{date}无结果")
            return
        elif page_count < self.further_threshold:
            for weibo in self.parse_weibo(response):
                self.check_environment()
                if self.check_limit():
                    return
                yield weibo
            if not self.check_keyword_limit(keyword):
                next_url = response.xpath('//a[@class="next"]/@href').extract_first()
                if next_url:
                    next_url = self.base_url + next_url
                    yield scrapy.Request(
                        url=next_url,
                        callback=self.parse_page,
                        meta={'keyword': keyword},
                        dont_filter=True
                    )
        else:
            start_date_str = date + '-0'
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d-%H')
            for i in range(1, 25):
                if self.check_keyword_limit(keyword):
                    break
                start_str = start_date.strftime('%Y-%m-%d-X%H').replace('X0', 'X').replace('X', '')
                start_date += timedelta(hours=1)
                end_str = start_date.strftime('%Y-%m-%d-X%H').replace('X0', 'X').replace('X', '')
                url = f'{base_url}{self.weibo_type}{self.contain_type}&timescope=custom:{start_str}:{end_str}&page=1'
                print(f"🚀 按小时拆分请求：{url}")
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_by_hour_province if province else self.parse_by_hour,
                    meta={'base_url': base_url, 'keyword': keyword, 'province': province, 'start_time': start_str,
                          'end_time': end_str},
                    dont_filter=True
                )

    def parse_by_hour(self, response):
        keyword = response.meta.get('keyword')
        if self.check_keyword_limit(keyword):
            return

        is_empty = response.xpath('//div[@class="card card-no-result s-pt20b40"]')
        if is_empty:
            print(f"📭 关键词「{keyword}」当前小时无结果")
            return
        else:
            for weibo in self.parse_weibo(response):
                self.check_environment()
                yield weibo
            if not self.check_keyword_limit(keyword):
                next_url = response.xpath('//a[@class="next"]/@href').extract_first()
                if next_url:
                    next_url = self.base_url + next_url
                    yield scrapy.Request(
                        url=next_url,
                        callback=self.parse_page,
                        meta={'keyword': keyword},
                        dont_filter=True
                    )

    def parse_by_hour_province(self, response):
        keyword = response.meta.get('keyword')
        if self.check_keyword_limit(keyword):
            return

        is_empty = response.xpath('//div[@class="card card-no-result s-pt20b40"]')
        start_time = response.meta.get('start_time')
        end_time = response.meta.get('end_time')
        province = response.meta.get('province')
        page_count = len(response.xpath('//ul[@class="s-scroll"]/li'))

        if is_empty:
            print(f"📭 关键词「{keyword}」{start_time[:10]} {start_time[11:]}无结果")
            return
        elif page_count < self.further_threshold:
            for weibo in self.parse_weibo(response):
                self.check_environment()
                yield weibo
            if not self.check_keyword_limit(keyword):
                next_url = response.xpath('//a[@class="next"]/@href').extract_first()
                if next_url:
                    next_url = self.base_url + next_url
                    yield scrapy.Request(
                        url=next_url,
                        callback=self.parse_page,
                        meta={'keyword': keyword},
                        dont_filter=True
                    )
        else:
            for city in province['city'].values():
                if self.check_keyword_limit(keyword):
                    break
                url = f'https://s.weibo.com/weibo?q={keyword}&region=custom:{province["code"]}:{city}'
                url += f'{self.weibo_type}{self.contain_type}&timescope=custom:{start_time}:{end_time}&page=1'
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_page,
                    meta={'keyword': keyword, 'start_time': start_time, 'end_time': end_time, 'province': province,
                          'city': city},
                    dont_filter=True
                )

    def parse_page(self, response):
        keyword = response.meta.get('keyword')
        if self.check_keyword_limit(keyword):
            return

        is_empty = response.xpath('//div[@class="card card-no-result s-pt20b40"]')
        if is_empty:
            print(f"📭 关键词「{keyword}」当前分页无结果")
            return
        else:
            for weibo in self.parse_weibo(response):
                self.check_environment()
                if self.check_limit():
                    return
                yield weibo
            if not self.check_keyword_limit(keyword):
                next_url = response.xpath('//a[@class="next"]/@href').extract_first()
                if next_url:
                    next_url = self.base_url + next_url
                    yield scrapy.Request(
                        url=next_url,
                        callback=self.parse_page,
                        meta={'keyword': keyword},
                        dont_filter=True
                    )

    def get_ip(self, bid):
        url = f"https://weibo.com/ajax/statuses/show?id={bid}&locale=zh-CN"
        response = requests.get(url, headers=self.settings.get('DEFAULT_REQUEST_HEADERS'))
        if response.status_code != 200:
            return ""
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            return ""
        ip_str = data.get("region_name", "")
        if ip_str:
            ip_str = ip_str.split()[-1]
        return ip_str

    def get_article_url(self, selector):
        article_url = ''
        text = selector.xpath('string(.)').extract_first().replace('\u200b', '').replace('\ue627', '').replace('\n',
                                                                                                               '').replace(
            ' ', '')
        if text.startswith('发布了头条文章'):
            urls = selector.xpath('.//a')
            for url in urls:
                if url.xpath('i[@class="wbicon"]/text()').extract_first() == 'O':
                    if url.xpath('@href').extract_first() and url.xpath('@href').extract_first().startswith(
                            'http://t.cn'):
                        article_url = url.xpath('@href').extract_first()
                    break
        return article_url

    def get_location(self, selector):
        a_list = selector.xpath('.//a')
        location = ''
        for a in a_list:
            if a.xpath('./i[@class="wbicon"]') and a.xpath('./i[@class="wbicon"]/text()').extract_first() == '2':
                location = a.xpath('string(.)').extract_first()[1:]
                break
        return location

    def get_at_users(self, selector):
        a_list = selector.xpath('.//a')
        at_users = ''
        at_list = []
        for a in a_list:
            if len(unquote(a.xpath('@href').extract_first())) > 14 and len(a.xpath('string(.)').extract_first()) > 1:
                if unquote(a.xpath('@href').extract_first())[14:] == a.xpath('string(.)').extract_first()[1:]:
                    at_user = a.xpath('string(.)').extract_first()[1:]
                    if at_user not in at_list:
                        at_list.append(at_user)
        if at_list:
            at_users = ','.join(at_list)
        return at_users

    def get_topics(self, selector):
        a_list = selector.xpath('.//a')
        topics = ''
        topic_list = []
        for a in a_list:
            text = a.xpath('string(.)').extract_first()
            if len(text) > 2 and text[0] == '#' and text[-1] == '#':
                if text[1:-1] not in topic_list:
                    topic_list.append(text[1:-1])
        if topic_list:
            topics = ','.join(topic_list)
        return topics

    def get_vip(self, selector):
        vip_type = "非会员"
        vip_level = 0
        vip_container = selector.xpath('.//div[@class="user_vip_icon_container"]')
        if vip_container:
            svvip_img = vip_container.xpath('.//img[contains(@src, "svvip_")]')
            if svvip_img:
                vip_type = "超级会员"
                src = svvip_img.xpath('@src').extract_first()
                level_match = re.search(r'svvip_(\d+)\.png', src)
                if level_match:
                    vip_level = int(level_match.group(1))
            else:
                vip_img = vip_container.xpath('.//img[contains(@src, "vip_")]')
                if vip_img:
                    vip_type = "会员"
                    src = vip_img.xpath('@src').extract_first()
                    level_match = re.search(r'vip_(\d+)\.png', src)
                    if level_match:
                        vip_level = int(level_match.group(1))
        return vip_type, vip_level

    def parse_weibo(self, response):
        keyword = response.meta.get('keyword')
        for sel in response.xpath("//div[@class='card-wrap']"):
            if self.check_keyword_limit(keyword):
                return
            if self.check_limit():
                return

            info = sel.xpath("div[@class='card']/div[@class='card-feed']/div[@class='content']/div[@class='info']")
            if info:
                weibo = WeiboItem()
                weibo['id'] = sel.xpath('@mid').extract_first()
                bid = sel.xpath('.//div[@class="from"]/a[1]/@href').extract_first().split('/')[-1].split('?')[0]
                weibo['bid'] = bid
                weibo['user_id'] = info[0].xpath('div[2]/a/@href').extract_first().split('?')[0].split('/')[-1]
                weibo['screen_name'] = info[0].xpath('div[2]/a/@nick-name').extract_first()
                weibo['vip_type'], weibo['vip_level'] = self.get_vip(info[0])
                txt_sel = sel.xpath('.//p[@class="txt"]')[0]
                retweet_sel = sel.xpath('.//div[@class="card-comment"]')
                retweet_txt_sel = ''
                if retweet_sel and retweet_sel[0].xpath('.//p[@class="txt"]'):
                    retweet_txt_sel = retweet_sel[0].xpath('.//p[@class="txt"]')[0]
                content_full = sel.xpath('.//p[@node-type="feed_list_content_full"]')

                is_long_weibo = False
                is_long_retweet = False
                if content_full:
                    if not retweet_sel:
                        txt_sel = content_full[0]
                        is_long_weibo = True
                    elif len(content_full) == 2:
                        txt_sel = content_full[0]
                        retweet_txt_sel = content_full[1]
                        is_long_weibo = True
                        is_long_retweet = True
                    elif retweet_sel[0].xpath('.//p[@node-type="feed_list_content_full"]'):
                        retweet_txt_sel = retweet_sel[0].xpath('.//p[@node-type="feed_list_content_full"]')[0]
                        is_long_retweet = True
                    else:
                        txt_sel = content_full[0]
                        is_long_weibo = True
                weibo['text'] = txt_sel.xpath('string(.)').extract_first().replace('\u200b', '').replace('\ue627', '')
                weibo['article_url'] = self.get_article_url(txt_sel)
                weibo['location'] = self.get_location(txt_sel)
                if weibo['location']:
                    weibo['text'] = weibo['text'].replace('2' + weibo['location'], '')
                weibo['text'] = weibo['text'][2:].replace(' ', '')
                if is_long_weibo:
                    weibo['text'] = weibo['text'][:-4]
                weibo['at_users'] = self.get_at_users(txt_sel)
                weibo['topics'] = self.get_topics(txt_sel)
                reposts_count = sel.xpath('.//a[@action-type="feed_list_forward"]/text()').extract()
                reposts_count = "".join(reposts_count)
                try:
                    reposts_count = re.findall(r'\d+.*', reposts_count)
                except TypeError:
                    print("❌ 无法解析转发按钮：可能是Cookie失效或页面布局变更")
                    raise CloseSpider()
                weibo['reposts_count'] = reposts_count[0] if reposts_count else '0'
                comments_count = sel.xpath('.//a[@action-type="feed_list_comment"]/text()').extract_first()
                comments_count = re.findall(r'\d+.*', comments_count)
                weibo['comments_count'] = comments_count[0] if comments_count else '0'
                attitudes_count = sel.xpath('.//a[@action-type="feed_list_like"]/button/span[2]/text()').extract_first()
                attitudes_count = re.findall(r'\d+.*', attitudes_count)
                weibo['attitudes_count'] = attitudes_count[0] if attitudes_count else '0'
                created_at = \
                    sel.xpath('.//div[@class="from"]/a[1]/text()').extract_first().replace(' ', '').replace('\n',
                                                                                                            '').split(
                        '前')[0]
                weibo['created_at'] = util.standardize_date(created_at)
                source = sel.xpath('.//div[@class="from"]/a[2]/text()').extract_first()
                weibo['source'] = source if source else ''
                pics = ''
                is_exist_pic = sel.xpath('.//div[@class="media media-piclist"]')
                if is_exist_pic:
                    pics = is_exist_pic[0].xpath('ul[1]/li/img/@src').extract()
                    pics = [pic[8:] for pic in pics]
                    pics = [re.sub(r'/.*?/', '/large/', pic, 1) for pic in pics]
                    pics = ['https://' + pic for pic in pics]
                video_url = ''
                is_exist_video = sel.xpath('.//div[@class="thumbnail"]//video-player').extract_first()
                if is_exist_video:
                    video_url = re.findall(r'src:\'(.*?)\'', is_exist_video)[0]
                    video_url = video_url.replace('&amp;', '&')
                    video_url = 'http:' + video_url
                if not retweet_sel:
                    weibo['pics'] = pics
                    weibo['video_url'] = video_url
                else:
                    weibo['pics'] = ''
                    weibo['video_url'] = ''
                weibo['retweet_id'] = ''
                if retweet_sel and retweet_sel[0].xpath('.//div[@node-type="feed_list_forwardContent"]/a[1]'):
                    retweet = WeiboItem()
                    retweet['id'] = retweet_sel[0].xpath(
                        './/a[@action-type="feed_list_like"]/@action-data').extract_first()[4:]
                    retweet['bid'] = \
                        retweet_sel[0].xpath('.//p[@class="from"]/a/@href').extract_first().split('/')[-1].split('?')[0]
                    info = retweet_sel[0].xpath('.//div[@node-type="feed_list_forwardContent"]/a[1]')[0]
                    retweet['user_id'] = info.xpath('@href').extract_first().split('/')[-1]
                    retweet['screen_name'] = info.xpath('@nick-name').extract_first()
                    retweet['vip_type'], retweet['vip_level'] = self.get_vip(info)
                    retweet['text'] = retweet_txt_sel.xpath('string(.)').extract_first().replace('\u200b', '').replace(
                        '\ue627', '')
                    retweet['article_url'] = self.get_article_url(retweet_txt_sel)
                    retweet['location'] = self.get_location(retweet_txt_sel)
                    if retweet['location']:
                        retweet['text'] = retweet['text'].replace('2' + retweet['location'], '')
                    retweet['text'] = retweet['text'][2:].replace(' ', '')
                    if is_long_retweet:
                        retweet['text'] = retweet['text'][:-4]
                    retweet['at_users'] = self.get_at_users(retweet_txt_sel)
                    retweet['topics'] = self.get_topics(retweet_txt_sel)
                    reposts_count = retweet_sel[0].xpath('.//ul[@class="act s-fr"]/li[1]/a[1]/text()').extract_first()
                    reposts_count = re.findall(r'\d+.*', reposts_count)
                    retweet['reposts_count'] = reposts_count[0] if reposts_count else '0'
                    comments_count = retweet_sel[0].xpath('.//ul[@class="act s-fr"]/li[2]/a[1]/text()').extract_first()
                    comments_count = re.findall(r'\d+.*', comments_count)
                    retweet['comments_count'] = comments_count[0] if comments_count else '0'
                    attitudes_count = retweet_sel[0].xpath(
                        './/a[@class="woo-box-flex woo-box-alignCenter woo-box-justifyCenter"]//span[@class="woo-like-count"]/text()').extract_first()
                    attitudes_count = re.findall(r'\d+.*', attitudes_count)
                    retweet['attitudes_count'] = attitudes_count[0] if attitudes_count else '0'
                    created_at = \
                        retweet_sel[0].xpath('.//p[@class="from"]/a[1]/text()').extract_first().replace(' ',
                                                                                                        '').replace(
                            '\n', '').split('前')[0]
                    retweet['created_at'] = util.standardize_date(created_at)
                    source = retweet_sel[0].xpath('.//p[@class="from"]/a[2]/text()').extract_first()
                    retweet['source'] = source if source else ''
                    retweet['pics'] = pics
                    retweet['video_url'] = video_url
                    retweet['retweet_id'] = ''

                    self.result_count += 1
                    self.item_counter[keyword] += 1

                    yield {'weibo': retweet, 'keyword': keyword}
                    print(f"📝 爬取到转发微博（关键词：{keyword}，累计：{self.item_counter[keyword]}条）")

                    if self.check_keyword_limit(keyword):
                        return

                    weibo['retweet_id'] = retweet['id']
                weibo["ip"] = self.get_ip(bid)

                avator = sel.xpath("div[@class='card']/div[@class='card-feed']/div[@class='avator']")
                if avator:
                    user_auth = avator.xpath('.//svg/@id').extract_first()
                    if user_auth == 'woo_svg_vblue':
                        weibo['user_authentication'] = '蓝V'
                    elif user_auth == 'woo_svg_vyellow':
                        weibo['user_authentication'] = '黄V'
                    elif user_auth == 'woo_svg_vorange':
                        weibo['user_authentication'] = '红V'
                    elif user_auth == 'woo_svg_vgold':
                        weibo['user_authentication'] = '金V'
                    else:
                        weibo['user_authentication'] = '普通用户'

                self.result_count += 1
                self.item_counter[keyword] += 1

                yield {'weibo': weibo, 'keyword': keyword}
                print(f"📝 爬取到主微博（关键词：{keyword}，累计：{self.item_counter[keyword]}条）")

                if self.check_keyword_limit(keyword):
                    return
