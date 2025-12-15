from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
import random
import json
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class StockCrawler:
    def __init__(self):
        self.driver = webdriver.Chrome()  # 确保已安装Chrome驱动
        self.base_url = "https://quote.eastmoney.com/center/gridlist.html#"
        self.search_url = "https://so.eastmoney.com/web/s?keyword={}"
        # 持久化 HTTP 会话（自动重试 + 常用请求头）
        self.session = requests.Session()
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        
    def init_driver(self):
        """初始化浏览器并访问主页"""
        self.driver.get(self.base_url)
        print("等待广告加载并尝试关闭...")
        time.sleep(2)  # 等待广告加载
        
        # 尝试查找并点击广告关闭按钮
        try:
            # 通过图片元素定位关闭按钮
            close_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='ic_close.png']"))
            )
            
            # 获取按钮位置并点击
            self.driver.execute_script("arguments[0].click();", close_button)
            print("成功点击广告关闭按钮")
            
        except TimeoutException:
            print("未找到广告关闭按钮，尝试继续执行...")
            
        # 等待一会儿确保广告消失
        time.sleep(2)
        
    def switch_board(self, board_name):
        """切换到指定板块"""
        try:
            # 先等待元素存在
            link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, board_name))
            )
            
            # 确保元素可见和可点击
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, board_name))
            )
            
            # 尝试使用JavaScript点击元素
            try:
                self.driver.execute_script("arguments[0].click();", link)
            except Exception as e:
                print(f"JavaScript点击失败，尝试常规点击: {str(e)}")
                link.click()
                
            time.sleep(2)  # 等待页面加载
            return True
        except TimeoutException:
            print(f"无法找到或点击板块: {board_name}")
            return False
        except Exception as e:
            print(f"切换板块时出错: {str(e)}")
            return False
            
    def get_stock_list(self):
        """获取当前页面的股票列表信息"""
        try:
            wait_time = 20
            print("等待股票数据加载...")
            
            # 使用准确的CSS选择器路径定位表格
            table_selector = "div.main div.mainlc.scf div#mainc div.pagehsj div.quotetable table"
            table = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, table_selector))
            )
            
            # 等待表格中有数据行
            WebDriverWait(self.driver, wait_time).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, f"{table_selector} tbody tr")) > 0
            )
            
            # 获取表头
            headers = []
            header_rows = table.find_elements(By.CSS_SELECTOR, "thead tr th")
            for th in header_rows:
                # 直接获取th标签的文本内容（排除子元素的文本）
                script = """
                    var el = arguments[0];
                    var text = '';
                    for (var i = 0; i < el.childNodes.length; i++) {
                        if (el.childNodes[i].nodeType === 3) {  // Text node
                            text += el.childNodes[i].textContent;
                        }
                    }
                    return text.trim();
                """
                header_text = self.driver.execute_script(script, th)
                if not header_text:  # 如果没有直接文本，则使用完整文本
                    header_text = th.text.strip()
                headers.append(header_text)
            
            print("提取到的列名:", headers)
            
            # 获取股票数据
            stocks = []
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            print(f"找到 {len(rows)} 行数据")
            
            for row in rows:
                stock_data = {}
                cells = row.find_elements(By.TAG_NAME, "td")
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        column_name = headers[i]
                        value = ""
                        
                        if column_name in ["代码", "名称"]:
                            # 对于代码和名称列，获取a标签的文本
                            links = cell.find_elements(By.TAG_NAME, "a")
                            if links:
                                value = links[0].text.strip()
                                if not value and column_name == "名称":
                                    value = links[0].get_attribute("title")
                        elif column_name == "相关链接":
                            # 跳过相关链接列
                            continue
                        elif column_name == "加自选":
                            # 跳过加自选列
                            continue
                        else:
                            # 对于其他列，查找span标签的文本
                            spans = cell.find_elements(By.TAG_NAME, "span")
                            if spans:
                                value = spans[0].text.strip()
                            else:
                                value = cell.text.strip()
                        
                        stock_data[column_name] = value
                        
                        stock_data[headers[i]] = value
                
                if any(stock_data.values()):  # 只添加非空的数据行
                    stocks.append(stock_data)
            
            if not stocks:
                print("警告：未获取到任何股票数据")
            else:
                print(f"成功获取到 {len(stocks)} 条股票数据")
                print("数据示例:", stocks[0])
                
            return stocks
            
        except TimeoutException as e:
            print(f"获取股票列表超时: {str(e)}")
            return []
        except Exception as e:
            print(f"获取股票数据时出错: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误详情: {str(e)}")
            return []

    def get_stock_k_line_data(self, stock_code, beg='19000101', end='20500101', klt=101, fqt=1):
        """使用 push2his 接口获取单只股票的历史K线数据（持久 Session、Referer 预热、JSONP 回退）。"""
        from typing import List
        try:
            session = self.session
            QUERY_URL = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'

            # 生成东方财富专用的secid
            # if stock_code[:3] == '000':   # 沪市指数
            #     secid = f'1.{stock_code}'
            # elif stock_code[:3] == '399': # 深证指数
            #     secid = f'0.{stock_code}'
            # elif stock_code[0] != '6':  # 沪市股票
            #     secid = f'0.{stock_code}'
            # else:
            #     secid = f'1.{stock_code}' # 深市股票
            secid = stock_code.split('/')[-1]
            stock_code = secid.split('.')[-1]
            # 预热统一报价页，获取必要 Cookie
            try:
                session.get(f'https://quote.eastmoney.com/unify/r/{secid}', timeout=(5, 15))
            except Exception:
                pass

            kline_fields = {
                'f51': '日期', 'f52': '开盘', 'f53': '收盘', 'f54': '最高', 'f55': '最低',
                'f56': '成交量', 'f57': '成交额', 'f58': '振幅', 'f59': '涨跌幅', 'f60': '涨跌额', 'f61': '换手率',
            }
            fields2 = ",".join(list(kline_fields.keys()))

            req_headers = session.headers.copy()
            req_headers.update({
                'Referer': f'https://quote.eastmoney.com/unify/r/{secid}',
                'Origin': 'https://quote.eastmoney.com',
            })

            params = {
                'secid': secid,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': fields2,
                'klt': str(klt),
                'fqt': str(fqt),
                'beg': beg,
                'end': end,
                'smplmt': '460',
                'lmt': '1000000',
                '_': str(int(time.time()*1000)),
            }
            code = secid.split('.')[-1]

            # 先尝试 JSON；失败则 JSONP 回退
            data_json = None
            resp = session.get(QUERY_URL, headers=req_headers, params=params, timeout=(5, 30))
            try:
                data_json = resp.json()
            except Exception:
                cb = f"jQuery{int(time.time()*1000)}"
                params_cb = dict(params)
                params_cb['cb'] = cb
                params_cb['_'] = str(int(time.time()*1000) + 1)
                resp2 = session.get(QUERY_URL, headers=req_headers, params=params_cb, timeout=(5, 30))
                raw = resp2.text
                prefix = f"{cb}("
                suffix = ")"
                if raw.startswith(prefix) and raw.endswith(suffix):
                    inner = raw[len(prefix):-len(suffix)]
                    data_json = json.loads(inner)
            data_list = []
            klines: List[str] = data_json.get('data', {}).get('klines', []) if data_json else []
            if not klines:
                print(f"未获取到股票{stock_code}的K线数据")
                return data_list
            name = data_json['data'].get('name', '') if data_json else ''
            rows = [kline.split(',') for kline in klines]
            for row in rows:
                # 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
                if len(row) < 11:
                    continue
                time_, open_, close, high, low, vol, quota, mm, change, range_, tun = row
                line_str = f'{open_},{close},{high},{low},{vol},{quota},{mm},{change},{range_},{tun}'
                data_list.append({
                    '代码': code,
                    '名称': name,
                    '日期': time_,
                    '开盘': open_,
                    '收盘': close,
                    '最高': high,
                    '最低': low,
                    '成交量': vol,
                    '成交额': quota,
                    '振幅': mm,
                    '涨跌幅': change,
                    '涨跌额': range_,
                    '换手率': tun
                })
                # data_list.append({'code': code, 'name': name, 'time': time, 'info': line_str})
            print(f"股票{stock_code}日K线数据(最新):", data_list[-1] if data_list else None)
            df_klines = pd.DataFrame(data_list)
            df_klines.to_csv(f"{stock_code}_kline_data.csv", index=False, encoding='utf-8-sig')
            print(f"已保存股票{stock_code}的K线数据到文件")
            return data_list
        except Exception as e:
            print(f"get_k_history_data error----------------------- {str(e)}")
            return []

    def close(self):
        """关闭浏览器"""
        self.driver.quit()

