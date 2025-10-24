"""
AoJia插件测试脚本
用于验证Python封装是否正常工作
"""

import sys
import os
import io
from aojia import AoJia
import time

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# 使用示例
if __name__ == "__main__":
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # DLL路径（请修改为你的实际路径）
    areg_path = os.path.join(current_dir, "ARegJ64.dll")
    aojia_path = os.path.join(current_dir, "AoJia64.dll")
    
    # 创建AoJia对象（免注册方式）
    aj = AoJia(areg_path, aojia_path)
    

    # AJD = aj.kq_hou_tai(Hwnd, "FD", "FD", "FD", "", 0)
    # AJD = aj.kq_hou_tai(Hwnd, "GDI", "WM", "WM", "", 0)
    # AJD = aj.kq_hou_tai(Hwnd, "GDI", "DX", "DX", "LAA|LAM|LFA|LFM", 1)
    # AJD = aj.gb_hou_tai()
    aj.run_app(r"C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\DuckDuckGo.exe", 0)

    while True:
        hwnd_ddg = aj.find_window(0, "", 0, "DuckDuckGo", "", 0, 1000)
        if hwnd_ddg != 0:
            break
        time.sleep(0.5)
    
    while True:
        hwnd_ddg_email = aj.find_window(hwnd_ddg, "", 0, "Chrome_RenderWidgetHostHWND", "", 0, 1000)
        if hwnd_ddg_email != 0:
            break
        time.sleep(0.5)
    
 
    aj.set_window_size(hwnd_ddg, 625, 907)
    aj.kq_hou_tai(hwnd_ddg_email, "DX", "DX", "DX", "LAA|LAM|LFA|LFM", 2)

    time.sleep(1)
    
    while True:
        while True:
            AJD = aj.find_pic(0, 0, 648-77, 934-177, r"C:\Users\Administrator\Desktop\work\ajdll\generate_enable.bmp", "000000", 0.6, 0, 0)
            if color == "2b55ca":
                break
            time.sleep(0.5)
        time.sleep(1)

        aj.move_to(314, 554)
        aj.left_click()
        time.sleep(1)

        while True:
            color = aj.get_color(473,555,0,0)
            if color == "2b55ca":
                break
            time.sleep(0.5)
        time.sleep(1)
        
        aj.move_to(534, 502)
        aj.left_click()
        time.sleep(1)

    aj.gb_hou_tai()
    aj.set_window_state(hwnd_ddg, 15)
    
    pass
    