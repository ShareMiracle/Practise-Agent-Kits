import os
import pandas as pd
from pathlib import Path
import shutil

def process_images(input_folder, output_folder="D:/projects/baidu_downloader/web_spider_image/new_image"):
    """
    处理图片文件，创建数据框并保存图片
    """
    # 创建输出文件夹
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)
    
    # 获取输入文件夹路径
    input_path = Path(input_folder)
    category = input_path.name
    
    data = []
    counter = 1
    
    # 遍历一级子文件夹
    for keyword_folder in input_path.iterdir():
        if keyword_folder.is_dir():
            keyword = keyword_folder.name
            
            # 遍历子文件夹中的文件
            for img_file in keyword_folder.glob('*'):
                if img_file.is_file() and img_file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}:
                    raw_path = str(img_file)
                    new_filename = f"{category}_{counter}{img_file.suffix}"
                    new_path = str(output_path / new_filename)
                    
                    # 复制文件到新路径
                    shutil.copy2(img_file, new_path)
                    
                    data.append({
                        'raw_path': raw_path,
                        'category': category,
                        'keyword': keyword,
                        'new_path': new_path
                    })
                    
                    counter += 1
    
    # 创建DataFrame
    df = pd.DataFrame(data, columns=['raw_path', 'category', 'keyword', 'new_path'])
    return df

# 使用示例
if __name__ == "__main__":
    input_folder = "D:/projects/baidu_downloader/web_spider_image/spot"  # 替换为你的文件夹路径
    df = process_images(input_folder)
    print(df)
    
    # 保存DataFrame到CSV（可选）
    df.to_excel('D:/projects/baidu_downloader/web_spider_image/new_imageimage_info.xlsx', index=False)
    