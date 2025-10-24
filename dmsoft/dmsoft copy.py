"""
大漠插件 Python 完整封装类
使用 DLL 直接调用方式（免注册）
包含所有426个大漠插件函数
支持32位和64位Python（64位通过32位子进程代理）

使用说明：
1. 32位Python：直接加载32位DLL，无需额外配置
2. 64位Python：需要系统安装32位Python，会自动启动32位子进程
   - 如果32位Python未自动找到，请设置环境变量：
     set PYTHON32_PATH=C:\\path\\to\\python32\\python.exe
   
3. 使用示例：
   from dmsoft import DmSoft
   dm = DmSoft()
   if dm.initialize():
       print(dm.ver())
"""
import os
import sys
import struct
import socket
import pickle
import subprocess
import time
import atexit
from ctypes import windll, CDLL, c_long, c_char_p, c_double, c_float, c_longlong, POINTER, byref, create_string_buffer, CFUNCTYPE


class DmSoftProxy:
    """64位Python代理客户端，通过socket与32位进程通信"""
    
    def __init__(self, py32_path):
        self.sock = None
        self.server_proc = None
        self.port = 19527  # 固定端口
        self.py32_path = py32_path
    def start_server(self):
        """启动32位Python服务进程"""
        # 查找32位Python
        # 优先使用环境变量指定的路径
        python32 = self.py32_path
        if not os.path.exists(python32):
            print(f"32位Python路径不存在: {python32},请检查是否安装32位Python")
            return False
        print(f"使用32位Python: {python32}")
        
        server_script = os.path.join(os.path.dirname(__file__), "dmsoft_server.py")
        if not os.path.exists(server_script):
            server_script = "dmsoft_server.py"
        
        print(f"启动32位服务进程，端口: {self.port}")
        
        try:
            # 创建启动信息，隐藏窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self.server_proc = subprocess.Popen(
                [python32, server_script, str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 等待服务器启动
            time.sleep(2)
            
            # 连接服务器
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('127.0.0.1', self.port))
            
            # 注册退出时关闭
            atexit.register(self.shutdown)
            
            return True
        except Exception as e:
            print(f"启动32位服务进程失败: {str(e)}")
            print(f"请确保已安装32位Python，或手动指定32位Python路径")
            return False
    
    def send_request(self, request):
        """发送请求并接收响应"""
        if not self.sock:
            return None
        try:
            serialized = pickle.dumps(request)
            length = len(serialized)
            self.sock.sendall(struct.pack('!I', length))
            self.sock.sendall(serialized)
            
            # 接收响应
            length_data = self.sock.recv(4)
            length = struct.unpack('!I', length_data)[0]
            data = b''
            while len(data) < length:
                chunk = self.sock.recv(min(length - len(data), 4096))
                if not chunk:
                    return None
                data += chunk
            
            return pickle.loads(data)
        except Exception as e:
            print(f"通信失败: {str(e)}")
            return None
    
    def initialize(self):
        """初始化"""
        if not self.start_server():
            return False
        
        response = self.send_request({'cmd': 'initialize'})
        if response and response.get('success'):
            return True
        else:
            error = response.get('error', '未知错误') if response else '无响应'
            print(f"初始化失败: {error}")
            return False
    
    def call_method(self, method_name, offset, restype, argtypes, *args):
        """调用方法"""
        # 将ctypes类型转换为字符串，便于序列化
        restype_str = self._ctype_to_str(restype)
        argtypes_str = [self._ctype_to_str(t) for t in argtypes]
        
        request = {
            'cmd': 'call_method',
            'method_name': method_name,
            'offset': offset,
            'restype': restype_str,
            'argtypes': argtypes_str,
            'args': args
        }
        response = self.send_request(request)
        if response and response.get('success'):
            return response.get('result')
        else:
            error = response.get('error', '未知错误') if response else '无响应'
            print(f"调用方法 {method_name} 失败: {error}")
            return None
    
    def _ctype_to_str(self, ctype):
        """将ctypes类型转换为字符串"""
        if ctype == c_long:
            return 'c_long'
        elif ctype == c_char_p:
            return 'c_char_p'
        elif ctype == c_double:
            return 'c_double'
        elif ctype == c_float:
            return 'c_float'
        elif ctype == c_longlong:
            return 'c_longlong'
        else:
            return 'c_long'  # 默认
    
    def shutdown(self):
        """关闭连接和服务进程"""
        try:
            if self.sock:
                try:
                    self.send_request({'cmd': 'shutdown'})
                except:
                    pass
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
        except:
            pass
        
        try:
            if self.server_proc:
                self.server_proc.terminate()
                self.server_proc.wait(timeout=5)
        except:
            pass


