import os
import base64
from tkinter import NO
import google.generativeai as genai
 
 
def call_gemini_api(prompt, image_path="", image_data=None, model_name="gemini-2.5-pro", api_key="AIzaSyB25V5pNQ1Rit65yPHSQ0xmNYrMjGjzt_A"):
    """
    调用 Gemini API，并返回文本响应。
    """
    # 配置 google.generativeai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name)
 
    if image_data==None:
        try:
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()
        except FileNotFoundError:
            print(f"错误：图片文件未找到：{image_path}")
            return ""
 
    # 将图片数据编码为 Base64 字符串
    base64_image = base64.b64encode(image_data).decode('utf-8')
 
    # 构建请求体
    contents = [
        {
            "parts": [
                {
                    "inline_data": {
                        "mime_type": "image/png",  # 假设图片为 JPEG 格式， 可根据你的图片类型修改
                        "data": base64_image
                    }
                },
                {
                    "text": prompt
                }
            ]
        }
    ]
 
    try:
        # 发送请求并获取响应
        response = model.generate_content(contents=contents)
        response.resolve()
        if response and response.text:
            return response.text
        else:
            return ""  # 请求失败或者没有文本
    except Exception as e:
        print(f"请求失败: {e}")
        return ""
 
 
if __name__ == "__main__":
    # 设置图片路径（这里使用一个在线图片URL）
    image_path = "captcha.jpg"  # 替换成你的图片路径
    
    # 设置文本提示
    prompt = f"图中最小的蓝色三棱柱的中心坐标，返回x,y坐标，用逗号分隔：如x,y，不要返回其他内容"  # 修改为你需要的提示语
 
    response_text = call_gemini_api(image_path, prompt)
 
    if response_text:
        print("Gemini API 响应:")
        print(response_text)
    else:
        print("调用 Gemini API 失败")