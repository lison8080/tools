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
    
    # DLL路径
    areg_path = os.path.join(current_dir, "ARegJ64.dll")
    aojia_path = os.path.join(current_dir, "AoJia64.dll")
    
    # 创建AoJia对象（免注册方式）
    aj = AoJia(areg_path, aojia_path)
    
    if aj.hr != 0:
        print(f"创建对象失败: {aj.hr}")
        sys.exit(1)
    
    print("AoJia对象创建成功")
    
    # 等待DuckDuckGo窗口
    print("等待DuckDuckGo窗口...")
    while True:
        hwnd_ddg = aj.find_window(0, "", 0, "DuckDuckGo", "", 0, 1000)
        if hwnd_ddg != 0:
            print(f"找到DuckDuckGo窗口: {hwnd_ddg}")
            break
        time.sleep(0.5)
    
    # 等待子窗口
    print("等待Chrome子窗口...")
    while True:
        hwnd_ddg_email = aj.find_window(hwnd_ddg, "", 0, "Chrome_RenderWidgetHostHWND", "", 0, 1000)
        if hwnd_ddg_email != 0:
            print(f"找到子窗口: {hwnd_ddg_email}")
            break
        time.sleep(0.5)
    
    # 设置窗口大小
    aj.set_window_size(hwnd_ddg, 625, 907)
    
    # 开启后台
    # ret = aj.kq_hou_tai(hwnd_ddg_email, "DX", "DX", "DX", "LAA|LAM|LFA|LFM", 2)
#     "FD": 表示图色不开启后台,只从窗口Hwnd的客户区所占据的桌面区域获取图色数据 
# "GDI": 表示图色开启后台 
# "GDI1": 表示图色开启后台.在这种模式下可以获取整个窗口的图色数据,包括标题栏、菜单和滚动条,而不只是客户区,这时所有图色和文字相关的函数的坐标参数和返回的坐标都相对于窗口左上角(0, 0),窗口右下角的坐标是(窗口宽度 - 1, 窗口高度 - 1).有的窗口没有标题栏、菜单和滚动条,只有客户区,所以窗口大小和客户区大小相等,窗口的坐标也就是客户区的坐标,这时GDI1模式和GDI模式没有分别 
# "GDI2": 表示图色开启后台.这种模式比GDI模式慢,如果在GDI模式下窗口处于后台不刷新时,可以使用这种模式试一试 
# "GDI3": 表示图色开启后台,坐标说明和GDI1模式一样,能获取整个窗口的图色数据并且坐标相对于窗口左上角.这种模式比GDI1模式慢,如果在GDI1模式下窗口处于后台不刷新时,可以使用这种模式试一试 
# "DX": 表示图色开启后台.指定成这个模式需要窗口所在进程是用DirectX10,11,12开发的 
# "DX9": 表示图色开启后台.指定成这个模式需要窗口所在进程是用DirectX9开发的 
# "OL": 表示图色开启后台.指定成这个模式需要窗口所在进程是用OpenGL开发的
    # ret = aj.kq_hou_tai(hwnd_ddg_email, "GDI", "DX", "DX", "LAA|LAM|LFA|LFM", 2)
    ret = aj.kq_hou_tai(hwnd_ddg, "GDI1", "DX", "DX", "LAA|LAM|LFA|LFM", 2)
    print(f"开启后台: {ret}")
    aj.screen_shot(0, 0, 500, 500, "无.bmp", 0, 0, 0, 0, 0, 0)
    time.sleep(1)
    
    while True:
        # 查找图片 - 正确处理返回值
        print("查找图片...")
        while True:
            # find_pic 返回 (ret, pic, x, y)
            ret, pic, x, y = aj.find_pic(
                0, 0, 648-77, 934-177, 
                r"C:\Users\Administrator\Desktop\work\ajdll\generate_enable.bmp", 
                "000000", 0.6, 0, 0
            )
            
            if ret == 1:  # 找到图片
                print(f"找到图片: {pic} 位置: ({x}, {y})")
                break
            
            time.sleep(0.5)
        
        time.sleep(1)
        
        # 点击
        print(f"移动鼠标并点击: (314, 554)")
        aj.move_to(314, 554)
        aj.left_click()
        time.sleep(1)
        
        # 获取颜色 - 正确处理返回值
        print("等待颜色变化...")
        while True:
            # get_color 返回整数（BGR格式）
            color_int = aj.get_color(473, 555, 0, 0)
            
            # 方式1: 转换为16进制字符串比较（BGR格式）
            color_hex = format(color_int, '06x')  # 转为6位16进制
            print(f"当前颜色: {color_hex} (整数: {color_int})")
            
            if color_hex == "ca552b":  # 注意：BGR格式，所以是倒过来的
                print("颜色匹配!")
                break
            
            # 方式2: 直接用整数比较（推荐）
            # if color_int == 0x2b55ca:  # RGB: 2b55ca = BGR: ca552b = 整数: 13259051
            #     break
            
            time.sleep(0.5)
        
        time.sleep(1)
        
        # 再次点击
        print(f"移动鼠标并点击: (534, 502)")
        aj.move_to(534, 502)
        aj.left_click()
        time.sleep(1)
    
    # 清理
    aj.gb_hou_tai()
    aj.set_window_state(hwnd_ddg, 15)
    
    print("完成!")