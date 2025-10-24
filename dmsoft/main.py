"""
大漠插件 Python 测试主程序
完整版 - 包含426个函数
"""
from dmsoft import DmSoft


def main():
    """主函数"""
    print("=" * 60)
    print("大漠插件 Python 完整测试程序")
    print("包含所有426个大漠插件函数")
    print("=" * 60)
    
    # 创建大漠对象
    dm = DmSoft()
    
    # 获取版本信息
    version = dm.ver()
    print(f"大漠插件版本: {version}")
    
    # 获取屏幕信息
    screen_width = dm.get_screen_width()
    screen_height = dm.get_screen_height()
    screen_depth = dm.get_screen_depth()
    print(f"屏幕分辨率: {screen_width} x {screen_height} x {screen_depth}位")
    

    hwnd_chrome = dm.find_window("Chrome","Chrome")
    hwnd_cursor = dm.find_window("Tauri","Cursor")
    dm.bind_window_ex(hwnd_chrome,"normal","windows","windows",'nromal',101)
    print(dm.get_window_title(hwnd_chrome))
    
    dm.set_window_state(hwnd_chrome, 13)

    dm.move_to(437, 384)
    dm.left_click()
    dm.delay(1000)
    dm.send_string(hwnd_chrome, "12对象句柄: 75953")
    dm.key_press(116)
    pass



if __name__ == "__main__":
    main()

