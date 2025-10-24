"""
AoJia64 Python封装
将C++ COM接口转换为Python接口
"""

import ctypes
from ctypes import c_long, c_wchar_p, windll
import pythoncom
import win32com.client


class ARegJ:
    """ARegJ辅助类，用于设置DLL路径实现免注册调用"""
    
    _dll = None
    
    @classmethod
    def set_dll_path(cls, areg_path, aojia_path):
        """设置DLL路径"""
        try:
            if cls._dll is None:
                cls._dll = ctypes.WinDLL(areg_path)
            
            set_path_func = cls._dll.SetDllPathW
            set_path_func.argtypes = [c_wchar_p, c_long]
            set_path_func.restype = c_long
            
            return set_path_func(aojia_path, 0)
        except Exception as e:
            print(f"设置DLL路径失败: {e}")
            return 0


class AoJia:
    """AoJia插件Python封装类"""
    
    CLSID = "{4F27E588-5B1E-45B4-AD67-E32D45C4E9CA}"
    
    def __init__(self, areg_path=None, aojia_path=None):
        """
        初始化AoJia对象
        
        Args:
            areg_path: ARegJ64.dll的路径（免注册调用需要）
            aojia_path: AoJia64.dll的路径（免注册调用需要）
        """
        self.com_obj = None
        self.hr = None
        
        # 如果提供了路径，进行免注册设置
        if areg_path and aojia_path:
            ARegJ.set_dll_path(areg_path, aojia_path)
        
        try:
            pythoncom.CoInitialize()
            self.com_obj = win32com.client.Dispatch(self.CLSID)
            self.hr = 0  # S_OK
        except Exception as e:
            print(f"创建COM对象失败: {e}")
            self.hr = -1
    
    def __del__(self):
        """清理COM对象"""
        if self.com_obj:
            self.com_obj = None
        pythoncom.CoUninitialize()
    
    # ==================== 基础功能 ====================
    
    def ver_s(self):
        """获取插件版本号"""
        return self.com_obj.VerS() if self.com_obj else ""
    
    def set_path(self, path):
        """设置插件工作路径"""
        return self.com_obj.SetPath(path) if self.com_obj else 0
    
    def set_error_msg(self, msg):
        """设置是否显示错误信息"""
        return self.com_obj.SetErrorMsg(msg) if self.com_obj else 0
    
    def set_thread(self, tn):
        """设置线程数"""
        return self.com_obj.SetThread(tn) if self.com_obj else 0
    
    def get_module_path(self, pid, hwnd, mn, type_):
        """获取模块路径"""
        return self.com_obj.GetModulePath(pid, hwnd, mn, type_) if self.com_obj else ""
    
    def get_machine_code(self):
        """获取机器码"""
        return self.com_obj.GetMachineCode() if self.com_obj else ""
    
    def get_os(self, type_):
        """
        获取操作系统信息
        返回: (ret, sv, svn, lvbn, sdir)
        """
        if not self.com_obj:
            return (0, "", "", -1, "")
        sv, svn, lvbn, sdir = "", "", 0, ""
        ret = self.com_obj.GetOs(sv, svn, lvbn, sdir, type_)
        return (ret, sv, svn, lvbn, sdir)
    
    def get_last_error(self):
        """获取最后的错误码"""
        return self.com_obj.GetLastError() if self.com_obj else 0
    
    def get_path(self):
        """获取插件工作路径"""
        return self.com_obj.GetPath() if self.com_obj else ""
    
    def get_aojia_id(self):
        """获取AoJia对象ID"""
        return self.com_obj.GetAoJiaID() if self.com_obj else 0
    
    def get_aojia_num(self):
        """获取AoJia对象数量"""
        return self.com_obj.GetAoJiaNum() if self.com_obj else 0
    
    # ==================== 窗口操作 ====================
    
    def find_window(self, parent, pro_name, pro_id, class_, title, type_, t):
        """查找窗口"""
        return self.com_obj.FindWindow(parent, pro_name, pro_id, class_, title, type_, t) if self.com_obj else 0
    
    def create_windows(self, x, y, width, height, e_width, e_height, type_):
        """创建窗口"""
        return self.com_obj.CreateWindows(x, y, width, height, e_width, e_height, type_) if self.com_obj else 0
    
    def find_window_ex(self, scdt1, flag1, type1, scdt2, flag2, type2, scdt3, flag3, type3, visible, t):
        """查找窗口扩展"""
        return self.com_obj.FindWindowEx(scdt1, flag1, type1, scdt2, flag2, type2, scdt3, flag3, type3, visible, t) if self.com_obj else 0
    
    def enum_window(self, parent, pro_name, pro_id, class_, title, type_, flag, t):
        """枚举窗口"""
        return self.com_obj.EnumWindow(parent, pro_name, pro_id, class_, title, type_, flag, t) if self.com_obj else ""
    
    def enum_window_ex(self, scdt1, flag1, type1, scdt2, flag2, type2, scdt3, flag3, type3, visible, sort, t):
        """枚举窗口扩展"""
        return self.com_obj.EnumWindowEx(scdt1, flag1, type1, scdt2, flag2, type2, scdt3, flag3, type3, visible, sort, t) if self.com_obj else ""
    
    def get_window_class(self, hwnd):
        """获取窗口类名"""
        return self.com_obj.GetWindowClass(hwnd) if self.com_obj else ""
    
    def get_window_title(self, hwnd):
        """获取窗口标题"""
        return self.com_obj.GetWindowTitle(hwnd) if self.com_obj else ""
    
    def set_window_title(self, hwnd, title):
        """设置窗口标题"""
        return self.com_obj.SetWindowTitle(hwnd, title) if self.com_obj else 0
    
    def get_client_rect(self, hwnd):
        """
        获取客户区坐标
        返回: (ret, x1, y1, x2, y2)
        """
        if not self.com_obj:
            return (0, -1, -1, -1, -1)
        # COM返回 (ret, x1, y1, x2, y2)
        result = self.com_obj.GetClientRect(hwnd, 0, 0, 0, 0)
        if isinstance(result, tuple) and len(result) >= 5:
            return (result[0], result[1], result[2], result[3], result[4])
        return (0, -1, -1, -1, -1)
    
    def get_client_size(self, hwnd):
        """
        获取客户区大小
        返回: (ret, width, height)
        """
        if not self.com_obj:
            return (0, -1, -1)
        # COM返回 (ret, width, height)
        result = self.com_obj.GetClientSize(hwnd, 0, 0)
        if isinstance(result, tuple) and len(result) >= 3:
            return (result[0], result[1], result[2])
        return (0, -1, -1)
    
    def get_window_rect(self, hwnd, type_):
        """
        获取窗口坐标
        返回: (ret, x1, y1, x2, y2)
        """
        if not self.com_obj:
            return (0, -1, -1, -1, -1)
        # COM返回 (ret, x1, y1, x2, y2)
        result = self.com_obj.GetWindowRect(hwnd, 0, 0, 0, 0, type_)
        if isinstance(result, tuple) and len(result) >= 5:
            return (result[0], result[1], result[2], result[3], result[4])
        return (0, -1, -1, -1, -1)
    
    def get_window_size(self, hwnd):
        """
        获取窗口大小
        返回: (ret, width, height)
        """
        if not self.com_obj:
            return (0, -1, -1)
        # COM返回 (ret, width, height)
        result = self.com_obj.GetWindowSize(hwnd, 0, 0)
        if isinstance(result, tuple) and len(result) >= 3:
            return (result[0], result[1], result[2])
        return (0, -1, -1)
    
    def client_to_screen(self, hwnd, x, y):
        """
        客户区坐标转屏幕坐标
        返回: (ret, x, y)
        """
        if not self.com_obj:
            return (0, x, y)
        # COM返回 (ret, x, y)
        result = self.com_obj.ClientToScreen(hwnd, x, y)
        if isinstance(result, tuple) and len(result) >= 3:
            return (result[0], result[1], result[2])
        return (0, x, y)
    
    def screen_to_client(self, hwnd, x, y):
        """
        屏幕坐标转客户区坐标
        返回: (ret, x, y)
        """
        if not self.com_obj:
            return (0, x, y)
        # COM返回 (ret, x, y)
        result = self.com_obj.ScreenToClient(hwnd, x, y)
        if isinstance(result, tuple) and len(result) >= 3:
            return (result[0], result[1], result[2])
        return (0, x, y)
    
    def set_client_size(self, hwnd, width, height):
        """设置客户区大小"""
        return self.com_obj.SetClientSize(hwnd, width, height) if self.com_obj else 0
    
    def set_window_size(self, hwnd, width, height):
        """设置窗口大小"""
        return self.com_obj.SetWindowSize(hwnd, width, height) if self.com_obj else 0
    
    def move_window(self, hwnd, x, y):
        """移动窗口"""
        return self.com_obj.MoveWindow(hwnd, x, y) if self.com_obj else 0
    
    def get_window_state(self, hwnd, type_):
        """获取窗口状态"""
        return self.com_obj.GetWindowState(hwnd, type_) if self.com_obj else -1
    
    def set_window_state(self, hwnd, type_):
        """设置窗口状态"""
        return self.com_obj.SetWindowState(hwnd, type_) if self.com_obj else -1
    
    def get_window_thread_process_id(self, hwnd, type_):
        """获取窗口线程或进程ID"""
        return self.com_obj.GetWindowThreadProcessId(hwnd, type_) if self.com_obj else 0
    
    def get_window_process_path(self, hwnd, type_):
        """获取窗口进程路径"""
        return self.com_obj.GetWindowProcessPath(hwnd, type_) if self.com_obj else ""
    
    def set_window_transparent(self, hwnd, color, tp, type_):
        """设置窗口透明"""
        return self.com_obj.SetWindowTransparent(hwnd, color, tp, type_) if self.com_obj else 0
    
    def get_foreground_window(self):
        """获取前台窗口"""
        return self.com_obj.GetForegroundWindow() if self.com_obj else 0
    
    def get_focus(self):
        """获取焦点窗口"""
        return self.com_obj.GetFocus() if self.com_obj else 0
    
    def get_window_from_point(self, x, y):
        """根据坐标获取窗口"""
        return self.com_obj.GetWindowFromPoint(x, y) if self.com_obj else 0
    
    def get_window_from_mouse(self):
        """获取鼠标所在窗口"""
        return self.com_obj.GetWindowFromMouse() if self.com_obj else 0
    
    def get_window(self, hwnd, type_):
        """获取关联窗口"""
        return self.com_obj.GetWindow(hwnd, type_) if self.com_obj else 0
    
    def close_window(self, hwnd):
        """关闭窗口"""
        return self.com_obj.CloseWindow(hwnd) if self.com_obj else 0
    
    # ==================== 进程操作 ====================
    
    def enum_process(self, pro_name):
        """枚举进程"""
        return self.com_obj.EnumProcess(pro_name) if self.com_obj else ""
    
    def terminate_process(self, pid, hwnd, pro_name, type_):
        """终止进程"""
        return self.com_obj.TerminateProcess(pid, hwnd, pro_name, type_) if self.com_obj else -1
    
    def get_process_info(self, pid, hwnd):
        """获取进程信息"""
        return self.com_obj.GetProcessInfo(pid, hwnd) if self.com_obj else ""
    
    def disable_ime(self, tid, type_):
        """禁用输入法"""
        return self.com_obj.DisableIME(tid, type_) if self.com_obj else 0
    
    def enum_thread(self, pid, hwnd):
        """枚举线程"""
        return self.com_obj.EnumThread(pid, hwnd) if self.com_obj else ""
    
    def get_current_thread_id(self):
        """获取当前线程ID"""
        return self.com_obj.GetCurrentThreadId() if self.com_obj else 0
    
    def terminate_thread(self, tid):
        """终止线程"""
        return self.com_obj.TerminateThread(tid) if self.com_obj else 0
    
    def get_current_process_id(self):
        """获取当前进程ID"""
        return self.com_obj.GetCurrentProcessId() if self.com_obj else 0
    
    def get_process_path(self, pid, type_):
        """获取进程路径"""
        return self.com_obj.GetProcessPath(pid, type_) if self.com_obj else ""
    
    def get_command_line(self, pid, hwnd):
        """获取命令行"""
        return self.com_obj.GetCommandLine(pid, hwnd) if self.com_obj else ""
    
    def enum_module(self, pid, hwnd):
        """枚举模块"""
        return self.com_obj.EnumModule(pid, hwnd) if self.com_obj else ""
    
    def get_module_base_addr(self, pid, hwnd, mn):
        """获取模块基址"""
        return self.com_obj.GetModuleBaseAddr(pid, hwnd, mn) if self.com_obj else 0
    
    def get_module_size(self, pid, hwnd, mn):
        """获取模块大小"""
        return self.com_obj.GetModuleSize(pid, hwnd, mn) if self.com_obj else 0
    
    def is_64_process(self, pid, hwnd):
        """判断是否64位进程"""
        return self.com_obj.Is64Process(pid, hwnd) if self.com_obj else -1
    
    def get_remote_proc_address(self, pid, hwnd, mn, func):
        """获取远程函数地址"""
        return self.com_obj.GetRemoteProcAddress(pid, hwnd, mn, func) if self.com_obj else 0
    
    # ==================== 内存操作 ====================
    
    def free_process_memory(self, pid, hwnd):
        """释放进程内存"""
        return self.com_obj.FreeProcessMemory(pid, hwnd) if self.com_obj else 0
    
    def virtual_alloc_ex(self, pid, hwnd, addr, size, type_):
        """分配内存"""
        return self.com_obj.VirtualAllocEx(pid, hwnd, addr, size, type_) if self.com_obj else 0
    
    def virtual_free_ex(self, pid, hwnd, addr):
        """释放内存"""
        return self.com_obj.VirtualFreeEx(pid, hwnd, addr) if self.com_obj else 0
    
    def virtual_query_ex(self, pid, hwnd, addr):
        """
        查询内存
        返回: (result, a_protect, protect, state, type_)
        """
        if not self.com_obj:
            return ("", -1, -1, -1, -1)
        a_protect, protect, state, type_ = 0, 0, 0, 0
        result = self.com_obj.VirtualQueryEx(pid, hwnd, addr, a_protect, protect, state, type_)
        return (result, a_protect, protect, state, type_)
    
    def virtual_protect_ex(self, pid, hwnd, addr, size, flag, protect):
        """
        修改内存属性
        返回: (ret, type_)
        """
        if not self.com_obj:
            return (0, 0)
        type_ = 0
        ret = self.com_obj.VirtualProtectEx(pid, hwnd, addr, size, flag, protect, type_)
        return (ret, type_)
    
    def read_data_s(self, pid, hwnd, addr_s, len_):
        """读取数据（字符串地址）"""
        return self.com_obj.ReadDataS(pid, hwnd, addr_s, len_) if self.com_obj else ""
    
    def read_data_l(self, pid, hwnd, addr_l, len_):
        """读取数据（数值地址）"""
        return self.com_obj.ReadDataL(pid, hwnd, addr_l, len_) if self.com_obj else ""
    
    def write_data_s(self, pid, hwnd, addr_s, data):
        """写入数据（字符串地址）"""
        return self.com_obj.WriteDataS(pid, hwnd, addr_s, data) if self.com_obj else 0
    
    def write_data_l(self, pid, hwnd, addr_l, data):
        """写入数据（数值地址）"""
        return self.com_obj.WriteDataL(pid, hwnd, addr_l, data) if self.com_obj else 0
    
    def read_int_s(self, pid, hwnd, addr_s, flag):
        """
        读取整数（字符串地址）
        返回: (value, type_)
        """
        if not self.com_obj:
            return (0, 0)
        type_ = 0
        value = self.com_obj.ReadIntS(pid, hwnd, addr_s, flag, type_)
        return (value, type_)
    
    def read_int_l(self, pid, hwnd, addr_l, flag):
        """
        读取整数（数值地址）
        返回: (value, type_)
        """
        if not self.com_obj:
            return (0, 0)
        type_ = 0
        value = self.com_obj.ReadIntL(pid, hwnd, addr_l, flag, type_)
        return (value, type_)
    
    def write_int_s(self, pid, hwnd, addr_s, value, type_):
        """写入整数（字符串地址）"""
        return self.com_obj.WriteIntS(pid, hwnd, addr_s, value, type_) if self.com_obj else 0
    
    def write_int_l(self, pid, hwnd, addr_l, value, type_):
        """写入整数（数值地址）"""
        return self.com_obj.WriteIntL(pid, hwnd, addr_l, value, type_) if self.com_obj else 0
    
    def read_double_s(self, pid, hwnd, addr_s):
        """
        读取双精度（字符串地址）
        返回: (value, type_)
        """
        if not self.com_obj:
            return (0.0, 0)
        type_ = 0
        value = self.com_obj.ReadDoubleS(pid, hwnd, addr_s, type_)
        return (value, type_)
    
    def read_double_l(self, pid, hwnd, addr_l):
        """
        读取双精度（数值地址）
        返回: (value, type_)
        """
        if not self.com_obj:
            return (0.0, 0)
        type_ = 0
        value = self.com_obj.ReadDoubleL(pid, hwnd, addr_l, type_)
        return (value, type_)
    
    def write_double_s(self, pid, hwnd, addr_s, value):
        """写入双精度（字符串地址）"""
        return self.com_obj.WriteDoubleS(pid, hwnd, addr_s, value) if self.com_obj else 0
    
    def write_double_l(self, pid, hwnd, addr_l, value):
        """写入双精度（数值地址）"""
        return self.com_obj.WriteDoubleL(pid, hwnd, addr_l, value) if self.com_obj else 0
    
    def read_float_s(self, pid, hwnd, addr_s):
        """
        读取单精度（字符串地址）
        返回: (value, type_)
        """
        if not self.com_obj:
            return (0.0, 0)
        type_ = 0
        value = self.com_obj.ReadFloatS(pid, hwnd, addr_s, type_)
        return (value, type_)
    
    def read_float_l(self, pid, hwnd, addr_l):
        """
        读取单精度（数值地址）
        返回: (value, type_)
        """
        if not self.com_obj:
            return (0.0, 0)
        type_ = 0
        value = self.com_obj.ReadFloatL(pid, hwnd, addr_l, type_)
        return (value, type_)
    
    def write_float_s(self, pid, hwnd, addr_s, value):
        """写入单精度（字符串地址）"""
        return self.com_obj.WriteFloatS(pid, hwnd, addr_s, value) if self.com_obj else 0
    
    def write_float_l(self, pid, hwnd, addr_l, value):
        """写入单精度（数值地址）"""
        return self.com_obj.WriteFloatL(pid, hwnd, addr_l, value) if self.com_obj else 0
    
    def read_string_s(self, pid, hwnd, addr_s, len_, flag):
        """
        读取字符串（字符串地址）
        返回: (string, type_)
        """
        if not self.com_obj:
            return ("", 0)
        type_ = 0
        string = self.com_obj.ReadStringS(pid, hwnd, addr_s, len_, flag, type_)
        return (string, type_)
    
    def read_string_l(self, pid, hwnd, addr_l, len_, flag):
        """
        读取字符串（数值地址）
        返回: (string, type_)
        """
        if not self.com_obj:
            return ("", 0)
        type_ = 0
        string = self.com_obj.ReadStringL(pid, hwnd, addr_l, len_, flag, type_)
        return (string, type_)
    
    def write_string_s(self, pid, hwnd, addr_s, string, type_):
        """写入字符串（字符串地址）"""
        return self.com_obj.WriteStringS(pid, hwnd, addr_s, string, type_) if self.com_obj else 0
    
    def write_string_l(self, pid, hwnd, addr_l, string, type_):
        """写入字符串（数值地址）"""
        return self.com_obj.WriteStringL(pid, hwnd, addr_l, string, type_) if self.com_obj else 0
    
    # ==================== 键盘鼠标 ====================
    
    def key_down(self, key):
        """按下键"""
        return self.com_obj.KeyDown(key) if self.com_obj else 0
    
    def key_up(self, key):
        """释放键"""
        return self.com_obj.KeyUp(key) if self.com_obj else 0
    
    def key_press(self, key):
        """按键"""
        return self.com_obj.KeyPress(key) if self.com_obj else 0
    
    def key_down_s(self, key_s):
        """按下键（字符串）"""
        return self.com_obj.KeyDownS(key_s) if self.com_obj else 0
    
    def key_up_s(self, key_s):
        """释放键（字符串）"""
        return self.com_obj.KeyUpS(key_s) if self.com_obj else 0
    
    def key_press_s(self, key_s):
        """按键（字符串）"""
        return self.com_obj.KeyPressS(key_s) if self.com_obj else 0
    
    def left_down(self):
        """左键按下"""
        return self.com_obj.LeftDown() if self.com_obj else 0
    
    def left_up(self):
        """左键释放"""
        return self.com_obj.LeftUp() if self.com_obj else 0
    
    def right_down(self):
        """右键按下"""
        return self.com_obj.RightDown() if self.com_obj else 0
    
    def right_up(self):
        """右键释放"""
        return self.com_obj.RightUp() if self.com_obj else 0
    
    def middle_down(self):
        """中键按下"""
        return self.com_obj.MiddleDown() if self.com_obj else 0
    
    def middle_up(self):
        """中键释放"""
        return self.com_obj.MiddleUp() if self.com_obj else 0
    
    def left_click(self):
        """左键单击"""
        return self.com_obj.LeftClick() if self.com_obj else 0
    
    def right_click(self):
        """右键单击"""
        return self.com_obj.RightClick() if self.com_obj else 0
    
    def middle_click(self):
        """中键单击"""
        return self.com_obj.MiddleClick() if self.com_obj else 0
    
    def left_double_click(self):
        """左键双击"""
        return self.com_obj.LeftDoubleClick() if self.com_obj else 0
    
    def move_to(self, x, y):
        """移动鼠标到指定坐标"""
        return self.com_obj.MoveTo(x, y) if self.com_obj else 0
    
    def move_r(self, rx, ry):
        """相对移动鼠标"""
        return self.com_obj.MoveR(rx, ry) if self.com_obj else 0
    
    def get_mouse_pos(self, type_):
        """
        获取鼠标位置
        返回: (ret, x, y)
        """
        if not self.com_obj:
            return (0, -1, -1)
        # COM返回 (ret, x, y)
        result = self.com_obj.GetMousePos(0, 0, type_)
        if isinstance(result, tuple) and len(result) >= 3:
            return (result[0], result[1], result[2])
        return (0, -1, -1)
    
    # ==================== 图色功能 ====================
    
    def find_color(self, x1, y1, x2, y2, color, sim, dir_):
        """
        查找颜色
        返回: (ret, x, y)
        """
        if not self.com_obj:
            return (-1, -1, -1)
        x, y = 0, 0
        ret = self.com_obj.FindColor(x1, y1, x2, y2, color, sim, dir_, x, y)
        return (ret, x, y)
    
    def find_color_ex(self, x1, y1, x2, y2, color, sim, dir_):
        """查找颜色扩展（返回所有坐标）"""
        return self.com_obj.FindColorEx(x1, y1, x2, y2, color, sim, dir_) if self.com_obj else ""
    
    def find_pic(self, x1, y1, x2, y2, pic_name, color_p, sim, dir_, type_):
        """
        查找图片
        返回: (ret, pic, x, y)
        """
        if not self.com_obj:
            return (-1, "", -1, -1)
        pic, x, y = "", 0, 0
        ret = self.com_obj.FindPic(x1, y1, x2, y2, pic_name, color_p, sim, dir_, type_, pic, x, y)
        return (ret, pic, x, y)
    
    def find_pic_ex(self, x1, y1, x2, y2, pic_name, color_p, sim, dir_, type_, type_t):
        """查找图片扩展（返回所有坐标）"""
        return self.com_obj.FindPicEx(x1, y1, x2, y2, pic_name, color_p, sim, dir_, type_, type_t) if self.com_obj else ""
    
    def get_color(self, x, y, type_, type_d):
        """获取指定坐标颜色"""
        return self.com_obj.GetColor(x, y, type_, type_d) if self.com_obj else -1
    
    def cmp_color(self, x, y, color, sim, type_):
        """比较颜色"""
        return self.com_obj.CmpColor(x, y, color, sim, type_) if self.com_obj else -1
    
    def load_pic(self, pic_name):
        """加载图片"""
        return self.com_obj.LoadPic(pic_name) if self.com_obj else 0
    
    def free_pic(self, pic_name):
        """释放图片"""
        return self.com_obj.FreePic(pic_name) if self.com_obj else 0
    
    def get_pic_size(self, pic_name):
        """
        获取图片大小
        返回: (ret, width, height)
        """
        if not self.com_obj:
            return (0, -1, -1)
        width, height = 0, 0
        ret = self.com_obj.GetPicSize(pic_name, width, height)
        return (ret, width, height)
    
    def screen_shot(self, x1, y1, x2, y2, pic_name, type_, quality, td, t, flag, mouse):
        """截图"""
        return self.com_obj.ScreenShot(x1, y1, x2, y2, pic_name, type_, quality, td, t, flag, mouse) if self.com_obj else 0
    
    # ==================== 文字识别 ====================
    
    def load_dict(self, d_num, d_name):
        """加载字库"""
        return self.com_obj.LoadDict(d_num, d_name) if self.com_obj else 0
    
    def set_dict(self, d_num):
        """设置字库"""
        return self.com_obj.SetDict(d_num) if self.com_obj else 0
    
    def free_dict(self, d_num):
        """释放字库"""
        return self.com_obj.FreeDict(d_num) if self.com_obj else 0
    
    def ocr(self, x1, y1, x2, y2, str_, color, sim, type_c, type_d, type_r, type_t, h_line, pic_name):
        """文字识别"""
        return self.com_obj.Ocr(x1, y1, x2, y2, str_, color, sim, type_c, type_d, type_r, type_t, h_line, pic_name) if self.com_obj else ""
    
    def find_str(self, x1, y1, x2, y2, str_, color, sim, dir_, type_c, type_d):
        """
        查找字符串
        返回: (ret, str_d, x, y)
        """
        if not self.com_obj:
            return (-1, "", -1, -1)
        str_d, x, y = "", 0, 0
        ret = self.com_obj.FindStr(x1, y1, x2, y2, str_, color, sim, dir_, type_c, type_d, str_d, x, y)
        return (ret, str_d, x, y)
    
    # ==================== 文件操作 ====================
    
    def create_folder(self, fn):
        """创建文件夹"""
        return self.com_obj.CreateFolder(fn) if self.com_obj else 0
    
    def delete_folder(self, fn):
        """删除文件夹"""
        return self.com_obj.DeleteFolder(fn) if self.com_obj else 0
    
    def find_file(self, fn):
        """查找文件"""
        return self.com_obj.FindFile(fn) if self.com_obj else ""
    
    def is_file_or_folder(self, fn):
        """判断文件或文件夹"""
        return self.com_obj.IsFileOrFolder(fn) if self.com_obj else 0
    
    def copy_file(self, sf, df, type_):
        """复制文件"""
        return self.com_obj.CopyFile(sf, df, type_) if self.com_obj else 0
    
    def copy_folder(self, sf, df, type_):
        """复制文件夹"""
        return self.com_obj.CopyFolder(sf, df, type_) if self.com_obj else 0
    
    def delete_file(self, fn):
        """删除文件"""
        return self.com_obj.DeleteFile(fn) if self.com_obj else 0
    
    def move_file(self, sf, df, type_):
        """移动文件"""
        return self.com_obj.MoveFile(sf, df, type_) if self.com_obj else 0
    
    def move_folder(self, sf, df, type_):
        """移动文件夹"""
        return self.com_obj.MoveFolder(sf, df, type_) if self.com_obj else 0
    
    def rename_file(self, sf, df):
        """重命名文件"""
        return self.com_obj.ReNameFile(sf, df) if self.com_obj else 0
    
    def read_file(self, fn, pos, flag, size, type_, type_d):
        """读取文件"""
        return self.com_obj.ReadFile(fn, pos, flag, size, type_, type_d) if self.com_obj else ""
    
    def write_file(self, fn, str_, pos, flag, size, type_, type_d):
        """写入文件"""
        return self.com_obj.WriteFile(fn, str_, pos, flag, size, type_, type_d) if self.com_obj else 0
    
    def get_file_size(self, fn):
        """
        获取文件大小
        返回: (size, fsh, fsl)
        """
        if not self.com_obj:
            return (-1.0, -1, -1)
        fsh, fsl = 0, 0
        size = self.com_obj.GetFileSize(fn, fsh, fsl)
        return (size, fsh, fsl)
    
    # ==================== 系统功能 ====================
    
    def get_screen(self):
        """
        获取屏幕分辨率
        返回: (ret, width, height)
        """
        if not self.com_obj:
            return (0, 0, 0)
        # COM返回 (ret, width, height)
        result = self.com_obj.GetScreen(0, 0)
        if isinstance(result, tuple) and len(result) >= 3:
            return (result[0], result[1], result[2])
        return (0, 0, 0)
    
    def get_screen_s(self):
        """
        获取所有屏幕信息
        返回: (result, xs, ys)
        """
        if not self.com_obj:
            return ("", 0, 0)
        xs, ys = 0, 0
        result = self.com_obj.GetScreenS(xs, ys)
        return (result, xs, ys)
    
    def set_screen(self, width, height):
        """设置屏幕分辨率"""
        return self.com_obj.SetScreen(width, height) if self.com_obj else 0
    
    def get_time(self):
        """获取系统运行时间"""
        return self.com_obj.GetTime() if self.com_obj else 0
    
    def get_system_time(self):
        """获取系统时间"""
        return self.com_obj.GetSystemTime() if self.com_obj else ""
    
    def set_system_time(self, st):
        """设置系统时间"""
        return self.com_obj.SetSystemTime(st) if self.com_obj else 0
    
    def yan_shi(self, r_min, r_max):
        """延时（随机）"""
        return self.com_obj.YanShi(r_min, r_max) if self.com_obj else 0
    
    def sui_ji(self, r_min, r_max):
        """随机数"""
        return self.com_obj.SuiJi(r_min, r_max) if self.com_obj else 0
    
    def beep(self, hz, t):
        """蜂鸣"""
        return self.com_obj.Beep(hz, t) if self.com_obj else 0
    
    def get_dpi(self):
        """获取屏幕DPI"""
        return self.com_obj.GetDPI() if self.com_obj else 0
    
    def cmd(self, cl, type_):
        """执行CMD命令"""
        return self.com_obj.Cmd(cl, type_) if self.com_obj else 0
    
    def run_app(self, path, type_):
        """运行程序"""
        return self.com_obj.RunApp(path, type_) if self.com_obj else 0
    
    def get_clipboard(self):
        """获取剪贴板内容"""
        return self.com_obj.GetClipboard() if self.com_obj else ""
    
    def set_clipboard(self, str_):
        """设置剪贴板内容"""
        return self.com_obj.SetClipboard(str_) if self.com_obj else 0
    
    # ==================== 后台操作 ====================
    
    def kq_hou_tai(self, hwnd, screen, keyboard, mouse, flag, type_):
        """开启后台"""
        return self.com_obj.KQHouTai(hwnd, screen, keyboard, mouse, flag, type_) if self.com_obj else 0
    
    def gb_hou_tai(self):
        """关闭后台"""
        return self.com_obj.GBHouTai() if self.com_obj else 0
    
    def set_hwnd_skm(self, hwnd_s, hwnd_k, hwnd_m):
        """设置窗口句柄"""
        return self.com_obj.SetHwndSKM(hwnd_s, hwnd_k, hwnd_m) if self.com_obj else 0


# 使用示例
if __name__ == "__main__":
    import os
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # DLL路径（请修改为你的实际路径）
    areg_path = os.path.join(current_dir, "ARegJ64.dll")
    aojia_path = os.path.join(current_dir, "AoJia64.dll")
    
    # 创建AoJia对象（免注册方式）
    aj = AoJia(areg_path, aojia_path)
    
    # 或者使用已注册的方式
    # aj = AoJia()
    
    if aj.hr == 0:
        # 获取版本号
        ver = aj.ver_s()
        print(f"版本号: {ver}")
        
        # 获取插件路径
        path = aj.get_module_path(0, 0, "AoJia64.dll", 0)
        print(f"插件路径: {path}")
        
        # 获取屏幕分辨率
        ret, width, height = aj.get_screen()
        print(f"屏幕分辨率: {width} x {height}")
        
        # 获取鼠标位置
        ret, x, y = aj.get_mouse_pos(0)
        print(f"鼠标位置: ({x}, {y})")
        
    else:
        print(f"创建对象失败，错误码: {aj.hr}")


