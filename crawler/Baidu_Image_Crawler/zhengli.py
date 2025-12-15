import pandas as pd
import os
from PIL import Image

def zhengli_spot(spot_list):
    df_spot = pd.read_excel("D:/projects/baidu_downloader/web_spider_image/spot_results.xlsx")
    keyword_list = list(df_spot['keyword'].unique())

    idx_list = []
    for key_word in keyword_list:
        print(key_word)
        df_tmp = df_spot[df_spot['keyword']==key_word]
        max_index = df_tmp['relevance_score'].idxmax()
        idx_list.append(max_index)

    df_results = df_spot.iloc[idx_list, :]

    df_final_res = df_results[df_results['keyword'].isin(spot_list)]
    df_final_res.reset_index(drop=True, inplace=True)

    os.makedirs("D:/projects/baidu_downloader/web_spider_image/new_cengci/spot", exist_ok=True)
    for i in range(df_final_res.shape[0]):
        base_path = "D:/projects/baidu_downloader/web_spider_image/new_cengci/spot"
        target_dir = os.path.join(base_path, df_final_res.loc[i, 'keyword'])
        os.makedirs(target_dir, exist_ok=True)

        target_image_path = os.path.join(target_dir, "1.jpg")
        source_image_path = df_final_res.loc[i, 'new_path']
        img = Image.open(source_image_path)
        rgb_image = img.convert('RGB')
        rgb_image.save(target_image_path)  
        rgb_image.close()

def zhengli_food(food_list):
    df_spot = pd.read_excel("D:/projects/baidu_downloader/web_spider_image/food_results.xlsx")
    keyword_list = list(df_spot['keyword'].unique())

    idx_list = []
    for key_word in keyword_list:
        print(key_word)
        df_tmp = df_spot[df_spot['keyword']==key_word]
        max_index = df_tmp['relevance_score'].idxmax()
        idx_list.append(max_index)

    df_results = df_spot.iloc[idx_list, :]

    df_final_res = df_results[df_results['keyword'].isin(food_list)]
    df_final_res.reset_index(drop=True, inplace=True)

    os.makedirs("D:/projects/baidu_downloader/web_spider_image/new_cengci/food", exist_ok=True)
    for i in range(df_final_res.shape[0]):
        base_path = "D:/projects/baidu_downloader/web_spider_image/new_cengci/food"
        target_dir = os.path.join(base_path, df_final_res.loc[i, 'keyword'])
        os.makedirs(target_dir, exist_ok=True)

        target_image_path = os.path.join(target_dir, "1.jpg")
        source_image_path = df_final_res.loc[i, 'new_path']
        img = Image.open(source_image_path)
        rgb_image = img.convert('RGB')
        rgb_image.save(target_image_path)  
        rgb_image.close()

    
def zhengli(spot_list, food_list):
    zhengli_spot(spot_list)
    zhengli_food(food_list)
