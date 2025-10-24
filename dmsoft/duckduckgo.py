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
    
    # hwnd = dm.find_window("DuckDuckGo","DuckDuckGo")
    hwnd = dm.find_window("Chrome_RenderWidgetHostHWND","Chrome Legacy Window")
    dm.bind_window_ex(hwnd,"normal","windows","windows",'nromal',101)
    dm.enum_window_super(str(hwnd), 4, 1,str(hwnd), 4, 1, 0)
    print(dm.get_window_title(hwnd))
    dm.set_window_size(hwnd, 1290, 900)
    
    dm.move_to(632, 780)
    dm.left_click()
    dm.delay(100)
    dm.move_to(798, 724)
    dm.left_click()
    dm.delay(100)
    pass



if __name__ == "__main__":
    main()

