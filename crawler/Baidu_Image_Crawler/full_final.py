import json
import os
import re
# from description import generate_image_description
from description import generate_image_description
from web import spider_from_web
# from spider_web import spider_from_web
from langchain_community.chat_models.tongyi import ChatTongyi
# from description import generate_image_description
# from spider_web1 import spider_from_web
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi
from get_path import process_images
import pandas as pd
import re
from openai import OpenAI
from zhengli import zhengli

# 读取JSON文件
# with open('D:/projects/baidu_downloader/苏州_2days_plan.json', 'r', encoding='utf-8') as file:
#     data = json.load(file)

# spot_list = []
# for i in range(len(data['spots'])):
#     spot = data['spots'][i]
#     spot_list.append(spot['name'])

# food_list = data['Foods']

# apikey = 'sk-c61a24683161407fbf94b80676424cfc'
# base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'

# os.environ["DASHSCOPE_API_KEY"] = apikey
# os.environ["DASHSCOPE_API_BASE"] = base_url

def get_num(text):
    numbers = re.findall(r'\d+\.?\d*', text)
    print(numbers)  # ['9.5']

    # 如果只需要第一个数字
    if numbers:
        result = float(numbers[0])  # 转换为浮点数
        print(result)  # 9.5
    return result

def web_image_download_from_list(cate, item_list, num=3):
    folder_path = f"D:/projects/baidu_downloader/web_spider_image/{cate}"
    try:
        os.mkdir(folder_path)
        print(f"文件夹创建成功: {folder_path}")
    except FileExistsError:
        print(f"文件夹已存在: {folder_path}")

    for item in item_list:
        keyword = item
        fd_path = f"{folder_path}/{keyword}"
        spider_from_web(folder_path=fd_path, keyword=keyword, num=num)
    
def web_image_download_full(num=3, spot_list=None, food_list=None):
    web_image_download_from_list(cate="spot", item_list=spot_list, num=num)
    web_image_download_from_list(cate="food", item_list=food_list, num=num)

def get_image_path():
    input_folder = "D:/projects/baidu_downloader/web_spider_image/spot"  
    df = process_images(input_folder)
    df.to_excel('D:/projects/baidu_downloader/web_spider_image/spot_info.xlsx', index=False)

    input_folder = "D:/projects/baidu_downloader/web_spider_image/food"  
    df = process_images(input_folder)
    df.to_excel('D:/projects/baidu_downloader/web_spider_image/food_info.xlsx', index=False)

def describe_images():
    df_spot = pd.read_excel('D:/projects/baidu_downloader/web_spider_image/spot_info.xlsx')
    df_food = pd.read_excel('D:/projects/baidu_downloader/web_spider_image/food_info.xlsx')
    for i in range(df_spot.shape[0]):
        des = generate_image_description(image_path=df_spot.loc[i].new_path)
        df_spot.loc[i, 'description'] = des
    for i in range(df_spot.shape[0]):
        key_word = df_spot.loc[i, 'keyword']
        des = df_spot.loc[i, 'description']
        prompt = f"景点名称：{key_word}。景点描述：{des}。请你对景点名称和景点描述的相关性打分，格式：获得分数：X分"
        client = OpenAI(
            api_key="sk-c61a24683161407fbf94b80676424cfc",
            # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[{'role': 'user', 'content': prompt}]
        )
        num = get_num(completion.choices[0].message.content)
        df_spot.loc[i, 'relevance_score'] = num
    df_spot.to_excel("D:/projects/baidu_downloader/web_spider_image/spot_results.xlsx", index=False)

    for i in range(df_food.shape[0]):
        des = generate_image_description(image_path=df_food.loc[i].new_path)
        df_food.loc[i, 'description'] = des
    for i in range(df_food.shape[0]):
        key_word = df_food.loc[i, 'keyword']
        des = df_food.loc[i, 'description']
        prompt = f"美食名称：{key_word}。美食描述：{des}。请你对美食名称和美食描述的相关性打分，格式：获得分数：X分"
        client = OpenAI(
            api_key="sk-c61a24683161407fbf94b80676424cfc",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[{'role': 'user', 'content': prompt}]
        )
        num = get_num(completion.choices[0].message.content)
        df_food.loc[i, 'relevance_score'] = num
    df_food.to_excel("D:/projects/baidu_downloader/web_spider_image/food_results.xlsx", index=False)


def final_full_cycle(json_file_path, num=5):
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    spot_list = []
    for i in range(len(data['spots'])):
        spot = data['spots'][i]
        spot_list.append(spot['name'])

    food_list = data['foods']

    apikey = 'sk-c61a24683161407fbf94b80676424cfc'
    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'

    os.environ["DASHSCOPE_API_KEY"] = apikey
    os.environ["DASHSCOPE_API_BASE"] = base_url

    web_image_download_full(num=num, spot_list=spot_list, food_list=food_list)
    get_image_path()
    describe_images()
    zhengli(spot_list=spot_list, food_list=food_list)


def search_img(json_file_path, num=5):
    final_full_cycle(json_file_path=json_file_path, num=num)


if __name__ == "__main__":
    search_img(json_file_path='D:/projects/baidu_downloader/苏州_2days_plan.json')
    # with open('D:/projects/baidu_downloader/苏州_2days_plan.json', 'r', encoding='utf-8') as file:
    #     data = json.load(file)

    # spot_list = []
    # for i in range(len(data['spots'])):
    #     spot = data['spots'][i]
    #     spot_list.append(spot['name'])

    # food_list = data['foods']

    # zhengli(spot_list=spot_list, food_list=food_list)
    # web_image_download_full(num=5, spot_list=spot_list, food_list=food_list)
    # final_full_cycle(json_file_path='D:/projects/baidu_downloader/final/苏州_2days_plan(2).json')