class DmSoft:
    """大漠插件封装类"""
    
    def __init__(self, dm_dll_path="xd47243.dll", crack_dll_path="Go.dll", py32_path=r"C:\Users\Administrator\anaconda3\envs\py32\python.exe"):
        self.is_64bit = struct.calcsize("P") * 8 == 64
        self.use_proxy = self.is_64bit
        self.proxy = None
        
        # 32位直接加载模式的属性
        self.obj = None
        self.dm_dll = None
        self.dm_handle = None
        self.dm_dll_path = dm_dll_path
        self.crack_dll_path = crack_dll_path
        self.py32_path = py32_path
        
        print(f"Python位数: {'64位' if self.is_64bit else '32位'}")
        print(f"运行模式: {'代理模式（通过32位子进程）' if self.use_proxy else '直接模式'}")
        
        print("\n" + "=" * 60)
        print("正在初始化大漠插件...")
        print("=" * 60 + "\n")
        if not self.initialize():
            print("初始化失败，程序退出")
            exit(1)

        
    def initialize(self):
        """初始化大漠插件"""
        if self.use_proxy:
            # 64位Python使用代理模式
            self.proxy = DmSoftProxy(self.py32_path)
            result = self.proxy.initialize()
            if result:
                # 设置一个占位obj值，用于方法调用检查
                self.obj = 1  # 占位值，实际obj在服务端
            return result
        else:
            # 32位Python直接加载DLL
            return self._initialize_direct()
    
    def _initialize_direct(self):
        """32位Python直接初始化"""
        try:
            # 加载大漠插件 DLL
            if not os.path.exists(self.dm_dll_path):
                print(f"DLL 文件不存在: {self.dm_dll_path}")
                return False
            
            self.dm_dll = CDLL(self.dm_dll_path)
            self.dm_handle = windll.kernel32.LoadLibraryA(self.dm_dll_path.encode())
            
            if not self.dm_handle:
                print(f"加载大漠插件失败: {self.dm_dll_path}")
                return False
            
            print(f"大漠 DLL 句柄: {self.dm_handle}")
            
            # 加载破解 DLL
            if not self._load_crack_dll(self.crack_dll_path, self.dm_handle):
                print(f"加载破解 DLL 失败: {self.crack_dll_path}")
                return False
            
            # 创建大漠对象（调用偏移地址 98304 的 CreateObj 函数）
            self.obj = self._call_function_direct(98304, c_long, [])
            if not self.obj:
                print("创建大漠对象失败")
                return False
            
            print(f"大漠对象句柄: {self.obj}")
            
            # 注册大漠插件（调用 Reg 函数 - 偏移: 121344）
            ret = self._call_function_direct(121344, c_long, [c_long, c_char_p, c_char_p], 
                                     self.obj, b"", b"")
            if ret == 1:
                print("大漠注册成功")
                return True
            else:
                print(f"大漠注册失败，返回值: {ret}")
                return False
                
        except Exception as e:
            print(f"初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _call_function(self, offset, restype, argtypes, *args):
        """调用 DLL 指定偏移地址的函数（支持代理模式）"""
        if self.use_proxy:
            # 64位代理模式
            # 提取方法名用于调试（从调用栈获取）
            import inspect
            frame = inspect.currentframe().f_back
            method_name = frame.f_code.co_name if frame else "unknown"
            
            # 代理模式下，跳过第一个参数（self.obj），因为服务端会使用自己的obj
            # args[0]通常是客户端的self.obj，在代理模式下是无效的
            proxy_args = args[1:] if len(args) > 0 and args[0] == self.obj else args
            
            return self.proxy.call_method(method_name, offset, restype, argtypes, *proxy_args)
        else:
            # 32位直接模式
            return self._call_function_direct(offset, restype, argtypes, *args)
    
    def _call_function_direct(self, offset, restype, argtypes, *args):
        """直接调用 DLL 指定偏移地址的函数"""
        func_addr = self.dm_handle + offset
        func_type = CFUNCTYPE(restype, *argtypes)
        func = func_type(func_addr)
        return func(*args)
    
    def _load_crack_dll(self, crack_dll_path, dm_handle):
        """加载破解 DLL 并调用 Go 函数"""
        try:
            if not os.path.exists(crack_dll_path):
                print(f"破解 DLL 文件不存在: {crack_dll_path}")
                return False
            
            crack_dll = CDLL(crack_dll_path)
            if not crack_dll:
                return False
            
            # 获取 Go 函数并调用
            go_func = crack_dll.Go
            go_func.argtypes = [c_long]
            go_func.restype = None
            go_func(dm_handle)
            
            print("破解 DLL 加载成功")
            return True
        except Exception as e:
            print(f"加载破解 DLL 异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_version(self):
        """获取大漠插件版本 - Ver 偏移: 100320"""
        if not self.obj:
            return None
        result = self._call_function(100320, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else None
    
    # 鼠标操作
    def move_to(self, x, y):
        """移动鼠标到指定坐标 - MoveTo 偏移: 109088"""
        if not self.obj:
            return 0
        return self._call_function(109088, c_long, [c_long, c_long, c_long], 
                                   self.obj, x, y)
    
    def left_click(self):
        """鼠标左键单击 - LeftClick 偏移: 118096"""
        if not self.obj:
            return 0
        return self._call_function(118096, c_long, [c_long], self.obj)
    
    def right_click(self):
        """鼠标右键单击 - RightClick 偏移: 104864"""
        if not self.obj:
            return 0
        return self._call_function(104864, c_long, [c_long], self.obj)
    
    def left_down(self):
        """鼠标左键按下 - LeftDown 偏移: 103456"""
        if not self.obj:
            return 0
        return self._call_function(103456, c_long, [c_long], self.obj)
    
    def left_up(self):
        """鼠标左键弹起 - LeftUp 偏移: 103840"""
        if not self.obj:
            return 0
        return self._call_function(103840, c_long, [c_long], self.obj)
    
    # 键盘操作
    def key_press(self, vk_code):
        """按键（按下并弹起） - KeyPress 偏移: 102400"""
        if not self.obj:
            return 0
        return self._call_function(102400, c_long, [c_long, c_long], 
                                   self.obj, vk_code)
    
    def key_down(self, vk_code):
        """按键按下 - KeyDown 偏移: 102272"""
        if not self.obj:
            return 0
        return self._call_function(102272, c_long, [c_long, c_long], 
                                   self.obj, vk_code)
    
    def key_up(self, vk_code):
        """按键弹起 - KeyUp 偏移: 102880"""
        if not self.obj:
            return 0
        return self._call_function(102880, c_long, [c_long, c_long], 
                                   self.obj, vk_code)
    
    def key_press_str(self, key_str, delay=50):
        """按键字符串 - KeyPressStr 偏移: 102528"""
        if not self.obj:
            return 0
        return self._call_function(102528, c_long, [c_long, c_char_p, c_long], 
                                   self.obj, key_str.encode('gbk'), delay)
    
    # 窗口操作
    def find_window(self, class_name, title_name):
        """查找窗口 - FindWindow 偏移: 112800"""
        if not self.obj:
            return 0
        return self._call_function(112800, c_long, [c_long, c_char_p, c_char_p], 
                                   self.obj, class_name.encode('gbk'), 
                                   title_name.encode('gbk'))
    
    def bind_window(self, hwnd, display, mouse, keypad, mode):
        """绑定窗口 - BindWindow 偏移: 100992"""
        if not self.obj:
            return 0
        return self._call_function(100992, c_long, 
                                   [c_long, c_long, c_char_p, c_char_p, c_char_p, c_long], 
                                   self.obj, hwnd, display.encode('gbk'), 
                                   mouse.encode('gbk'), keypad.encode('gbk'), mode)
    
    def unbind_window(self):
        """解绑窗口 - UnBindWindow 偏移: 124000"""
        if not self.obj:
            return 0
        return self._call_function(124000, c_long, [c_long], self.obj)
    
    # 其他实用功能
    def delay(self, milliseconds):
        """延时 - Delay 偏移: 101760"""
        if not self.obj:
            return 0
        return self._call_function(101760, c_long, [c_long, c_long], 
                                   self.obj, milliseconds)
    
    def set_sim_mode(self, mode):
        """设置仿真模式 - SetSimMode 偏移: 123616"""
        if not self.obj:
            return 0
        return self._call_function(123616, c_long, [c_long, c_long], 
                                   self.obj, mode)
    
    def get_screen_width(self):
        """获取屏幕宽度 - GetScreenWidth 偏移: 113920"""
        if not self.obj:
            return 0
        return self._call_function(113920, c_long, [c_long], self.obj)
    
    def get_screen_height(self):
        """获取屏幕高度 - GetScreenHeight 偏移: 117792"""
        if not self.obj:
            return 0
        return self._call_function(117792, c_long, [c_long], self.obj)
    

    def active_input_method(self, hwnd, id):
        """ActiveInputMethod - 偏移: 124320"""
        if not self.obj:
            return 0
        return self._call_function(124320, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, id.encode('gbk') if isinstance(id, str) else id)

    def add_dict(self, index, dict_info):
        """AddDict - 偏移: 106336"""
        if not self.obj:
            return 0
        return self._call_function(106336, c_long, [c_long, c_long, c_char_p], self.obj, index, dict_info.encode('gbk') if isinstance(dict_info, str) else dict_info)

    def ai_enable_find_pic_window(self, enable):
        """AiEnableFindPicWindow - 偏移: 100064"""
        if not self.obj:
            return 0
        return self._call_function(100064, c_long, [c_long, c_long], self.obj, enable)

    def ai_find_pic(self, x1, y1, x2, y2, pic_name, sim, dir, x, y):
        """AiFindPic - 偏移: 121536"""
        if not self.obj:
            return 0
        return self._call_function(121536, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def ai_find_pic_ex(self, x1, y1, x2, y2, pic_name, sim, dir):
        """AiFindPicEx - 偏移: 119136"""
        if not self.obj:
            return ''
        result = self._call_function(119136, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, sim, dir)
        return result.decode('gbk') if result else ''

    def ai_find_pic_mem(self, x1, y1, x2, y2, pic_info, sim, dir, x, y):
        """AiFindPicMem - 偏移: 111696"""
        if not self.obj:
            return 0
        return self._call_function(111696, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def ai_find_pic_mem_ex(self, x1, y1, x2, y2, pic_info, sim, dir):
        """AiFindPicMemEx - 偏移: 102976"""
        if not self.obj:
            return ''
        result = self._call_function(102976, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, sim, dir)
        return result.decode('gbk') if result else ''

    def ai_yolo_detect_objects(self, x1, y1, x2, y2, prob, iou):
        """AiYoloDetectObjects - 偏移: 116112"""
        if not self.obj:
            return ''
        result = self._call_function(116112, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_float, c_float], self.obj, x1, y1, x2, y2, prob, iou)
        return result.decode('gbk') if result else ''

    def ai_yolo_detect_objects_to_data_bmp(self, x1, y1, x2, y2, prob, iou, data, size, mode):
        """AiYoloDetectObjectsToDataBmp - 偏移: 98928"""
        if not self.obj:
            return 0
        return self._call_function(98928, c_long, [c_long, c_long, c_long, c_long, c_long, c_float, c_float, POINTER(c_long), POINTER(c_long), c_long], self.obj, x1, y1, x2, y2, prob, iou, byref(data) if isinstance(data, c_long) else data, byref(size) if isinstance(size, c_long) else size, mode)

    def ai_yolo_detect_objects_to_file(self, x1, y1, x2, y2, prob, iou, file, mode):
        """AiYoloDetectObjectsToFile - 偏移: 109504"""
        if not self.obj:
            return 0
        return self._call_function(109504, c_long, [c_long, c_long, c_long, c_long, c_long, c_float, c_float, c_char_p, c_long], self.obj, x1, y1, x2, y2, prob, iou, file.encode('gbk') if isinstance(file, str) else file, mode)

    def ai_yolo_free_model(self, index):
        """AiYoloFreeModel - 偏移: 106592"""
        if not self.obj:
            return 0
        return self._call_function(106592, c_long, [c_long, c_long], self.obj, index)

    def ai_yolo_objects_to_string(self, objects):
        """AiYoloObjectsToString - 偏移: 111456"""
        if not self.obj:
            return ''
        result = self._call_function(111456, c_char_p, [c_long, c_char_p], self.obj, objects.encode('gbk') if isinstance(objects, str) else objects)
        return result.decode('gbk') if result else ''

    def ai_yolo_set_model(self, index, file, pwd):
        """AiYoloSetModel - 偏移: 104416"""
        if not self.obj:
            return 0
        return self._call_function(104416, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, index, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def ai_yolo_set_model_memory(self, index, addr, size, pwd):
        """AiYoloSetModelMemory - 偏移: 117600"""
        if not self.obj:
            return 0
        return self._call_function(117600, c_long, [c_long, c_long, c_long, c_long, c_char_p], self.obj, index, addr, size, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def ai_yolo_set_version(self, ver):
        """AiYoloSetVersion - 偏移: 118496"""
        if not self.obj:
            return 0
        return self._call_function(118496, c_long, [c_long, c_char_p], self.obj, ver.encode('gbk') if isinstance(ver, str) else ver)

    def ai_yolo_sorts_objects(self, objects, height):
        """AiYoloSortsObjects - 偏移: 120480"""
        if not self.obj:
            return ''
        result = self._call_function(120480, c_char_p, [c_long, c_char_p, c_long], self.obj, objects.encode('gbk') if isinstance(objects, str) else objects, height)
        return result.decode('gbk') if result else ''

    def ai_yolo_use_model(self, index):
        """AiYoloUseModel - 偏移: 110032"""
        if not self.obj:
            return 0
        return self._call_function(110032, c_long, [c_long, c_long], self.obj, index)

    def append_pic_addr(self, pic_info, addr, size):
        """AppendPicAddr - 偏移: 106832"""
        if not self.obj:
            return ''
        result = self._call_function(106832, c_char_p, [c_long, c_char_p, c_long, c_long], self.obj, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, addr, size)
        return result.decode('gbk') if result else ''

    def asm_add(self, asm_ins):
        """AsmAdd - 偏移: 121232"""
        if not self.obj:
            return 0
        return self._call_function(121232, c_long, [c_long, c_char_p], self.obj, asm_ins.encode('gbk') if isinstance(asm_ins, str) else asm_ins)

    def asm_call(self, hwnd, mode):
        """AsmCall - 偏移: 114656"""
        if not self.obj:
            return 0
        return self._call_function(114656, c_longlong, [c_long, c_long, c_long], self.obj, hwnd, mode)

    def asm_call_ex(self, hwnd, mode, base_addr):
        """AsmCallEx - 偏移: 99632"""
        if not self.obj:
            return 0
        return self._call_function(99632, c_longlong, [c_long, c_long, c_long, c_char_p], self.obj, hwnd, mode, base_addr.encode('gbk') if isinstance(base_addr, str) else base_addr)

    def asm_clear(self):
        """AsmClear - 偏移: 119968"""
        if not self.obj:
            return 0
        return self._call_function(119968, c_long, [c_long], self.obj)

    def asm_set_timeout(self, time_out, param):
        """AsmSetTimeout - 偏移: 117920"""
        if not self.obj:
            return 0
        return self._call_function(117920, c_long, [c_long, c_long, c_long], self.obj, time_out, param)

    def assemble(self, base_addr, is_64bit):
        """Assemble - 偏移: 119584"""
        if not self.obj:
            return ''
        result = self._call_function(119584, c_char_p, [c_long, c_longlong, c_long], self.obj, base_addr, is_64bit)
        return result.decode('gbk') if result else ''

    def bgr2_rgb(self, bgr_color):
        """BGR2RGB - 偏移: 118736"""
        if not self.obj:
            return ''
        result = self._call_function(118736, c_char_p, [c_long, c_char_p], self.obj, bgr_color.encode('gbk') if isinstance(bgr_color, str) else bgr_color)
        return result.decode('gbk') if result else ''

    def beep(self, fre, delay):
        """Beep - 偏移: 104544"""
        if not self.obj:
            return 0
        return self._call_function(104544, c_long, [c_long, c_long, c_long], self.obj, fre, delay)

    def bind_window(self, hwnd, display, mouse, keypad, mode):
        """BindWindow - 偏移: 120080"""
        if not self.obj:
            return 0
        return self._call_function(120080, c_long, [c_long, c_long, c_char_p, c_char_p, c_char_p, c_long], self.obj, hwnd, display.encode('gbk') if isinstance(display, str) else display, mouse.encode('gbk') if isinstance(mouse, str) else mouse, keypad.encode('gbk') if isinstance(keypad, str) else keypad, mode)

    def bind_window_ex(self, hwnd, display, mouse, keypad, public_desc, mode):
        """BindWindowEx - 偏移: 99456"""
        if not self.obj:
            return 0
        return self._call_function(99456, c_long, [c_long, c_long, c_char_p, c_char_p, c_char_p, c_char_p, c_long], self.obj, hwnd, display.encode('gbk') if isinstance(display, str) else display, mouse.encode('gbk') if isinstance(mouse, str) else mouse, keypad.encode('gbk') if isinstance(keypad, str) else keypad, public_desc.encode('gbk') if isinstance(public_desc, str) else public_desc, mode)

    def capture(self, x1, y1, x2, y2, file):
        """Capture - 偏移: 119456"""
        if not self.obj:
            return 0
        return self._call_function(119456, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file)

    def capture_gif(self, x1, y1, x2, y2, file, delay, time):
        """CaptureGif - 偏移: 120912"""
        if not self.obj:
            return 0
        return self._call_function(120912, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file, delay, time)

    def capture_jpg(self, x1, y1, x2, y2, file, quality):
        """CaptureJpg - 偏移: 106400"""
        if not self.obj:
            return 0
        return self._call_function(106400, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_long], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file, quality)

    def capture_png(self, x1, y1, x2, y2, file):
        """CapturePng - 偏移: 114080"""
        if not self.obj:
            return 0
        return self._call_function(114080, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file)

    def capture_pre(self, file):
        """CapturePre - 偏移: 109456"""
        if not self.obj:
            return 0
        return self._call_function(109456, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def check_font_smooth(self):
        """CheckFontSmooth - 偏移: 117552"""
        if not self.obj:
            return 0
        return self._call_function(117552, c_long, [c_long], self.obj)

    def check_input_method(self, hwnd, id):
        """CheckInputMethod - 偏移: 101792"""
        if not self.obj:
            return 0
        return self._call_function(101792, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, id.encode('gbk') if isinstance(id, str) else id)

    def check_uac(self):
        """CheckUAC - 偏移: 123104"""
        if not self.obj:
            return 0
        return self._call_function(123104, c_long, [c_long], self.obj)

    def clear_dict(self, index):
        """ClearDict - 偏移: 123152"""
        if not self.obj:
            return 0
        return self._call_function(123152, c_long, [c_long, c_long], self.obj, index)

    def client_to_screen(self, hwnd, x, y):
        """ClientToScreen - 偏移: 116512"""
        if not self.obj:
            return 0
        return self._call_function(116512, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def cmp_color(self, x, y, color, sim):
        """CmpColor - 偏移: 109648"""
        if not self.obj:
            return 0
        return self._call_function(109648, c_long, [c_long, c_long, c_long, c_char_p, c_double], self.obj, x, y, color.encode('gbk') if isinstance(color, str) else color, sim)

    def copy_file(self, src_file, dst_file, over):
        """CopyFile - 偏移: 100688"""
        if not self.obj:
            return 0
        return self._call_function(100688, c_long, [c_long, c_char_p, c_char_p, c_long], self.obj, src_file.encode('gbk') if isinstance(src_file, str) else src_file, dst_file.encode('gbk') if isinstance(dst_file, str) else dst_file, over)

    def create_folder(self, folder_name):
        """CreateFolder - 偏移: 113120"""
        if not self.obj:
            return 0
        return self._call_function(113120, c_long, [c_long, c_char_p], self.obj, folder_name.encode('gbk') if isinstance(folder_name, str) else folder_name)

    def create_foobar_custom(self, hwnd, x, y, pic, trans_color, sim):
        """CreateFoobarCustom - 偏移: 105872"""
        if not self.obj:
            return 0
        return self._call_function(105872, c_long, [c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, hwnd, x, y, pic.encode('gbk') if isinstance(pic, str) else pic, trans_color.encode('gbk') if isinstance(trans_color, str) else trans_color, sim)

    def create_foobar_ellipse(self, hwnd, x, y, w, h):
        """CreateFoobarEllipse - 偏移: 114592"""
        if not self.obj:
            return 0
        return self._call_function(114592, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h)

    def create_foobar_rect(self, hwnd, x, y, w, h):
        """CreateFoobarRect - 偏移: 119072"""
        if not self.obj:
            return 0
        return self._call_function(119072, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h)

    def create_foobar_round_rect(self, hwnd, x, y, w, h, rw, rh):
        """CreateFoobarRoundRect - 偏移: 108352"""
        if not self.obj:
            return 0
        return self._call_function(108352, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h, rw, rh)

    def decode_file(self, file, pwd):
        """DecodeFile - 偏移: 122496"""
        if not self.obj:
            return 0
        return self._call_function(122496, c_long, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def delay(self, mis):
        """Delay - 偏移: 106480"""
        if not self.obj:
            return 0
        return self._call_function(106480, c_long, [c_long, c_long], self.obj, mis)

    def delays(self, min_s, max_s):
        """Delays - 偏移: 123328"""
        if not self.obj:
            return 0
        return self._call_function(123328, c_long, [c_long, c_long, c_long], self.obj, min_s, max_s)

    def delete_file(self, file):
        """DeleteFile - 偏移: 99408"""
        if not self.obj:
            return 0
        return self._call_function(99408, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def delete_folder(self, folder_name):
        """DeleteFolder - 偏移: 118800"""
        if not self.obj:
            return 0
        return self._call_function(118800, c_long, [c_long, c_char_p], self.obj, folder_name.encode('gbk') if isinstance(folder_name, str) else folder_name)

    def delete_ini(self, section, key, file):
        """DeleteIni - 偏移: 111168"""
        if not self.obj:
            return 0
        return self._call_function(111168, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file)

    def delete_ini_pwd(self, section, key, file, pwd):
        """DeleteIniPwd - 偏移: 99344"""
        if not self.obj:
            return 0
        return self._call_function(99344, c_long, [c_long, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def dis_assemble(self, asm_code, base_addr, is_64bit):
        """DisAssemble - 偏移: 112656"""
        if not self.obj:
            return ''
        result = self._call_function(112656, c_char_p, [c_long, c_char_p, c_longlong, c_long], self.obj, asm_code.encode('gbk') if isinstance(asm_code, str) else asm_code, base_addr, is_64bit)
        return result.decode('gbk') if result else ''

    def disable_close_display_and_sleep(self):
        """DisableCloseDisplayAndSleep - 偏移: 114416"""
        if not self.obj:
            return 0
        return self._call_function(114416, c_long, [c_long], self.obj)

    def disable_font_smooth(self):
        """DisableFontSmooth - 偏移: 118368"""
        if not self.obj:
            return 0
        return self._call_function(118368, c_long, [c_long], self.obj)

    def disable_power_save(self):
        """DisablePowerSave - 偏移: 121952"""
        if not self.obj:
            return 0
        return self._call_function(121952, c_long, [c_long], self.obj)

    def disable_screen_save(self):
        """DisableScreenSave - 偏移: 112800"""
        if not self.obj:
            return 0
        return self._call_function(112800, c_long, [c_long], self.obj)

    def dm_guard(self, enable, type):
        """DmGuard - 偏移: 103552"""
        if not self.obj:
            return 0
        return self._call_function(103552, c_long, [c_long, c_long, c_char_p], self.obj, enable, type.encode('gbk') if isinstance(type, str) else type)

    def dm_guard_extract(self, type, path):
        """DmGuardExtract - 偏移: 112160"""
        if not self.obj:
            return 0
        return self._call_function(112160, c_long, [c_long, c_char_p, c_char_p], self.obj, type.encode('gbk') if isinstance(type, str) else type, path.encode('gbk') if isinstance(path, str) else path)

    def dm_guard_load_custom(self, type, path):
        """DmGuardLoadCustom - 偏移: 106896"""
        if not self.obj:
            return 0
        return self._call_function(106896, c_long, [c_long, c_char_p, c_char_p], self.obj, type.encode('gbk') if isinstance(type, str) else type, path.encode('gbk') if isinstance(path, str) else path)

    def dm_guard_params(self, cmd, sub_cmd, param):
        """DmGuardParams - 偏移: 105472"""
        if not self.obj:
            return ''
        result = self._call_function(105472, c_char_p, [c_long, c_char_p, c_char_p, c_char_p], self.obj, cmd.encode('gbk') if isinstance(cmd, str) else cmd, sub_cmd.encode('gbk') if isinstance(sub_cmd, str) else sub_cmd, param.encode('gbk') if isinstance(param, str) else param)
        return result.decode('gbk') if result else ''

    def double_to_data(self, double_value):
        """DoubleToData - 偏移: 111856"""
        if not self.obj:
            return ''
        result = self._call_function(111856, c_char_p, [c_long, c_double], self.obj, double_value)
        return result.decode('gbk') if result else ''

    def down_cpu(self, type, rate):
        """DownCpu - 偏移: 112960"""
        if not self.obj:
            return 0
        return self._call_function(112960, c_long, [c_long, c_long, c_long], self.obj, type, rate)

    def download_file(self, url, save_file, timeout):
        """DownloadFile - 偏移: 123648"""
        if not self.obj:
            return 0
        return self._call_function(123648, c_long, [c_long, c_char_p, c_char_p, c_long], self.obj, url.encode('gbk') if isinstance(url, str) else url, save_file.encode('gbk') if isinstance(save_file, str) else save_file, timeout)

    def enable_bind(self, en):
        """EnableBind - 偏移: 116576"""
        if not self.obj:
            return 0
        return self._call_function(116576, c_long, [c_long, c_long], self.obj, en)

    def enable_display_debug(self, enable_debug):
        """EnableDisplayDebug - 偏移: 99296"""
        if not self.obj:
            return 0
        return self._call_function(99296, c_long, [c_long, c_long], self.obj, enable_debug)

    def enable_fake_active(self, en):
        """EnableFakeActive - 偏移: 107888"""
        if not self.obj:
            return 0
        return self._call_function(107888, c_long, [c_long, c_long], self.obj, en)

    def enable_find_pic_multithread(self, en):
        """EnableFindPicMultithread - 偏移: 118048"""
        if not self.obj:
            return 0
        return self._call_function(118048, c_long, [c_long, c_long], self.obj, en)

    def enable_font_smooth(self):
        """EnableFontSmooth - 偏移: 103936"""
        if not self.obj:
            return 0
        return self._call_function(103936, c_long, [c_long], self.obj)

    def enable_get_color_by_capture(self, enable):
        """EnableGetColorByCapture - 偏移: 109216"""
        if not self.obj:
            return 0
        return self._call_function(109216, c_long, [c_long, c_long], self.obj, enable)

    def enable_ime(self, en):
        """EnableIme - 偏移: 120192"""
        if not self.obj:
            return 0
        return self._call_function(120192, c_long, [c_long, c_long], self.obj, en)

    def enable_keypad_msg(self, en):
        """EnableKeypadMsg - 偏移: 120864"""
        if not self.obj:
            return 0
        return self._call_function(120864, c_long, [c_long, c_long], self.obj, en)

    def enable_keypad_patch(self, enable):
        """EnableKeypadPatch - 偏移: 116672"""
        if not self.obj:
            return 0
        return self._call_function(116672, c_long, [c_long, c_long], self.obj, enable)

    def enable_keypad_sync(self, enable, time_out):
        """EnableKeypadSync - 偏移: 109968"""
        if not self.obj:
            return 0
        return self._call_function(109968, c_long, [c_long, c_long, c_long], self.obj, enable, time_out)

    def enable_mouse_accuracy(self, en):
        """EnableMouseAccuracy - 偏移: 123760"""
        if not self.obj:
            return 0
        return self._call_function(123760, c_long, [c_long, c_long], self.obj, en)

    def enable_mouse_msg(self, en):
        """EnableMouseMsg - 偏移: 101344"""
        if not self.obj:
            return 0
        return self._call_function(101344, c_long, [c_long, c_long], self.obj, en)

    def enable_mouse_sync(self, enable, time_out):
        """EnableMouseSync - 偏移: 98496"""
        if not self.obj:
            return 0
        return self._call_function(98496, c_long, [c_long, c_long, c_long], self.obj, enable, time_out)

    def enable_pic_cache(self, en):
        """EnablePicCache - 偏移: 99536"""
        if not self.obj:
            return 0
        return self._call_function(99536, c_long, [c_long, c_long], self.obj, en)

    def enable_real_keypad(self, en):
        """EnableRealKeypad - 偏移: 105648"""
        if not self.obj:
            return 0
        return self._call_function(105648, c_long, [c_long, c_long], self.obj, en)

    def enable_real_mouse(self, en, mousedelay, mousestep):
        """EnableRealMouse - 偏移: 105952"""
        if not self.obj:
            return 0
        return self._call_function(105952, c_long, [c_long, c_long, c_long, c_long], self.obj, en, mousedelay, mousestep)

    def enable_share_dict(self, en):
        """EnableShareDict - 偏移: 108992"""
        if not self.obj:
            return 0
        return self._call_function(108992, c_long, [c_long, c_long], self.obj, en)

    def enable_speed_dx(self, en):
        """EnableSpeedDx - 偏移: 115472"""
        if not self.obj:
            return 0
        return self._call_function(115472, c_long, [c_long, c_long], self.obj, en)

    def encode_file(self, file, pwd):
        """EncodeFile - 偏移: 106528"""
        if not self.obj:
            return 0
        return self._call_function(106528, c_long, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def enter_cri(self):
        """EnterCri - 偏移: 116336"""
        if not self.obj:
            return 0
        return self._call_function(116336, c_long, [c_long], self.obj)

    def enum_ini_key(self, section, file):
        """EnumIniKey - 偏移: 108032"""
        if not self.obj:
            return ''
        result = self._call_function(108032, c_char_p, [c_long, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, file.encode('gbk') if isinstance(file, str) else file)
        return result.decode('gbk') if result else ''

    def enum_ini_key_pwd(self, section, file, pwd):
        """EnumIniKeyPwd - 偏移: 116768"""
        if not self.obj:
            return ''
        result = self._call_function(116768, c_char_p, [c_long, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)
        return result.decode('gbk') if result else ''

    def enum_ini_section(self, file):
        """EnumIniSection - 偏移: 117184"""
        if not self.obj:
            return ''
        result = self._call_function(117184, c_char_p, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)
        return result.decode('gbk') if result else ''

    def enum_ini_section_pwd(self, file, pwd):
        """EnumIniSectionPwd - 偏移: 116992"""
        if not self.obj:
            return ''
        result = self._call_function(116992, c_char_p, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)
        return result.decode('gbk') if result else ''

    def enum_process(self, name):
        """EnumProcess - 偏移: 112288"""
        if not self.obj:
            return ''
        result = self._call_function(112288, c_char_p, [c_long, c_char_p], self.obj, name.encode('gbk') if isinstance(name, str) else name)
        return result.decode('gbk') if result else ''

    def enum_window(self, parent, title, class_name, filter):
        """EnumWindow - 偏移: 115296"""
        if not self.obj:
            return ''
        result = self._call_function(115296, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long], self.obj, parent, title.encode('gbk') if isinstance(title, str) else title, class_name.encode('gbk') if isinstance(class_name, str) else class_name, filter)
        return result.decode('gbk') if result else ''

    def enum_window_by_process(self, process_name, title, class_name, filter):
        """EnumWindowByProcess - 偏移: 110192"""
        if not self.obj:
            return ''
        result = self._call_function(110192, c_char_p, [c_long, c_char_p, c_char_p, c_char_p, c_long], self.obj, process_name.encode('gbk') if isinstance(process_name, str) else process_name, title.encode('gbk') if isinstance(title, str) else title, class_name.encode('gbk') if isinstance(class_name, str) else class_name, filter)
        return result.decode('gbk') if result else ''

    def enum_window_by_process_id(self, pid, title, class_name, filter):
        """EnumWindowByProcessId - 偏移: 124672"""
        if not self.obj:
            return ''
        result = self._call_function(124672, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long], self.obj, pid, title.encode('gbk') if isinstance(title, str) else title, class_name.encode('gbk') if isinstance(class_name, str) else class_name, filter)
        return result.decode('gbk') if result else ''

    def enum_window_super(self, spec1, flag1, type1, spec2, flag2, type2, sort):
        """EnumWindowSuper - 偏移: 107360"""
        if not self.obj:
            return ''
        result = self._call_function(107360, c_char_p, [c_long, c_char_p, c_long, c_long, c_char_p, c_long, c_long, c_long], self.obj, spec1.encode('gbk') if isinstance(spec1, str) else spec1, flag1, type1, spec2.encode('gbk') if isinstance(spec2, str) else spec2, flag2, type2, sort)
        return result.decode('gbk') if result else ''

    def exclude_pos(self, all_pos, type, x1, y1, x2, y2):
        """ExcludePos - 偏移: 120992"""
        if not self.obj:
            return ''
        result = self._call_function(120992, c_char_p, [c_long, c_char_p, c_long, c_long, c_long, c_long, c_long], self.obj, all_pos.encode('gbk') if isinstance(all_pos, str) else all_pos, type, x1, y1, x2, y2)
        return result.decode('gbk') if result else ''

    def execute_cmd(self, cmd, current_dir, time_out):
        """ExecuteCmd - 偏移: 116928"""
        if not self.obj:
            return ''
        result = self._call_function(116928, c_char_p, [c_long, c_char_p, c_char_p, c_long], self.obj, cmd.encode('gbk') if isinstance(cmd, str) else cmd, current_dir.encode('gbk') if isinstance(current_dir, str) else current_dir, time_out)
        return result.decode('gbk') if result else ''

    def exit_os(self, type):
        """ExitOs - 偏移: 115024"""
        if not self.obj:
            return 0
        return self._call_function(115024, c_long, [c_long, c_long], self.obj, type)

    def faq_cancel(self):
        """FaqCancel - 偏移: 113968"""
        if not self.obj:
            return 0
        return self._call_function(113968, c_long, [c_long], self.obj)

    def faq_capture(self, x1, y1, x2, y2, quality, delay, time):
        """FaqCapture - 偏移: 118416"""
        if not self.obj:
            return 0
        return self._call_function(118416, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2, quality, delay, time)

    def faq_capture_from_file(self, x1, y1, x2, y2, file, quality):
        """FaqCaptureFromFile - 偏移: 116256"""
        if not self.obj:
            return 0
        return self._call_function(116256, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_long], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file, quality)

    def faq_capture_string(self, str):
        """FaqCaptureString - 偏移: 106208"""
        if not self.obj:
            return 0
        return self._call_function(106208, c_long, [c_long, c_char_p], self.obj, str.encode('gbk') if isinstance(str, str) else str)

    def faq_fetch(self):
        """FaqFetch - 偏移: 117744"""
        if not self.obj:
            return ''
        result = self._call_function(117744, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def faq_get_size(self, handle):
        """FaqGetSize - 偏移: 103456"""
        if not self.obj:
            return 0
        return self._call_function(103456, c_long, [c_long, c_long], self.obj, handle)

    def faq_is_posted(self):
        """FaqIsPosted - 偏移: 102864"""
        if not self.obj:
            return 0
        return self._call_function(102864, c_long, [c_long], self.obj)

    def faq_post(self, server, handle, request_type, time_out):
        """FaqPost - 偏移: 107440"""
        if not self.obj:
            return 0
        return self._call_function(107440, c_long, [c_long, c_char_p, c_long, c_long, c_long], self.obj, server.encode('gbk') if isinstance(server, str) else server, handle, request_type, time_out)

    def faq_send(self, server, handle, request_type, time_out):
        """FaqSend - 偏移: 114016"""
        if not self.obj:
            return ''
        result = self._call_function(114016, c_char_p, [c_long, c_char_p, c_long, c_long, c_long], self.obj, server.encode('gbk') if isinstance(server, str) else server, handle, request_type, time_out)
        return result.decode('gbk') if result else ''

    def fetch_word(self, x1, y1, x2, y2, color, word):
        """FetchWord - 偏移: 117840"""
        if not self.obj:
            return ''
        result = self._call_function(117840, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, word.encode('gbk') if isinstance(word, str) else word)
        return result.decode('gbk') if result else ''

    def find_color(self, x1, y1, x2, y2, color, sim, dir, x, y):
        """FindColor - 偏移: 106112"""
        if not self.obj:
            return 0
        return self._call_function(106112, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_color_block(self, x1, y1, x2, y2, color, sim, count, width, height, x, y):
        """FindColorBlock - 偏移: 113568"""
        if not self.obj:
            return 0
        return self._call_function(113568, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, count, width, height, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_color_block_ex(self, x1, y1, x2, y2, color, sim, count, width, height):
        """FindColorBlockEx - 偏移: 103840"""
        if not self.obj:
            return ''
        result = self._call_function(103840, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, c_long, c_long], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, count, width, height)
        return result.decode('gbk') if result else ''

    def find_color_e(self, x1, y1, x2, y2, color, sim, dir):
        """FindColorE - 偏移: 120384"""
        if not self.obj:
            return ''
        result = self._call_function(120384, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_color_ex(self, x1, y1, x2, y2, color, sim, dir):
        """FindColorEx - 偏移: 103600"""
        if not self.obj:
            return ''
        result = self._call_function(103600, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_data(self, hwnd, addr_range, data):
        """FindData - 偏移: 109760"""
        if not self.obj:
            return ''
        result = self._call_function(109760, c_char_p, [c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, data.encode('gbk') if isinstance(data, str) else data)
        return result.decode('gbk') if result else ''

    def find_data_ex(self, hwnd, addr_range, data, step, multi_thread, mode):
        """FindDataEx - 偏移: 123200"""
        if not self.obj:
            return ''
        result = self._call_function(123200, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, data.encode('gbk') if isinstance(data, str) else data, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_double(self, hwnd, addr_range, double_value_min, double_value_max):
        """FindDouble - 偏移: 102192"""
        if not self.obj:
            return ''
        result = self._call_function(102192, c_char_p, [c_long, c_long, c_char_p, c_double, c_double], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, double_value_min, double_value_max)
        return result.decode('gbk') if result else ''

    def find_double_ex(self, hwnd, addr_range, double_value_min, double_value_max, step, multi_thread, mode):
        """FindDoubleEx - 偏移: 110416"""
        if not self.obj:
            return ''
        result = self._call_function(110416, c_char_p, [c_long, c_long, c_char_p, c_double, c_double, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, double_value_min, double_value_max, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_float(self, hwnd, addr_range, float_value_min, float_value_max):
        """FindFloat - 偏移: 103216"""
        if not self.obj:
            return ''
        result = self._call_function(103216, c_char_p, [c_long, c_long, c_char_p, c_float, c_float], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, float_value_min, float_value_max)
        return result.decode('gbk') if result else ''

    def find_float_ex(self, hwnd, addr_range, float_value_min, float_value_max, step, multi_thread, mode):
        """FindFloatEx - 偏移: 107040"""
        if not self.obj:
            return ''
        result = self._call_function(107040, c_char_p, [c_long, c_long, c_char_p, c_float, c_float, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, float_value_min, float_value_max, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_input_method(self, id):
        """FindInputMethod - 偏移: 113872"""
        if not self.obj:
            return 0
        return self._call_function(113872, c_long, [c_long, c_char_p], self.obj, id.encode('gbk') if isinstance(id, str) else id)

    def find_int(self, hwnd, addr_range, int_value_min, int_value_max, type):
        """FindInt - 偏移: 106256"""
        if not self.obj:
            return ''
        result = self._call_function(106256, c_char_p, [c_long, c_long, c_char_p, c_longlong, c_longlong, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, int_value_min, int_value_max, type)
        return result.decode('gbk') if result else ''

    def find_int_ex(self, hwnd, addr_range, int_value_min, int_value_max, type, step, multi_thread, mode):
        """FindIntEx - 偏移: 107216"""
        if not self.obj:
            return ''
        result = self._call_function(107216, c_char_p, [c_long, c_long, c_char_p, c_longlong, c_longlong, c_long, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, int_value_min, int_value_max, type, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_mul_color(self, x1, y1, x2, y2, color, sim):
        """FindMulColor - 偏移: 111552"""
        if not self.obj:
            return 0
        return self._call_function(111552, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)

    def find_multi_color(self, x1, y1, x2, y2, first_color, offset_color, sim, dir, x, y):
        """FindMultiColor - 偏移: 109360"""
        if not self.obj:
            return 0
        return self._call_function(109360, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, first_color.encode('gbk') if isinstance(first_color, str) else first_color, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_multi_color_e(self, x1, y1, x2, y2, first_color, offset_color, sim, dir):
        """FindMultiColorE - 偏移: 101696"""
        if not self.obj:
            return ''
        result = self._call_function(101696, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, first_color.encode('gbk') if isinstance(first_color, str) else first_color, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_multi_color_ex(self, x1, y1, x2, y2, first_color, offset_color, sim, dir):
        """FindMultiColorEx - 偏移: 122560"""
        if not self.obj:
            return ''
        result = self._call_function(122560, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, first_color.encode('gbk') if isinstance(first_color, str) else first_color, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_nearest_pos(self, all_pos, type, x, y):
        """FindNearestPos - 偏移: 112480"""
        if not self.obj:
            return ''
        result = self._call_function(112480, c_char_p, [c_long, c_char_p, c_long, c_long, c_long], self.obj, all_pos.encode('gbk') if isinstance(all_pos, str) else all_pos, type, x, y)
        return result.decode('gbk') if result else ''

    def find_pic(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir, x, y):
        """FindPic - 偏移: 104032"""
        if not self.obj:
            return 0
        return self._call_function(104032, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_e(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """FindPicE - 偏移: 114144"""
        if not self.obj:
            return ''
        result = self._call_function(114144, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_ex(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """FindPicEx - 偏移: 108160"""
        if not self.obj:
            return ''
        result = self._call_function(108160, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_ex_s(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """FindPicExS - 偏移: 100368"""
        if not self.obj:
            return ''
        result = self._call_function(100368, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_mem(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir, x, y):
        """FindPicMem - 偏移: 103696"""
        if not self.obj:
            return 0
        return self._call_function(103696, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_mem_e(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """FindPicMemE - 偏移: 109264"""
        if not self.obj:
            return ''
        result = self._call_function(109264, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_mem_ex(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """FindPicMemEx - 偏移: 101440"""
        if not self.obj:
            return ''
        result = self._call_function(101440, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_s(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir, x, y):
        """FindPicS - 偏移: 101952"""
        if not self.obj:
            return ''
        result = self._call_function(101952, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)
        return result.decode('gbk') if result else ''

    def find_pic_sim(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir, x, y):
        """FindPicSim - 偏移: 98768"""
        if not self.obj:
            return 0
        return self._call_function(98768, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_sim_e(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """FindPicSimE - 偏移: 123440"""
        if not self.obj:
            return ''
        result = self._call_function(123440, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_sim_ex(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """FindPicSimEx - 偏移: 113728"""
        if not self.obj:
            return ''
        result = self._call_function(113728, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_sim_mem(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir, x, y):
        """FindPicSimMem - 偏移: 121744"""
        if not self.obj:
            return 0
        return self._call_function(121744, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_sim_mem_e(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """FindPicSimMemE - 偏移: 113296"""
        if not self.obj:
            return ''
        result = self._call_function(113296, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_sim_mem_ex(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """FindPicSimMemEx - 偏移: 124912"""
        if not self.obj:
            return ''
        result = self._call_function(124912, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_shape(self, x1, y1, x2, y2, offset_color, sim, dir, x, y):
        """FindShape - 偏移: 123856"""
        if not self.obj:
            return 0
        return self._call_function(123856, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_shape_e(self, x1, y1, x2, y2, offset_color, sim, dir):
        """FindShapeE - 偏移: 120592"""
        if not self.obj:
            return ''
        result = self._call_function(120592, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_shape_ex(self, x1, y1, x2, y2, offset_color, sim, dir):
        """FindShapeEx - 偏移: 99792"""
        if not self.obj:
            return ''
        result = self._call_function(99792, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_str(self, x1, y1, x2, y2, str, color, sim, x, y):
        """FindStr - 偏移: 110320"""
        if not self.obj:
            return 0
        return self._call_function(110320, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_str_e(self, x1, y1, x2, y2, str, color, sim):
        """FindStrE - 偏移: 122400"""
        if not self.obj:
            return ''
        result = self._call_function(122400, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_ex(self, x1, y1, x2, y2, str, color, sim):
        """FindStrEx - 偏移: 106640"""
        if not self.obj:
            return ''
        result = self._call_function(106640, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_ex_s(self, x1, y1, x2, y2, str, color, sim):
        """FindStrExS - 偏移: 100528"""
        if not self.obj:
            return ''
        result = self._call_function(100528, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast(self, x1, y1, x2, y2, str, color, sim, x, y):
        """FindStrFast - 偏移: 115584"""
        if not self.obj:
            return 0
        return self._call_function(115584, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_str_fast_e(self, x1, y1, x2, y2, str, color, sim):
        """FindStrFastE - 偏移: 120288"""
        if not self.obj:
            return ''
        result = self._call_function(120288, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast_ex(self, x1, y1, x2, y2, str, color, sim):
        """FindStrFastEx - 偏移: 122000"""
        if not self.obj:
            return ''
        result = self._call_function(122000, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast_ex_s(self, x1, y1, x2, y2, str, color, sim):
        """FindStrFastExS - 偏移: 124176"""
        if not self.obj:
            return ''
        result = self._call_function(124176, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast_s(self, x1, y1, x2, y2, str, color, sim, x, y):
        """FindStrFastS - 偏移: 98672"""
        if not self.obj:
            return ''
        result = self._call_function(98672, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)
        return result.decode('gbk') if result else ''

    def find_str_s(self, x1, y1, x2, y2, str, color, sim, x, y):
        """FindStrS - 偏移: 116832"""
        if not self.obj:
            return ''
        result = self._call_function(116832, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)
        return result.decode('gbk') if result else ''

    def find_str_with_font(self, x1, y1, x2, y2, str, color, sim, font_name, font_size, flag, x, y):
        """FindStrWithFont - 偏移: 119856"""
        if not self.obj:
            return 0
        return self._call_function(119856, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_char_p, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_str_with_font_e(self, x1, y1, x2, y2, str, color, sim, font_name, font_size, flag):
        """FindStrWithFontE - 偏移: 112544"""
        if not self.obj:
            return ''
        result = self._call_function(112544, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag)
        return result.decode('gbk') if result else ''

    def find_str_with_font_ex(self, x1, y1, x2, y2, str, color, sim, font_name, font_size, flag):
        """FindStrWithFontEx - 偏移: 118848"""
        if not self.obj:
            return ''
        result = self._call_function(118848, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, str.encode('gbk') if isinstance(str, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag)
        return result.decode('gbk') if result else ''

    def find_string(self, hwnd, addr_range, string_value, type):
        """FindString - 偏移: 110752"""
        if not self.obj:
            return ''
        result = self._call_function(110752, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, string_value.encode('gbk') if isinstance(string_value, str) else string_value, type)
        return result.decode('gbk') if result else ''

    def find_string_ex(self, hwnd, addr_range, string_value, type, step, multi_thread, mode):
        """FindStringEx - 偏移: 124384"""
        if not self.obj:
            return ''
        result = self._call_function(124384, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, string_value.encode('gbk') if isinstance(string_value, str) else string_value, type, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_window(self, class_name, title_name):
        """FindWindow - 偏移: 104288"""
        if not self.obj:
            return 0
        return self._call_function(104288, c_long, [c_long, c_char_p, c_char_p], self.obj, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_by_process(self, process_name, class_name, title_name):
        """FindWindowByProcess - 偏移: 122336"""
        if not self.obj:
            return 0
        return self._call_function(122336, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, process_name.encode('gbk') if isinstance(process_name, str) else process_name, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_by_process_id(self, process_id, class_name, title_name):
        """FindWindowByProcessId - 偏移: 104176"""
        if not self.obj:
            return 0
        return self._call_function(104176, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, process_id, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_ex(self, parent, class_name, title_name):
        """FindWindowEx - 偏移: 115408"""
        if not self.obj:
            return 0
        return self._call_function(115408, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, parent, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_super(self, spec1, flag1, type1, spec2, flag2, type2):
        """FindWindowSuper - 偏移: 108432"""
        if not self.obj:
            return 0
        return self._call_function(108432, c_long, [c_long, c_char_p, c_long, c_long, c_char_p, c_long, c_long], self.obj, spec1.encode('gbk') if isinstance(spec1, str) else spec1, flag1, type1, spec2.encode('gbk') if isinstance(spec2, str) else spec2, flag2, type2)

    def float_to_data(self, float_value):
        """FloatToData - 偏移: 100464"""
        if not self.obj:
            return ''
        result = self._call_function(100464, c_char_p, [c_long, c_float], self.obj, float_value)
        return result.decode('gbk') if result else ''

    def foobar_clear_text(self, hwnd):
        """FoobarClearText - 偏移: 113072"""
        if not self.obj:
            return 0
        return self._call_function(113072, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_close(self, hwnd):
        """FoobarClose - 偏移: 102480"""
        if not self.obj:
            return 0
        return self._call_function(102480, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_draw_line(self, hwnd, x1, y1, x2, y2, color, style, width):
        """FoobarDrawLine - 偏移: 116384"""
        if not self.obj:
            return 0
        return self._call_function(116384, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, style, width)

    def foobar_draw_pic(self, hwnd, x, y, pic, trans_color):
        """FoobarDrawPic - 偏移: 114288"""
        if not self.obj:
            return 0
        return self._call_function(114288, c_long, [c_long, c_long, c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, x, y, pic.encode('gbk') if isinstance(pic, str) else pic, trans_color.encode('gbk') if isinstance(trans_color, str) else trans_color)

    def foobar_draw_text(self, hwnd, x, y, w, h, text, color, align):
        """FoobarDrawText - 偏移: 119712"""
        if not self.obj:
            return 0
        return self._call_function(119712, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long], self.obj, hwnd, x, y, w, h, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color, align)

    def foobar_fill_rect(self, hwnd, x1, y1, x2, y2, color):
        """FoobarFillRect - 偏移: 103136"""
        if not self.obj:
            return 0
        return self._call_function(103136, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, hwnd, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color)

    def foobar_lock(self, hwnd):
        """FoobarLock - 偏移: 109824"""
        if not self.obj:
            return 0
        return self._call_function(109824, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_print_text(self, hwnd, text, color):
        """FoobarPrintText - 偏移: 108720"""
        if not self.obj:
            return 0
        return self._call_function(108720, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color)

    def foobar_set_font(self, hwnd, font_name, size, flag):
        """FoobarSetFont - 偏移: 111632"""
        if not self.obj:
            return 0
        return self._call_function(111632, c_long, [c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, font_name.encode('gbk') if isinstance(font_name, str) else font_name, size, flag)

    def foobar_set_save(self, hwnd, file, en, header):
        """FoobarSetSave - 偏移: 124736"""
        if not self.obj:
            return 0
        return self._call_function(124736, c_long, [c_long, c_long, c_char_p, c_long, c_char_p], self.obj, hwnd, file.encode('gbk') if isinstance(file, str) else file, en, header.encode('gbk') if isinstance(header, str) else header)

    def foobar_set_trans(self, hwnd, trans, color, sim):
        """FoobarSetTrans - 偏移: 117248"""
        if not self.obj:
            return 0
        return self._call_function(117248, c_long, [c_long, c_long, c_long, c_char_p, c_double], self.obj, hwnd, trans, color.encode('gbk') if isinstance(color, str) else color, sim)

    def foobar_start_gif(self, hwnd, x, y, pic_name, repeat_limit, delay):
        """FoobarStartGif - 偏移: 117664"""
        if not self.obj:
            return 0
        return self._call_function(117664, c_long, [c_long, c_long, c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, x, y, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, repeat_limit, delay)

    def foobar_stop_gif(self, hwnd, x, y, pic_name):
        """FoobarStopGif - 偏移: 108096"""
        if not self.obj:
            return 0
        return self._call_function(108096, c_long, [c_long, c_long, c_long, c_long, c_char_p], self.obj, hwnd, x, y, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)

    def foobar_text_line_gap(self, hwnd, gap):
        """FoobarTextLineGap - 偏移: 124848"""
        if not self.obj:
            return 0
        return self._call_function(124848, c_long, [c_long, c_long, c_long], self.obj, hwnd, gap)

    def foobar_text_print_dir(self, hwnd, dir):
        """FoobarTextPrintDir - 偏移: 103072"""
        if not self.obj:
            return 0
        return self._call_function(103072, c_long, [c_long, c_long, c_long], self.obj, hwnd, dir)

    def foobar_text_rect(self, hwnd, x, y, w, h):
        """FoobarTextRect - 偏移: 108784"""
        if not self.obj:
            return 0
        return self._call_function(108784, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h)

    def foobar_unlock(self, hwnd):
        """FoobarUnlock - 偏移: 123952"""
        if not self.obj:
            return 0
        return self._call_function(123952, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_update(self, hwnd):
        """FoobarUpdate - 偏移: 119280"""
        if not self.obj:
            return 0
        return self._call_function(119280, c_long, [c_long, c_long], self.obj, hwnd)

    def force_un_bind_window(self, hwnd):
        """ForceUnBindWindow - 偏移: 120144"""
        if not self.obj:
            return 0
        return self._call_function(120144, c_long, [c_long, c_long], self.obj, hwnd)

    def free_pic(self, pic_name):
        """FreePic - 偏移: 103408"""
        if not self.obj:
            return 0
        return self._call_function(103408, c_long, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)

    def free_process_memory(self, hwnd):
        """FreeProcessMemory - 偏移: 111120"""
        if not self.obj:
            return 0
        return self._call_function(111120, c_long, [c_long, c_long], self.obj, hwnd)

    def get_ave_hsv(self, x1, y1, x2, y2):
        """GetAveHSV - 偏移: 100176"""
        if not self.obj:
            return ''
        result = self._call_function(100176, c_char_p, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)
        return result.decode('gbk') if result else ''

    def get_ave_rgb(self, x1, y1, x2, y2):
        """GetAveRGB - 偏移: 118192"""
        if not self.obj:
            return ''
        result = self._call_function(118192, c_char_p, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)
        return result.decode('gbk') if result else ''

    def get_base_path(self):
        """GetBasePath - 偏移: 107312"""
        if not self.obj:
            return ''
        result = self._call_function(107312, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_bind_window(self):
        """GetBindWindow - 偏移: 109712"""
        if not self.obj:
            return 0
        return self._call_function(109712, c_long, [c_long], self.obj)

    def get_client_rect(self, hwnd, x1, y1, x2, y2):
        """GetClientRect - 偏移: 105808"""
        if not self.obj:
            return 0
        return self._call_function(105808, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x1) if isinstance(x1, c_long) else x1, byref(y1) if isinstance(y1, c_long) else y1, byref(x2) if isinstance(x2, c_long) else x2, byref(y2) if isinstance(y2, c_long) else y2)

    def get_client_size(self, hwnd, width, height):
        """GetClientSize - 偏移: 103344"""
        if not self.obj:
            return 0
        return self._call_function(103344, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(width) if isinstance(width, c_long) else width, byref(height) if isinstance(height, c_long) else height)

    def get_clipboard(self):
        """GetClipboard - 偏移: 116624"""
        if not self.obj:
            return ''
        result = self._call_function(116624, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_color(self, x, y):
        """GetColor - 偏移: 117424"""
        if not self.obj:
            return ''
        result = self._call_function(117424, c_char_p, [c_long, c_long, c_long], self.obj, x, y)
        return result.decode('gbk') if result else ''

    def get_color_bgr(self, x, y):
        """GetColorBGR - 偏移: 100000"""
        if not self.obj:
            return ''
        result = self._call_function(100000, c_char_p, [c_long, c_long, c_long], self.obj, x, y)
        return result.decode('gbk') if result else ''

    def get_color_hsv(self, x, y):
        """GetColorHSV - 偏移: 116192"""
        if not self.obj:
            return ''
        result = self._call_function(116192, c_char_p, [c_long, c_long, c_long], self.obj, x, y)
        return result.decode('gbk') if result else ''

    def get_color_num(self, x1, y1, x2, y2, color, sim):
        """GetColorNum - 偏移: 124048"""
        if not self.obj:
            return 0
        return self._call_function(124048, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)

    def get_command_line(self, hwnd):
        """GetCommandLine - 偏移: 100752"""
        if not self.obj:
            return ''
        result = self._call_function(100752, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_cpu_type(self):
        """GetCpuType - 偏移: 102432"""
        if not self.obj:
            return 0
        return self._call_function(102432, c_long, [c_long], self.obj)

    def get_cpu_usage(self):
        """GetCpuUsage - 偏移: 121072"""
        if not self.obj:
            return 0
        return self._call_function(121072, c_long, [c_long], self.obj)

    def get_cursor_pos(self, x, y):
        """GetCursorPos - 偏移: 121680"""
        if not self.obj:
            return 0
        return self._call_function(121680, c_long, [c_long, POINTER(c_long), POINTER(c_long)], self.obj, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def get_cursor_shape(self):
        """GetCursorShape - 偏移: 111984"""
        if not self.obj:
            return ''
        result = self._call_function(111984, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_cursor_shape_ex(self, type):
        """GetCursorShapeEx - 偏移: 117488"""
        if not self.obj:
            return ''
        result = self._call_function(117488, c_char_p, [c_long, c_long], self.obj, type)
        return result.decode('gbk') if result else ''

    def get_cursor_spot(self):
        """GetCursorSpot - 偏移: 125056"""
        if not self.obj:
            return ''
        result = self._call_function(125056, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_dpi(self):
        """GetDPI - 偏移: 107664"""
        if not self.obj:
            return 0
        return self._call_function(107664, c_long, [c_long], self.obj)

    def get_dict(self, index, font_index):
        """GetDict - 偏移: 99184"""
        if not self.obj:
            return ''
        result = self._call_function(99184, c_char_p, [c_long, c_long, c_long], self.obj, index, font_index)
        return result.decode('gbk') if result else ''

    def get_dict_count(self, index):
        """GetDictCount - 偏移: 99584"""
        if not self.obj:
            return 0
        return self._call_function(99584, c_long, [c_long, c_long], self.obj, index)

    def get_dict_info(self, str, font_name, font_size, flag):
        """GetDictInfo - 偏移: 100624"""
        if not self.obj:
            return ''
        result = self._call_function(100624, c_char_p, [c_long, c_char_p, c_char_p, c_long, c_long], self.obj, str.encode('gbk') if isinstance(str, str) else str, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag)
        return result.decode('gbk') if result else ''

    def get_dir(self, type):
        """GetDir - 偏移: 124512"""
        if not self.obj:
            return ''
        result = self._call_function(124512, c_char_p, [c_long, c_long], self.obj, type)
        return result.decode('gbk') if result else ''

    def get_disk_model(self, index):
        """GetDiskModel - 偏移: 102128"""
        if not self.obj:
            return ''
        result = self._call_function(102128, c_char_p, [c_long, c_long], self.obj, index)
        return result.decode('gbk') if result else ''

    def get_disk_reversion(self, index):
        """GetDiskReversion - 偏移: 109040"""
        if not self.obj:
            return ''
        result = self._call_function(109040, c_char_p, [c_long, c_long], self.obj, index)
        return result.decode('gbk') if result else ''

    def get_disk_serial(self, index):
        """GetDiskSerial - 偏移: 112352"""
        if not self.obj:
            return ''
        result = self._call_function(112352, c_char_p, [c_long, c_long], self.obj, index)
        return result.decode('gbk') if result else ''

    def get_display_info(self):
        """GetDisplayInfo - 偏移: 122992"""
        if not self.obj:
            return ''
        result = self._call_function(122992, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_dm_count(self):
        """GetDmCount - 偏移: 125008"""
        if not self.obj:
            return 0
        return self._call_function(125008, c_long, [c_long], self.obj)

    def get_file_length(self, file):
        """GetFileLength - 偏移: 111296"""
        if not self.obj:
            return 0
        return self._call_function(111296, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def get_foreground_focus(self):
        """GetForegroundFocus - 偏移: 108512"""
        if not self.obj:
            return 0
        return self._call_function(108512, c_long, [c_long], self.obj)

    def get_foreground_window(self):
        """GetForegroundWindow - 偏移: 115360"""
        if not self.obj:
            return 0
        return self._call_function(115360, c_long, [c_long], self.obj)

    def get_fps(self):
        """GetFps - 偏移: 106016"""
        if not self.obj:
            return 0
        return self._call_function(106016, c_long, [c_long], self.obj)

    def get_id(self):
        """GetID - 偏移: 105184"""
        if not self.obj:
            return 0
        return self._call_function(105184, c_long, [c_long], self.obj)

    def get_key_state(self, vk):
        """GetKeyState - 偏移: 103296"""
        if not self.obj:
            return 0
        return self._call_function(103296, c_long, [c_long, c_long], self.obj, vk)

    def get_last_error(self):
        """GetLastError - 偏移: 107936"""
        if not self.obj:
            return 0
        return self._call_function(107936, c_long, [c_long], self.obj)

    def get_locale(self):
        """GetLocale - 偏移: 122096"""
        if not self.obj:
            return 0
        return self._call_function(122096, c_long, [c_long], self.obj)

    def get_mac(self):
        """GetMac - 偏移: 123536"""
        if not self.obj:
            return ''
        result = self._call_function(123536, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_machine_code(self):
        """GetMachineCode - 偏移: 113456"""
        if not self.obj:
            return ''
        result = self._call_function(113456, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_machine_code_no_mac(self):
        """GetMachineCodeNoMac - 偏移: 120544"""
        if not self.obj:
            return ''
        result = self._call_function(120544, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_memory_usage(self):
        """GetMemoryUsage - 偏移: 106064"""
        if not self.obj:
            return 0
        return self._call_function(106064, c_long, [c_long], self.obj)

    def get_module_base_addr(self, hwnd, module_name):
        """GetModuleBaseAddr - 偏移: 108848"""
        if not self.obj:
            return 0
        return self._call_function(108848, c_longlong, [c_long, c_long, c_char_p], self.obj, hwnd, module_name.encode('gbk') if isinstance(module_name, str) else module_name)

    def get_module_size(self, hwnd, module_name):
        """GetModuleSize - 偏移: 120016"""
        if not self.obj:
            return 0
        return self._call_function(120016, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, module_name.encode('gbk') if isinstance(module_name, str) else module_name)

    def get_mouse_point_window(self):
        """GetMousePointWindow - 偏移: 105424"""
        if not self.obj:
            return 0
        return self._call_function(105424, c_long, [c_long], self.obj)

    def get_mouse_speed(self):
        """GetMouseSpeed - 偏移: 99248"""
        if not self.obj:
            return 0
        return self._call_function(99248, c_long, [c_long], self.obj)

    def get_net_time(self):
        """GetNetTime - 偏移: 107712"""
        if not self.obj:
            return ''
        result = self._call_function(107712, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_net_time_by_ip(self, ip):
        """GetNetTimeByIp - 偏移: 105360"""
        if not self.obj:
            return ''
        result = self._call_function(105360, c_char_p, [c_long, c_char_p], self.obj, ip.encode('gbk') if isinstance(ip, str) else ip)
        return result.decode('gbk') if result else ''

    def get_net_time_safe(self):
        """GetNetTimeSafe - 偏移: 107760"""
        if not self.obj:
            return ''
        result = self._call_function(107760, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_now_dict(self):
        """GetNowDict - 偏移: 101584"""
        if not self.obj:
            return 0
        return self._call_function(101584, c_long, [c_long], self.obj)

    def get_os_build_number(self):
        """GetOsBuildNumber - 偏移: 104240"""
        if not self.obj:
            return 0
        return self._call_function(104240, c_long, [c_long], self.obj)

    def get_os_type(self):
        """GetOsType - 偏移: 121632"""
        if not self.obj:
            return 0
        return self._call_function(121632, c_long, [c_long], self.obj)

    def get_path(self):
        """GetPath - 偏移: 109600"""
        if not self.obj:
            return ''
        result = self._call_function(109600, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_pic_size(self, pic_name):
        """GetPicSize - 偏移: 114960"""
        if not self.obj:
            return ''
        result = self._call_function(114960, c_char_p, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)
        return result.decode('gbk') if result else ''

    def get_point_window(self, x, y):
        """GetPointWindow - 偏移: 118544"""
        if not self.obj:
            return 0
        return self._call_function(118544, c_long, [c_long, c_long, c_long], self.obj, x, y)

    def get_process_info(self, pid):
        """GetProcessInfo - 偏移: 119024"""
        if not self.obj:
            return ''
        result = self._call_function(119024, c_char_p, [c_long, c_long], self.obj, pid)
        return result.decode('gbk') if result else ''

    def get_real_path(self, path):
        """GetRealPath - 偏移: 105008"""
        if not self.obj:
            return ''
        result = self._call_function(105008, c_char_p, [c_long, c_char_p], self.obj, path.encode('gbk') if isinstance(path, str) else path)
        return result.decode('gbk') if result else ''

    def get_remote_api_address(self, hwnd, base_addr, fun_name):
        """GetRemoteApiAddress - 偏移: 122192"""
        if not self.obj:
            return 0
        return self._call_function(122192, c_longlong, [c_long, c_long, c_longlong, c_char_p], self.obj, hwnd, base_addr, fun_name.encode('gbk') if isinstance(fun_name, str) else fun_name)

    def get_result_count(self, str):
        """GetResultCount - 偏移: 116720"""
        if not self.obj:
            return 0
        return self._call_function(116720, c_long, [c_long, c_char_p], self.obj, str.encode('gbk') if isinstance(str, str) else str)

    def get_result_pos(self, str, index, x, y):
        """GetResultPos - 偏移: 102800"""
        if not self.obj:
            return 0
        return self._call_function(102800, c_long, [c_long, c_char_p, c_long, POINTER(c_long), POINTER(c_long)], self.obj, str.encode('gbk') if isinstance(str, str) else str, index, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def get_screen_data(self, x1, y1, x2, y2):
        """GetScreenData - 偏移: 125104"""
        if not self.obj:
            return 0
        return self._call_function(125104, c_long, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)

    def get_screen_data_bmp(self, x1, y1, x2, y2, data, size):
        """GetScreenDataBmp - 偏移: 107136"""
        if not self.obj:
            return 0
        return self._call_function(107136, c_long, [c_long, c_long, c_long, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, byref(data) if isinstance(data, c_long) else data, byref(size) if isinstance(size, c_long) else size)

    def get_screen_depth(self):
        """GetScreenDepth - 偏移: 102384"""
        if not self.obj:
            return 0
        return self._call_function(102384, c_long, [c_long], self.obj)

    def get_screen_height(self):
        """GetScreenHeight - 偏移: 117792"""
        if not self.obj:
            return 0
        return self._call_function(117792, c_long, [c_long], self.obj)

    def get_screen_width(self):
        """GetScreenWidth - 偏移: 113920"""
        if not self.obj:
            return 0
        return self._call_function(113920, c_long, [c_long], self.obj)

    def get_special_window(self, flag):
        """GetSpecialWindow - 偏移: 102336"""
        if not self.obj:
            return 0
        return self._call_function(102336, c_long, [c_long, c_long], self.obj, flag)

    def get_system_info(self, type, method):
        """GetSystemInfo - 偏移: 115680"""
        if not self.obj:
            return ''
        result = self._call_function(115680, c_char_p, [c_long, c_char_p, c_long], self.obj, type.encode('gbk') if isinstance(type, str) else type, method)
        return result.decode('gbk') if result else ''

    def get_time(self):
        """GetTime - 偏移: 103504"""
        if not self.obj:
            return 0
        return self._call_function(103504, c_long, [c_long], self.obj)

    def get_window(self, hwnd, flag):
        """GetWindow - 偏移: 120752"""
        if not self.obj:
            return 0
        return self._call_function(120752, c_long, [c_long, c_long, c_long], self.obj, hwnd, flag)

    def get_window_class(self, hwnd):
        """GetWindowClass - 偏移: 117056"""
        if not self.obj:
            return ''
        result = self._call_function(117056, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_window_process_id(self, hwnd):
        """GetWindowProcessId - 偏移: 124464"""
        if not self.obj:
            return 0
        return self._call_function(124464, c_long, [c_long, c_long], self.obj, hwnd)

    def get_window_process_path(self, hwnd):
        """GetWindowProcessPath - 偏移: 105232"""
        if not self.obj:
            return ''
        result = self._call_function(105232, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_window_rect(self, hwnd, x1, y1, x2, y2):
        """GetWindowRect - 偏移: 122656"""
        if not self.obj:
            return 0
        return self._call_function(122656, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x1) if isinstance(x1, c_long) else x1, byref(y1) if isinstance(y1, c_long) else y1, byref(x2) if isinstance(x2, c_long) else x2, byref(y2) if isinstance(y2, c_long) else y2)

    def get_window_state(self, hwnd, flag):
        """GetWindowState - 偏移: 100112"""
        if not self.obj:
            return 0
        return self._call_function(100112, c_long, [c_long, c_long, c_long], self.obj, hwnd, flag)

    def get_window_thread_id(self, hwnd):
        """GetWindowThreadId - 偏移: 107504"""
        if not self.obj:
            return 0
        return self._call_function(107504, c_long, [c_long, c_long], self.obj, hwnd)

    def get_window_title(self, hwnd):
        """GetWindowTitle - 偏移: 110816"""
        if not self.obj:
            return ''
        result = self._call_function(110816, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_word_result_count(self, str):
        """GetWordResultCount - 偏移: 103984"""
        if not self.obj:
            return 0
        return self._call_function(103984, c_long, [c_long, c_char_p], self.obj, str.encode('gbk') if isinstance(str, str) else str)

    def get_word_result_pos(self, str, index, x, y):
        """GetWordResultPos - 偏移: 114352"""
        if not self.obj:
            return 0
        return self._call_function(114352, c_long, [c_long, c_char_p, c_long, POINTER(c_long), POINTER(c_long)], self.obj, str.encode('gbk') if isinstance(str, str) else str, index, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def get_word_result_str(self, str, index):
        """GetWordResultStr - 偏移: 104768"""
        if not self.obj:
            return ''
        result = self._call_function(104768, c_char_p, [c_long, c_char_p, c_long], self.obj, str.encode('gbk') if isinstance(str, str) else str, index)
        return result.decode('gbk') if result else ''

    def get_words(self, x1, y1, x2, y2, color, sim):
        """GetWords - 偏移: 107808"""
        if not self.obj:
            return ''
        result = self._call_function(107808, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def get_words_no_dict(self, x1, y1, x2, y2, color):
        """GetWordsNoDict - 偏移: 99024"""
        if not self.obj:
            return ''
        result = self._call_function(99024, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color)
        return result.decode('gbk') if result else ''

    def hack_speed(self, rate):
        """HackSpeed - 偏移: 104352"""
        if not self.obj:
            return 0
        return self._call_function(104352, c_long, [c_long, c_double], self.obj, rate)

    def hex32(self, v):
        """Hex32 - 偏移: 110080"""
        if not self.obj:
            return ''
        result = self._call_function(110080, c_char_p, [c_long, c_long], self.obj, v)
        return result.decode('gbk') if result else ''

    def hex64(self, v):
        """Hex64 - 偏移: 105296"""
        if not self.obj:
            return ''
        result = self._call_function(105296, c_char_p, [c_long, c_longlong], self.obj, v)
        return result.decode('gbk') if result else ''

    def image_to_bmp(self, pic_name, bmp_name):
        """ImageToBmp - 偏移: 109152"""
        if not self.obj:
            return 0
        return self._call_function(109152, c_long, [c_long, c_char_p, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, bmp_name.encode('gbk') if isinstance(bmp_name, str) else bmp_name)

    def init_cri(self):
        """InitCri - 偏移: 120240"""
        if not self.obj:
            return 0
        return self._call_function(120240, c_long, [c_long], self.obj)

    def int64_to_int32(self, v):
        """Int64ToInt32 - 偏移: 110880"""
        if not self.obj:
            return 0
        return self._call_function(110880, c_long, [c_long, c_longlong], self.obj, v)

    def int_to_data(self, int_value, type):
        """IntToData - 偏移: 122272"""
        if not self.obj:
            return ''
        result = self._call_function(122272, c_char_p, [c_long, c_longlong, c_long], self.obj, int_value, type)
        return result.decode('gbk') if result else ''

    def is64_bit(self):
        """Is64Bit - 偏移: 110512"""
        if not self.obj:
            return 0
        return self._call_function(110512, c_long, [c_long], self.obj)

    def is_bind(self, hwnd):
        """IsBind - 偏移: 119232"""
        if not self.obj:
            return 0
        return self._call_function(119232, c_long, [c_long, c_long], self.obj, hwnd)

    def is_display_dead(self, x1, y1, x2, y2, t):
        """IsDisplayDead - 偏移: 114896"""
        if not self.obj:
            return 0
        return self._call_function(114896, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2, t)

    def is_file_exist(self, file):
        """IsFileExist - 偏移: 113824"""
        if not self.obj:
            return 0
        return self._call_function(113824, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def is_folder_exist(self, folder):
        """IsFolderExist - 偏移: 121184"""
        if not self.obj:
            return 0
        return self._call_function(121184, c_long, [c_long, c_char_p], self.obj, folder.encode('gbk') if isinstance(folder, str) else folder)

    def is_surrpot_vt(self):
        """IsSurrpotVt - 偏移: 106992"""
        if not self.obj:
            return 0
        return self._call_function(106992, c_long, [c_long], self.obj)

    def key_down(self, vk):
        """KeyDown - 偏移: 115120"""
        if not self.obj:
            return 0
        return self._call_function(115120, c_long, [c_long, c_long], self.obj, vk)

    def key_down_char(self, key_str):
        """KeyDownChar - 偏移: 105600"""
        if not self.obj:
            return 0
        return self._call_function(105600, c_long, [c_long, c_char_p], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str)

    def key_press(self, vk):
        """KeyPress - 偏移: 118688"""
        if not self.obj:
            return 0
        return self._call_function(118688, c_long, [c_long, c_long], self.obj, vk)

    def key_press_char(self, key_str):
        """KeyPressChar - 偏移: 116464"""
        if not self.obj:
            return 0
        return self._call_function(116464, c_long, [c_long, c_char_p], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str)

    def key_press_str(self, key_str, delay):
        """KeyPressStr - 偏移: 102528"""
        if not self.obj:
            return 0
        return self._call_function(102528, c_long, [c_long, c_char_p, c_long], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str, delay)

    def key_up(self, vk):
        """KeyUp - 偏移: 113248"""
        if not self.obj:
            return 0
        return self._call_function(113248, c_long, [c_long, c_long], self.obj, vk)

    def key_up_char(self, key_str):
        """KeyUpChar - 偏移: 121904"""
        if not self.obj:
            return 0
        return self._call_function(121904, c_long, [c_long, c_char_p], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str)

    def leave_cri(self):
        """LeaveCri - 偏移: 120816"""
        if not self.obj:
            return 0
        return self._call_function(120816, c_long, [c_long], self.obj)

    def left_click(self):
        """LeftClick - 偏移: 118096"""
        if not self.obj:
            return 0
        return self._call_function(118096, c_long, [c_long], self.obj)

    def left_double_click(self):
        """LeftDoubleClick - 偏移: 101136"""
        if not self.obj:
            return 0
        return self._call_function(101136, c_long, [c_long], self.obj)

    def left_down(self):
        """LeftDown - 偏移: 106736"""
        if not self.obj:
            return 0
        return self._call_function(106736, c_long, [c_long], self.obj)

    def left_up(self):
        """LeftUp - 偏移: 113680"""
        if not self.obj:
            return 0
        return self._call_function(113680, c_long, [c_long], self.obj)

    def load_ai(self, file):
        """LoadAi - 偏移: 106944"""
        if not self.obj:
            return 0
        return self._call_function(106944, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def load_ai_memory(self, addr, size):
        """LoadAiMemory - 偏移: 108256"""
        if not self.obj:
            return 0
        return self._call_function(108256, c_long, [c_long, c_long, c_long], self.obj, addr, size)

    def load_pic(self, pic_name):
        """LoadPic - 偏移: 124128"""
        if not self.obj:
            return 0
        return self._call_function(124128, c_long, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)

    def load_pic_byte(self, addr, size, name):
        """LoadPicByte - 偏移: 121408"""
        if not self.obj:
            return 0
        return self._call_function(121408, c_long, [c_long, c_long, c_long, c_char_p], self.obj, addr, size, name.encode('gbk') if isinstance(name, str) else name)

    def lock_display(self, lock):
        """LockDisplay - 偏移: 108304"""
        if not self.obj:
            return 0
        return self._call_function(108304, c_long, [c_long, c_long], self.obj, lock)

    def lock_input(self, lock):
        """LockInput - 偏移: 124272"""
        if not self.obj:
            return 0
        return self._call_function(124272, c_long, [c_long, c_long], self.obj, lock)

    def lock_mouse_rect(self, x1, y1, x2, y2):
        """LockMouseRect - 偏移: 119792"""
        if not self.obj:
            return 0
        return self._call_function(119792, c_long, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)

    def match_pic_name(self, pic_name):
        """MatchPicName - 偏移: 117984"""
        if not self.obj:
            return ''
        result = self._call_function(117984, c_char_p, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)
        return result.decode('gbk') if result else ''

    def md5(self, str):
        """Md5 - 偏移: 117376"""
        if not self.obj:
            return ''
        result = self._call_function(117376, c_char_p, [c_long, c_char_p], self.obj, str.encode('gbk') if isinstance(str, str) else str)
        return result.decode('gbk') if result else ''

    def middle_click(self):
        """MiddleClick - 偏移: 108560"""
        if not self.obj:
            return 0
        return self._call_function(108560, c_long, [c_long], self.obj)

    def middle_down(self):
        """MiddleDown - 偏移: 109872"""
        if not self.obj:
            return 0
        return self._call_function(109872, c_long, [c_long], self.obj)

    def middle_up(self):
        """MiddleUp - 偏移: 115072"""
        if not self.obj:
            return 0
        return self._call_function(115072, c_long, [c_long], self.obj)

    def move_dd(self, dx, dy):
        """MoveDD - 偏移: 121840"""
        if not self.obj:
            return 0
        return self._call_function(121840, c_long, [c_long, c_long, c_long], self.obj, dx, dy)

    def move_file(self, src_file, dst_file):
        """MoveFile - 偏移: 102272"""
        if not self.obj:
            return 0
        return self._call_function(102272, c_long, [c_long, c_char_p, c_char_p], self.obj, src_file.encode('gbk') if isinstance(src_file, str) else src_file, dst_file.encode('gbk') if isinstance(dst_file, str) else dst_file)

    def move_r(self, rx, ry):
        """MoveR - 偏移: 113504"""
        if not self.obj:
            return 0
        return self._call_function(113504, c_long, [c_long, c_long, c_long], self.obj, rx, ry)

    def move_to(self, x, y):
        """MoveTo - 偏移: 109088"""
        if not self.obj:
            return 0
        return self._call_function(109088, c_long, [c_long, c_long, c_long], self.obj, x, y)

    def move_to_ex(self, x, y, w, h):
        """MoveToEx - 偏移: 120688"""
        if not self.obj:
            return ''
        result = self._call_function(120688, c_char_p, [c_long, c_long, c_long, c_long, c_long], self.obj, x, y, w, h)
        return result.decode('gbk') if result else ''

    def move_window(self, hwnd, x, y):
        """MoveWindow - 偏移: 119648"""
        if not self.obj:
            return 0
        return self._call_function(119648, c_long, [c_long, c_long, c_long, c_long], self.obj, hwnd, x, y)

    def ocr(self, x1, y1, x2, y2, color, sim):
        """Ocr - 偏移: 110992"""
        if not self.obj:
            return ''
        result = self._call_function(110992, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def ocr_ex(self, x1, y1, x2, y2, color, sim):
        """OcrEx - 偏移: 113168"""
        if not self.obj:
            return ''
        result = self._call_function(113168, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def ocr_ex_one(self, x1, y1, x2, y2, color, sim):
        """OcrExOne - 偏移: 112080"""
        if not self.obj:
            return ''
        result = self._call_function(112080, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def ocr_in_file(self, x1, y1, x2, y2, pic_name, color, sim):
        """OcrInFile - 偏移: 110608"""
        if not self.obj:
            return ''
        result = self._call_function(110608, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def open_process(self, pid):
        """OpenProcess - 偏移: 124624"""
        if not self.obj:
            return 0
        return self._call_function(124624, c_long, [c_long, c_long], self.obj, pid)

    def play(self, file):
        """Play - 偏移: 105072"""
        if not self.obj:
            return 0
        return self._call_function(105072, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def rgb2_bgr(self, rgb_color):
        """RGB2BGR - 偏移: 115744"""
        if not self.obj:
            return ''
        result = self._call_function(115744, c_char_p, [c_long, c_char_p], self.obj, rgb_color.encode('gbk') if isinstance(rgb_color, str) else rgb_color)
        return result.decode('gbk') if result else ''

    def read_data(self, hwnd, addr, len):
        """ReadData - 偏移: 111232"""
        if not self.obj:
            return ''
        result = self._call_function(111232, c_char_p, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, len)
        return result.decode('gbk') if result else ''

    def read_data_addr(self, hwnd, addr, len):
        """ReadDataAddr - 偏移: 123584"""
        if not self.obj:
            return ''
        result = self._call_function(123584, c_char_p, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, len)
        return result.decode('gbk') if result else ''

    def read_data_addr_to_bin(self, hwnd, addr, len):
        """ReadDataAddrToBin - 偏移: 111792"""
        if not self.obj:
            return 0
        return self._call_function(111792, c_long, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, len)

    def read_data_to_bin(self, hwnd, addr, len):
        """ReadDataToBin - 偏移: 104480"""
        if not self.obj:
            return 0
        return self._call_function(104480, c_long, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, len)

    def read_double(self, hwnd, addr):
        """ReadDouble - 偏移: 110128"""
        if not self.obj:
            return 0.0
        return self._call_function(110128, c_double, [c_long, c_long, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr)

    def read_double_addr(self, hwnd, addr):
        """ReadDoubleAddr - 偏移: 113392"""
        if not self.obj:
            return 0.0
        return self._call_function(113392, c_double, [c_long, c_long, c_longlong], self.obj, hwnd, addr)

    def read_file(self, file):
        """ReadFile - 偏移: 114464"""
        if not self.obj:
            return ''
        result = self._call_function(114464, c_char_p, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)
        return result.decode('gbk') if result else ''

    def read_file_data(self, file, start_pos, end_pos):
        """ReadFileData - 偏移: 115808"""
        if not self.obj:
            return ''
        result = self._call_function(115808, c_char_p, [c_long, c_char_p, c_long, c_long], self.obj, file.encode('gbk') if isinstance(file, str) else file, start_pos, end_pos)
        return result.decode('gbk') if result else ''

    def read_float(self, hwnd, addr):
        """ReadFloat - 偏移: 100976"""
        if not self.obj:
            return 0.0
        return self._call_function(100976, c_float, [c_long, c_long, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr)

    def read_float_addr(self, hwnd, addr):
        """ReadFloatAddr - 偏移: 100816"""
        if not self.obj:
            return 0.0
        return self._call_function(100816, c_float, [c_long, c_long, c_longlong], self.obj, hwnd, addr)

    def read_ini(self, section, key, file):
        """ReadIni - 偏移: 102912"""
        if not self.obj:
            return ''
        result = self._call_function(102912, c_char_p, [c_long, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file)
        return result.decode('gbk') if result else ''

    def read_ini_pwd(self, section, key, file, pwd):
        """ReadIniPwd - 偏移: 102064"""
        if not self.obj:
            return ''
        result = self._call_function(102064, c_char_p, [c_long, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)
        return result.decode('gbk') if result else ''

    def read_int(self, hwnd, addr, type):
        """ReadInt - 偏移: 112720"""
        if not self.obj:
            return 0
        return self._call_function(112720, c_longlong, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type)

    def read_int_addr(self, hwnd, addr, type):
        """ReadIntAddr - 偏移: 99712"""
        if not self.obj:
            return 0
        return self._call_function(99712, c_longlong, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, type)

    def read_string(self, hwnd, addr, type, len):
        """ReadString - 偏移: 121472"""
        if not self.obj:
            return ''
        result = self._call_function(121472, c_char_p, [c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type, len)
        return result.decode('gbk') if result else ''

    def read_string_addr(self, hwnd, addr, type, len):
        """ReadStringAddr - 偏移: 118608"""
        if not self.obj:
            return ''
        result = self._call_function(118608, c_char_p, [c_long, c_long, c_longlong, c_long, c_long], self.obj, hwnd, addr, type, len)
        return result.decode('gbk') if result else ''

    def reg(self, code, ver):
        """Reg - 偏移: 121344"""
        if not self.obj:
            return 0
        return self._call_function(121344, c_long, [c_long, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver)

    def reg_ex(self, code, ver, ip):
        """RegEx - 偏移: 98864"""
        if not self.obj:
            return 0
        return self._call_function(98864, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver, ip.encode('gbk') if isinstance(ip, str) else ip)

    def reg_ex_no_mac(self, code, ver, ip):
        """RegExNoMac - 偏移: 107552"""
        if not self.obj:
            return 0
        return self._call_function(107552, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver, ip.encode('gbk') if isinstance(ip, str) else ip)

    def reg_no_mac(self, code, ver):
        """RegNoMac - 偏移: 118960"""
        if not self.obj:
            return 0
        return self._call_function(118960, c_long, [c_long, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver)

    def release_ref(self):
        """ReleaseRef - 偏移: 111072"""
        if not self.obj:
            return 0
        return self._call_function(111072, c_long, [c_long], self.obj)

    def right_click(self):
        """RightClick - 偏移: 101040"""
        if not self.obj:
            return 0
        return self._call_function(101040, c_long, [c_long], self.obj)

    def right_down(self):
        """RightDown - 偏移: 124576"""
        if not self.obj:
            return 0
        return self._call_function(124576, c_long, [c_long], self.obj)

    def right_up(self):
        """RightUp - 偏移: 111504"""
        if not self.obj:
            return 0
        return self._call_function(111504, c_long, [c_long], self.obj)

    def run_app(self, path, mode):
        """RunApp - 偏移: 122832"""
        if not self.obj:
            return 0
        return self._call_function(122832, c_long, [c_long, c_char_p, c_long], self.obj, path.encode('gbk') if isinstance(path, str) else path, mode)

    def save_dict(self, index, file):
        """SaveDict - 偏移: 115520"""
        if not self.obj:
            return 0
        return self._call_function(115520, c_long, [c_long, c_long, c_char_p], self.obj, index, file.encode('gbk') if isinstance(file, str) else file)

    def screen_to_client(self, hwnd, x, y):
        """ScreenToClient - 偏移: 111392"""
        if not self.obj:
            return 0
        return self._call_function(111392, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def select_directory(self):
        """SelectDirectory - 偏移: 116000"""
        if not self.obj:
            return ''
        result = self._call_function(116000, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def select_file(self):
        """SelectFile - 偏移: 118144"""
        if not self.obj:
            return ''
        result = self._call_function(118144, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def send_paste(self, hwnd):
        """SendPaste - 偏移: 122944"""
        if not self.obj:
            return 0
        return self._call_function(122944, c_long, [c_long, c_long], self.obj, hwnd)

    def send_string(self, hwnd, str):
        """SendString - 偏移: 114832"""
        if not self.obj:
            return 0
        return self._call_function(114832, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, str.encode('gbk') if isinstance(str, str) else str)

    def send_string2(self, hwnd, str):
        """SendString2 - 偏移: 99888"""
        if not self.obj:
            return 0
        return self._call_function(99888, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, str.encode('gbk') if isinstance(str, str) else str)

    def send_string_ime(self, str):
        """SendStringIme - 偏移: 124000"""
        if not self.obj:
            return 0
        return self._call_function(124000, c_long, [c_long, c_char_p], self.obj, str.encode('gbk') if isinstance(str, str) else str)

    def send_string_ime2(self, hwnd, str, mode):
        """SendStringIme2 - 偏移: 119520"""
        if not self.obj:
            return 0
        return self._call_function(119520, c_long, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, str.encode('gbk') if isinstance(str, str) else str, mode)

    def set_aero(self, enable):
        """SetAero - 偏移: 102640"""
        if not self.obj:
            return 0
        return self._call_function(102640, c_long, [c_long, c_long], self.obj, enable)

    def set_client_size(self, hwnd, width, height):
        """SetClientSize - 偏移: 104896"""
        if not self.obj:
            return 0
        return self._call_function(104896, c_long, [c_long, c_long, c_long, c_long], self.obj, hwnd, width, height)

    def set_clipboard(self, data):
        """SetClipboard - 偏移: 104960"""
        if not self.obj:
            return 0
        return self._call_function(104960, c_long, [c_long, c_char_p], self.obj, data.encode('gbk') if isinstance(data, str) else data)

    def set_col_gap_no_dict(self, col_gap):
        """SetColGapNoDict - 偏移: 102592"""
        if not self.obj:
            return 0
        return self._call_function(102592, c_long, [c_long, c_long], self.obj, col_gap)

    def set_dict(self, index, dict_name):
        """SetDict - 偏移: 121280"""
        if not self.obj:
            return 0
        return self._call_function(121280, c_long, [c_long, c_long, c_char_p], self.obj, index, dict_name.encode('gbk') if isinstance(dict_name, str) else dict_name)

    def set_dict_mem(self, index, addr, size):
        """SetDictMem - 偏移: 104704"""
        if not self.obj:
            return 0
        return self._call_function(104704, c_long, [c_long, c_long, c_long, c_long], self.obj, index, addr, size)

    def set_dict_pwd(self, pwd):
        """SetDictPwd - 偏移: 104128"""
        if not self.obj:
            return 0
        return self._call_function(104128, c_long, [c_long, c_char_p], self.obj, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def set_display_acceler(self, level):
        """SetDisplayAcceler - 偏移: 101088"""
        if not self.obj:
            return 0
        return self._call_function(101088, c_long, [c_long, c_long], self.obj, level)

    def set_display_delay(self, t):
        """SetDisplayDelay - 偏移: 122784"""
        if not self.obj:
            return 0
        return self._call_function(122784, c_long, [c_long, c_long], self.obj, t)

    def set_display_input(self, mode):
        """SetDisplayInput - 偏移: 110944"""
        if not self.obj:
            return 0
        return self._call_function(110944, c_long, [c_long, c_char_p], self.obj, mode.encode('gbk') if isinstance(mode, str) else mode)

    def set_display_refresh_delay(self, t):
        """SetDisplayRefreshDelay - 偏移: 111344"""
        if not self.obj:
            return 0
        return self._call_function(111344, c_long, [c_long, c_long], self.obj, t)

    def set_enum_window_delay(self, delay):
        """SetEnumWindowDelay - 偏移: 114720"""
        if not self.obj:
            return 0
        return self._call_function(114720, c_long, [c_long, c_long], self.obj, delay)

    def set_exact_ocr(self, exact_ocr):
        """SetExactOcr - 偏移: 123280"""
        if not self.obj:
            return 0
        return self._call_function(123280, c_long, [c_long, c_long], self.obj, exact_ocr)

    def set_exclude_region(self, type, info):
        """SetExcludeRegion - 偏移: 104832"""
        if not self.obj:
            return 0
        return self._call_function(104832, c_long, [c_long, c_long, c_char_p], self.obj, type, info.encode('gbk') if isinstance(info, str) else info)

    def set_exit_thread(self, mode):
        """SetExitThread - 偏移: 101536"""
        if not self.obj:
            return 0
        return self._call_function(101536, c_long, [c_long, c_long], self.obj, mode)

    def set_export_dict(self, index, dict_name):
        """SetExportDict - 偏移: 119392"""
        if not self.obj:
            return 0
        return self._call_function(119392, c_long, [c_long, c_long, c_char_p], self.obj, index, dict_name.encode('gbk') if isinstance(dict_name, str) else dict_name)

    def set_find_pic_multithread_count(self, count):
        """SetFindPicMultithreadCount - 偏移: 106784"""
        if not self.obj:
            return 0
        return self._call_function(106784, c_long, [c_long, c_long], self.obj, count)

    def set_find_pic_multithread_limit(self, limit):
        """SetFindPicMultithreadLimit - 偏移: 107616"""
        if not self.obj:
            return 0
        return self._call_function(107616, c_long, [c_long, c_long], self.obj, limit)

    def set_input_dm(self, input_dm, rx, ry):
        """SetInputDm - 偏移: 108656"""
        if not self.obj:
            return 0
        return self._call_function(108656, c_long, [c_long, c_long, c_long, c_long], self.obj, input_dm, rx, ry)

    def set_keypad_delay(self, type, delay):
        """SetKeypadDelay - 偏移: 110256"""
        if not self.obj:
            return 0
        return self._call_function(110256, c_long, [c_long, c_char_p, c_long], self.obj, type.encode('gbk') if isinstance(type, str) else type, delay)

    def set_locale(self):
        """SetLocale - 偏移: 100928"""
        if not self.obj:
            return 0
        return self._call_function(100928, c_long, [c_long], self.obj)

    def set_memory_find_result_to_file(self, file):
        """SetMemoryFindResultToFile - 偏移: 110704"""
        if not self.obj:
            return 0
        return self._call_function(110704, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def set_memory_hwnd_as_process_id(self, en):
        """SetMemoryHwndAsProcessId - 偏移: 107984"""
        if not self.obj:
            return 0
        return self._call_function(107984, c_long, [c_long, c_long], self.obj, en)

    def set_min_col_gap(self, col_gap):
        """SetMinColGap - 偏移: 110560"""
        if not self.obj:
            return 0
        return self._call_function(110560, c_long, [c_long, c_long], self.obj, col_gap)

    def set_min_row_gap(self, row_gap):
        """SetMinRowGap - 偏移: 122144"""
        if not self.obj:
            return 0
        return self._call_function(122144, c_long, [c_long, c_long], self.obj, row_gap)

    def set_mouse_delay(self, type, delay):
        """SetMouseDelay - 偏移: 104592"""
        if not self.obj:
            return 0
        return self._call_function(104592, c_long, [c_long, c_char_p, c_long], self.obj, type.encode('gbk') if isinstance(type, str) else type, delay)

    def set_mouse_speed(self, speed):
        """SetMouseSpeed - 偏移: 124800"""
        if not self.obj:
            return 0
        return self._call_function(124800, c_long, [c_long, c_long], self.obj, speed)

    def set_param64_to_pointer(self):
        """SetParam64ToPointer - 偏移: 99952"""
        if not self.obj:
            return 0
        return self._call_function(99952, c_long, [c_long], self.obj)

    def set_path(self, path):
        """SetPath - 偏移: 123808"""
        if not self.obj:
            return 0
        return self._call_function(123808, c_long, [c_long, c_char_p], self.obj, path.encode('gbk') if isinstance(path, str) else path)

    def set_pic_pwd(self, pwd):
        """SetPicPwd - 偏移: 123712"""
        if not self.obj:
            return 0
        return self._call_function(123712, c_long, [c_long, c_char_p], self.obj, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def set_row_gap_no_dict(self, row_gap):
        """SetRowGapNoDict - 偏移: 118256"""
        if not self.obj:
            return 0
        return self._call_function(118256, c_long, [c_long, c_long], self.obj, row_gap)

    def set_screen(self, width, height, depth):
        """SetScreen - 偏移: 115168"""
        if not self.obj:
            return 0
        return self._call_function(115168, c_long, [c_long, c_long, c_long, c_long], self.obj, width, height, depth)

    def set_show_asm_error_msg(self, show):
        """SetShowAsmErrorMsg - 偏移: 101392"""
        if not self.obj:
            return 0
        return self._call_function(101392, c_long, [c_long, c_long], self.obj, show)

    def set_show_error_msg(self, show):
        """SetShowErrorMsg - 偏移: 101856"""
        if not self.obj:
            return 0
        return self._call_function(101856, c_long, [c_long, c_long], self.obj, show)

    def set_sim_mode(self, mode):
        """SetSimMode - 偏移: 122896"""
        if not self.obj:
            return 0
        return self._call_function(122896, c_long, [c_long, c_long], self.obj, mode)

    def set_uac(self, uac):
        """SetUAC - 偏移: 108608"""
        if not self.obj:
            return 0
        return self._call_function(108608, c_long, [c_long, c_long], self.obj, uac)

    def set_window_size(self, hwnd, width, height):
        """SetWindowSize - 偏移: 98560"""
        if not self.obj:
            return 0
        return self._call_function(98560, c_long, [c_long, c_long, c_long, c_long], self.obj, hwnd, width, height)

    def set_window_state(self, hwnd, flag):
        """SetWindowState - 偏移: 102736"""
        if not self.obj:
            return 0
        return self._call_function(102736, c_long, [c_long, c_long, c_long], self.obj, hwnd, flag)

    def set_window_text(self, hwnd, text):
        """SetWindowText - 偏移: 113008"""
        if not self.obj:
            return 0
        return self._call_function(113008, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, text.encode('gbk') if isinstance(text, str) else text)

    def set_window_transparent(self, hwnd, v):
        """SetWindowTransparent - 偏移: 112896"""
        if not self.obj:
            return 0
        return self._call_function(112896, c_long, [c_long, c_long, c_long], self.obj, hwnd, v)

    def set_word_gap(self, word_gap):
        """SetWordGap - 偏移: 98624"""
        if not self.obj:
            return 0
        return self._call_function(98624, c_long, [c_long, c_long], self.obj, word_gap)

    def set_word_gap_no_dict(self, word_gap):
        """SetWordGapNoDict - 偏移: 123392"""
        if not self.obj:
            return 0
        return self._call_function(123392, c_long, [c_long, c_long], self.obj, word_gap)

    def set_word_line_height(self, line_height):
        """SetWordLineHeight - 偏移: 101296"""
        if not self.obj:
            return 0
        return self._call_function(101296, c_long, [c_long, c_long], self.obj, line_height)

    def set_word_line_height_no_dict(self, line_height):
        """SetWordLineHeightNoDict - 偏移: 103792"""
        if not self.obj:
            return 0
        return self._call_function(103792, c_long, [c_long, c_long], self.obj, line_height)

    def show_scr_msg(self, x1, y1, x2, y2, msg, color):
        """ShowScrMsg - 偏移: 112208"""
        if not self.obj:
            return 0
        return self._call_function(112208, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p], self.obj, x1, y1, x2, y2, msg.encode('gbk') if isinstance(msg, str) else msg, color.encode('gbk') if isinstance(color, str) else color)

    def show_task_bar_icon(self, hwnd, is_show):
        """ShowTaskBarIcon - 偏移: 119328"""
        if not self.obj:
            return 0
        return self._call_function(119328, c_long, [c_long, c_long, c_long], self.obj, hwnd, is_show)

    def sort_pos_distance(self, all_pos, type, x, y):
        """SortPosDistance - 偏移: 117120"""
        if not self.obj:
            return ''
        result = self._call_function(117120, c_char_p, [c_long, c_char_p, c_long, c_long, c_long], self.obj, all_pos.encode('gbk') if isinstance(all_pos, str) else all_pos, type, x, y)
        return result.decode('gbk') if result else ''

    def speed_normal_graphic(self, en):
        """SpeedNormalGraphic - 偏移: 101184"""
        if not self.obj:
            return 0
        return self._call_function(101184, c_long, [c_long, c_long], self.obj, en)

    def stop(self, id):
        """Stop - 偏移: 100880"""
        if not self.obj:
            return 0
        return self._call_function(100880, c_long, [c_long, c_long], self.obj, id)

    def string_to_data(self, string_value, type):
        """StringToData - 偏移: 114768"""
        if not self.obj:
            return ''
        result = self._call_function(114768, c_char_p, [c_long, c_char_p, c_long], self.obj, string_value.encode('gbk') if isinstance(string_value, str) else string_value, type)
        return result.decode('gbk') if result else ''

    def switch_bind_window(self, hwnd):
        """SwitchBindWindow - 偏移: 109920"""
        if not self.obj:
            return 0
        return self._call_function(109920, c_long, [c_long, c_long], self.obj, hwnd)

    def terminate_process(self, pid):
        """TerminateProcess - 偏移: 112032"""
        if not self.obj:
            return 0
        return self._call_function(112032, c_long, [c_long, c_long], self.obj, pid)

    def terminate_process_tree(self, pid):
        """TerminateProcessTree - 偏移: 114240"""
        if not self.obj:
            return 0
        return self._call_function(114240, c_long, [c_long, c_long], self.obj, pid)

    def un_bind_window(self):
        """UnBindWindow - 偏移: 101904"""
        if not self.obj:
            return 0
        return self._call_function(101904, c_long, [c_long], self.obj)

    def un_load_driver(self):
        """UnLoadDriver - 偏移: 105696"""
        if not self.obj:
            return 0
        return self._call_function(105696, c_long, [c_long], self.obj)

    def use_dict(self, index):
        """UseDict - 偏移: 104656"""
        if not self.obj:
            return 0
        return self._call_function(104656, c_long, [c_long, c_long], self.obj, index)

    def ver(self):
        """Ver - 偏移: 100320"""
        if not self.obj:
            return ''
        result = self._call_function(100320, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def virtual_alloc_ex(self, hwnd, addr, size, type):
        """VirtualAllocEx - 偏移: 99104"""
        if not self.obj:
            return 0
        return self._call_function(99104, c_longlong, [c_long, c_long, c_longlong, c_long, c_long], self.obj, hwnd, addr, size, type)

    def virtual_free_ex(self, hwnd, addr):
        """VirtualFreeEx - 偏移: 105120"""
        if not self.obj:
            return 0
        return self._call_function(105120, c_long, [c_long, c_long, c_longlong], self.obj, hwnd, addr)

    def virtual_protect_ex(self, hwnd, addr, size, type, old_protect):
        """VirtualProtectEx - 偏移: 108912"""
        if not self.obj:
            return 0
        return self._call_function(108912, c_long, [c_long, c_long, c_longlong, c_long, c_long, c_long], self.obj, hwnd, addr, size, type, old_protect)

    def virtual_query_ex(self, hwnd, addr, pmbi):
        """VirtualQueryEx - 偏移: 101632"""
        if not self.obj:
            return ''
        result = self._call_function(101632, c_char_p, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, pmbi)
        return result.decode('gbk') if result else ''

    def wait_key(self, key_code, time_out):
        """WaitKey - 偏移: 114528"""
        if not self.obj:
            return 0
        return self._call_function(114528, c_long, [c_long, c_long, c_long], self.obj, key_code, time_out)

    def wheel_down(self):
        """WheelDown - 偏移: 112848"""
        if not self.obj:
            return 0
        return self._call_function(112848, c_long, [c_long], self.obj)

    def wheel_up(self):
        """WheelUp - 偏移: 102688"""
        if not self.obj:
            return 0
        return self._call_function(102688, c_long, [c_long], self.obj)

    def write_data(self, hwnd, addr, data):
        """WriteData - 偏移: 123040"""
        if not self.obj:
            return 0
        return self._call_function(123040, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, data.encode('gbk') if isinstance(data, str) else data)

    def write_data_addr(self, hwnd, addr, data):
        """WriteDataAddr - 偏移: 105744"""
        if not self.obj:
            return 0
        return self._call_function(105744, c_long, [c_long, c_long, c_longlong, c_char_p], self.obj, hwnd, addr, data.encode('gbk') if isinstance(data, str) else data)

    def write_data_addr_from_bin(self, hwnd, addr, data, len):
        """WriteDataAddrFromBin - 偏移: 121120"""
        if not self.obj:
            return 0
        return self._call_function(121120, c_long, [c_long, c_long, c_longlong, c_long, c_long], self.obj, hwnd, addr, data, len)

    def write_data_from_bin(self, hwnd, addr, data, len):
        """WriteDataFromBin - 偏移: 118304"""
        if not self.obj:
            return 0
        return self._call_function(118304, c_long, [c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, data, len)

    def write_double(self, hwnd, addr, double_value):
        """WriteDouble - 偏移: 116048"""
        if not self.obj:
            return 0
        return self._call_function(116048, c_long, [c_long, c_long, c_char_p, c_double], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, double_value)

    def write_double_addr(self, hwnd, addr, double_value):
        """WriteDoubleAddr - 偏移: 115232"""
        if not self.obj:
            return 0
        return self._call_function(115232, c_long, [c_long, c_long, c_longlong, c_double], self.obj, hwnd, addr, double_value)

    def write_file(self, file, content):
        """WriteFile - 偏移: 105536"""
        if not self.obj:
            return 0
        return self._call_function(105536, c_long, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, content.encode('gbk') if isinstance(content, str) else content)

    def write_float(self, hwnd, addr, float_value):
        """WriteFloat - 偏移: 111920"""
        if not self.obj:
            return 0
        return self._call_function(111920, c_long, [c_long, c_long, c_char_p, c_float], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, float_value)

    def write_float_addr(self, hwnd, addr, float_value):
        """WriteFloatAddr - 偏移: 117312"""
        if not self.obj:
            return 0
        return self._call_function(117312, c_long, [c_long, c_long, c_longlong, c_float], self.obj, hwnd, addr, float_value)

    def write_ini(self, section, key, v, file):
        """WriteIni - 偏移: 101232"""
        if not self.obj:
            return 0
        return self._call_function(101232, c_long, [c_long, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, v.encode('gbk') if isinstance(v, str) else v, file.encode('gbk') if isinstance(file, str) else file)

    def write_ini_pwd(self, section, key, v, file, pwd):
        """WriteIniPwd - 偏移: 115872"""
        if not self.obj:
            return 0
        return self._call_function(115872, c_long, [c_long, c_char_p, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, v.encode('gbk') if isinstance(v, str) else v, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def write_int(self, hwnd, addr, type, v):
        """WriteInt - 偏移: 112416"""
        if not self.obj:
            return 0
        return self._call_function(112416, c_long, [c_long, c_long, c_char_p, c_long, c_longlong], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type, v)

    def write_int_addr(self, hwnd, addr, type, v):
        """WriteIntAddr - 偏移: 100240"""
        if not self.obj:
            return 0
        return self._call_function(100240, c_long, [c_long, c_long, c_longlong, c_long, c_longlong], self.obj, hwnd, addr, type, v)

    def write_string(self, hwnd, addr, type, v):
        """WriteString - 偏移: 115936"""
        if not self.obj:
            return 0
        return self._call_function(115936, c_long, [c_long, c_long, c_char_p, c_long, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type, v.encode('gbk') if isinstance(v, str) else v)

    def write_string_addr(self, hwnd, addr, type, v):
        """WriteStringAddr - 偏移: 122720"""
        if not self.obj:
            return 0
        return self._call_function(122720, c_long, [c_long, c_long, c_longlong, c_long, c_char_p], self.obj, hwnd, addr, type, v.encode('gbk') if isinstance(v, str) else v)


    def __del__(self):
        """析构函数"""
        try:
            if self.use_proxy and hasattr(self, 'proxy') and self.proxy:
                # 代理模式先关闭代理连接
                self.proxy.shutdown()
            elif self.obj and not self.use_proxy:
                # 直接模式才释放对象
                try:
                    self._call_function(98400, c_long, [c_long], self.obj)
                except:
                    pass
            self.obj = None
        except:
            pass