def main():
    crawler = StockCrawler()
    try:
        # 初始化浏览器
        crawler.init_driver()
        
        # 测试不同板块的切换和数据获取
        # boards = ["沪深京A股", "上证A股", "深证A股", "北证A股", "新股", 
        #          "创业板", "科创板", "沪股通(港>沪)", "深股通(港>深)", "B股"]
        # boards = ["上证A股", "深证A股", "北证A股"]
        
        # for board in boards:
        #     if crawler.switch_board(board):
        #         print(f"\n获取{board}数据:")
        #         stocks = crawler.get_stock_list()
        #         print(f"获取到 {len(stocks)} 条股票数据")
        #         df = pd.DataFrame(stocks)
        #         safe_filename = re.sub(r'[<>:"/\\|?*]', '_', board)  # 将非法字符替换为下划线
        #         df.to_csv(f"{safe_filename}_stocks.csv", index=False, encoding='utf-8-sig')
        #         # 尝试获取第一个股票的K线数据
        #         if stocks:
        #             for stock in stocks:
        #                 stock_code = stock.get("代码", "")
        #                 if stock_code:
        #                     print(f"尝试获取股票 {stock_code} 的K线数据")
        #                     crawler.get_stock_k_line_data(stock_code)

        #         time.sleep(random.uniform(1, 3))  # 避免频繁请求，随机等待1-3秒
        data = pd.read_csv("stock_data_all_pages.csv", encoding='utf-8-sig')
        print(f"共读取到 {len(data)} 条股票数据")
        #便利数据
        for stock in data.itertuples(index=False):
            stock_code = stock.相关链接
            print(f"处理股票 {stock_code}")
            crawler.get_stock_k_line_data(stock_code)
            #每爬取一个股票，随机等待5~13秒
            time.sleep(random.uniform(5, 13))
    finally:
        crawler.close()

if __name__ == "__main__":
    main()
