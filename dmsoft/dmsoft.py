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
    
    def __init__(self, dm_dll_path="72424.dll", crack_dll_path="go.dll", py32_path=r"C:\Users\Administrator\anaconda3\envs\py32\python.exe"):
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
        """
        MoveTo
        
        把鼠标移动到目的点(x,y)
        
        参数:
            x (整形数): X坐标
            y (整形数): Y坐标
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(109088, c_long, [c_long, c_long, c_long], 
                                   self.obj, x, y)
    
    def left_click(self):
        """
        LeftClick
        
        按下鼠标左键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(118096, c_long, [c_long], self.obj)
    
    def right_click(self):
        """
        RightClick
        
        按下鼠标右键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(104864, c_long, [c_long], self.obj)
    
    def left_down(self):
        """
        LeftDown
        
        按住鼠标左键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(103456, c_long, [c_long], self.obj)
    
    def left_up(self):
        """
        LeftUp
        
        弹起鼠标左键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(103840, c_long, [c_long], self.obj)
    
    # 键盘操作
    def key_press(self, vk_code):
        """
        KeyPress
        
        按下指定的虚拟键码
        
        参数:
            vk (\_code 整形数): 虚拟按键码
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102400, c_long, [c_long, c_long], 
                                   self.obj, vk_code)
    
    def key_down(self, vk_code):
        """
        KeyDown
        
        按住指定的虚拟键码
        
        参数:
            vk (\_code **整形数**): 虚拟按键码
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102272, c_long, [c_long, c_long], 
                                   self.obj, vk_code)
    
    def key_up(self, vk_code):
        """
        KeyUp
        
        弹起来虚拟键vk\_code
        
        参数:
            vk (\_code 整形数): 虚拟按键码
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102880, c_long, [c_long, c_long], 
                                   self.obj, vk_code)
    
    def key_press_str(self, key_str, delay=50):
        """
        KeyPressStr
        
        根据指定的字符串序列，依次按顺序按下其中的字符.
        
        参数:
            key (\_str** 字符串**): ** 需要按下的字符串序列. 比如"1234","abcd","7389,1462"等.
            delay (整形数): 每按下一个按键，需要延时多久. 单位毫秒.这个值越大，按的速度越慢。
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102528, c_long, [c_long, c_char_p, c_long], 
                                   self.obj, key_str.encode('gbk'), delay)
    
    # 窗口操作
    def find_window(self, class_name, title_name):
        """
        FindWindow
        
        查找符合类名或者标题名的顶层可见窗口
        
        参数:
            class (字符串): 窗口类名，如果为空，则匹配所有. 这里的匹配是模糊匹配.
            title (字符串): 窗口标题,如果为空，则匹配所有.这里的匹配是模糊匹配.
        
        返回值:
            整形数: 整形数表示的窗口句柄，没找到返回0
        """
        if not self.obj:
            return 0
        return self._call_function(112800, c_long, [c_long, c_char_p, c_char_p], 
                                   self.obj, class_name.encode('gbk'), 
                                   title_name.encode('gbk'))
    
    def bind_window(self, hwnd, display, mouse, keypad, mode):
        """
        BindWindow
        
        绑定指定的窗口,并指定这个窗口的屏幕颜色获取方式,鼠标仿真模式,键盘仿真模式,以及模式设定,高级用户可以参考[BindWindowEx](#chmtopic277)更加灵活强大.
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            display (字符串): 屏幕颜色获取方式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台截屏模式\ \ "gdi" : gdi模式,用于窗口采用GDI方式刷新时. 此模式占用CPU较大. 参考[SetAero](#chmtopic278) win10以上系统使用此模式，如果截图失败，尝试把目标程序重新开启再试试。
            mouse (字符串): 鼠标仿真模式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台鼠标模式\ \ "windows": Windows模式,采取模拟windows消息方式 同按键自带后台插件.
            keypad (字符串): 键盘仿真模式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台键盘模式\ \ "windows": Windows模式,采取模拟windows消息方式 同按键的后台插件.\ \ "dx": dx模式,采用模拟dx后台键盘模式。有些窗口在此模式下绑定时，需要先激活窗口再绑定(或者绑定以后激活)，否则可能会出现绑定后键盘无效的情况. 此模式等同于BindWindowEx中的keypad为以下组合\ "dx.public.active.api|dx.public.active.message| dx.keypad.state.api|dx.keypad.api|dx.keypad.input.lock.api"
            mode (整形数): 模式。 取值有以下几种
            需要注意的 (是): 模式101 103在大部分窗口下绑定都没问题。但也有少数特殊的窗口，比如有很多子窗口的窗口，对于这种窗口，在绑定时，一定要把\ 鼠标指向一个可以输入文字的窗口，比如一个文本框，最好能激活这个文本框，这样可以保证绑定的成功.
        
        返回值:
            整形数: 0: 失败 1: 成功  如果返回0，可以调用[GetLastError](#chmtopic280)来查看具体失败错误码,帮助分析问题.
        """
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
        """
        Delay
        
        延时指定的毫秒,过程中不阻塞UI操作. 一般高级语言使用.按键用不到.
        
        参数:
            mis整形 (数): 毫秒数. **必须大于0.**
        
        """
        if not self.obj:
            return 0
        return self._call_function(101760, c_long, [c_long, c_long], 
                                   self.obj, milliseconds)
    
    def set_sim_mode(self, mode):
        """
        SetSimMode
        
        设置前台键鼠的模拟方式. \ 驱动功能支持的系统版本号为(win7/win8/win8.1/win10(10240)/win10(10586)/win10(14393)/win10(15063)/win10(16299)/win10(17134)/win10(17763)/win10(18362)/win10(18363)/win10(19041)/win10(19042) /win10(19043)/ win10(19045)/win11(22000)/win11(22621)/win11(22631)\ 不支持所有的预览版本,仅仅支持正式版本.  除了模式3,其他模式同时支持32位系统和64位系统.
        
        参数:
            mode (整形数): 0 正常模式(默认模式)\ 1 硬件模拟\ 2 硬件模拟2(ps2)（仅仅支持标准的3键鼠标，即左键，右键，中键，带滚轮的鼠标,2键和5键等扩展鼠标不支持）\ 3 硬件模拟3
        
        返回值:
            整形数: 0  : 插件没注册 -1 : 32位系统不支持 -2 : 驱动释放失败. -3 : 驱动加载失败.可能是权限不够. 参考UAC权限设置. 或者是被安全软件拦截.  `     `如果是WIN10 1607之后的系统，出现这个错误，可[参考这里](#chmtopic84) -10: 设置失败 -7 : 系统版本不支持. 可以用winver命令查看系统内部版本号. 驱动只支持正式发布的版本，所有预览版本都不支持. 1  : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(123616, c_long, [c_long, c_long], 
                                   self.obj, mode)
    
    def get_screen_width(self):
        """
        GetScreenWidth
        
        获取屏幕的宽度.
        
        返回值:
            整形数: 返回屏幕的宽度
        """
        if not self.obj:
            return 0
        return self._call_function(113920, c_long, [c_long], self.obj)
    
    def get_screen_height(self):
        """
        GetScreenHeight
        
        获取屏幕的高度.
        
        返回值:
            整形数: 返回屏幕的高度
        """
        if not self.obj:
            return 0
        return self._call_function(117792, c_long, [c_long], self.obj)
    

    def active_input_method(self, hwnd, id):
        """
        ActiveInputMethod
        
        激活指定窗口所在进程的输入法.
        
        参数:
            hwnd (整形数): 窗口句柄\ 
            input (\_method 字符串): 输入法名字。 具体输入法名字对应表查看注册表中以下位置:
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(124320, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, id.encode('gbk') if isinstance(id, str) else id)

    def add_dict(self, index, dict_info):
        """
        AddDict
        
        给指定的字库中添加一条字库信息.
        
        参数:
            index (整形数): 字库的序号,取值为0-99,目前最多支持100个字库
            dict (\_info 字符串): 字库描述串，具体参考大漠综合工具中的字符定义
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(106336, c_long, [c_long, c_long, c_char_p], self.obj, index, dict_info.encode('gbk') if isinstance(dict_info, str) else dict_info)

    def ai_enable_find_pic_window(self, enable):
        """
        AiEnableFindPicWindow
        
        设置是否在调用AiFindPicXX系列接口时,是否弹出找图结果的窗口.  方便调试. 默认是关闭的.
        
        参数:
            enable (整形数): 0 关闭\ 1 开启
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(100064, c_long, [c_long, c_long], self.obj, enable)

    def ai_find_pic(self, x1, y1, x2, y2, pic_name, sim, dir, x, y):
        """
        AiFindPic
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个找到的X Y坐标. 此接口使用Ai模块来实现,比传统的FindPic的效果更好. 不需要训练
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回图片左上角的X坐标
            intY (变参指针): 返回图片左上角的Y坐标
        
        返回值:
            整形数: 返回找到的图片的序号,从0开始索引.如果没找到返回-1
        """
        if not self.obj:
            return 0
        return self._call_function(121536, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def ai_find_pic_ex(self, x1, y1, x2, y2, pic_name, sim, dir):
        """
        AiFindPicEx
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,并且返回所有找到的图像的坐标. 此接口使用Ai模块来实现,比传统的FindPicEx的效果更好.不需要训练
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回的是所有找到的坐标格式如下:"id,x,y|id,x,y..|id,x,y" (图片左上角的坐标)
            比如"0,100,20|2,30,40" 表示找到了两个,第一个,对应的图片是图像序号为0的图片,坐标是(100,20),第二个是序号为2的图片,坐标(30,40) (由于内存限制,返回的图片数量最多为1500个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(119136, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, sim, dir)
        return result.decode('gbk') if result else ''

    def ai_find_pic_mem(self, x1, y1, x2, y2, pic_info, sim, dir, x, y):
        """
        AiFindPicMem
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个找到的X Y坐标. 这个函数要求图片是数据地址. 此接口使用Ai模块来实现,比传统的FindPicMem的效果更好.不需要训练
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic35)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回图片左上角的X坐标
            intY (变参指针): 返回图片左上角的Y坐标
        
        返回值:
            整形数: 返回找到的图片的序号,从0开始索引.如果没找到返回-1
        """
        if not self.obj:
            return 0
        return self._call_function(111696, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def ai_find_pic_mem_ex(self, x1, y1, x2, y2, pic_info, sim, dir):
        """
        AiFindPicMemEx
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,并且返回所有找到的图像的坐标. 这个函数要求图片是数据地址. 此接口使用Ai模块来实现,比传统的FindPicMemEx的效果更好.不需要训练
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic35)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回的是所有找到的坐标格式如下:"id,x,y|id,x,y..|id,x,y" (图片左上角的坐标)
            比如"0,100,20|2,30,40" 表示找到了两个,第一个,对应的图片是图像序号为0的图片,坐标是(100,20),第二个是序号为2的图片,坐标(30,40) (由于内存限制,返回的图片数量最多为1500个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(102976, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, sim, dir)
        return result.decode('gbk') if result else ''

    def ai_yolo_detect_objects(self, x1, y1, x2, y2, prob, iou):
        """
        AiYoloDetectObjects
        
        需要先加载Ai模块. 在指定范围内检测对象.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            prob双精度浮点数 (**): ** 置信度,也可以认为是相似度. 超过这个prob的对象才会被检测
            iou (双精度浮点数**): ** 用于对多个检测框进行合并. 越大越不容易合并(很多框重叠). 越小越容易合并(可能会把正常的框也给合并). 所以这个值一般建议0.4-0.6之间. \ 可以在Yolo综合工具里进行测试.
        
        返回值:
            字符串: 返回的是所有检测到的对象.格式是"类名,置信度,x,y,w,h|....". 如果没检测到任何对象,返回空字符串.
        """
        if not self.obj:
            return ''
        result = self._call_function(116112, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_float, c_float], self.obj, x1, y1, x2, y2, prob, iou)
        return result.decode('gbk') if result else ''

    def ai_yolo_detect_objects_to_data_bmp(self, x1, y1, x2, y2, prob, iou, data, size, mode):
        """
        AiYoloDetectObjectsToDataBmp
        
        需要先加载Ai模块. 在指定范围内检测对象,把结果输出到BMP图像数据.用于二次开发.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            prob双精度浮点数 (**): ** 置信度,也可以认为是相似度. 超过这个prob的对象才会被检测
            iou (双精度浮点数**): ** 用于对多个检测框进行合并. 越大越不容易合并(很多框重叠). 越小越容易合并(可能会把正常的框也给合并). 所以这个值一般建议0.4-0.6之间. \ 可以在Yolo综合工具里进行测试.
            data (变参指针): 返回图片的数据指针
            size (变参指针): 返回图片的数据长度
            mode (整形数): 0表示绘制的文字信息里包含置信度. 1表示不包含.
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(98928, c_long, [c_long, c_long, c_long, c_long, c_long, c_float, c_float, POINTER(c_long), POINTER(c_long), c_long], self.obj, x1, y1, x2, y2, prob, iou, byref(data) if isinstance(data, c_long) else data, byref(size) if isinstance(size, c_long) else size, mode)

    def ai_yolo_detect_objects_to_file(self, x1, y1, x2, y2, prob, iou, file, mode):
        """
        AiYoloDetectObjectsToFile
        
        需要先加载Ai模块. 在指定范围内检测对象,把结果输出到指定的BMP文件.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            prob双精度浮点数 (**): ** 置信度,也可以认为是相似度. 超过这个prob的对象才会被检测
            iou (双精度浮点数**): ** 用于对多个检测框进行合并. 越大越不容易合并(很多框重叠). 越小越容易合并(可能会把正常的框也给合并). 所以这个值一般建议0.4-0.6之间. \ 可以在Yolo综合工具里进行测试.
            file (字符串): 图片名,比如"test.bmp"
            mode (整形数): 0表示绘制的文字信息里包含置信度. 1表示不包含.
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(109504, c_long, [c_long, c_long, c_long, c_long, c_long, c_float, c_float, c_char_p, c_long], self.obj, x1, y1, x2, y2, prob, iou, file.encode('gbk') if isinstance(file, str) else file, mode)

    def ai_yolo_free_model(self, index):
        """
        AiYoloFreeModel
        
        需要先加载Ai模块. 卸载指定的模型
        
        参数:
            index (整形数**): ** 模型的序号. 最多支持20个. 从0开始
        
        返回值:
            整形数: 1  表示成功 0  失败
        """
        if not self.obj:
            return 0
        return self._call_function(106592, c_long, [c_long, c_long], self.obj, index)

    def ai_yolo_objects_to_string(self, objects):
        """
        AiYoloObjectsToString
        
        需要先加载Ai模块. 把通过AiYoloDetectObjects或者是AiYoloSortsObjects的结果,按照顺序把class信息连接输出.
        
        参数:
            objects (字符串): AiYoloDetectObjects或者AiYoloSortsObjects的返回值.
        
        返回值:
            字符串: 返回的是class信息连接后的信息.
        """
        if not self.obj:
            return ''
        result = self._call_function(111456, c_char_p, [c_long, c_char_p], self.obj, objects.encode('gbk') if isinstance(objects, str) else objects)
        return result.decode('gbk') if result else ''

    def ai_yolo_set_model(self, index, file, pwd):
        """
        AiYoloSetModel
        
        需要先加载Ai模块. 从文件加载指定的模型.
        
        参数:
            index (整形数**): ** 模型的序号. 最多支持20个. 从0开始
            file字符串 (**): ** 模型文件名. 比如"xxxx.onnx"或者"xxxx.dmx"
            pwd字符串 (**): ** 模型的密码. 仅对dmx格式有效.
        
        返回值:
            整形数: 1  表示成功 0  失败
        """
        if not self.obj:
            return 0
        return self._call_function(104416, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, index, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def ai_yolo_set_model_memory(self, index, addr, size, pwd):
        """
        AiYoloSetModelMemory
        
        需要先加载Ai模块. 从内存加载指定的模型. 仅支持dmx格式的内存
        
        参数:
            index (整形数**): ** 模型的序号. 最多支持20个. 从0开始
            data (整形数**): ** dmx模型的内存地址
            size (整形数**): ** dmx模型的大小
            pwd字符串 (**): ** dmx模型的密码
        
        返回值:
            整形数: 1  表示成功 0  失败
        """
        if not self.obj:
            return 0
        return self._call_function(117600, c_long, [c_long, c_long, c_long, c_long, c_char_p], self.obj, index, addr, size, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def ai_yolo_set_version(self, ver):
        """
        AiYoloSetVersion
        
        需要先加载Ai模块. 设置Yolo的版本
        
        参数:
            ver字符串 (**): ** Yolo的版本信息. 需要在加载Ai模块后,第一时间调用. 目前可选的值只有"v5-7.0"
        
        返回值:
            整形数: 1  表示成功 0  失败
        """
        if not self.obj:
            return 0
        return self._call_function(118496, c_long, [c_long, c_char_p], self.obj, ver.encode('gbk') if isinstance(ver, str) else ver)

    def ai_yolo_sorts_objects(self, objects, height):
        """
        AiYoloSortsObjects
        
        需要先加载Ai模块. 把通过AiYoloDetectObjects的结果进行排序. 排序按照从上到下,从左到右.
        
        参数:
            objects (字符串): AiYoloDetectObjects的返回值
            height整形 (数): 行高信息. 排序时需要使用此行高. 用于确定两个检测框是否处于同一行. 如果两个框的Y坐标相差绝对值小于此行高,认为是同一行.
        
        返回值:
            字符串: 返回的是所有检测到的对象.格式是"类名,置信度,x,y,w,h|....". 如果没检测到任何对象,返回空字符串.
        """
        if not self.obj:
            return ''
        result = self._call_function(120480, c_char_p, [c_long, c_char_p, c_long], self.obj, objects.encode('gbk') if isinstance(objects, str) else objects, height)
        return result.decode('gbk') if result else ''

    def ai_yolo_use_model(self, index):
        """
        AiYoloUseModel
        
        需要先加载Ai模块. 切换当前使用的模型序号.用于AiYoloDetectXX等系列接口.
        
        参数:
            index (整形数**): ** 模型的序号. 最多支持20个. 从0开始
        
        返回值:
            整形数: 1  表示成功 0  失败
        """
        if not self.obj:
            return 0
        return self._call_function(110032, c_long, [c_long, c_long], self.obj, index)

    def append_pic_addr(self, pic_info, addr, size):
        """
        AppendPicAddr
        
        对指定的数据地址和长度，组合成新的参数. FindPicMem FindPicMemE 以及FindPicMemEx专用
        
        参数:
            pic (\_info 字符串): 老的地址描述串
            addr (整形数): 数据地址
            size (整形数): 数据长度
        
        """
        if not self.obj:
            return ''
        result = self._call_function(106832, c_char_p, [c_long, c_char_p, c_long, c_long], self.obj, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, addr, size)
        return result.decode('gbk') if result else ''

    def asm_add(self, asm_ins):
        """
        AsmAdd
        
        添加指定的MASM汇编指令. 支持标准的masm汇编指令.
        
        参数:
            asm (\_ins **字符串**): MASM汇编指令,大小写均可以 比如 "mov eax,1" ,也支持直接加入字节，比如"emit 90 90 90 90"等. 同时也支持跳转指令，标记. \ 标记必须以":"开头. 跳转指令后必须接本次AsmCall之前的存在的有效Label. 另外跳转只支持短跳转,就是跳转的字节码不能超过128个字节.
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(121232, c_long, [c_long, c_char_p], self.obj, asm_ins.encode('gbk') if isinstance(asm_ins, str) else asm_ins)

    def asm_call(self, hwnd, mode):
        """
        AsmCall
        
        执行用AsmAdd加到缓冲中的指令.
        
        参数:
            hwnd (**整形数**): 窗口句柄
            mode (整形数): 模式，取值如下
        
        返回值:
            长整形数: 获取执行汇编代码以后的EAX的值(32位进程),或者RAX的值(64位进程).一般是函数的返回值. 如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数. -200 : 执行中出现错误. -201 : 使用模式5时，没有开启memory盾.
        """
        if not self.obj:
            return 0
        return self._call_function(114656, c_longlong, [c_long, c_long, c_long], self.obj, hwnd, mode)

    def asm_call_ex(self, hwnd, mode, base_addr):
        """
        AsmCallEx
        
        执行用AsmAdd加到缓冲中的指令.  这个接口同AsmCall,但是由于插件内部在每次AsmCall时,都会有对目标进程分配内存的操作,这样会不够效率.\ 所以增加这个接口，可以让调用者指定分配好的内存,并在此内存上执行call的操作.
        
        参数:
            hwnd (**整形数**): 窗口句柄
            mode (整形数): 模式，取值如下
            base (\_addr** 字符串**): ** 16进制格式. 比如"45A00000",此参数指定的地址必须要求有可读可写可执行属性. 并且内存大小最少要200个字节. 模式6要求至少400个字节. 如果Call的内容较多,那么长度相应也要增加. 如果此参数为空,那么效果就和AsmCall一样.
        
        返回值:
            长整形数: 获取执行汇编代码以后的EAX的值(32位进程),或者RAX的值(64位进程).一般是函数的返回值. 如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数. -200 : 执行中出现错误. -201 : 使用模式5时，没有开启memory盾.
        """
        if not self.obj:
            return 0
        return self._call_function(99632, c_longlong, [c_long, c_long, c_long, c_char_p], self.obj, hwnd, mode, base_addr.encode('gbk') if isinstance(base_addr, str) else base_addr)

    def asm_clear(self):
        """
        AsmClear
        
        清除汇编指令缓冲区 用AsmAdd添加到缓冲的指令全部清除
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(119968, c_long, [c_long], self.obj)

    def asm_set_timeout(self, time_out, param):
        """
        AsmSetTimeout
        
        此接口对AsmCall和AsmCallEx中的模式5和6中内置的一些延时参数进行设置.
        
        参数:
            time (\_out 整形数): 具体含义看以下说明.(默认值10000) 单位毫秒
            param (整形数): 具体含义看以下说明. (默认值100) 单位毫秒
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(117920, c_long, [c_long, c_long, c_long], self.obj, time_out, param)

    def assemble(self, base_addr, is_64bit):
        """
        Assemble
        
        把汇编缓冲区的指令转换为机器码 并用16进制字符串的形式输出
        
        参数:
            base (\_addr 长整形数): 用AsmAdd添加到缓冲区的第一条指令所在的地址
            is (\_64bit 整形数): 表示缓冲区的指令是32位还是64位. 32位表示为0,64位表示为1
        
        返回值:
            字符串: 机器码，比如 "aa bb cc"这样的形式
        """
        if not self.obj:
            return ''
        result = self._call_function(119584, c_char_p, [c_long, c_longlong, c_long], self.obj, base_addr, is_64bit)
        return result.decode('gbk') if result else ''

    def bgr2_rgb(self, bgr_color):
        """
        BGR2RGB
        
        把BGR(按键格式)的颜色格式转换为RGB
        
        参数:
            bgr (\_color 字符串): bgr格式的颜色字符串
        
        返回值:
            字符串: RGB格式的字符串
        """
        if not self.obj:
            return ''
        result = self._call_function(118736, c_char_p, [c_long, c_char_p], self.obj, bgr_color.encode('gbk') if isinstance(bgr_color, str) else bgr_color)
        return result.decode('gbk') if result else ''

    def beep(self, fre, delay):
        """
        Beep
        
        蜂鸣器.
        
        参数:
            f (整形数): 频率
            duration (整形数): 时长(ms).
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(104544, c_long, [c_long, c_long, c_long], self.obj, fre, delay)

    def bind_window(self, hwnd, display, mouse, keypad, mode):
        """
        BindWindow
        
        绑定指定的窗口,并指定这个窗口的屏幕颜色获取方式,鼠标仿真模式,键盘仿真模式,以及模式设定,高级用户可以参考[BindWindowEx](#chmtopic277)更加灵活强大.
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            display (字符串): 屏幕颜色获取方式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台截屏模式\ \ "gdi" : gdi模式,用于窗口采用GDI方式刷新时. 此模式占用CPU较大. 参考[SetAero](#chmtopic278) win10以上系统使用此模式，如果截图失败，尝试把目标程序重新开启再试试。
            mouse (字符串): 鼠标仿真模式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台鼠标模式\ \ "windows": Windows模式,采取模拟windows消息方式 同按键自带后台插件.
            keypad (字符串): 键盘仿真模式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台键盘模式\ \ "windows": Windows模式,采取模拟windows消息方式 同按键的后台插件.\ \ "dx": dx模式,采用模拟dx后台键盘模式。有些窗口在此模式下绑定时，需要先激活窗口再绑定(或者绑定以后激活)，否则可能会出现绑定后键盘无效的情况. 此模式等同于BindWindowEx中的keypad为以下组合\ "dx.public.active.api|dx.public.active.message| dx.keypad.state.api|dx.keypad.api|dx.keypad.input.lock.api"
            mode (整形数): 模式。 取值有以下几种
            需要注意的 (是): 模式101 103在大部分窗口下绑定都没问题。但也有少数特殊的窗口，比如有很多子窗口的窗口，对于这种窗口，在绑定时，一定要把\ 鼠标指向一个可以输入文字的窗口，比如一个文本框，最好能激活这个文本框，这样可以保证绑定的成功.
        
        返回值:
            整形数: 0: 失败 1: 成功  如果返回0，可以调用[GetLastError](#chmtopic280)来查看具体失败错误码,帮助分析问题.
        """
        if not self.obj:
            return 0
        return self._call_function(120080, c_long, [c_long, c_long, c_char_p, c_char_p, c_char_p, c_long], self.obj, hwnd, display.encode('gbk') if isinstance(display, str) else display, mouse.encode('gbk') if isinstance(mouse, str) else mouse, keypad.encode('gbk') if isinstance(keypad, str) else keypad, mode)

    def bind_window_ex(self, hwnd, display, mouse, keypad, public_desc, mode):
        """
        BindWindowEx
        
        绑定指定的窗口,并指定这个窗口的屏幕颜色获取方式,鼠标仿真模式,键盘仿真模式 高级用户使用.
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            display (字符串): 屏幕颜色获取方式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台截屏模式\ \ "gdi" : gdi模式,用于窗口采用GDI方式刷新时. 此模式占用CPU较大. 参考[SetAero](#chmtopic278). win10以上系统使用此模式，如果截图失败，尝试把目标程序重新开启再试试。
            mouse (字符串): 鼠标仿真模式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台鼠标模式\ \ "windows": Windows模式,采取模拟windows消息方式 同按键的后台插件.
            keypad (字符串): 键盘仿真模式 取值有以下几种\ \ "normal" : 正常模式,平常我们用的前台键盘模式\ \ "windows": Windows模式,采取模拟windows消息方式 同按键的后台插件.\ \ dx模式,取值可以是以下任意组合. 组合采用"|"符号进行连接. 支持BindWindow中的缩写模式.比如dx代表" dx.public.active.api|dx.public.active.message| dx.keypad.state.api|dx.keypad.api|dx.keypad.input.lock.api"\ 1\. "dx.keypad.input.lock.api" 此模式表示通过封锁系统API来锁定键盘输入接口.\ 2\. "dx.keypad.state.api" 此模式表示通过封锁系统API来锁定键盘输入状态.\ 3\. "dx.keypad.api" 此模式表示通过封锁系统API来模拟dx键盘输入. \ 4\. "dx.keypad.raw.input" 有些窗口需要这个才可以正常操作键盘.\ 5\. "dx.keypad.raw.input.active" 这个参数必须配合dx.keypad.raw.input才有意义. 有些窗口必须配合这个参数才可以后台. 使用这个参数时，必须在绑定前激活目标窗口. (这个参数能不用就不要用,除非非用不可,可能会对前台产生干扰)
            public (字符串): 公共属性 dx模式共有 \ \ 取值可以是以下任意组合. 组合采用"|"符号进行连接 这个值可以为空\ 1\. "dx.public.active.api" 此模式表示通过封锁系统API来锁定窗口激活状态. 注意，部分窗口在此模式下会耗费大量资源 慎用. \ 2\. "dx.public.active.message" 此模式表示通过封锁系统消息来锁定窗口激活状态. 注意，部分窗口在此模式下会耗费大量资源 慎用. 另外如果要让此模式生效，必须在绑定前，让绑定窗口处于激活状态,否则此模式将失效. 比如dm.SetWindowState hwnd,1 然后再绑定.\ 3\. "dx.public.disable.window.position" 此模式将锁定绑定窗口位置.不可与"dx.public.fake.window.min"共用.\ 4\. "dx.public.disable.window.size" 此模式将锁定绑定窗口,禁止改变大小. 不可与"dx.public.fake.window.min"共用.\ 5\. "dx.public.disable.window.minmax" 此模式将禁止窗口最大化和最小化,但是付出的代价是窗口同时也会被置顶. 不可与"dx.public.fake.window.min"共用.\ 6\. "dx.public.fake.window.min" 此模式将允许目标窗口在最小化状态时，仍然能够像非最小化一样操作.. 另注意，此模式会导致任务栏顺序重排，所以如果是多开模式下，会看起来比较混乱，建议单开使用，多开不建议使用. 同时此模式不是万能的,有些情况下最小化以后图色会不刷新或者黑屏.\ 7\. "dx.public.hide.dll" 此模式将会隐藏目标进程的大漠插件，避免被检测..另外使用此模式前，请仔细做过测试，此模式可能会造成目标进程不稳定，出现崩溃。\ 8\. "dx.public.active.api2" 此模式表示通过封锁系统API来锁定窗口激活状态. 部分窗口遮挡无法后台,需要这个属性. \ 9\. "dx.public.input.ime" 此模式是配合SendStringIme使用. 具体可以查看[SendStringIme](#chmtopic283)接口.\ 10 "dx.public.graphic.protect" 此模式可以保护dx图色不被恶意检测.同时对dx.keypad.api和dx.mouse.api也有保护效果. 这个参数可能会导致某些情况下目标图色失效.一般出现在场景重新加载的时候. 重新绑定会恢复.\ 11 "dx.public.disable.window.show" 禁止目标窗口显示,这个一般用来配合dx.public.fake.window.min来使用. \ 12 "dx.public.anti.api" 此模式可以突破部分窗口对后台的保护.\ 13 "dx.public.km.protect" 此模式可以保护dx键鼠不被恶意检测.最好配合dx.public.anti.api一起使用. 此属性可能会导致部分后台功能失效.\ 14 "dx.public.prevent.block" 绑定模式1 3 5 7 101 103下，可能会导致部分窗口卡死. 这个属性可以避免卡死.\ 15 "dx.public.ori.proc" 此属性只能用在模式0 1 2 3和101下. 有些窗口在不同的界面下(比如登录界面和登录进以后的界面)，键鼠的控制效果不相同. 那可以用这个属性来尝试让保持一致. 注意的是，这个属性不可以滥用，确保测试无问题才可以使用. 否则可能会导致后台失效.\ 16 "dx.public.down.cpu" 此模式可以配合DownCpu来降低目标进程CPU占用. 当图色方式降低CPU无效时，可以尝试此种方式. 需要注意的是，当使用此方式降低CPU时，会让图色方式降低CPU失效\ 17 "dx.public.focus.message" 当后台绑定后,后台无法正常在焦点窗口输入文字时,可以尝试加入此属性. 此属性会强制键盘消息发送到焦点窗口. 慎用此模式,此模式有可能会导致后台键盘在某些情况下失灵.\ 18 "dx.public.graphic.speed" 只针对图色中的dx模式有效.此模式会牺牲目标窗口的性能，来提高DX图色速度，尤其是目标窗口刷新很慢时，这个参数就很有用了.\ 19 "dx.public.memory" 让本对象突破目标进程防护,可以正常使用内存接口. 当用此方式使用内存接口时，内存接口的速度会取决于目标窗口的刷新率.\ 20 "dx.public.inject.super" 突破某些难以绑定的窗口. 此属性仅对除了模式0和2的其他模式有效.\ 21 "dx.public.hack.speed" 类似变速齿轮，配合接口HackSpeed使用\ 22 "dx.public.inject.c" 突破某些难以绑定的窗口. 此属性仅对除了模式0和2的其他模式有效.\ 23 "dx.public.graphic.revert" 此模式将截图后的内容上下反向. 仅对图色模式为dx.graphic.opengl和dx.graphic.opengl.esv2生效.
            mode (整形数): 模式。 取值有以下几种
            需要注意的 (是): 模式101 103在大部分窗口下绑定都没问题。但也有少数特殊的窗口，比如有很多子窗口的窗口，对于这种窗口，在绑定时，一定要把鼠标指向一个可以输入文字的窗口，比如一个文本框，最好能激活这个文本框，这样可以保证绑定的成功.
        
        返回值:
            整形数: 0: 失败 1: 成功  如果返回0，可以调用[GetLastError](#chmtopic280)来查看具体失败错误码,帮助分析问题.
        """
        if not self.obj:
            return 0
        return self._call_function(99456, c_long, [c_long, c_long, c_char_p, c_char_p, c_char_p, c_char_p, c_long], self.obj, hwnd, display.encode('gbk') if isinstance(display, str) else display, mouse.encode('gbk') if isinstance(mouse, str) else mouse, keypad.encode('gbk') if isinstance(keypad, str) else keypad, public_desc.encode('gbk') if isinstance(public_desc, str) else public_desc, mode)

    def capture(self, x1, y1, x2, y2, file):
        """
        Capture
        
        抓取指定区域(x1, y1, x2, y2)的图像,保存为file(24位位图)
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            file (字符串): 保存的文件名,保存的地方一般为SetPath中设置的目录
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(119456, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file)

    def capture_gif(self, x1, y1, x2, y2, file, delay, time):
        """
        CaptureGif
        
        抓取指定区域(x1, y1, x2, y2)的动画，保存为gif格式
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            file (字符串): 保存的文件名,保存的地方一般为SetPath中设置的目录
            delay (整形数): 动画间隔，单位毫秒。 如果为0，表示只截取静态图片
            time (整形数): 总共截取多久的动画，单位毫秒。
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(120912, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file, delay, time)

    def capture_jpg(self, x1, y1, x2, y2, file, quality):
        """
        CaptureJpg
        
        抓取指定区域(x1, y1, x2, y2)的图像,保存为file(JPG压缩格式)
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            file (字符串): 保存的文件名,保存的地方一般为SetPath中设置的目录
            quality (整形数): jpg压缩比率(1-100) 越大图片质量越好
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(106400, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_long], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file, quality)

    def capture_png(self, x1, y1, x2, y2, file):
        """
        CapturePng
        
        同Capture函数，只是保存的格式为PNG.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            file (字符串): 保存的文件名,保存的地方一般为SetPath中设置的目录
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(114080, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file)

    def capture_pre(self, file):
        """
        CapturePre
        
        抓取上次操作的图色区域，保存为file(24位位图)
        
        参数:
            file (字符串): 保存的文件名,保存的地方一般为SetPath中设置的目录
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(109456, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def check_font_smooth(self):
        """
        CheckFontSmooth
        
        检测当前系统是否有开启屏幕字体平滑.
        
        """
        if not self.obj:
            return 0
        return self._call_function(117552, c_long, [c_long], self.obj)

    def check_input_method(self, hwnd, id):
        """
        CheckInputMethod
        
        检测指定窗口所在线程输入法是否开启
        
        参数:
            hwnd (整形数): 窗口句柄\ 
            input (\_method 字符串): 输入法名字。 具体输入法名字对应表查看注册表中以下位置:
        
        返回值:
            整形数: 0 : 未开启
            1 : 开启
        """
        if not self.obj:
            return 0
        return self._call_function(101792, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, id.encode('gbk') if isinstance(id, str) else id)

    def check_uac(self):
        """
        CheckUAC
        
        检测当前系统是否有开启UAC(用户账户控制).
        
        返回值:
            整形数: 0 : 没开启UAC
            1 : 开启了UAC
        """
        if not self.obj:
            return 0
        return self._call_function(123104, c_long, [c_long], self.obj)

    def clear_dict(self, index):
        """
        ClearDict
        
        清空指定的字库.
        
        参数:
            index (整形数): 字库的序号,取值为0-99,目前最多支持100个字库
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(123152, c_long, [c_long, c_long], self.obj, index)

    def client_to_screen(self, hwnd, x, y):
        """
        ClientToScreen
        
        把窗口坐标转换为屏幕坐标
        
        参数:
            hwnd (整形数): 指定的窗口句柄
            x (变参指针): 窗口X坐标
            y (变参指针): 窗口Y坐标
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(116512, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def cmp_color(self, x, y, color, sim):
        """
        CmpColor
        
        比较指定坐标点(x,y)的颜色
        
        参数:
            x (整形数): X坐标
            y (整形数): Y坐标
            color (字符串): 颜色字符串,可以支持偏色,多色,例如 "ffffff-202020|000000-000000" 这个表示白色偏色为202020,和黑色偏色为000000.颜色最多支持10种颜色组合. 注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度(0.1-1.0)
        
        返回值:
            整形数: 0: 颜色匹配 1: 颜色不匹配
        """
        if not self.obj:
            return 0
        return self._call_function(109648, c_long, [c_long, c_long, c_long, c_char_p, c_double], self.obj, x, y, color.encode('gbk') if isinstance(color, str) else color, sim)

    def copy_file(self, src_file, dst_file, over):
        """
        CopyFile
        
        拷贝文件.
        
        参数:
            src (\_file 字符串): 原始文件名
            dst (\_file 字符串): 目标文件名.
            over整形 (数): 取值如下,\ 0 : 如果dst\_file文件存在则不覆盖返回.\ 1 : 如果dst\_file文件存在则覆盖.
        
        """
        if not self.obj:
            return 0
        return self._call_function(100688, c_long, [c_long, c_char_p, c_char_p, c_long], self.obj, src_file.encode('gbk') if isinstance(src_file, str) else src_file, dst_file.encode('gbk') if isinstance(dst_file, str) else dst_file, over)

    def create_folder(self, folder_name):
        """
        CreateFolder
        
        创建指定目录.
        
        参数:
            folder (字符串): 目录名
        
        """
        if not self.obj:
            return 0
        return self._call_function(113120, c_long, [c_long, c_char_p], self.obj, folder_name.encode('gbk') if isinstance(folder_name, str) else folder_name)

    def create_foobar_custom(self, hwnd, x, y, pic, trans_color, sim):
        """
        CreateFoobarCustom
        
        根据指定的位图创建一个自定义形状的窗口
        
        参数:
            hwnd (整形数): 指定的窗口句柄,如果此值为0,那么就在桌面创建此窗口\ 
            x (整形数): 左上角X坐标(相对于hwnd客户区坐标)
            y (整形数): 左上角Y坐标(相对于hwnd客户区坐标)
            pic (\_name 字符串): 位图名字. [如果第一个字符是@,则采用指针方式. @后面是指针地址和大小. 必须是十进制](mailto:如果第一个字符是@,则采用指针方式.%20@后面是指针地址和大小.%20必须是十进制). 具体看下面的例子
            trans (\_color 字符串): 透明色(RRGGBB)
            sim (双精度浮点数): 透明色的相似值 0.1-1.0
        
        """
        if not self.obj:
            return 0
        return self._call_function(105872, c_long, [c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, hwnd, x, y, pic.encode('gbk') if isinstance(pic, str) else pic, trans_color.encode('gbk') if isinstance(trans_color, str) else trans_color, sim)

    def create_foobar_ellipse(self, hwnd, x, y, w, h):
        """
        CreateFoobarEllipse
        
        创建一个椭圆窗口
        
        参数:
            hwnd整形 (数): 指定的窗口句柄,如果此值为0,那么就在桌面创建此窗口\ 
            x整形 (数): 左上角X坐标(相对于hwnd客户区坐标)
            y整形 (数): 左上角Y坐标(相对于hwnd客户区坐标)
            w整形 (数): 矩形区域的宽度
            h整形 (数): 矩形区域的高度
        
        """
        if not self.obj:
            return 0
        return self._call_function(114592, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h)

    def create_foobar_rect(self, hwnd, x, y, w, h):
        """
        CreateFoobarRect
        
        创建一个矩形窗口
        
        参数:
            hwnd整形 (数): 指定的窗口句柄,如果此值为0,那么就在桌面创建此窗口\ 
            x整形 (数): 左上角X坐标(相对于hwnd客户区坐标)
            y整形 (数): 左上角Y坐标(相对于hwnd客户区坐标)
            w整形 (数): 矩形区域的宽度
            h整形 (数): 矩形区域的高度
        
        """
        if not self.obj:
            return 0
        return self._call_function(119072, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h)

    def create_foobar_round_rect(self, hwnd, x, y, w, h, rw, rh):
        """
        CreateFoobarRoundRect
        
        创建一个圆角矩形窗口
        
        参数:
            hwnd整形 (数): 指定的窗口句柄,如果此值为0,那么就在桌面创建此窗口\ 
            x整形 (数): 左上角X坐标(相对于hwnd客户区坐标)
            y整形 (数): 左上角Y坐标(相对于hwnd客户区坐标)
            w整形 (数): 矩形区域的宽度
            h整形 (数): 矩形区域的高度
            rw整形 (数): 圆角的宽度
            rh整形 (数): 圆角的高度
        
        """
        if not self.obj:
            return 0
        return self._call_function(108352, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h, rw, rh)

    def decode_file(self, file, pwd):
        """
        DecodeFile
        
        解密指定的文件.
        
        参数:
            file (字符串): 文件名.
            pwd (字符串): 密码.
        
        """
        if not self.obj:
            return 0
        return self._call_function(122496, c_long, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def delay(self, mis):
        """
        Delay
        
        延时指定的毫秒,过程中不阻塞UI操作. 一般高级语言使用.按键用不到.
        
        参数:
            mis整形 (数): 毫秒数. **必须大于0.**
        
        """
        if not self.obj:
            return 0
        return self._call_function(106480, c_long, [c_long, c_long], self.obj, mis)

    def delays(self, min_s, max_s):
        """
        Delays
        
        延时指定范围内随机毫秒,过程中不阻塞UI操作. 一般高级语言使用.按键用不到.
        
        参数:
            mis (\_min整形数): 最小毫秒数. **必须大于0**
            mis (\_max整形数): 最大毫秒数. **必须大于0**
        
        """
        if not self.obj:
            return 0
        return self._call_function(123328, c_long, [c_long, c_long, c_long], self.obj, min_s, max_s)

    def delete_file(self, file):
        """
        DeleteFile
        
        删除文件.
        
        参数:
            file (字符串): 文件名
        
        """
        if not self.obj:
            return 0
        return self._call_function(99408, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def delete_folder(self, folder_name):
        """
        DeleteFolder
        
        删除指定目录.
        
        参数:
            folder (字符串): 目录名
        
        """
        if not self.obj:
            return 0
        return self._call_function(118800, c_long, [c_long, c_char_p], self.obj, folder_name.encode('gbk') if isinstance(folder_name, str) else folder_name)

    def delete_ini(self, section, key, file):
        """
        DeleteIni
        
        删除指定的ini小节.
        
        参数:
            section (字符串): 小节名
            key (字符串): 变量名. 如果这个变量为空串，则删除整个section小节.
            file (字符串): ini文件名.
        
        """
        if not self.obj:
            return 0
        return self._call_function(111168, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file)

    def delete_ini_pwd(self, section, key, file, pwd):
        """
        DeleteIniPwd
        
        删除指定的ini小节.支持加密文件
        
        参数:
            section (字符串): 小节名
            key (字符串): 变量名. 如果这个变量为空串，则删除整个section小节.
            file (字符串): ini文件名.
            pwd (字符串): 密码.
        
        """
        if not self.obj:
            return 0
        return self._call_function(99344, c_long, [c_long, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def dis_assemble(self, asm_code, base_addr, is_64bit):
        """
        DisAssemble
        
        把指定的机器码转换为汇编语言输出
        
        参数:
            asm (\_code **字符串**): 机器码，形式如 "aa bb cc"这样的16进制表示的字符串(空格无所谓)
            base (\_addr 长整形数): 指令所在的地址
            is (\_64bit 整形数): 表示asm\_code表示的指令是32位还是64位. 32位表示为0,64位表示为1
        
        返回值:
            字符串: MASM汇编语言字符串.如果有多条指令，则每条指令以字符"|"连接.
        """
        if not self.obj:
            return ''
        result = self._call_function(112656, c_char_p, [c_long, c_char_p, c_longlong, c_long], self.obj, asm_code.encode('gbk') if isinstance(asm_code, str) else asm_code, base_addr, is_64bit)
        return result.decode('gbk') if result else ''

    def disable_close_display_and_sleep(self):
        """
        DisableCloseDisplayAndSleep
        
        设置当前的电源设置，禁止关闭显示器，禁止关闭硬盘，禁止睡眠，禁止待机. 不支持XP.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(114416, c_long, [c_long], self.obj)

    def disable_font_smooth(self):
        """
        DisableFontSmooth
        
        关闭当前系统屏幕字体平滑.同时关闭系统的ClearType功能.
        
        """
        if not self.obj:
            return 0
        return self._call_function(118368, c_long, [c_long], self.obj)

    def disable_power_save(self):
        """
        DisablePowerSave
        
        关闭电源管理，不会进入睡眠.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(121952, c_long, [c_long], self.obj)

    def disable_screen_save(self):
        """
        DisableScreenSave
        
        关闭屏幕保护.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(112800, c_long, [c_long], self.obj)

    def dm_guard(self, enable, type):
        """
        DmGuard
        
        针对部分检测措施的保护盾.  前面有五角星的表示同时支持32位和64位,否则就仅支持64位. \ 驱动功能支持的系统版本号为(win7/win8/win8.1/win10(10240)/win10(10586)/win10(14393)/win10(15063)/win10(16299)/win10(17134)/win10(17763)/win10(18362)/win10(18363)/win10(19041)/win10(19042) /win10(19043)/win10(19044)/win10(19045)/win11(22000)/win11(22621)/win11(22631)\ 不支持所有的预览版本,仅仅支持正式版本. 新点的WIN10和WIN11必须要关闭内核隔离.否则会无法加载驱动,或者加载某些功能蓝屏.
        
        参数:
            enable (整形数): \ 0表示关闭保护盾(仅仅对memory memory2 memory3 memory4 b2 b3起作用)\ 1表示打开保护盾
            type (字符串): 参数具体内容可以是以下任意一个.\ ★"np" : 这个是防止NP检测(这个盾已经过时,不建议使用).\ ★"memory" : 这个保护内存系列接口和汇编接口可以正常运行. (此模式需要加载驱动)\ ★"memory2" : 这个保护内存系列接口和汇编接口可以正常运行. (此模式需要加载驱动)\ "memory3 pid addr\_start addr\_end" : 这个保护内存系列接口和汇编接口可以正常运行.pid表示要操作内存的进程ID,指定了以后,所有内存系列接口仅能对此pid进程进行操作,其他进程无效. 但此盾速度较快。addr\_start表示起始地址(此参数可以忽略),addr\_end表示结束地址(此参数可以忽略). 另外，如果你发现有地址读写不到，可以尝试重新调用一次此盾.此盾是对指定的PID，指定的地址范围做快照. (此模式需要加载驱动)\ "memory4" : 这个保护内存系列接口和汇编接口可以正常运行. (此模式需要加载驱动)\ "memory5" : 这个保护内存系列接口和汇编接口可以正常运行. (此模式需要加载驱动,直接读写物理内存,所以对于地址空间不在物理内存里的地址,就会无法读写.)\ "memory6" : 这个保护内存系列接口和汇编接口可以正常运行. (此模式是memory5的加强版本,需要加载驱动,直接读写物理内存,所以对于地址空间不在物理内存里的地址,就会无法读写.)\ "phide [pid]" : 隐藏指定进程,保护指定进程以及进程内的窗口不被非法访问. pid为可选参数.如果不指定pid，默认保护当前进程. (此模式需要加载驱动,目前仅支持32位系统)\ "phide2 [pid]" : 同phide. 只是进程不隐藏(可在任务管理器中操作) (此模式需要加载驱动,目前仅支持32位系统)\ "phide3 [pid]" : 只隐藏进程(在任务管理器看不到),但不保护进程和窗口. (此模式需要加载驱动,目前仅支持32位系统)\ ★"display2" : 同display,但此模式用在一些极端的场合. 比如用任何截图软件也无法截图时，可以考虑这个盾.\ \ ★"display3 <hwnd>" : 此盾可以保护当前进程指定的窗口(和子窗口)，无法被用正常手段截图. hwnd是必选参数. 并且必须是和当前调用进程相同进程的顶级窗口. 此盾有限制,具体查看下方的备注.
        
        """
        if not self.obj:
            return 0
        return self._call_function(103552, c_long, [c_long, c_long, c_char_p], self.obj, enable, type.encode('gbk') if isinstance(type, str) else type)

    def dm_guard_extract(self, type, path):
        """
        DmGuardExtract
        
        释放插件用的驱动. 可以自己拿去签名. 防止有人对我的签名进行检测. 强烈推荐使用驱动的用户使用. 仅释放64位系统的驱动.
        
        参数:
            type (字符串): 需要释放的驱动类型. 这里写"common"即可.
            path (字符串): 释放出的驱动文件全路径. 比如"c:\test.sys".
        
        """
        if not self.obj:
            return 0
        return self._call_function(112160, c_long, [c_long, c_char_p, c_char_p], self.obj, type.encode('gbk') if isinstance(type, str) else type, path.encode('gbk') if isinstance(path, str) else path)

    def dm_guard_load_custom(self, type, path):
        """
        DmGuardLoadCustom
        
        加载用DmGuardExtract释放出的驱动. 建议自己签名后,然后找个自己喜欢的路径加载. 仅支持64位系统的驱动加载. 加载成功后,就可以正常调用DmGuard了.
        
        参数:
            type (字符串): 需要释放的驱动类型. 这里写"common"即可.
            path (字符串): 驱动文件全路径. 比如"c:\test.sys".
        
        """
        if not self.obj:
            return 0
        return self._call_function(106896, c_long, [c_long, c_char_p, c_char_p], self.obj, type.encode('gbk') if isinstance(type, str) else type, path.encode('gbk') if isinstance(path, str) else path)

    def dm_guard_params(self, cmd, sub_cmd, param):
        """
        DmGuardParams
        
        DmGuard的加强接口,用于获取一些额外信息. 具体看下面参数介绍
        
        参数:
            cmd (字符串): 盾类型. 这里取值为"gr"或者"th"(以后可能会有扩充). 这里要注意的是,如果要获取指定的盾类型信息,必须先成功用DmGuard开启此盾.比如这里的"gr"必须dm.DmGuard 1,"gr"开启成功才可以
            subcmd (字符串): 针对具体的盾类型，需要获取的具体信息.
            param (字符串): 参数信息,这里具体的含义取决于cmd和subcmd.
        
        返回值:
            字符串: 根据不同的cmd和subcmd,返回值不同.
            `           `如果cmd为"gr"时,subcmd取值为如下时，具体的返回值: `                      `"enum" : "handle1|handle2|.....|handlen",每个handle都是10进制长整数. 如果失败返回空字符串 `                      `"get"  : "type|name|access". type表示句柄的类型，比如"Event","File"等之类的. name表示句柄的名字,有些句柄的名字可能是空的. access10进制整数,表示此句柄的权限值. 如果失败返回空字符串 `                      `"set"  : 成功返回"ok",否则为空字符串. `                      `"close": 成功返回"ok",否则为空字符串.
            `           `如果cmd为"th"时,subcmd取值为如下时，具体的返回值: `                      `"enum" : "tid1|tid2|.....|tidn",每个tid都是10进制整数. 如果失败返回空字符串 `                      `"get"  : "tid|prority|ethread|teb|win32StartAddress|module\_name|switch\_count|state|suspend\_count".如果失败返回空字符串. `                                `tid : 线程tid,10进制整数 `                                `prority : 线程优先级, 10进制整数 `                                `ethread : 线程内核对象ETHREAD指针. 64位16进制整数. `                                `teb : 线程内核对象TEB指针. 64位16进制整数 `                                `win32StartAddress : 线程起始地址. 64位16进制整数 `                                `module\_name : 线程起始地址所在的模块名. `                                `switch\_count : 线程切换次数. 10进制整数 `                                `state : 线程状态. 10进制整数. 0 : 初始化 1 : 准备 2 : 运行 3 : 待机 4 : 结束 5 : 等待 6 : 转换. 这个地方其实只需要关心是不是4就行了. 如果是4表示线程结束了. 其它的状态都可以认为是运行状态. 不用太关心. `                                `suspend\_count : 线程挂起次数. 10进制整数. 线程挂起次数,当此值大于0时,表示线程处于挂起状态. 等于0表示处于运行状态. `                      `"resume"  : 成功返回"ok",否则为空字符串. `                      `"suspend": 成功返回"ok",否则为空字符串. `                      `"terminate": 成功返回"ok",否则为空字符串.
        """
        if not self.obj:
            return ''
        result = self._call_function(105472, c_char_p, [c_long, c_char_p, c_char_p, c_char_p], self.obj, cmd.encode('gbk') if isinstance(cmd, str) else cmd, sub_cmd.encode('gbk') if isinstance(sub_cmd, str) else sub_cmd, param.encode('gbk') if isinstance(param, str) else param)
        return result.decode('gbk') if result else ''

    def double_to_data(self, double_value):
        """
        DoubleToData
        
        把双精度浮点数转换成二进制形式.
        
        参数:
            value (**双精度浮点数**): 需要转化的双精度浮点数
        
        返回值:
            字符串: 字符串形式表达的二进制数据. 可以用于WriteData FindData FindDataEx等接口.
        """
        if not self.obj:
            return ''
        result = self._call_function(111856, c_char_p, [c_long, c_double], self.obj, double_value)
        return result.decode('gbk') if result else ''

    def down_cpu(self, type, rate):
        """
        DownCpu
        
        降低目标窗口所在进程的CPU占用.
        
        参数:
            type (整形数): 当取值为0时,rate取值范围大于等于0 ,这个值越大表示降低CPU效果越好\ 当取值为1时,rate取值范围大于等于0,表示以固定的FPS来降低CPU. rate表示FPS. 并且这时不能有dx.public.down.cpu.
            rate (整形数): 取值取决于type. 为0表示关闭
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(112960, c_long, [c_long, c_long, c_long], self.obj, type, rate)

    def download_file(self, url, save_file, timeout):
        """
        DownloadFile
        
        从internet上下载一个文件.
        
        参数:
            url (字符串): 下载的url地址.
            save (\_file 字符串): 要保存的文件名.
            timeout整形 (数): 连接超时时间，单位是毫秒.
        
        """
        if not self.obj:
            return 0
        return self._call_function(123648, c_long, [c_long, c_char_p, c_char_p, c_long], self.obj, url.encode('gbk') if isinstance(url, str) else url, save_file.encode('gbk') if isinstance(save_file, str) else save_file, timeout)

    def enable_bind(self, en):
        """
        EnableBind
        
        设置是否暂时关闭或者开启后台功能. 默认是开启.  一般用在前台切换，或者脚本暂停和恢复时，可以让用户操作窗口.
        
        参数:
            enable (整形数): 0 全部关闭(图色键鼠都关闭,也就是说图色,键鼠都是前台,但是如果有指定dx.public.active.message时，在窗口前后台切换时，这个属性会失效.)\ -1 只关闭图色.(也就是说图色是normal前台. 键鼠不变)\ 1 开启(恢复原始状态)\ 5 同0，也是全部关闭，但是这个模式下，就算窗口在前后台切换时，属性dx.public.active.message的效果也一样不会失效.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(116576, c_long, [c_long, c_long], self.obj, en)

    def enable_display_debug(self, enable_debug):
        """
        EnableDisplayDebug
        
        开启图色调试模式，此模式会稍许降低图色和文字识别的速度.默认不开启.
        
        参数:
            enable (\_debug 整形数): 0 为关闭
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(99296, c_long, [c_long, c_long], self.obj, enable_debug)

    def enable_fake_active(self, en):
        """
        EnableFakeActive
        
        设置是否开启后台假激活功能. 默认是关闭. 一般用不到. 除非有人有特殊需求. 注意看注释.
        
        参数:
            enable (整形数): 0 关闭\ 1 开启
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(107888, c_long, [c_long, c_long], self.obj, en)

    def enable_find_pic_multithread(self, en):
        """
        EnableFindPicMultithread
        
        当执行FindPicXXX系列接口时,是否在条件满足下(查找的图片大于等于4,这个值可以根据[SetFindPicMultithreadCount](#chmtopic586)来修改),开启多线程查找。 默认打开.
        
        参数:
            enable (整形数): 0 关闭
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(118048, c_long, [c_long, c_long], self.obj, en)

    def enable_font_smooth(self):
        """
        EnableFontSmooth
        
        开启当前系统屏幕字体平滑.同时开启系统的ClearType功能.
        
        """
        if not self.obj:
            return 0
        return self._call_function(103936, c_long, [c_long], self.obj)

    def enable_get_color_by_capture(self, enable):
        """
        EnableGetColorByCapture
        
        允许调用GetColor GetColorBGR GetColorHSV 以及 CmpColor时，以截图的方式来获取颜色。 默认关闭.
        
        参数:
            enable (整形数): 0 关闭
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(109216, c_long, [c_long, c_long], self.obj, enable)

    def enable_ime(self, en):
        """
        EnableIme
        
        设置是否关闭绑定窗口所在进程的输入法.
        
        参数:
            enable (整形数): 1 开启\ 0 关闭
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(120192, c_long, [c_long, c_long], self.obj, en)

    def enable_keypad_msg(self, en):
        """
        EnableKeypadMsg
        
        是否在使用dx键盘时开启windows消息.默认开启.
        
        参数:
            enable (整形数): 0 禁止\ 1开启
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(120864, c_long, [c_long, c_long], self.obj, en)

    def enable_keypad_patch(self, enable):
        """
        EnableKeypadPatch
        
        键盘消息发送补丁. 默认是关闭.
        
        参数:
            enable (整形数): 0 禁止\ 1开启
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(116672, c_long, [c_long, c_long], self.obj, enable)

    def enable_keypad_sync(self, enable, time_out):
        """
        EnableKeypadSync
        
        键盘消息采用同步发送模式.默认异步.
        
        参数:
            enable (整形数): 0 禁止同步\ 1开启同步
            time (\_out 整形数): 单位是毫秒,表示同步等待的最大时间.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(109968, c_long, [c_long, c_long, c_long], self.obj, enable, time_out)

    def enable_mouse_accuracy(self, en):
        """
        EnableMouseAccuracy
        
        设置当前系统鼠标的精确度开关. 如果所示。 此接口仅仅对前台MoveR接口起作用. ![](Aspose.Words.894c5d01-8a6e-49c3-93b9-a1140f340381.016.jpeg)
        
        参数:
            enable整形 (数): 0 关闭指针精确度开关. 1打开指针精确度开关. 一般推荐关闭.
        
        返回值:
            整形数: 设置之前的精确度开关.
        """
        if not self.obj:
            return 0
        return self._call_function(123760, c_long, [c_long, c_long], self.obj, en)

    def enable_mouse_msg(self, en):
        """
        EnableMouseMsg
        
        是否在使用dx鼠标时开启windows消息.默认开启.
        
        参数:
            enable (整形数): 0 禁止\ 1开启
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(101344, c_long, [c_long, c_long], self.obj, en)

    def enable_mouse_sync(self, enable, time_out):
        """
        EnableMouseSync
        
        鼠标消息采用同步发送模式.默认异步.
        
        参数:
            enable (整形数): 0 禁止同步\ 1开启同步
            time (\_out 整形数): 单位是毫秒,表示同步等待的最大时间.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(98496, c_long, [c_long, c_long, c_long], self.obj, enable, time_out)

    def enable_pic_cache(self, en):
        """
        EnablePicCache
        
        设置是否开启或者关闭插件内部的图片缓存机制. (默认是打开).
        
        参数:
            enable (整形数): \ 0 : 关闭\ 1 : 打开
        
        返回值:
            整形数: 0: 失败
            1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(99536, c_long, [c_long, c_long], self.obj, en)

    def enable_real_keypad(self, en):
        """
        EnableRealKeypad
        
        键盘动作模拟真实操作,点击延时随机.
        
        参数:
            enable (整形数): 0 关闭模拟\ 1 开启模拟
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(105648, c_long, [c_long, c_long], self.obj, en)

    def enable_real_mouse(self, en, mousedelay, mousestep):
        """
        EnableRealMouse
        
        鼠标动作模拟真实操作,带移动轨迹,以及点击延时随机.
        
        参数:
            enable (整形数): 0 关闭模拟\ 1 开启模拟(直线模拟)\ 2 开启模拟(随机曲线,更接近真实)\ 3 开启模拟(小弧度曲线,弧度随机)\ 4 开启模拟(大弧度曲线,弧度随机)
            mousedelay (整形数): 单位是毫秒. 表示在模拟鼠标移动轨迹时,每移动一次的时间间隔.这个值越大,鼠标移动越慢. 必须大于0,否则会失败.
            Mousestep (整形数): 表示在模拟鼠标移动轨迹时,每移动一次的距离. 这个值越大，鼠标移动越快速.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(105952, c_long, [c_long, c_long, c_long, c_long], self.obj, en, mousedelay, mousestep)

    def enable_share_dict(self, en):
        """
        EnableShareDict
        
        允许当前调用的对象使用全局字库。  如果你的程序中对象太多,并且每个对象都用到了同样的字库,可以考虑用全局字库,这样可以节省大量内存.
        
        参数:
            enable (整形数): 0 关闭
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(108992, c_long, [c_long, c_long], self.obj, en)

    def enable_speed_dx(self, en):
        """
        EnableSpeedDx
        
        设置是否开启高速dx键鼠模式。 默认是关闭.
        
        参数:
            enable (整形数): 0 关闭\ 1 开启
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(115472, c_long, [c_long, c_long], self.obj, en)

    def encode_file(self, file, pwd):
        """
        EncodeFile
        
        加密指定的文件.
        
        参数:
            file (字符串): 文件名.
            pwd (字符串): 密码.
        
        """
        if not self.obj:
            return 0
        return self._call_function(106528, c_long, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def enter_cri(self):
        """
        EnterCri
        
        检测是否可以进入临界区,如果可以返回1,否则返回0. 此函数如果返回1，则调用对象就会占用此互斥信号量,直到此对象调用LeaveCri,否则不会释放.注意:如果调用对象在释放时，会自动把本对象占用的互斥信号量释放.
        
        返回值:
            整形数: 0 : 不可以
            1 : 已经进入临界区
        """
        if not self.obj:
            return 0
        return self._call_function(116336, c_long, [c_long], self.obj)

    def enum_ini_key(self, section, file):
        """
        EnumIniKey
        
        根据指定的ini文件以及section,枚举此section中所有的key名
        
        参数:
            section (字符串): 小节名. (不可为空)
            file (字符串): ini文件名.
        
        """
        if not self.obj:
            return ''
        result = self._call_function(108032, c_char_p, [c_long, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, file.encode('gbk') if isinstance(file, str) else file)
        return result.decode('gbk') if result else ''

    def enum_ini_key_pwd(self, section, file, pwd):
        """
        EnumIniKeyPwd
        
        根据指定的ini文件以及section,枚举此section中所有的key名.可支持加密文件
        
        参数:
            section (字符串): 小节名. (不可为空)
            file (字符串): ini文件名.
            pwd (字符串): 密码
        
        """
        if not self.obj:
            return ''
        result = self._call_function(116768, c_char_p, [c_long, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)
        return result.decode('gbk') if result else ''

    def enum_ini_section(self, file):
        """
        EnumIniSection
        
        根据指定的ini文件,枚举此ini中所有的Section(小节名)
        
        参数:
            file (字符串): ini文件名.
        
        """
        if not self.obj:
            return ''
        result = self._call_function(117184, c_char_p, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)
        return result.decode('gbk') if result else ''

    def enum_ini_section_pwd(self, file, pwd):
        """
        EnumIniSectionPwd
        
        根据指定的ini文件,枚举此ini中所有的Section(小节名) 可支持加密文件
        
        参数:
            file (字符串): ini文件名.
            pwd (字符串): 密码
        
        """
        if not self.obj:
            return ''
        result = self._call_function(116992, c_char_p, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)
        return result.decode('gbk') if result else ''

    def enum_process(self, name):
        """
        EnumProcess
        
        根据指定进程名,枚举系统中符合条件的进程PID,并且按照进程打开顺序排序.
        
        参数:
            name (字符串): 进程名,比如qq.exe
        
        返回值:
            字符串 : 返回所有匹配的进程PID,并按打开顺序排序,格式"pid1,pid2,pid3"
        """
        if not self.obj:
            return ''
        result = self._call_function(112288, c_char_p, [c_long, c_char_p], self.obj, name.encode('gbk') if isinstance(name, str) else name)
        return result.decode('gbk') if result else ''

    def enum_window(self, parent, title, class_name, filter):
        """
        EnumWindow
        
        根据指定条件,枚举系统中符合条件的窗口,可以枚举到按键自带的无法枚举到的窗口
        
        参数:
            parent (整形数): 获得的窗口句柄是该窗口的子窗口的窗口句柄,取0时为获得桌面句柄
            title (字符串): 窗口标题. 此参数是模糊匹配.
            class (\_name 字符串): 窗口类名. 此参数是模糊匹配.
            filter整形 (数): 取值定义如下
            1 (): 匹配窗口标题,参数title有效
            2 (): 匹配窗口类名,参数class\_name有效.
            4 (): 只匹配指定父窗口的第一层孩子窗口
            8 (): 匹配父窗口为0的窗口,即顶级窗口
            16 (): 匹配可见的窗口
            32 (): 匹配出的窗口按照窗口打开顺序依次排列
        
        返回值:
            字符串 : 返回所有匹配的窗口句柄字符串,格式"hwnd1,hwnd2,hwnd3"
        """
        if not self.obj:
            return ''
        result = self._call_function(115296, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long], self.obj, parent, title.encode('gbk') if isinstance(title, str) else title, class_name.encode('gbk') if isinstance(class_name, str) else class_name, filter)
        return result.decode('gbk') if result else ''

    def enum_window_by_process(self, process_name, title, class_name, filter):
        """
        EnumWindowByProcess
        
        根据指定进程以及其它条件,枚举系统中符合条件的窗口,可以枚举到按键自带的无法枚举到的窗口
        
        参数:
            process (\_name 字符串): 进程映像名.比如(svchost.exe). 此参数是精确匹配,但不区分大小写.
            title (字符串): 窗口标题. 此参数是模糊匹配.
            class (\_name 字符串): 窗口类名. 此参数是模糊匹配.
            filter (整形数): 取值定义如下
            1 (): 匹配窗口标题,参数title有效
            2 (): 匹配窗口类名,参数class\_name有效
            4 (): 只匹配指定映像的所对应的第一个进程. 可能有很多同映像名的进程，只匹配第一个进程的.
            8 (): 匹配父窗口为0的窗口,即顶级窗口
            16 (): 匹配可见的窗口
            32 (): 匹配出的窗口按照窗口打开顺序依次排列
        
        返回值:
            字符串: 返回所有匹配的窗口句柄字符串,格式"hwnd1,hwnd2,hwnd3"
        """
        if not self.obj:
            return ''
        result = self._call_function(110192, c_char_p, [c_long, c_char_p, c_char_p, c_char_p, c_long], self.obj, process_name.encode('gbk') if isinstance(process_name, str) else process_name, title.encode('gbk') if isinstance(title, str) else title, class_name.encode('gbk') if isinstance(class_name, str) else class_name, filter)
        return result.decode('gbk') if result else ''

    def enum_window_by_process_id(self, pid, title, class_name, filter):
        """
        EnumWindowByProcessId
        
        根据指定进程pid以及其它条件,枚举系统中符合条件的窗口,可以枚举到按键自带的无法枚举到的窗口
        
        参数:
            pid (整形数): 进程pid.
            title (字符串): 窗口标题. 此参数是模糊匹配.
            class (\_name 字符串): 窗口类名. 此参数是模糊匹配.
            filter (整形数): 取值定义如下
            1 (): 匹配窗口标题,参数title有效
            2 (): 匹配窗口类名,参数class\_name有效
            8 (): 匹配父窗口为0的窗口,即顶级窗口
            16 (): 匹配可见的窗口
        
        返回值:
            字符串: 返回所有匹配的窗口句柄字符串,格式"hwnd1,hwnd2,hwnd3"
        """
        if not self.obj:
            return ''
        result = self._call_function(124672, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long], self.obj, pid, title.encode('gbk') if isinstance(title, str) else title, class_name.encode('gbk') if isinstance(class_name, str) else class_name, filter)
        return result.decode('gbk') if result else ''

    def enum_window_super(self, spec1, flag1, type1, spec2, flag2, type2, sort):
        """
        EnumWindowSuper
        
        根据两组设定条件来枚举指定窗口.
        
        参数:
            spec1 (字符串): 查找串1. (内容取决于flag1的值)
            flag1整形数 (: 取值如下): 
            type1 (整形数): 取值如下
            spec2 (字符串): 查找串2. (内容取决于flag2的值)
            flag2 (整形数): 取值如下:
            type2 (整形数): 取值如下
            sort (整形数): 取值如下
        
        """
        if not self.obj:
            return ''
        result = self._call_function(107360, c_char_p, [c_long, c_char_p, c_long, c_long, c_char_p, c_long, c_long, c_long], self.obj, spec1.encode('gbk') if isinstance(spec1, str) else spec1, flag1, type1, spec2.encode('gbk') if isinstance(spec2, str) else spec2, flag2, type2, sort)
        return result.decode('gbk') if result else ''

    def exclude_pos(self, all_pos, type, x1, y1, x2, y2):
        """
        ExcludePos
        
        根据部分Ex接口的返回值，排除指定范围区域内的坐标.
        
        参数:
            all (\_pos 字符串): 坐标描述串。 一般是FindStrEx,FindStrFastEx,FindStrWithFontEx, FindColorEx, FindMultiColorEx,和FindPicEx的返回值.
            type (整形数): 取值为0或者1
            x1 (整形数): 左上角横坐标
            y1 (整形数): 左上角纵坐标
            x2 (整形数): 右下角横坐标
            y2 (整形数): 右下角纵坐标
        
        返回值:
            字符串: 经过筛选以后的返回值，格式和type指定的一致.
        """
        if not self.obj:
            return ''
        result = self._call_function(120992, c_char_p, [c_long, c_char_p, c_long, c_long, c_long, c_long, c_long], self.obj, all_pos.encode('gbk') if isinstance(all_pos, str) else all_pos, type, x1, y1, x2, y2)
        return result.decode('gbk') if result else ''

    def execute_cmd(self, cmd, current_dir, time_out):
        """
        ExecuteCmd
        
        执行指定的CMD指令,并返回cmd的输出结果.
        
        参数:
            cmd字符 (串): 需要执行的CMD指令. 比如"dir"
            current (\_dir字符串): 执行此cmd命令时,所在目录. 如果为空，表示使用当前目录. 比如""或者"c:"
            time (\_out 整形数): 超时设置,单位是毫秒. 0表示一直等待. 大于0表示等待指定的时间后强制结束,防止卡死.
        
        返回值:
            字符串: cmd指令的执行结果.  返回空字符串表示执行失败.
        """
        if not self.obj:
            return ''
        result = self._call_function(116928, c_char_p, [c_long, c_char_p, c_char_p, c_long], self.obj, cmd.encode('gbk') if isinstance(cmd, str) else cmd, current_dir.encode('gbk') if isinstance(current_dir, str) else current_dir, time_out)
        return result.decode('gbk') if result else ''

    def exit_os(self, type):
        """
        ExitOs
        
        退出系统(注销 重启 关机)
        
        参数:
            type (整形数): 取值为以下类型
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(115024, c_long, [c_long, c_long], self.obj, type)

    def faq_cancel(self):
        """
        FaqCancel
        
        可以把上次FaqPost的发送取消,接着下一次FaqPost
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(113968, c_long, [c_long], self.obj)

    def faq_capture(self, x1, y1, x2, y2, quality, delay, time):
        """
        FaqCapture
        
        截取指定范围内的动画或者图像,并返回此句柄.
        
        参数:
            x1 (整形数): 左上角X坐标
            y1 (整形数): 左上角Y坐标
            x2 (整形数): 右下角X坐标
            y2 (整形数): 右下角Y坐标
            quality (整形数): 图像或动画品质,或者叫压缩率,此值越大图像质量越好 取值范围（1-100或者250） 当此值为250时，那么会截取无损bmp图像数据.
            delay (整形数): 截取动画时用,表示相隔两帧间的时间间隔,单位毫秒 （如果只是截取静态图像,这个参数必须是0）
            time (整形数): 表示总共截取多久的动画,单位毫秒 （如果只是截取静态图像,这个参数必须是0）
        
        返回值:
            整形数: 图像或者动画句柄
        """
        if not self.obj:
            return 0
        return self._call_function(118416, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2, quality, delay, time)

    def faq_capture_from_file(self, x1, y1, x2, y2, file, quality):
        """
        FaqCaptureFromFile
        
        截取指定图片中的图像,并返回此句柄.
        
        参数:
            x1 (整形数): 左上角X坐标
            y1 (整形数): 左上角Y坐标
            x2 (整形数): 右下角X坐标
            y2 (整形数): 右下角Y坐标
            file (字符串): 图片文件名,图像格式基本都支持.
            quality (整形数): 图像或动画品质,或者叫压缩率,此值越大图像质量越好 取值范围（1-100或者250）.当此值为250时,会截取无损bmp图像数据.
        
        返回值:
            整形数: 图像或者动画句柄
        """
        if not self.obj:
            return 0
        return self._call_function(116256, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_long], self.obj, x1, y1, x2, y2, file.encode('gbk') if isinstance(file, str) else file, quality)

    def faq_capture_string(self, text):
        """
        FaqCaptureString
        
        从给定的字符串(也可以算是文字类型的问题),获取此句柄. （此接口必须配合答题器v30以后的版本）
        
        参数:
            text (字符串): 文字类型的问题. 比如(桃园三结义指的是哪些人?)
        
        返回值:
            整形数: 文字句柄
        """
        if not self.obj:
            return 0
        return self._call_function(106208, c_long, [c_long, c_char_p], self.obj, text.encode('gbk') if isinstance(text, str) else text)

    def faq_fetch(self):
        """
        FaqFetch
        
        获取由FaqPost发送后，由服务器返回的答案.
        
        返回值:
            字符串: 如果此函数调用失败,那么返回值如下
            "Error:错误描述"
            如果函数调用成功,那么返回值如下
            "OK:答案"
            根据FaqPost中 request\_type取值的不同,返回值不同
            当request\_type 为0时,答案的格式为"x,y" (不包含引号)
            当request\_type 为1时,答案的格式为"1" "2" "3" "4" "5" "6" (不包含引号)
            当request\_type 为2时,答案就是要求的答案 比如 "李白" (不包含引号)
            当request\_type 为3时,答案的格式为"x1,y1|..|xn,yn" 比如 "20,30|78,68|33,33" (不包含引号)
            如果返回为空字符串，表示FaqPost还未处理完毕,或者没有调用过FaqPost.
        """
        if not self.obj:
            return ''
        result = self._call_function(117744, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def faq_get_size(self, handle):
        """
        FaqGetSize
        
        获取句柄所对应的数据包的大小,单位是字节
        
        参数:
            handle (整形数): 由FaqCapture返回的句柄
        
        返回值:
            整形数: 数据包大小,一般用于判断数据大小,选择合适的压缩比率.
        """
        if not self.obj:
            return 0
        return self._call_function(103456, c_long, [c_long, c_long], self.obj, handle)

    def faq_is_posted(self):
        """
        FaqIsPosted
        
        用于判断当前对象是否有发送过答题(FaqPost)
        
        返回值:
            整形数: 0 : 没有 1 : 有发送过
        """
        if not self.obj:
            return 0
        return self._call_function(102864, c_long, [c_long], self.obj)

    def faq_post(self, server, handle, request_type, time_out):
        """
        FaqPost
        
        发送指定的图像句柄到指定的服务器,并立即返回(异步操作).
        
        参数:
            server (字符串): 服务器地址以及端口,格式为(ip:port),例如 "192.168.1.100:12345"
            handle (整形数): 由FaqCapture获取到的句柄
            request (\_type 整形数): 取值定义如下
            3 (): 要求获取N个坐标.此功能要求答题器必须是v15之后的版本.
            time (\_out 整形数): 表示等待多久,单位是毫秒
        
        返回值:
            整形数: 0 : 失败，一般情况下是由于上个FaqPost还没有处理完毕(服务器还没返回)
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(107440, c_long, [c_long, c_char_p, c_long, c_long, c_long], self.obj, server.encode('gbk') if isinstance(server, str) else server, handle, request_type, time_out)

    def faq_send(self, server, handle, request_type, time_out):
        """
        FaqSend
        
        发送指定的图像句柄到指定的服务器,并等待返回结果(同步等待).
        
        参数:
            server (字符串): 服务器地址以及端口,格式为(ip:port),例如 "192.168.1.100:12345"\ 多个地址可以用"|"符号连接。比如"192.168.1.100:12345|192.168.1.101:12345"。
            handle (整形数): 由FaqCapture获取到的句柄
            request (\_type 整形数): 取值定义如下
            3 (): 要求获取N个坐标.此功能要求答题器必须是v15之后的版本.
            time (\_out 整形数): 表示等待多久,单位是毫秒
        
        返回值:
            字符串:
            如果此函数调用失败,那么返回值如下
            "Error:错误描述"
            如果函数调用成功,那么返回值如下
            "OK:答案"
            根据request\_type取值的不同,返回值不同
            当request\_type 为0时,答案的格式为"x,y" (不包含引号)
            当request\_type 为1时,答案的格式为"1" "2" "3" "4" "5" "6" (不包含引号)
            当request\_type 为2时,答案就是要求的答案 比如 "李白" (不包含引号)
            当request\_type 为3时,答案的格式为"x1,y1|...|xn,yn|" 比如 "20,30|78,68|33,33" (不包含引号)
        """
        if not self.obj:
            return ''
        result = self._call_function(114016, c_char_p, [c_long, c_char_p, c_long, c_long, c_long], self.obj, server.encode('gbk') if isinstance(server, str) else server, handle, request_type, time_out)
        return result.decode('gbk') if result else ''

    def fetch_word(self, x1, y1, x2, y2, color, word):
        """
        FetchWord
        
        根据指定的范围,以及指定的颜色描述，提取点阵信息，类似于大漠工具里的单独提取.
        
        参数:
            x1 (整形数): 左上角X坐标
            y1 (整形数): 左上角Y坐标
            x2 (整形数): 右下角X坐标
            y2 (整形数): 右下角Y坐标
            color (字符串): 颜色格式串.注意，RGB和HSV,以及灰度格式都支持.
            word (字符串): 待定义的文字,不能为空，且不能为关键符号"$"
        
        返回值:
            字符串: 识别到的点阵信息，可用于AddDict 如果失败，返回空
        """
        if not self.obj:
            return ''
        result = self._call_function(117840, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, word.encode('gbk') if isinstance(word, str) else word)
        return result.decode('gbk') if result else ''

    def find_color(self, x1, y1, x2, y2, color, sim, dir, x, y):
        """
        FindColor
        
        查找指定区域内的颜色,颜色格式"RRGGBB-DRDGDB",注意,和按键的颜色格式相反
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (字符串): 颜色 格式为"RRGGBB-DRDGDB",比如"123456-000000|aabbcc-202020". 也可以支持反色模式. 前面加@即可. 比如"@123456-000000|aabbcc-202020". 具体可以看下放注释. 注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 \ 1: 从左到右,从下到上 \ 2: 从右到左,从上到下 \ 3: 从右到左,从下到上 \ 4：从中心往外查找\ 5: 从上到下,从左到右 \ 6: 从上到下,从右到左\ 7: 从下到上,从左到右\ 8: 从下到上,从右到左
            intX (变参指针): 返回X坐标
            intY (变参指针): 返回Y坐标
        
        返回值:
            整形数: 0:没找到 1:找到
        """
        if not self.obj:
            return 0
        return self._call_function(106112, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_color_block(self, x1, y1, x2, y2, color, sim, count, width, height, x, y):
        """
        FindColorBlock
        
        查找指定区域内的颜色块,颜色格式"RRGGBB-DRDGDB",注意,和按键的颜色格式相反
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (字符串): 颜色 格式为"RRGGBB-DRDGDB",比如"123456-000000|aabbcc-202020".也可以支持反色模式. 前面加@即可. 比如"@123456-000000|aabbcc-202020". 具体可以看下放注释.注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            count整形 (数): 在宽度为width,高度为height的颜色块中，符合color颜色的最小数量.(注意,这个颜色数量可以在综合工具的二值化区域中看到)
            width (整形数): 颜色块的宽度
            height (整形数): 颜色块的高度
            intX (变参指针): 返回X坐标(指向颜色块的左上角)
            intY (变参指针): 返回Y坐标(指向颜色块的左上角)
        
        返回值:
            整形数: 0:没找到 1:找到
        """
        if not self.obj:
            return 0
        return self._call_function(113568, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, count, width, height, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_color_block_ex(self, x1, y1, x2, y2, color, sim, count, width, height):
        """
        FindColorBlockEx
        
        查找指定区域内的所有颜色块,颜色格式"RRGGBB-DRDGDB",注意,和按键的颜色格式相反
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (字符串): 颜色 格式为"RRGGBB-DRDGDB" 比如"aabbcc-000000|123456-202020".也可以支持反色模式. 前面加@即可. 比如"@123456-000000|aabbcc-202020". 具体可以看下放注释.注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            count整形 (数): 在宽度为width,高度为height的颜色块中，符合color颜色的最小数量.(注意,这个颜色数量可以在综合工具的二值化区域中看到)
            width (整形数): 颜色块的宽度
            height (整形数): 颜色块的高度
        
        返回值:
            字符串: 返回所有颜色块信息的坐标值,然后通过GetResultCount等接口来解析 (由于内存限制,返回的颜色数量最多为1800个左右)
            **示例:[](#chmtopic595)**
            s = dm.FindColorBlockEx(0,0,2000,2000,"123456-000000|abcdef-202020",1.0,350,100,200) count = dm.GetResultCount(s) index = 0 Do While index < count `    `dm\_ret = dm.GetResultPos(s,index,intX,intY) `    `MessageBox intX&","&intY  `    `index = index + 1  Loop
        """
        if not self.obj:
            return ''
        result = self._call_function(103840, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, c_long, c_long], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, count, width, height)
        return result.decode('gbk') if result else ''

    def find_color_e(self, x1, y1, x2, y2, color, sim, dir):
        """
        FindColorE
        
        查找指定区域内的颜色,颜色格式"RRGGBB-DRDGDB",注意,和按键的颜色格式相反 易语言用不了FindColor可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (字符串): 颜色 格式为"RRGGBB-DRDGDB",比如"123456-000000|aabbcc-202020".也可以支持反色模式. 前面加@即可. 比如"@123456-000000|aabbcc-202020". 具体可以看下放注释.注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 \ 1: 从左到右,从下到上 \ 2: 从右到左,从上到下 \ 3: 从右到左,从下到上 \ 4：从中心往外查找\ 5: 从上到下,从左到右 \ 6: 从上到下,从右到左\ 7: 从下到上,从左到右\ 8: 从下到上,从右到左
        
        返回值:
            字符串: 返回X和Y坐标 形式如"x|y", 比如"100|200"
        """
        if not self.obj:
            return ''
        result = self._call_function(120384, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_color_ex(self, x1, y1, x2, y2, color, sim, dir):
        """
        FindColorEx
        
        查找指定区域内的所有颜色,颜色格式"RRGGBB-DRDGDB",注意,和按键的颜色格式相反
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (字符串): 颜色 格式为"RRGGBB-DRDGDB" 比如"aabbcc-000000|123456-202020".也可以支持反色模式. 前面加@即可. 比如"@123456-000000|aabbcc-202020". 具体可以看下放注释.注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 \ 1: 从左到右,从下到上 \ 2: 从右到左,从上到下 \ 3: 从右到左,从下到上 \ 5: 从上到下,从左到右 \ 6: 从上到下,从右到左\ 7: 从下到上,从左到右\ 8: 从下到上,从右到左
        
        返回值:
            字符串: 返回所有颜色信息的坐标值,然后通过GetResultCount等接口来解析 (由于内存限制,返回的颜色数量最多为1800个左右)
            **示例:[](#chmtopic595)**
            s = dm.FindColorEx(0,0,2000,2000,"123456-000000|abcdef-202020",1.0,0) count = dm.GetResultCount(s) index = 0 Do While index < count `    `dm\_ret = dm.GetResultPos(s,index,intX,intY) `    `MessageBox intX&","&intY  `    `index = index + 1  Loop
        """
        if not self.obj:
            return ''
        result = self._call_function(103600, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_data(self, hwnd, addr_range, data):
        """
        FindData
        
        搜索指定的二进制数据,默认步长是1.默认开启多线程,默认搜索全部内存军类型.如果要定制搜索,请用FindDataEx
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            data (字符串): 要搜索的二进制数据 以字符串的形式描述 比如"00 01 23 45 67 86 ab ce f1"等. \ 这里也可以支持模糊查找,用??来代替单个字节. 比如"00 01 ?? ?? 67 86 ?? ce f1"等. \ 注意,这里不支持半个字节,比如3?这种不行.
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(109760, c_char_p, [c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, data.encode('gbk') if isinstance(data, str) else data)
        return result.decode('gbk') if result else ''

    def find_data_ex(self, hwnd, addr_range, data, step, multi_thread, mode):
        """
        FindDataEx
        
        搜索指定的二进制数据.
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            data (字符串): 要搜索的二进制数据 以字符串的形式描述 比如"00 01 23 45 67 86 ab ce f1"等\ 这里也可以支持模糊查找,用??来代替单个字节. 比如"00 01 ?? ?? 67 86 ?? ce f1"等.\ 注意,这里不支持半个字节,比如3?这种不行.
            step (整形数): 搜索步长.
            multi (\_thread整形数): 表示是否开启多线程查找. 0不开启，1开启.\ 开启多线程查找速度较快，但会耗费较多CPU资源. 不开启速度较慢，但节省CPU.
            mode (整形数): 1 表示开启快速扫描(略过只读内存) 0表示所有内存类型全部扫描.
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(123200, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, data.encode('gbk') if isinstance(data, str) else data, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_double(self, hwnd, addr_range, double_value_min, double_value_max):
        """
        FindDouble
        
        搜索指定的双精度浮点数,默认步长是1.如果要定制步长，请用FindDoubleEx
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            double (\_value\_min 双精度浮点数): 搜索的双精度数值最小值
            double (\_value\_max 双精度浮点数): 搜索的双精度数值最大值
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(102192, c_char_p, [c_long, c_long, c_char_p, c_double, c_double], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, double_value_min, double_value_max)
        return result.decode('gbk') if result else ''

    def find_double_ex(self, hwnd, addr_range, double_value_min, double_value_max, step, multi_thread, mode):
        """
        FindDoubleEx
        
        搜索指定的双精度浮点数.
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            double (\_value\_min 双精度浮点数): 搜索的双精度数值最小值
            double (\_value\_max 双精度浮点数): 搜索的双精度数值最大值
            step (整形数): 搜索步长.
            multi (\_thread整形数): 表示是否开启多线程查找. 0不开启，1开启.\ 开启多线程查找速度较快，但会耗费较多CPU资源. 不开启速度较慢，但节省CPU.
            mode (整形数): 1 表示开启快速扫描(略过只读内存) 0表示所有内存类型全部扫描.
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(110416, c_char_p, [c_long, c_long, c_char_p, c_double, c_double, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, double_value_min, double_value_max, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_float(self, hwnd, addr_range, float_value_min, float_value_max):
        """
        FindFloat
        
        搜索指定的单精度浮点数,默认步长是1.如果要定制步长，请用FindFloatEx
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            float (\_value\_min 单精度浮点数): 搜索的单精度数值最小值
            float (\_value\_max 单精度浮点数): 搜索的单精度数值最大值
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(103216, c_char_p, [c_long, c_long, c_char_p, c_float, c_float], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, float_value_min, float_value_max)
        return result.decode('gbk') if result else ''

    def find_float_ex(self, hwnd, addr_range, float_value_min, float_value_max, step, multi_thread, mode):
        """
        FindFloatEx
        
        搜索指定的单精度浮点数.
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            float (\_value\_min 单精度浮点数): 搜索的单精度数值最小值
            float (\_value\_max 单精度浮点数): 搜索的单精度数值最大值
            step (整形数): 搜索步长.
            multi (\_thread整形数): 表示是否开启多线程查找. 0不开启，1开启.\ 开启多线程查找速度较快，但会耗费较多CPU资源. 不开启速度较慢，但节省CPU.
            mode (整形数): 1 表示开启快速扫描(略过只读内存) 0表示所有内存类型全部扫描.
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(107040, c_char_p, [c_long, c_long, c_char_p, c_float, c_float, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, float_value_min, float_value_max, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_input_method(self, id):
        """
        FindInputMethod
        
        检测系统中是否安装了指定输入法
        
        参数:
            input (\_method 字符串): 输入法名字。 具体输入法名字对应表查看注册表中以下位置:
        
        返回值:
            整形数: 0 : 未安装
            1 : 安装了
        """
        if not self.obj:
            return 0
        return self._call_function(113872, c_long, [c_long, c_char_p], self.obj, id.encode('gbk') if isinstance(id, str) else id)

    def find_int(self, hwnd, addr_range, int_value_min, int_value_max, type):
        """
        FindInt
        
        搜索指定的整数,默认步长是1.如果要定制步长，请用FindIntEx
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            int (\_value\_min 长整形数): 搜索的整数数值最小值
            int (\_value\_max 长整形数): 搜索的整数数值最大值
            type (整形数): 搜索的整数类型,取值如下
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(106256, c_char_p, [c_long, c_long, c_char_p, c_longlong, c_longlong, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, int_value_min, int_value_max, type)
        return result.decode('gbk') if result else ''

    def find_int_ex(self, hwnd, addr_range, int_value_min, int_value_max, type, step, multi_thread, mode):
        """
        FindIntEx
        
        搜索指定的整数.
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            int (\_value\_min 长整形数): 搜索的整数数值最小值
            int (\_value\_max 长整形数): 搜索的整数数值最大值
            type (整形数): 搜索的整数类型,取值如下
            step (整形数): 搜索步长.
            multi (\_thread整形数): 表示是否开启多线程查找. 0不开启，1开启.\ 开启多线程查找速度较快，但会耗费较多CPU资源. 不开启速度较慢，但节省CPU.
            mode (整形数): 1 表示开启快速扫描(略过只读内存) 0表示所有内存类型全部扫描.
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(107216, c_char_p, [c_long, c_long, c_char_p, c_longlong, c_longlong, c_long, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, int_value_min, int_value_max, type, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_mul_color(self, x1, y1, x2, y2, color, sim):
        """
        FindMulColor
        
        查找指定区域内的所有颜色.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (字符串): 颜色 格式为"RRGGBB-DRDGDB",比如"123456-000000|aabbcc-202020".也可以支持反色模式. 前面加@即可. 比如"@123456-000000|aabbcc-202020". 具体可以看下放注释.注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            整形数: 0:没找到或者部分颜色没找到 1:所有颜色都找到
        """
        if not self.obj:
            return 0
        return self._call_function(111552, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)

    def find_multi_color(self, x1, y1, x2, y2, first_color, offset_color, sim, dir, x, y):
        """
        FindMultiColor
        
        根据指定的多点查找颜色坐标
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            first (\_color 字符串): 颜色 格式为"RRGGBB-DRDGDB|RRGGBB-DRDGDB|…………",比如"123456-000000"
            offset (\_color 字符串): 偏移颜色 可以支持任意多个点 格式和按键自带的Color插件意义相同, 只不过我的可以支持偏色和多种颜色组合
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回X坐标(坐标为first\_color所在坐标)
            intY (变参指针): 返回Y坐标(坐标为first\_color所在坐标)
        
        返回值:
            整形数: 0:没找到 1:找到
        """
        if not self.obj:
            return 0
        return self._call_function(109360, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, first_color.encode('gbk') if isinstance(first_color, str) else first_color, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_multi_color_e(self, x1, y1, x2, y2, first_color, offset_color, sim, dir):
        """
        FindMultiColorE
        
        根据指定的多点查找颜色坐标 易语言用不了FindMultiColor可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            first (\_color 字符串): 颜色 格式为"RRGGBB-DRDGDB|RRGGBB-DRDGDB|…………",比如"123456-000000"
            offset (\_color 字符串): 偏移颜色 可以支持任意多个点 格式和按键自带的Color插件意义相同, 只不过我的可以支持偏色和多种颜色组合
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回X和Y坐标 形式如"x|y", 比如"100|200"
        """
        if not self.obj:
            return ''
        result = self._call_function(101696, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, first_color.encode('gbk') if isinstance(first_color, str) else first_color, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_multi_color_ex(self, x1, y1, x2, y2, first_color, offset_color, sim, dir):
        """
        FindMultiColorEx
        
        根据指定的多点查找所有颜色坐标
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            first (\_color 字符串): 颜色 格式为"RRGGBB-DRDGDB|RRGGBB-DRDGDB|…………",比如"123456-000000"
            offset (\_color 字符串): 偏移颜色 可以支持任意多个点 格式和按键自带的Color插件意义相同, 只不过我的可以支持偏色和多种颜色组合
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回所有颜色信息的坐标值,然后通过GetResultCount等接口来解析(由于内存限制,返回的坐标数量最多为1800个左右)
            坐标是first\_color所在的坐标
        """
        if not self.obj:
            return ''
        result = self._call_function(122560, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, first_color.encode('gbk') if isinstance(first_color, str) else first_color, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_nearest_pos(self, all_pos, type, x, y):
        """
        FindNearestPos
        
        根据部分Ex接口的返回值，然后在所有坐标里找出距离指定坐标最近的那个坐标.
        
        参数:
            all (\_pos 字符串): 坐标描述串。 一般是FindStrEx,FindStrFastEx,FindStrWithFontEx, FindColorEx, FindMultiColorEx,和FindPicEx的返回值.
            type (整形数): 取值为0或者1
            x (整形数): 横坐标
            y (整形数): 纵坐标
        
        """
        if not self.obj:
            return ''
        result = self._call_function(112480, c_char_p, [c_long, c_char_p, c_long, c_long, c_long], self.obj, all_pos.encode('gbk') if isinstance(all_pos, str) else all_pos, type, x, y)
        return result.decode('gbk') if result else ''

    def find_pic(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir, x, y):
        """
        FindPic
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个找到的X Y坐标.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示). 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回图片左上角的X坐标
            intY (变参指针): 返回图片左上角的Y坐标
        
        返回值:
            整形数: 返回找到的图片的序号,从0开始索引.如果没找到返回-1
        """
        if not self.obj:
            return 0
        return self._call_function(104032, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_e(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """
        FindPicE
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个找到的X Y坐标. 易语言用不了FindPic可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        """
        if not self.obj:
            return ''
        result = self._call_function(114144, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_ex(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """
        FindPicEx
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,并且返回所有找到的图像的坐标.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回的是所有找到的坐标格式如下:"id,x,y|id,x,y..|id,x,y" (图片左上角的坐标)
            比如"0,100,20|2,30,40" 表示找到了两个,第一个,对应的图片是图像序号为0的图片,坐标是(100,20),第二个是序号为2的图片,坐标(30,40) (由于内存限制,返回的图片数量最多为1500个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(108160, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_ex_s(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """
        FindPicExS
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,并且返回所有找到的图像的坐标. 此函数同FindPicEx.只是返回值不同.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回的是所有找到的坐标格式如下:"file,x,y| file,x,y..| file,x,y" (图片左上角的坐标)
            比如"1.bmp,100,20|2.bmp,30,40" 表示找到了两个,第一个,对应的图片是1.bmp,坐标是(100,20),第二个是2.bmp,坐标(30,40) (由于内存限制,返回的图片数量最多为1500个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(100368, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_mem(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir, x, y):
        """
        FindPicMem
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个找到的X Y坐标. 这个函数要求图片是数据地址.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic568)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回图片左上角的X坐标
            intY (变参指针): 返回图片左上角的Y坐标
        
        返回值:
            整形数: 返回找到的图片的序号,从0开始索引.如果没找到返回-1
        """
        if not self.obj:
            return 0
        return self._call_function(103696, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_mem_e(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """
        FindPicMemE
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个找到的X Y坐标. 这个函数要求图片是数据地址.\ \ 易语言用不了FindPicMem可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic568)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        """
        if not self.obj:
            return ''
        result = self._call_function(109264, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_mem_ex(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """
        FindPicMemEx
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,并且返回所有找到的图像的坐标. 这个函数要求图片是数据地址.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic568)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回的是所有找到的坐标格式如下:"id,x,y|id,x,y..|id,x,y" (图片左上角的坐标)
            比如"0,100,20|2,30,40" 表示找到了两个,第一个,对应的图片是图像序号为0的图片,坐标是(100,20),第二个是序号为2的图片,坐标(30,40) (由于内存限制,返回的图片数量最多为1500个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(101440, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_s(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir, x, y):
        """
        FindPicS
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个找到的X Y坐标. 此函数同FindPic.只是返回值不同.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回图片左上角的X坐标
            intY (变参指针): 返回图片左上角的Y坐标
        
        返回值:
            字符串: 返回找到的图片的文件名. 没找到返回长度为0的字符串.
        """
        if not self.obj:
            return ''
        result = self._call_function(101952, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)
        return result.decode('gbk') if result else ''

    def find_pic_sim(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir, x, y):
        """
        FindPicSim
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,只返回第一个匹配的X Y坐标.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示). 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (整形数): 最小百分比相似率. 表示匹配的颜色占总颜色数的百分比. 其中透明色也算作匹配色. 取值为0到100. 100表示必须完全匹配. 0表示任意颜色都匹配. 只有大于sim的相似率的才会被匹配
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回图片左上角的X坐标
            intY (变参指针): 返回图片左上角的Y坐标
        
        返回值:
            整形数: 返回找到的图片的序号,从0开始索引.如果没找到返回-1
        """
        if not self.obj:
            return 0
        return self._call_function(98768, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_sim_e(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """
        FindPicSimE
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片, 只返回第一个匹配的X Y坐标. 易语言用不了FindPicSim可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (整形数): 最小百分比相似率. 表示匹配的颜色占总颜色数的百分比. 其中透明色也算作匹配色. 取值为0到100. 100表示必须完全匹配. 0表示任意颜色都匹配. 只有大于sim的相似率的才会被匹配
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        """
        if not self.obj:
            return ''
        result = self._call_function(123440, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_sim_ex(self, x1, y1, x2, y2, pic_name, delta_color, sim, dir):
        """
        FindPicSimEx
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,并且返回所有找到的图像的坐标.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片名,可以是多个图片,比如"test.bmp|test2.bmp|test3.bmp"
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (整形数): 最小百分比相似率. 表示匹配的颜色占总颜色数的百分比. 其中透明色也算作匹配色. 取值为0到100. 100表示必须完全匹配. 0表示任意颜色都匹配. 只有大于sim的相似率的才会被匹配
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回的是所有找到的坐标格式如下:"id,sim,x,y|id,sim,x,y..|id,sim,x,y" (图片左上角的坐标)
            比如"0,82,100,20|2,70,30,40" 表示找到了两个,第一个,对应的图片是图像序号为0的图片,坐标是(100,20),当前匹配百分比是82,第二个是序号为2的图片,坐标(30,40),当前匹配百分比是70 (由于内存限制,返回的图片数量最多为1500个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(113728, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_sim_mem(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir, x, y):
        """
        FindPicSimMem
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片, 只返回第一个匹配的X Y坐标. 这个函数要求图片是数据地址.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic568)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (整形数): 最小百分比相似率. 表示匹配的颜色占总颜色数的百分比. 其中透明色也算作匹配色. 取值为0到100. 100表示必须完全匹配. 0表示任意颜色都匹配. 只有大于sim的相似率的才会被匹配
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回图片左上角的X坐标
            intY (变参指针): 返回图片左上角的Y坐标
        
        返回值:
            整形数: 返回找到的图片的序号,从0开始索引.如果没找到返回-1
        """
        if not self.obj:
            return 0
        return self._call_function(121744, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_pic_sim_mem_e(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """
        FindPicSimMemE
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片, 只返回第一个匹配的X Y坐标. 这个函数要求图片是数据地址.\ \ 易语言用不了FindPicSimMem可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic568)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (整形数): 最小百分比相似率. 表示匹配的颜色占总颜色数的百分比. 其中透明色也算作匹配色. 取值为0到100. 100表示必须完全匹配. 0表示任意颜色都匹配. 只有大于sim的相似率的才会被匹配
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        """
        if not self.obj:
            return ''
        result = self._call_function(113296, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_pic_sim_mem_ex(self, x1, y1, x2, y2, pic_info, delta_color, sim, dir):
        """
        FindPicSimMemEx
        
        查找指定区域内的图片,位图必须是24位色格式,支持透明色,当图像上下左右4个顶点的颜色一样时,则这个颜色将作为透明色处理. 这个函数可以查找多个图片,并且返回所有找到的图像的坐标. 这个函数要求图片是数据地址.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_info 字符串): 图片数据地址集合. 格式为"地址1,长度1|地址2,长度2.....|地址n,长度n". 可以用[AppendPicAddr](#chmtopic568)来组合. \ 地址表示24位位图资源在内存中的首地址，用十进制的数值表示\ 长度表示位图资源在内存中的长度，用十进制数值表示.
            delta (\_color 字符串): 颜色色偏 比如"203040" 表示RGB的色偏分别是20 30 40 (这里是16进制表示) . 如果这里的色偏是2位，表示使用灰度找图. 比如"20"
            sim (整形数): 最小百分比相似率. 表示匹配的颜色占总颜色数的百分比. 其中透明色也算作匹配色. 取值为0到100. 100表示必须完全匹配. 0表示任意颜色都匹配. 只有大于sim的相似率的才会被匹配
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回的是所有找到的坐标格式如下:"id,sim,x,y|id,sim,x,y..|id,sim,x,y" (图片左上角的坐标)
            比如"0,82,100,20|2,70,30,40" 表示找到了两个,第一个,对应的图片是图像序号为0的图片,坐标是(100,20),当前匹配百分比是82,第二个是序号为2的图片,坐标(30,40),当前匹配百分比是70 (由于内存限制,返回的图片数量最多为1500个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(124912, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, pic_info.encode('gbk') if isinstance(pic_info, str) else pic_info, delta_color.encode('gbk') if isinstance(delta_color, str) else delta_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_shape(self, x1, y1, x2, y2, offset_color, sim, dir, x, y):
        """
        FindShape
        
        查找指定的形状. 形状的描述同按键的抓抓. 具体可以参考按键的抓抓. \ 和按键的语法不同，需要用大漠综合工具的颜色转换.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            offset (\_color 字符串): 坐标偏移描述 可以支持任意多个点 格式和按键自带的Color插件意义相同
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
            intX (变参指针): 返回X坐标(坐标为形状(0,0)所在坐标)
            intY (变参指针): 返回Y坐标(坐标为形状(0,0)所在坐标)
        
        返回值:
            整形数: 0:没找到 1:找到
        """
        if not self.obj:
            return 0
        return self._call_function(123856, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_shape_e(self, x1, y1, x2, y2, offset_color, sim, dir):
        """
        FindShapeE
        
        查找指定的形状. 形状的描述同按键的抓抓. 具体可以参考按键的抓抓. \ 和按键的语法不同，需要用大漠综合工具的颜色转换.  易语言用不了FindShape可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            offset (\_color 字符串): 坐标偏移描述 可以支持任意多个点 格式和按键自带的Color插件意义相同
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回X和Y坐标 形式如"x|y", 比如"100|200"
        """
        if not self.obj:
            return ''
        result = self._call_function(120592, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_shape_ex(self, x1, y1, x2, y2, offset_color, sim, dir):
        """
        FindShapeEx
        
        查找所有指定的形状的坐标. 形状的描述同按键的抓抓. 具体可以参考按键的抓抓. \ 和按键的语法不同，需要用大漠综合工具的颜色转换.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            offset (\_color 字符串): 坐标偏移描述 可以支持任意多个点 格式和按键自带的Color插件意义相同
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            dir (整形数): 查找方向 0: 从左到右,从上到下 1: 从左到右,从下到上 2: 从右到左,从上到下 3: 从右到左, 从下到上
        
        返回值:
            字符串: 返回所有形状的坐标值,然后通过GetResultCount等接口来解析(由于内存限制,返回的坐标数量最多为1800个左右)
        """
        if not self.obj:
            return ''
        result = self._call_function(99792, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double, c_long], self.obj, x1, y1, x2, y2, offset_color.encode('gbk') if isinstance(offset_color, str) else offset_color, sim, dir)
        return result.decode('gbk') if result else ''

    def find_str(self, x1, y1, x2, y2, text, color, sim, x, y):
        """
        FindStr
        
        在屏幕范围(x1,y1,x2,y2)内,查找string(可以是任意个字符串的组合),并返回符合color\_format的坐标位置,相似度sim同Ocr接口描述. (多色,差色查找类似于Ocr接口,不再重述)
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串,可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例 .注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            intX (变参指针): 返回X坐标 没找到返回-1
            intY (变参指针): 返回Y坐标 没找到返回-1
        
        返回值:
            整形数: 返回字符串的索引 没找到返回-1, 比如"长安|洛阳",若找到长安，则返回0
        """
        if not self.obj:
            return 0
        return self._call_function(110320, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_str_e(self, x1, y1, x2, y2, text, color, sim):
        """
        FindStrE
        
        在屏幕范围(x1,y1,x2,y2)内,查找string(可以是任意个字符串的组合),并返回符合color\_format的坐标位置,相似度sim同Ocr接口描述. (多色,差色查找类似于Ocr接口,不再重述) 易语言用不了FindStr可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回字符串序号以及X和Y坐标,形式如"id|x|y", 比如"0|100|200",没找到时，id和X以及Y均为-1，"-1|-1|-1"
        """
        if not self.obj:
            return ''
        result = self._call_function(122400, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_ex(self, x1, y1, x2, y2, text, color, sim):
        """
        FindStrEx
        
        在屏幕范围(x1,y1,x2,y2)内,查找string(可以是任意字符串的组合),并返回符合color\_format的所有坐标位置,相似度sim同Ocr接口描述. (多色,差色查找类似于Ocr接口,不再重述)
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回所有找到的坐标集合,格式如下: "id,x0,y0|id,x1,y1|......|id,xn,yn" 比如"0,100,20|2,30,40" 表示找到了两个,第一个,对应的是序号为0的字符串,坐标是(100,20),第二个是序号为2的字符串,坐标(30,40)
            \
        """
        if not self.obj:
            return ''
        result = self._call_function(106640, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_ex_s(self, x1, y1, x2, y2, text, color, sim):
        """
        FindStrExS
        
        在屏幕范围(x1,y1,x2,y2)内,查找string(可以是任意字符串的组合),并返回符合color\_format的所有坐标位置,相似度sim同Ocr接口描述. (多色,差色查找类似于Ocr接口,不再重述). 此函数同FindStrEx,只是返回值不同.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回所有找到的坐标集合,格式如下: "str,x0,y0| str,x1,y1|......| str,xn,yn" 比如"长安,100,20|大雁塔,30,40" 表示找到了两个,第一个是长安 ,坐标是(100,20),第二个是大雁塔,坐标(30,40)
            \
        """
        if not self.obj:
            return ''
        result = self._call_function(100528, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast(self, x1, y1, x2, y2, text, color, sim, x, y):
        """
        FindStrFast
        
        同FindStr。
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串,可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            intX (变参指针): 返回X坐标 没找到返回-1
            intY (变参指针): 返回Y坐标 没找到返回-1
        
        返回值:
            整形数: 返回字符串的索引 没找到返回-1, 比如"长安|洛阳",若找到长安，则返回0
        """
        if not self.obj:
            return 0
        return self._call_function(115584, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_str_fast_e(self, x1, y1, x2, y2, text, color, sim):
        """
        FindStrFastE
        
        同FindStrE 易语言用不了FindStrFast可以用此接口来代替
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回字符串序号以及X和Y坐标,形式如"id|x|y", 比如"0|100|200",没找到时，id和X以及Y均为-1，"-1|-1|-1"
        """
        if not self.obj:
            return ''
        result = self._call_function(120288, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast_ex(self, x1, y1, x2, y2, text, color, sim):
        """
        FindStrFastEx
        
        同FindStrEx
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回所有找到的坐标集合,格式如下: "id,x0,y0|id,x1,y1|......|id,xn,yn" 比如"0,100,20|2,30,40" 表示找到了两个,第一个,对应的是序号为0的字符串,坐标是(100,20),第二个是序号为2的字符串,坐标(30,40)
            \
        """
        if not self.obj:
            return ''
        result = self._call_function(122000, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast_ex_s(self, x1, y1, x2, y2, text, color, sim):
        """
        FindStrFastExS
        
        同FindStrExS.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例 .注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回所有找到的坐标集合,格式如下: "str,x0,y0| str,x1,y1|......| str,xn,yn" 比如"长安,100,20|大雁塔,30,40" 表示找到了两个,第一个是长安 ,坐标是(100,20),第二个是大雁塔,坐标(30,40)
            \
        """
        if not self.obj:
            return ''
        result = self._call_function(124176, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def find_str_fast_s(self, x1, y1, x2, y2, text, color, sim, x, y):
        """
        FindStrFastS
        
        同FindStrS.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串,可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例 .注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            intX (变参指针): 返回X坐标 没找到返回-1
            intY (变参指针): 返回Y坐标 没找到返回-1
        
        返回值:
            字符串: 返回找到的字符串. 没找到的话返回长度为0的字符串.
        """
        if not self.obj:
            return ''
        result = self._call_function(98672, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)
        return result.decode('gbk') if result else ''

    def find_str_s(self, x1, y1, x2, y2, text, color, sim, x, y):
        """
        FindStrS
        
        在屏幕范围(x1,y1,x2,y2)内,查找string(可以是任意个字符串的组合),并返回符合color\_format的坐标位置,相似度sim同Ocr接口描述. (多色,差色查找类似于Ocr接口,不再重述).此函数同FindStr,只是返回值不同.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串,可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例 .注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            intX (变参指针): 返回X坐标 没找到返回-1
            intY (变参指针): 返回Y坐标 没找到返回-1
        
        返回值:
            字符串: 返回找到的字符串. 没找到的话返回长度为0的字符串.
        """
        if not self.obj:
            return ''
        result = self._call_function(116832, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)
        return result.decode('gbk') if result else ''

    def find_str_with_font(self, x1, y1, x2, y2, text, color, sim, font_name, font_size, flag, x, y):
        """
        FindStrWithFont
        
        同FindStr，但是不使用SetDict设置的字库，而利用系统自带的字库，速度比FindStr稍慢.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串,可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例 .注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            font (\_name 字符串): 系统字体名,比如"宋体"
            font (\_size 整形数): 系统字体尺寸，这个尺寸一定要以大漠综合工具获取的为准.如果获取尺寸看视频教程.
            flag (整形数): 字体类别 取值可以是以下值的组合,比如1+2+4+8,2+4. 0表示正常字体.\ 1 : 粗体\ 2 : 斜体\ 4 : 下划线\ 8 : 删除线
            intX (变参指针): 返回X坐标 没找到返回-1
            intY (变参指针): 返回Y坐标 没找到返回-1
        
        返回值:
            整形数: 返回字符串的索引 没找到返回-1, 比如"长安|洛阳",若找到长安，则返回0
        """
        if not self.obj:
            return 0
        return self._call_function(119856, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_char_p, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def find_str_with_font_e(self, x1, y1, x2, y2, text, color, sim, font_name, font_size, flag):
        """
        FindStrWithFontE
        
        同FindStrE，但是不使用SetDict设置的字库，而利用系统自带的字库，速度比FindStrE稍慢
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            font (\_name 字符串): 系统字体名,比如"宋体"
            font (\_size 整形数): 系统字体尺寸，这个尺寸一定要以大漠综合工具获取的为准.如果获取尺寸看视频教程.
            flag (整形数): 字体类别 取值可以是以下值的组合,比如1+2+4+8,2+4. 0表示正常字体.\ 1 : 粗体\ 2 : 斜体\ 4 : 下划线\ 8 : 删除线
        
        返回值:
            字符串: 返回字符串序号以及X和Y坐标,形式如"id|x|y", 比如"0|100|200",没找到时，id和X以及Y均为-1，"-1|-1|-1"
        """
        if not self.obj:
            return ''
        result = self._call_function(112544, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag)
        return result.decode('gbk') if result else ''

    def find_str_with_font_ex(self, x1, y1, x2, y2, text, color, sim, font_name, font_size, flag):
        """
        FindStrWithFontEx
        
        同FindStrEx，但是不使用SetDict设置的字库，而利用系统自带的字库，速度比FindStrEx稍慢
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            string (字符串): 待查找的字符串, 可以是字符串组合，比如"长安|洛阳|大雁塔",中间用"|"来分割字符串
            color (\_format 字符串): 颜色格式串, 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
            font (\_name 字符串): 系统字体名,比如"宋体"
            font (\_size 整形数): 系统字体尺寸，这个尺寸一定要以大漠综合工具获取的为准.如果获取尺寸看视频教程.
            flag (整形数): 字体类别 取值可以是以下值的组合,比如1+2+4+8,2+4. 0表示正常字体.\ 1 : 粗体\ 2 : 斜体\ 4 : 下划线\ 8 : 删除线
        
        返回值:
            字符串: 返回所有找到的坐标集合,格式如下: "id,x0,y0|id,x1,y1|......|id,xn,yn" 比如"0,100,20|2,30,40" 表示找到了两个,第一个,对应的是序号为0的字符串,坐标是(100,20),第二个是序号为2的字符串,坐标(30,40)
            \
        """
        if not self.obj:
            return ''
        result = self._call_function(118848, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double, c_char_p, c_long, c_long], self.obj, x1, y1, x2, y2, text.encode('gbk') if isinstance(text, str) else str, color.encode('gbk') if isinstance(color, str) else color, sim, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag)
        return result.decode('gbk') if result else ''

    def find_string(self, hwnd, addr_range, string_value, type):
        """
        FindString
        
        搜索指定的字符串,默认步长是1.如果要定制步长，请用FindStringEx
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            string (\_value 字符串): 搜索的字符串
            type (整形数): 搜索的字符串类型,取值如下
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(110752, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, string_value.encode('gbk') if isinstance(string_value, str) else string_value, type)
        return result.decode('gbk') if result else ''

    def find_string_ex(self, hwnd, addr_range, string_value, type, step, multi_thread, mode):
        """
        FindStringEx
        
        搜索指定的字符串.
        
        参数:
            hwnd (**整形数**): 指定搜索的窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (\_range 字符串): 指定搜索的地址集合，字符串类型，这个地方可以是上次FindXXX的返回地址集合,可以进行二次搜索.(类似CE的再次扫描)
            string (\_value 字符串): 搜索的字符串
            type (整形数): 搜索的字符串类型,取值如下
            step (整形数): 搜索步长.
            multi (\_thread整形数): 表示是否开启多线程查找. 0不开启，1开启.\ 开启多线程查找速度较快，但会耗费较多CPU资源. 不开启速度较慢，但节省CPU.
            mode (整形数): 1 表示开启快速扫描(略过只读内存) 0表示所有内存类型全部扫描.
        
        返回值:
            字符串: 返回搜索到的地址集合，地址格式如下:
            "addr1|addr2|addr3…|addrn"
            比如"400050|423435|453430"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(124384, c_char_p, [c_long, c_long, c_char_p, c_char_p, c_long, c_long, c_long, c_long], self.obj, hwnd, addr_range.encode('gbk') if isinstance(addr_range, str) else addr_range, string_value.encode('gbk') if isinstance(string_value, str) else string_value, type, step, multi_thread, mode)
        return result.decode('gbk') if result else ''

    def find_window(self, class_name, title_name):
        """
        FindWindow
        
        查找符合类名或者标题名的顶层可见窗口
        
        参数:
            class (字符串): 窗口类名，如果为空，则匹配所有. 这里的匹配是模糊匹配.
            title (字符串): 窗口标题,如果为空，则匹配所有.这里的匹配是模糊匹配.
        
        返回值:
            整形数: 整形数表示的窗口句柄，没找到返回0
        """
        if not self.obj:
            return 0
        return self._call_function(104288, c_long, [c_long, c_char_p, c_char_p], self.obj, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_by_process(self, process_name, class_name, title_name):
        """
        FindWindowByProcess
        
        根据指定的进程名字，来查找可见窗口.
        
        参数:
            process (\_name 字符串): 进程名. 比如(notepad.exe).这里是精确匹配,但不区分大小写.**\ 
            class (字符串): 窗口类名，如果为空，则匹配所有. 这里的匹配是模糊匹配.
            title (字符串): 窗口标题,如果为空，则匹配所有.这里的匹配是模糊匹配.
        
        """
        if not self.obj:
            return 0
        return self._call_function(122336, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, process_name.encode('gbk') if isinstance(process_name, str) else process_name, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_by_process_id(self, process_id, class_name, title_name):
        """
        FindWindowByProcessId
        
        根据指定的进程Id，来查找可见窗口.
        
        参数:
            process (\_id 整形数): 进程id.** \ 
            class (字符串): 窗口类名，如果为空，则匹配所有. 这里的匹配是模糊匹配.
            title (字符串): 窗口标题,如果为空，则匹配所有.这里的匹配是模糊匹配.
        
        """
        if not self.obj:
            return 0
        return self._call_function(104176, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, process_id, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_ex(self, parent, class_name, title_name):
        """
        FindWindowEx
        
        查找符合类名或者标题名的顶层可见窗口,如果指定了parent,则在parent的第一层子窗口中查找.
        
        参数:
            parent (整形数): 父窗口句柄，如果为空，则匹配所有顶层窗口
            class (字符串): 窗口类名，如果为空，则匹配所有. 这里的匹配是模糊匹配.
            title (字符串): 窗口标题,如果为空，则匹配所有. 这里的匹配是模糊匹配.
        
        返回值:
            整形数: 整形数表示的窗口句柄，没找到返回0
        """
        if not self.obj:
            return 0
        return self._call_function(115408, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, parent, class_name.encode('gbk') if isinstance(class_name, str) else class_name, title_name.encode('gbk') if isinstance(title_name, str) else title_name)

    def find_window_super(self, spec1, flag1, type1, spec2, flag2, type2):
        """
        FindWindowSuper
        
        根据两组设定条件来查找指定窗口.
        
        参数:
            spec1 (字符串): 查找串1. (内容取决于flag1的值)
            flag1整形数 (: 取值如下): 
            type1 (整形数): 取值如下
            spec2 (字符串): 查找串2. (内容取决于flag2的值)
            flag2 (整形数): 取值如下:
            type2 (整形数): 取值如下
        
        """
        if not self.obj:
            return 0
        return self._call_function(108432, c_long, [c_long, c_char_p, c_long, c_long, c_char_p, c_long, c_long], self.obj, spec1.encode('gbk') if isinstance(spec1, str) else spec1, flag1, type1, spec2.encode('gbk') if isinstance(spec2, str) else spec2, flag2, type2)

    def float_to_data(self, float_value):
        """
        FloatToData
        
        把单精度浮点数转换成二进制形式.
        
        参数:
            value (**单精度浮点数**): 需要转化的单精度浮点数
        
        返回值:
            字符串: 字符串形式表达的二进制数据. 可以用于WriteData FindData FindDataEx等接口.
        """
        if not self.obj:
            return ''
        result = self._call_function(100464, c_char_p, [c_long, c_float], self.obj, float_value)
        return result.decode('gbk') if result else ''

    def foobar_clear_text(self, hwnd):
        """
        FoobarClearText
        
        清除指定的Foobar滚动文本区
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
        
        返回值:
            整形数 : 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(113072, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_close(self, hwnd):
        """
        FoobarClose
        
        关闭一个Foobar,注意,必须调用此函数来关闭窗口,用SetWindowState也可以关闭,但会造成内存泄漏.
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口句柄
        
        """
        if not self.obj:
            return 0
        return self._call_function(102480, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_draw_line(self, hwnd, x1, y1, x2, y2, color, style, width):
        """
        FoobarDrawLine
        
        在指定的Foobar窗口内部画线条.
        
        参数:
            hwnd (整形数): 指定的Foobar窗口,注意,此句柄必须是通过CreateFoobarxxxx系列函数创建出来的\ 
            x1 (整形数): 左上角X坐标(相对于hwnd客户区坐标)
            y1 (整形数): 左上角Y坐标(相对于hwnd客户区坐标)
            x2 (整形数): 右下角X坐标(相对于hwnd客户区坐标)
            y2 (整形数): 右下角Y坐标(相对于hwnd客户区坐标)
            color字符 (串): 填充的颜色值
            style (整形数): 画笔类型. 0为实线. 1为虚线
            width (整形数): 线条宽度.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(116384, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, style, width)

    def foobar_draw_pic(self, hwnd, x, y, pic, trans_color):
        """
        FoobarDrawPic
        
        在指定的Foobar窗口绘制图像
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口,注意,此句柄必须是通过CreateFoobarxxxx系列函数创建出来的\ 
            x整形 (数): 左上角X坐标(相对于hwnd客户区坐标)
            y整形 (数): 左上角Y坐标(相对于hwnd客户区坐标)
            pic (\_name字符串): 图像文件名 [如果第一个字符是@,则采用指针方式. @后面是指针地址和大小. 必须是十进制](mailto:如果第一个字符是@,则采用指针方式.%20@后面是指针地址和大小.%20必须是十进制). 具体看下面的例子
            trans (\_color字符串): 图像透明色
        
        返回值:
            整形数 : 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(114288, c_long, [c_long, c_long, c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, x, y, pic.encode('gbk') if isinstance(pic, str) else pic, trans_color.encode('gbk') if isinstance(trans_color, str) else trans_color)

    def foobar_draw_text(self, hwnd, x, y, w, h, text, color, align):
        """
        FoobarDrawText
        
        在指定的Foobar窗口绘制文字
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口,注意,此句柄必须是通过CreateFoobarxxxx系列函数创建出来的\ 
            x整形 (数): 左上角X坐标(相对于hwnd客户区坐标)
            y整形 (数): 左上角Y坐标(相对于hwnd客户区坐标)
            w整形 (数): 矩形区域的宽度
            h整形 (数): 矩形区域的高度
            text字符 (串): 字符串
            color字符 (串): 文字颜色值
            align (整形数): 取值定义如下
            1 (): 左对齐
            2 (): 中间对齐
            4 (): 右对齐
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(119712, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_long], self.obj, hwnd, x, y, w, h, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color, align)

    def foobar_fill_rect(self, hwnd, x1, y1, x2, y2, color):
        """
        FoobarFillRect
        
        在指定的Foobar窗口内部填充矩形
        
        参数:
            hwnd (整形数): 指定的Foobar窗口,注意,此句柄必须是通过CreateFoobarxxxx系列函数创建出来的\ 
            x1 (整形数): 左上角X坐标(相对于hwnd客户区坐标)
            y1 (整形数): 左上角Y坐标(相对于hwnd客户区坐标)
            x2 (整形数): 右下角X坐标(相对于hwnd客户区坐标)
            y2 (整形数): 右下角Y坐标(相对于hwnd客户区坐标)
            color字符 (串): 填充的颜色值
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(103136, c_long, [c_long, c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, hwnd, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color)

    def foobar_lock(self, hwnd):
        """
        FoobarLock
        
        锁定指定的Foobar窗口,不能通过鼠标来移动
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(109824, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_print_text(self, hwnd, text, color):
        """
        FoobarPrintText
        
        向指定的Foobar窗口区域内输出滚动文字
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
            text字符 (串): 文本内容
            color字符 (串): 文本颜色
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(108720, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, text.encode('gbk') if isinstance(text, str) else text, color.encode('gbk') if isinstance(color, str) else color)

    def foobar_set_font(self, hwnd, font_name, size, flag):
        """
        FoobarSetFont
        
        设置指定Foobar窗口的字体
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
            font (\_name字符串): 系统字体名,注意,必须保证系统中有此字体
            size整形 (数): 字体大小
            flag整形 (数): 取值定义如下
            0 (): 正常字体
            1 (): 粗体
            2 (): 斜体
            4 (): 下划线
            文字可以是以上的组合 (比如粗斜体就是1+2,斜体带下划线就是): 2+4等.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(111632, c_long, [c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, font_name.encode('gbk') if isinstance(font_name, str) else font_name, size, flag)

    def foobar_set_save(self, hwnd, file, en, header):
        """
        FoobarSetSave
        
        设置保存指定的Foobar滚动文本区信息到文件.
        
        参数:
            hwnd (整形数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
            file (字符串): 保存的文件名
            enable (整形数): 取值如下\ 0 : 关闭向文件输出 (默认是0)\ 1 : 开启向文件输出
            header (字符串): 输出的附加头信息. (比如行数 日期 时间信息) 格式是如下格式串的顺序组合.如果为空串，表示无附加头.\ "%L0nd%" 表示附加头信息带有行号，并且是按照十进制输出. n表示按多少个十进制数字补0对齐. 比如"%L04d%",输出的行号为0001 0002 0003等. "%L03d",输出的行号为001 002 003..等.\ "%L0nx%"表示附加头信息带有行号，并且是按照16进制小写输出. n表示按多少个16进制数字补0对齐. 比如"%L04x%",输出的行号为0009 000a 000b等. "%L03x",输出的行号为009 00a 00b..等.\ "%L0nX%"表示附加头信息带有行号，并且是按照16进制大写输出. n表示按多少个16进制数字补0对齐. 比如"%L04X%",输出的行号为0009 000A 000B等. "%L03X",输出的行号为009 00A 00B..等.\ "%yyyy%"表示年. 比如2012\ "%MM%"表示月. 比如12\ "%dd%"表示日. 比如28\ "%hh%"表示小时. 比如13\ "%mm%"表示分钟. 比如59\ "%ss%"表示秒. 比如48.
        
        返回值:
            整形数 : 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(124736, c_long, [c_long, c_long, c_char_p, c_long, c_char_p], self.obj, hwnd, file.encode('gbk') if isinstance(file, str) else file, en, header.encode('gbk') if isinstance(header, str) else header)

    def foobar_set_trans(self, hwnd, trans, color, sim):
        """
        FoobarSetTrans
        
        设置指定Foobar窗口的是否透明
        
        参数:
            hwnd (整形数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
            is (\_trans 整形数): 是否透明. 0为不透明(此时,color和sim无效)，1为透明.
            color (字符串): 透明色(RRGGBB)
            sim (双精度浮点数): 透明色的相似值 0.1-1.0
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(117248, c_long, [c_long, c_long, c_long, c_char_p, c_double], self.obj, hwnd, trans, color.encode('gbk') if isinstance(color, str) else color, sim)

    def foobar_start_gif(self, hwnd, x, y, pic_name, repeat_limit, delay):
        """
        FoobarStartGif
        
        在指定的Foobar窗口绘制gif动画.
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口,注意,此句柄必须是通过CreateFoobarxxxx系列函数创建出来的\ 
            x整形 (数): 左上角X坐标(相对于hwnd客户区坐标)
            y整形 (数): 左上角Y坐标(相对于hwnd客户区坐标)
            pic (\_name字符串): 图像文件名 [如果第一个字符是@,则采用指针方式. @后面是指针地址和大小. 必须是十进制](mailto:如果第一个字符是@,则采用指针方式.%20@后面是指针地址和大小.%20必须是十进制). 具体看下面的例子
            repeat (\_limit 整形数): 表示重复GIF动画的次数，如果是0表示一直循环显示.大于0，则表示循环指定的次数以后就停止显示.
            delay (整形数): 表示每帧GIF动画之间的时间间隔.如果是0，表示使用GIF内置的时间，如果大于0，表示使用自定义的时间间隔.
        
        返回值:
            整形数 : 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(117664, c_long, [c_long, c_long, c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, x, y, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, repeat_limit, delay)

    def foobar_stop_gif(self, hwnd, x, y, pic_name):
        """
        FoobarStopGif
        
        停止在指定foobar里显示的gif动画.
        
        参数:
            hwnd整形 (数): 指定的Foobar窗口,注意,此句柄必须是通过CreateFoobarxxxx系列函数创建出来的\ 
            x整形 (数): 左上角X坐标(相对于hwnd客户区坐标)
            y整形 (数): 左上角Y坐标(相对于hwnd客户区坐标)
            pic (\_name字符串): 图像文件名
        
        返回值:
            整形数 : 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(108096, c_long, [c_long, c_long, c_long, c_long, c_char_p], self.obj, hwnd, x, y, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)

    def foobar_text_line_gap(self, hwnd, gap):
        """
        FoobarTextLineGap
        
        设置滚动文本区的文字行间距,默认是3
        
        参数:
            hwnd (整形数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
            line (\_gap 整形数): 文本行间距
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(124848, c_long, [c_long, c_long, c_long], self.obj, hwnd, gap)

    def foobar_text_print_dir(self, hwnd, dir):
        """
        FoobarTextPrintDir
        
        设置滚动文本区的文字输出方向,默认是0
        
        参数:
            hwnd (整形数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
            dir (整形数): 0 表示向下输出
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(103072, c_long, [c_long, c_long, c_long], self.obj, hwnd, dir)

    def foobar_text_rect(self, hwnd, x, y, w, h):
        """
        FoobarTextRect
        
        设置指定Foobar窗口的滚动文本框范围,默认的文本框范围是窗口区域
        
        参数:
            hwnd (整形数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
            x (整形数): x坐标
            y (整形数): y坐标
            w (整形数): 宽度
            h (整形数): 高度
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(108784, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, hwnd, x, y, w, h)

    def foobar_unlock(self, hwnd):
        """
        FoobarUnlock
        
        解锁指定的Foobar窗口,可以通过鼠标来移动
        
        参数:
            hwnd (整形数): 指定的Foobar窗口句柄,此句柄必须是通过CreateFoobarxxx创建而来
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(123952, c_long, [c_long, c_long], self.obj, hwnd)

    def foobar_update(self, hwnd):
        """
        FoobarUpdate
        
        刷新指定的Foobar窗口
        
        参数:
            hwnd (整形数): 指定的Foobar窗口,注意,此句柄必须是通过CreateFoobarxxxx系列函数创建出来的
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(119280, c_long, [c_long, c_long], self.obj, hwnd)

    def force_un_bind_window(self, hwnd):
        """
        ForceUnBindWindow
        
        强制解除绑定窗口,并释放系统资源.
        
        参数:
            hwnd (整形数): 需要强制解除绑定的窗口句柄.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(120144, c_long, [c_long, c_long], self.obj, hwnd)

    def free_pic(self, pic_name):
        """
        FreePic
        
        释放指定的图片,此函数不必要调用,除非你想节省内存.
        
        参数:
            pic (\_name 字符串): 文件名 比如"1.bmp|2.bmp|3.bmp" 等,可以使用通配符,比如
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(103408, c_long, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)

    def free_process_memory(self, hwnd):
        """
        FreeProcessMemory
        
        释放指定进程的不常用内存.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
        
        返回值:
            整形数:  0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(111120, c_long, [c_long, c_long], self.obj, hwnd)

    def get_ave_hsv(self, x1, y1, x2, y2):
        """
        GetAveHSV
        
        获取范围(x1,y1,x2,y2)颜色的均值,返回格式"H.S.V"
        
        参数:
            x1 (整形数): 左上角X
            y1 (整形数): 左上角Y
            x2 (整形数): 右下角X
            y2 (整形数): 右下角Y
        
        返回值:
            字符串: 颜色字符串
        """
        if not self.obj:
            return ''
        result = self._call_function(100176, c_char_p, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)
        return result.decode('gbk') if result else ''

    def get_ave_rgb(self, x1, y1, x2, y2):
        """
        GetAveRGB
        
        获取范围(x1,y1,x2,y2)颜色的均值,返回格式"RRGGBB"
        
        参数:
            x1 (整形数): 左上角X
            y1 (整形数): 左上角Y
            x2 (整形数): 右下角X
            y2 (整形数): 右下角Y
        
        返回值:
            字符串: 颜色字符串
        """
        if not self.obj:
            return ''
        result = self._call_function(118192, c_char_p, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)
        return result.decode('gbk') if result else ''

    def get_base_path(self):
        """
        GetBasePath
        
        获取注册在系统中的dm.dll的路径.
        
        返回值:
            字符串: 返回dm.dll所在路径
        """
        if not self.obj:
            return ''
        result = self._call_function(107312, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_bind_window(self):
        """
        GetBindWindow
        
        获取当前对象已经绑定的窗口句柄. 无绑定返回0
        
        返回值:
            整形数: 窗口句柄
        """
        if not self.obj:
            return 0
        return self._call_function(109712, c_long, [c_long], self.obj)

    def get_client_rect(self, hwnd, x1, y1, x2, y2):
        """
        GetClientRect
        
        获取窗口客户区域在屏幕上的位置
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            x1 (变参指针): 返回窗口客户区左上角X坐标
            y1 (变参指针): 返回窗口客户区左上角Y坐标
            x2 (变参指针): 返回窗口客户区右下角X坐标
            y2 (变参指针): 返回窗口客户区右下角Y坐标
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(105808, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x1) if isinstance(x1, c_long) else x1, byref(y1) if isinstance(y1, c_long) else y1, byref(x2) if isinstance(x2, c_long) else x2, byref(y2) if isinstance(y2, c_long) else y2)

    def get_client_size(self, hwnd, width, height):
        """
        GetClientSize
        
        获取窗口客户区域的宽度和高度
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            width (变参指针): 宽度
            height (变参指针): 高度
        
        """
        if not self.obj:
            return 0
        return self._call_function(103344, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(width) if isinstance(width, c_long) else width, byref(height) if isinstance(height, c_long) else height)

    def get_clipboard(self):
        """
        GetClipboard
        
        获取剪贴板的内容
        
        返回值:
            字符串: 以字符串表示的剪贴板内容
        """
        if not self.obj:
            return ''
        result = self._call_function(116624, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_color(self, x, y):
        """
        GetColor
        
        获取(x,y)的颜色,颜色返回格式"RRGGBB",注意,和按键的颜色格式相反
        
        参数:
            x (整形数): X坐标
            y (整形数): Y坐标
        
        返回值:
            字符串: 颜色字符串(注意这里都是小写字符，和工具相匹配)
        """
        if not self.obj:
            return ''
        result = self._call_function(117424, c_char_p, [c_long, c_long, c_long], self.obj, x, y)
        return result.decode('gbk') if result else ''

    def get_color_bgr(self, x, y):
        """
        GetColorBGR
        
        获取(x,y)的颜色,颜色返回格式"BBGGRR"
        
        参数:
            x (整形数): X坐标
            y (整形数): Y坐标
        
        返回值:
            字符串: 颜色字符串(注意这里都是小写字符，和工具相匹配)
        """
        if not self.obj:
            return ''
        result = self._call_function(100000, c_char_p, [c_long, c_long, c_long], self.obj, x, y)
        return result.decode('gbk') if result else ''

    def get_color_hsv(self, x, y):
        """
        GetColorHSV
        
        获取(x,y)的HSV颜色,颜色返回格式"H.S.V"
        
        参数:
            x (整形数): X坐标
            y (整形数): Y坐标
        
        返回值:
            字符串: 颜色字符串
        """
        if not self.obj:
            return ''
        result = self._call_function(116192, c_char_p, [c_long, c_long, c_long], self.obj, x, y)
        return result.decode('gbk') if result else ''

    def get_color_num(self, x1, y1, x2, y2, color, sim):
        """
        GetColorNum
        
        获取指定区域的颜色数量,颜色格式"RRGGBB-DRDGDB",注意,和按键的颜色格式相反
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (字符串): 颜色 格式为"RRGGBB-DRDGDB",比如"123456-000000|aabbcc-202020".也可以支持反色模式. 前面加@即可. 比如"@123456-000000|aabbcc-202020". 具体可以看下放注释.注意，这里只支持RGB颜色.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            整形数: 颜色数量
        """
        if not self.obj:
            return 0
        return self._call_function(124048, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)

    def get_command_line(self, hwnd):
        """
        GetCommandLine
        
        获取指定窗口所在进程的启动命令行
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
        
        返回值:
            字符串: 读取到的启动命令行
        """
        if not self.obj:
            return ''
        result = self._call_function(100752, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_cpu_type(self):
        """
        GetCpuType
        
        获取当前CPU类型(intel或者amd).
        
        """
        if not self.obj:
            return 0
        return self._call_function(102432, c_long, [c_long], self.obj)

    def get_cpu_usage(self):
        """
        GetCpuUsage
        
        获取当前CPU的使用率. 用百分比返回.
        
        """
        if not self.obj:
            return 0
        return self._call_function(121072, c_long, [c_long], self.obj)

    def get_cursor_pos(self, x, y):
        """
        GetCursorPos
        
        获取鼠标位置.
        
        参数:
            x (变参指针): 返回X坐标
            y (变参指针): 返回Y坐标
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(121680, c_long, [c_long, POINTER(c_long), POINTER(c_long)], self.obj, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def get_cursor_shape(self):
        """
        GetCursorShape
        
        获取鼠标特征码. 当BindWindow或者BindWindowEx中的mouse参数含有dx.mouse.cursor时， 获取到的是后台鼠标特征，否则是前台鼠标特征. [关于如何识别后台鼠标特征.](#chmtopic122)
        
        返回值:
            字符串: 成功时，返回鼠标特征码.   失败时，返回空的串.
        """
        if not self.obj:
            return ''
        result = self._call_function(111984, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_cursor_shape_ex(self, type):
        """
        GetCursorShapeEx
        
        获取鼠标特征码. 当BindWindow或者BindWindowEx中的mouse参数含有dx.mouse.cursor时， 获取到的是后台鼠标特征，否则是前台鼠标特征.  [关于如何识别后台鼠标特征.](#chmtopic122)
        
        参数:
            type (整形数): 获取鼠标特征码的方式. 和工具中的方式1 方式2对应. 方式1此参数值为0. 方式2此参数值为1.
        
        返回值:
            字符串: 成功时，返回鼠标特征码.   失败时，返回空的串.
        """
        if not self.obj:
            return ''
        result = self._call_function(117488, c_char_p, [c_long, c_long], self.obj, type)
        return result.decode('gbk') if result else ''

    def get_cursor_spot(self):
        """
        GetCursorSpot
        
        获取鼠标热点位置.(参考工具中抓取鼠标后，那个闪动的点就是热点坐标,不是鼠标坐标) 当BindWindow或者BindWindowEx中的mouse参数含有dx.mouse.cursor时， 获取到的是后台鼠标热点位置，否则是前台鼠标热点位置.  [关于如何识别后台鼠标特征.](#chmtopic122)
        
        返回值:
            字符串: 成功时，返回形如"x,y"的字符串   失败时，返回空的串.
        """
        if not self.obj:
            return ''
        result = self._call_function(125056, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_dpi(self):
        """
        GetDPI
        
        判断当前系统的DPI(文字缩放)是不是100%缩放.
        
        """
        if not self.obj:
            return 0
        return self._call_function(107664, c_long, [c_long], self.obj)

    def get_dict(self, index, font_index):
        """
        GetDict
        
        获取指定字库中指定条目的字库信息.
        
        参数:
            index (整形数): 字库序号(0-99)
            font (\_index 整形数): 字库条目序号(从0开始计数,数值不得超过指定字库的字库上限,具体参考[GetDictCount](#chmtopic768))
        
        返回值:
            字符串: 返回字库条目信息. 失败返回空串.
        """
        if not self.obj:
            return ''
        result = self._call_function(99184, c_char_p, [c_long, c_long, c_long], self.obj, index, font_index)
        return result.decode('gbk') if result else ''

    def get_dict_count(self, index):
        """
        GetDictCount
        
        获取指定的字库中的字符数量.
        
        参数:
            index (整形数): 字库序号(0-99)
        
        返回值:
            整形数: 字库数量
        """
        if not self.obj:
            return 0
        return self._call_function(99584, c_long, [c_long, c_long], self.obj, index)

    def get_dict_info(self, text, font_name, font_size, flag):
        """
        GetDictInfo
        
        根据指定的文字，以及指定的系统字库信息，获取字库描述信息.
        
        参数:
            text (字符串): 需要获取的字符串
            font (\_name 字符串): 系统字体名,比如"宋体"
            font (\_size 整形数): 系统字体尺寸，这个尺寸一定要以大漠综合工具获取的为准.如何获取尺寸看视频教程.
            flag (整形数): 字体类别 取值可以是以下值的组合,比如1+2+4+8,2+4. 0表示正常字体.\ 1 : 粗体\ 2 : 斜体\ 4 : 下划线\ 8 : 删除线
        
        返回值:
            字符串: 返回字库信息,每个字符的字库信息用"|"来分割
        """
        if not self.obj:
            return ''
        result = self._call_function(100624, c_char_p, [c_long, c_char_p, c_char_p, c_long, c_long], self.obj, text.encode('gbk') if isinstance(text, str) else text, font_name.encode('gbk') if isinstance(font_name, str) else font_name, font_size, flag)
        return result.decode('gbk') if result else ''

    def get_dir(self, type):
        """
        GetDir
        
        得到系统的路径
        
        参数:
            type (整形数): 取值为以下类型
        
        返回值:
            字符串: 返回路径
        """
        if not self.obj:
            return ''
        result = self._call_function(124512, c_char_p, [c_long, c_long], self.obj, type)
        return result.decode('gbk') if result else ''

    def get_disk_model(self, index):
        """
        GetDiskModel
        
        获取本机的指定硬盘的厂商信息. 要求调用进程必须有管理员权限. 否则返回空串.
        
        参数:
            index整形 (数): 硬盘序号. 表示是第几块硬盘. 从0开始编号,最小为0,最大为5,也就是最多支持6块硬盘的厂商信息获取.
        
        返回值:
            字符串: 字符串表达的硬盘厂商信息
        """
        if not self.obj:
            return ''
        result = self._call_function(102128, c_char_p, [c_long, c_long], self.obj, index)
        return result.decode('gbk') if result else ''

    def get_disk_reversion(self, index):
        """
        GetDiskReversion
        
        获取本机的指定硬盘的修正版本信息. 要求调用进程必须有管理员权限. 否则返回空串.
        
        参数:
            index整形 (数): 硬盘序号. 表示是第几块硬盘. 从0开始编号,最小为0,最大为5,也就是最多支持6块硬盘的修正版本信息获取.
        
        返回值:
            字符串: 字符串表达的修正版本信息
        """
        if not self.obj:
            return ''
        result = self._call_function(109040, c_char_p, [c_long, c_long], self.obj, index)
        return result.decode('gbk') if result else ''

    def get_disk_serial(self, index):
        """
        GetDiskSerial
        
        获取本机的指定硬盘的序列号. 要求调用进程必须有管理员权限. 否则返回空串.
        
        参数:
            index整形 (数): 硬盘序号. 表示是第几块硬盘. 从0开始编号,最小为0,最大为5,也就是最多支持6块硬盘的序列号获取.
        
        返回值:
            字符串: 字符串表达的硬盘序列号
        """
        if not self.obj:
            return ''
        result = self._call_function(112352, c_char_p, [c_long, c_long], self.obj, index)
        return result.decode('gbk') if result else ''

    def get_display_info(self):
        """
        GetDisplayInfo
        
        获取本机的显卡信息.
        
        返回值:
            字符串: 字符串表达的显卡描述信息. 如果有多个显卡,用"|"连接
        """
        if not self.obj:
            return ''
        result = self._call_function(122992, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_dm_count(self):
        """
        GetDmCount
        
        返回当前进程已经创建的dm对象个数.
        
        返回值:
            整形数: 个数.
        """
        if not self.obj:
            return 0
        return self._call_function(125008, c_long, [c_long], self.obj)

    def get_file_length(self, file):
        """
        GetFileLength
        
        获取指定的文件长度.
        
        参数:
            file (字符串): 文件名
        
        """
        if not self.obj:
            return 0
        return self._call_function(111296, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def get_foreground_focus(self):
        """
        GetForegroundFocus
        
        获取顶层活动窗口中具有输入焦点的窗口句柄
        
        返回值:
            整形数: 返回整型表示的窗口句柄
        """
        if not self.obj:
            return 0
        return self._call_function(108512, c_long, [c_long], self.obj)

    def get_foreground_window(self):
        """
        GetForegroundWindow
        
        获取顶层活动窗口,可以获取到按键自带插件无法获取到的句柄
        
        返回值:
            整形数: 返回整型表示的窗口句柄
        """
        if not self.obj:
            return 0
        return self._call_function(115360, c_long, [c_long], self.obj)

    def get_fps(self):
        """
        GetFps
        
        获取绑定窗口的fps. (即时fps,不是平均fps).  要想获取fps,那么图色模式必须是dx模式的其中一种.  比如dx.graphic.3d  dx.graphic.opengl等.
        
        返回值:
            整形数: fps
        """
        if not self.obj:
            return 0
        return self._call_function(106016, c_long, [c_long], self.obj)

    def get_id(self):
        """
        GetID
        
        返回当前大漠对象的ID值，这个值对于每个对象是唯一存在的。可以用来判定两个大漠对象是否一致.
        
        返回值:
            整形数: 当前对象的ID值.
        """
        if not self.obj:
            return 0
        return self._call_function(105184, c_long, [c_long], self.obj)

    def get_key_state(self, vk):
        """
        GetKeyState
        
        获取指定的按键状态.(前台信息,不是后台)
        
        参数:
            vk (\_code 整形数): 虚拟按键码
        
        返回值:
            整形数: 0:弹起 1:按下
        """
        if not self.obj:
            return 0
        return self._call_function(103296, c_long, [c_long, c_long], self.obj, vk)

    def get_last_error(self):
        """
        GetLastError
        
        获取插件命令的最后错误
        
        返回值:
            整形数: 返回值表示错误值。 0表示无错误.
            -1 : 表示你使用了绑定里的收费功能，但是没注册，无法使用. -2 : 使用模式0 2 时出现，因为目标窗口有保护. 常见于win7以上系统.或者有安全软件拦截插件.解决办法: 关闭所有安全软件，然后再重新尝试. 如果还不行就可以肯定是目标窗口有特殊保护.  -3 : 使用模式0 2 时出现，可能目标窗口有保护，也可能是异常错误. 可以尝试换绑定模式或许可以解决. -4 : 使用模式101 103时出现，这是异常错误. -5 : 使用模式101 103时出现, 这个错误的解决办法就是关闭目标窗口，重新打开再绑定即可. 也可能是运行脚本的进程没有管理员权限.  -6 : 被安全软件拦截。 典型的是金山.360等. 如果是360关闭即可。 如果是金山，必须卸载，关闭是没用的. -7 -9 : 使用模式101 103时出现,异常错误. 还有可能是安全软件的问题，比如360等。尝试卸载360. -8 -10 : 使用模式101 103时出现, 目标进程可能有保护,也可能是插件版本过老，试试新的或许可以解决. -8可以尝试使用DmGuard中的np2盾配合. -11 : 使用模式101 103时出现, 目标进程有保护. 告诉我解决。 -12 : 使用模式101 103时出现, 目标进程有保护. 告诉我解决。 -13 : 使用模式101 103时出现, 目标进程有保护. 或者是因为上次的绑定没有解绑导致。 尝试在绑定前调用ForceUnBindWindow.  -37 : 使用模式101 103时出现, 目标进程有保护. 告诉我解决。 -14 : 可能系统缺少部分DLL,尝试安装d3d. 或者是鼠标或者键盘使用了dx.mouse.api或者dx.keypad.api，但实际系统没有插鼠标和键盘. 也有可能是图色中有dx.graphic.3d之类的,但相应的图色被占用,比如全屏D3D程序. -16 : 可能使用了绑定模式 0 和 101，然后可能指定了一个子窗口.导致不支持.可以换模式2或者103来尝试. 另外也可以考虑使用父窗口或者顶级窗口.来避免这个错误。还有可能是目标窗口没有正常解绑 然后再次绑定的时候. -17 : 模式101 103时出现. 这个是异常错误. 告诉我解决. -18 : 句柄无效. -19 : 使用模式0 11 101时出现,这是异常错误,告诉我解决. -20 : 使用模式101 103 时出现,说明目标进程里没有解绑，并且子绑定达到了最大. 尝试在返回这个错误时，调用ForceUnBindWindow来强制解除绑定. -21 : 使用模式任何模式时出现,说明目标进程已经存在了绑定(没有正确解绑就退出了?被其它软件绑定?,或者多个线程同时进行了绑定?). 尝试在返回这个错误时，调用ForceUnBindWindow来强制解除绑定.或者检查自己的代码. -22 : 使用模式0 2,绑定64位进程窗口时出现,因为安全软件拦截插件释放的EXE文件导致. -23 : 使用模式0 2,绑定64位进程窗口时出现,因为安全软件拦截插件释放的DLL文件导致. -24 : 使用模式0 2,绑定64位进程窗口时出现,因为安全软件拦截插件运行释放的EXE. -25 : 使用模式0 2,绑定64位进程窗口时出现,因为安全软件拦截插件运行释放的EXE. -26 : 使用模式0 2,绑定64位进程窗口时出现, 因为目标窗口有保护. 常见于win7以上系统.或者有安全软件拦截插件.解决办法: 关闭所有安全软件，然后再重新尝试. 如果还不行就可以肯定是目标窗口有特殊保护. -27 : 绑定64位进程窗口时出现，因为使用了不支持的模式，目前暂时只支持模式0 2 11 13 101 103 -28 : 绑定32位进程窗口时出现，因为使用了不支持的模式，目前暂时只支持模式0 2 11 13 101 103 -38 : 是用了大于2的绑定模式,并且使用了dx.public.inject.c时，分配内存失败. 可以考虑开启memory系列盾来尝试. -39 : 是用了大于2的绑定模式,并且使用了dx.public.inject.c时的异常错误. 可以联系我解决. -40 : 是用了大于2的绑定模式,并且使用了dx.public.inject.c时, 写入内存失败. 可以考虑开启memory系列盾来尝试. -41 : 是用了大于2的绑定模式,并且使用了dx.public.inject.c时的异常错误. 可以联系我解决. -42 : 绑定时,创建映射内存失败. 这是个异常错误. 一般不会出现. 如果出现了，检查下代码是不是有同个对象同时绑定的情况.还有可能是你的进程有句柄泄露导致无法创建句柄会出这个错误. -43 : 绑定时,映射内存失败. 这是个异常错误. 一般不会出现. 如果出现了，一般是你的进程内存不足,检查下你的进程是不是内存泄漏了.  -44 : 无效的参数,通常是传递了不支持的参数. -45 : 绑定时,创建互斥信号失败. 这个是一场错误. 一般不会出现. 如果出现了检查进程是否有句柄泄漏的情况.
            -100 : 调用读写内存函数后，发现无效的窗口句柄 -101 : 读写内存函数失败 -200 : AsmCall失败 -202 : AsmCall平台兼容问题.联系我解决.
        """
        if not self.obj:
            return 0
        return self._call_function(107936, c_long, [c_long], self.obj)

    def get_locale(self):
        """
        GetLocale
        
        判断当前系统使用的非UNICODE字符集是否是GB2312(简体中文)(由于设计插件时偷懒了,使用的是非UNICODE字符集，导致插件必须运行在GB2312字符集环境下).
        
        """
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
        """
        GetMachineCode
        
        获取本机的机器码.(带网卡). 此机器码用于插件网站后台. 要求调用进程必须有管理员权限. 否则返回空串.
        
        返回值:
            字符串: 字符串表达的机器机器码
        """
        if not self.obj:
            return ''
        result = self._call_function(113456, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_machine_code_no_mac(self):
        """
        GetMachineCodeNoMac
        
        获取本机的机器码.(不带网卡) 要求调用进程必须有管理员权限. 否则返回空串.
        
        返回值:
            字符串: 字符串表达的机器机器码
        """
        if not self.obj:
            return ''
        result = self._call_function(120544, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_memory_usage(self):
        """
        GetMemoryUsage
        
        获取当前内存的使用率. 用百分比返回.
        
        """
        if not self.obj:
            return 0
        return self._call_function(106064, c_long, [c_long], self.obj)

    def get_module_base_addr(self, hwnd, module_name):
        """
        GetModuleBaseAddr
        
        根据指定的窗口句柄，来获取对应窗口句柄进程下的指定模块的基址
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            module (字符串): 模块名
        
        返回值:
            长整形数: 模块的基址
        """
        if not self.obj:
            return 0
        return self._call_function(108848, c_longlong, [c_long, c_long, c_char_p], self.obj, hwnd, module_name.encode('gbk') if isinstance(module_name, str) else module_name)

    def get_module_size(self, hwnd, module_name):
        """
        GetModuleSize
        
        根据指定的窗口句柄，来获取对应窗口句柄进程下的指定模块的大小
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            module (字符串): 模块名
        
        返回值:
            整形数: 模块的大小
        """
        if not self.obj:
            return 0
        return self._call_function(120016, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, module_name.encode('gbk') if isinstance(module_name, str) else module_name)

    def get_mouse_point_window(self):
        """
        GetMousePointWindow
        
        获取鼠标指向的可见窗口句柄,可以获取到按键自带的插件无法获取到的句柄
        
        返回值:
            整形数: 返回整型表示的窗口句柄
        """
        if not self.obj:
            return 0
        return self._call_function(105424, c_long, [c_long], self.obj)

    def get_mouse_speed(self):
        """
        GetMouseSpeed
        
        获取系统鼠标的移动速度.  如图所示红色区域. 一共分为11个级别. 从1开始,11结束. 这仅是前台鼠标的速度. 后台不用理会这个. ![ref3]
        
        返回值:
            整形数: 0:失败 其他值,当前系统鼠标的移动速度
        """
        if not self.obj:
            return 0
        return self._call_function(99248, c_long, [c_long], self.obj)

    def get_net_time(self):
        """
        GetNetTime
        
        从网络获取当前北京时间.
        
        返回值:
            字符串: 时间格式. 和now返回一致. 比如"2001-11-01 23:14:08"
        """
        if not self.obj:
            return ''
        result = self._call_function(107712, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_net_time_by_ip(self, ip):
        """
        GetNetTimeByIp
        
        根据指定时间服务器IP,从网络获取当前北京时间.
        
        参数:
            ip (字符串): IP或者域名,并且支持多个IP或者域名连接
        
        返回值:
            字符串: 时间格式. 和now返回一致. 比如"2001-11-01 23:14:08"
        """
        if not self.obj:
            return ''
        result = self._call_function(105360, c_char_p, [c_long, c_char_p], self.obj, ip.encode('gbk') if isinstance(ip, str) else ip)
        return result.decode('gbk') if result else ''

    def get_net_time_safe(self):
        """
        GetNetTimeSafe
        
        服务器压力太大,此函数不再支持。 请使用GetNetTimeByIp
        
        """
        if not self.obj:
            return ''
        result = self._call_function(107760, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_now_dict(self):
        """
        GetNowDict
        
        获取当前使用的字库序号(0-99)
        
        返回值:
            整形数: 字库序号(0-99)
        """
        if not self.obj:
            return 0
        return self._call_function(101584, c_long, [c_long], self.obj)

    def get_os_build_number(self):
        """
        GetOsBuildNumber
        
        得到操作系统的build版本号.  比如win10 16299,那么返回的就是16299. 其他类似
        
        返回值:
            整形数: build 版本号 失败返回0
        """
        if not self.obj:
            return 0
        return self._call_function(104240, c_long, [c_long], self.obj)

    def get_os_type(self):
        """
        GetOsType
        
        得到操作系统的类型
        
        返回值:
            整形数: 0 : win95/98/me/nt4.0
            1 : xp/2000
            2 : 2003/2003 R2/xp-64
            3 : vista/2008
            4 : win7/2008 R2
            5 : win8/2012
            6 : win8.1/2012 R2
            7 : win10/2016 TP/win11
        """
        if not self.obj:
            return 0
        return self._call_function(121632, c_long, [c_long], self.obj)

    def get_path(self):
        """
        GetPath
        
        获取全局路径.(可用于调试)
        
        返回值:
            字符串: 以字符串的形式返回当前设置的全局路径
        """
        if not self.obj:
            return ''
        result = self._call_function(109600, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def get_pic_size(self, pic_name):
        """
        GetPicSize
        
        获取指定图片的尺寸，如果指定的图片已经被加入缓存，则从缓存中获取信息.\ 此接口也会把此图片加入缓存. （当图色缓存机制打开时,具体参考[EnablePicCache](#chmtopic352)）
        
        参数:
            pic (\_name 字符串): 文件名 比如"1.bmp"
        
        返回值:
            字符串: 形式如 "w,h" 比如"30,20"
        """
        if not self.obj:
            return ''
        result = self._call_function(114960, c_char_p, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)
        return result.decode('gbk') if result else ''

    def get_point_window(self, x, y):
        """
        GetPointWindow
        
        获取给定坐标的可见窗口句柄,可以获取到按键自带的插件无法获取到的句柄
        
        参数:
            X (整形数): 屏幕X坐标
            Y (整形数): 屏幕Y坐标
        
        返回值:
            整形数: 返回整型表示的窗口句柄
        """
        if not self.obj:
            return 0
        return self._call_function(118544, c_long, [c_long, c_long, c_long], self.obj, x, y)

    def get_process_info(self, pid):
        """
        GetProcessInfo
        
        根据指定的pid获取进程详细信息,(进程名,进程全路径,CPU占用率(百分比),内存占用量(字节))
        
        参数:
            pid (整形数): 进程pid
        
        """
        if not self.obj:
            return ''
        result = self._call_function(119024, c_char_p, [c_long, c_long], self.obj, pid)
        return result.decode('gbk') if result else ''

    def get_real_path(self, path):
        """
        GetRealPath
        
        获取指定文件或目录的真实路径
        
        参数:
            path字符 (串): 路径名,可以是文件路径，也可以是目录. 这里必须是全路径
        
        """
        if not self.obj:
            return ''
        result = self._call_function(105008, c_char_p, [c_long, c_char_p], self.obj, path.encode('gbk') if isinstance(path, str) else path)
        return result.decode('gbk') if result else ''

    def get_remote_api_address(self, hwnd, base_addr, fun_name):
        """
        GetRemoteApiAddress
        
        根据指定的目标模块地址,获取目标窗口(进程)内的导出函数地址.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            base (\_addr 长整形数): 目标模块地址,比如user32.dll的地址,可以通过GetModuleBaseAddr来获取.
            fun (\_addr字符串**): ** 需要获取的导出函数名. 比如"SetWindowTextA".
        
        返回值:
            长整形数: 获取的地址. 如果失败返回0
        """
        if not self.obj:
            return 0
        return self._call_function(122192, c_longlong, [c_long, c_long, c_longlong, c_char_p], self.obj, hwnd, base_addr, fun_name.encode('gbk') if isinstance(fun_name, str) else fun_name)

    def get_result_count(self, text):
        """
        GetResultCount
        
        对插件部分接口的返回值进行解析,并返回ret中的坐标个数
        
        参数:
            ret (字符串): 部分接口的返回串
        
        返回值:
            整形数: 返回ret中的坐标个数
        """
        if not self.obj:
            return 0
        return self._call_function(116720, c_long, [c_long, c_char_p], self.obj, text.encode('gbk') if isinstance(text, str) else text)

    def get_result_pos(self, text, index, x, y):
        """
        GetResultPos
        
        对插件部分接口的返回值进行解析,并根据指定的第index个坐标,返回具体的值
        
        参数:
            ret (字符串): 部分接口的返回串
            index (整形数): 第几个坐标
            intX (变参指针): 返回X坐标
            intY (变参指针): 返回Y坐标
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102800, c_long, [c_long, c_char_p, c_long, POINTER(c_long), POINTER(c_long)], self.obj, text.encode('gbk') if isinstance(text, str) else text, index, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def get_screen_data(self, x1, y1, x2, y2):
        """
        GetScreenData
        
        获取指定区域的图像,用二进制数据的方式返回,（不适合按键使用）方便二次开发.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
        
        返回值:
            整形数: 返回的是指定区域的二进制颜色数据地址,每个颜色是4个字节,表示方式为(00RRGGBB)
        """
        if not self.obj:
            return 0
        return self._call_function(125104, c_long, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)

    def get_screen_data_bmp(self, x1, y1, x2, y2, data, size):
        """
        GetScreenDataBmp
        
        获取指定区域的图像,用24位位图的数据格式返回,方便二次开发.（或者可以配合SetDisplayInput的mem模式）
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            data (变参指针): 返回图片的数据指针
            size (变参指针): 返回图片的数据长度
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(107136, c_long, [c_long, c_long, c_long, c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, x1, y1, x2, y2, byref(data) if isinstance(data, c_long) else data, byref(size) if isinstance(size, c_long) else size)

    def get_screen_depth(self):
        """
        GetScreenDepth
        
        获取屏幕的色深.
        
        返回值:
            整形数: 返回系统颜色深度.(16或者32等)
        """
        if not self.obj:
            return 0
        return self._call_function(102384, c_long, [c_long], self.obj)

    def get_screen_height(self):
        """
        GetScreenHeight
        
        获取屏幕的高度.
        
        返回值:
            整形数: 返回屏幕的高度
        """
        if not self.obj:
            return 0
        return self._call_function(117792, c_long, [c_long], self.obj)

    def get_screen_width(self):
        """
        GetScreenWidth
        
        获取屏幕的宽度.
        
        返回值:
            整形数: 返回屏幕的宽度
        """
        if not self.obj:
            return 0
        return self._call_function(113920, c_long, [c_long], self.obj)

    def get_special_window(self, flag):
        """
        GetSpecialWindow
        
        获取特殊窗口
        
        参数:
            Flag (整形数): 取值定义如下
            0 (): 获取桌面窗口
            1 (): 获取任务栏窗口
        
        返回值:
            整形数: 以整型数表示的窗口句柄
        """
        if not self.obj:
            return 0
        return self._call_function(102336, c_long, [c_long, c_long], self.obj, flag)

    def get_system_info(self, type, method):
        """
        GetSystemInfo
        
        获取指定的系统信息.
        
        参数:
            type (字符串): 取值如下\ "cpuid" : 表示获取cpu序列号. method可取0和1\ "disk\_volume\_serial id" : 表示获取分区序列号. id表示分区序号. 0表示C盘.1表示D盘.以此类推. 最高取到5. 也就是6个分区. method可取0\ "bios\_vendor" : 表示获取bios厂商信息. method可取0和1\ "bios\_version" : 表示获取bios版本信息. method可取0和1\ "bios\_release\_date" : 表示获取bios发布日期. method可取0和1\ "bios\_oem" : 表示获取bios里的oem信息. method可取0\ "board\_vendor" : 表示获取主板制造厂商信息. method可取0和1\ "board\_product" : 表示获取主板产品信息. method可取0和1\ "board\_version" : 表示获取主板版本信息. method可取0和1\ "board\_serial" : 表示获取主板序列号. method可取0\ "board\_location" : 表示获取主板位置信息. method可取0\ "system\_manufacturer" : 表示获取系统制造商信息. method可取0和1\ "system\_product" : 表示获取系统产品信息. method可取0和1\ "system\_serial" : 表示获取bios序列号. method可取0\ "system\_uuid" : 表示获取bios uuid. method可取0\ "system\_version" : 表示获取系统版本信息. method可取0和1\ "system\_sku" : 表示获取系统sku序列号. method可取0和1\ "system\_family" : 表示获取系统家族信息. method可取0和1\ "product\_id" : 表示获取系统产品id. method可取0\ "system\_identifier" : 表示获取系统标识. method可取0\ "system\_bios\_version" : 表示获取系统BIOS版本号. method可取0. 多个结果用"|"连接.\ "system\_bios\_date" : 表示获取系统BIOS日期. method可取0
            method整形 (数): 获取方法. 一般从0开始取值.
        
        返回值:
            字符串: 字符串表达的系统信息.
        """
        if not self.obj:
            return ''
        result = self._call_function(115680, c_char_p, [c_long, c_char_p, c_long], self.obj, type.encode('gbk') if isinstance(type, str) else type, method)
        return result.decode('gbk') if result else ''

    def get_time(self):
        """
        GetTime
        
        获取当前系统从开机到现在所经历过的时间，单位是毫秒
        
        返回值:
            整形数: 时间(单位毫秒)
        """
        if not self.obj:
            return 0
        return self._call_function(103504, c_long, [c_long], self.obj)

    def get_window(self, hwnd, flag):
        """
        GetWindow
        
        获取给定窗口相关的窗口句柄
        
        参数:
            hwnd (整形数): 窗口句柄
            flag (整形数): 取值定义如下
            0 (): 获取父窗口
            1 (): 获取第一个儿子窗口
            2 (): 获取First 窗口
            3 (): 获取Last窗口
            4 (): 获取下一个窗口
            5 (): 获取上一个窗口
            6 (): 获取拥有者窗口
            7 (): 获取顶层窗口
        
        返回值:
            整形数: 返回整型表示的窗口句柄
        """
        if not self.obj:
            return 0
        return self._call_function(120752, c_long, [c_long, c_long, c_long], self.obj, hwnd, flag)

    def get_window_class(self, hwnd):
        """
        GetWindowClass
        
        获取窗口的类名
        
        参数:
            hwnd (整形数): 指定的窗口句柄
        
        返回值:
            字符串: 窗口的类名
        """
        if not self.obj:
            return ''
        result = self._call_function(117056, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_window_process_id(self, hwnd):
        """
        GetWindowProcessId
        
        获取指定窗口所在的进程ID.
        
        参数:
            hwnd (整形数): 窗口句柄
        
        返回值:
            整形数: 返回整型表示的是进程ID
        """
        if not self.obj:
            return 0
        return self._call_function(124464, c_long, [c_long, c_long], self.obj, hwnd)

    def get_window_process_path(self, hwnd):
        """
        GetWindowProcessPath
        
        获取指定窗口所在的进程的exe文件全路径.
        
        参数:
            hwnd (整形数): 窗口句柄
        
        返回值:
            字符串: 返回字符串表示的是exe全路径名
        """
        if not self.obj:
            return ''
        result = self._call_function(105232, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_window_rect(self, hwnd, x1, y1, x2, y2):
        """
        GetWindowRect
        
        获取窗口在屏幕上的位置
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            x1 (变参指针): 返回窗口左上角X坐标
            y1 (变参指针): 返回窗口左上角Y坐标
            x2 (变参指针): 返回窗口右下角X坐标
            y2 (变参指针): 返回窗口右下角Y坐标
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(122656, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x1) if isinstance(x1, c_long) else x1, byref(y1) if isinstance(y1, c_long) else y1, byref(x2) if isinstance(x2, c_long) else x2, byref(y2) if isinstance(y2, c_long) else y2)

    def get_window_state(self, hwnd, flag):
        """
        GetWindowState
        
        获取指定窗口的一些属性
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            flag (整形数): 取值定义如下
            0 (): 判断窗口是否存在
            1 (): 判断窗口是否处于激活
            2 (): 判断窗口是否可见
            3 (): 判断窗口是否最小化
            4 (): 判断窗口是否最大化
            5 (): 判断窗口是否置顶
            6 (): 判断窗口是否无响应
            7 (): 判断窗口是否可用(灰色为不可用)
            8 (): 另外的方式判断窗口是否无响应,如果6无效可以尝试这个
            9 (): 判断窗口所在进程是不是64位
        
        返回值:
            整形数: 0: 不满足条件 1: 满足条件
        """
        if not self.obj:
            return 0
        return self._call_function(100112, c_long, [c_long, c_long, c_long], self.obj, hwnd, flag)

    def get_window_thread_id(self, hwnd):
        """
        GetWindowThreadId
        
        获取指定窗口所在的线程ID.
        
        参数:
            hwnd (整形数): 窗口句柄
        
        返回值:
            整形数: 返回整型表示的是线程ID
        """
        if not self.obj:
            return 0
        return self._call_function(107504, c_long, [c_long, c_long], self.obj, hwnd)

    def get_window_title(self, hwnd):
        """
        GetWindowTitle
        
        获取窗口的标题
        
        参数:
            hwnd (整形数): 指定的窗口句柄
        
        返回值:
            字符串: 窗口的标题
        """
        if not self.obj:
            return ''
        result = self._call_function(110816, c_char_p, [c_long, c_long], self.obj, hwnd)
        return result.decode('gbk') if result else ''

    def get_word_result_count(self, text):
        """
        GetWordResultCount
        
        在使用GetWords进行词组识别以后,可以用此接口进行识别词组数量的计算.
        
        参数:
            text (字符串): GetWords接口调用以后的返回值
        
        返回值:
            整形数: 返回词组数量
        """
        if not self.obj:
            return 0
        return self._call_function(103984, c_long, [c_long, c_char_p], self.obj, text.encode('gbk') if isinstance(text, str) else text)

    def get_word_result_pos(self, text, index, x, y):
        """
        GetWordResultPos
        
        在使用GetWords进行词组识别以后,可以用此接口进行识别各个词组的坐标
        
        参数:
            text (字符串): GetWords的返回值
            index (整形数): 表示第几个词组
            intX (变参指针): 返回的X坐标
            intY (变参指针): 返回的Y坐标
        
        返回值:
            整形数: 0: 失败
            1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(114352, c_long, [c_long, c_char_p, c_long, POINTER(c_long), POINTER(c_long)], self.obj, text.encode('gbk') if isinstance(text, str) else text, index, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def get_word_result_str(self, text, index):
        """
        GetWordResultStr
        
        在使用GetWords进行词组识别以后,可以用此接口进行识别各个词组的内容
        
        参数:
            text (字符串): GetWords的返回值
            index (整形数): 表示第几个词组
        
        返回值:
            字符串: 返回的第index个词组内容
        """
        if not self.obj:
            return ''
        result = self._call_function(104768, c_char_p, [c_long, c_char_p, c_long], self.obj, text.encode('gbk') if isinstance(text, str) else text, index)
        return result.decode('gbk') if result else ''

    def get_words(self, x1, y1, x2, y2, color, sim):
        """
        GetWords
        
        根据指定的范围,以及设定好的词组识别参数(一般不用更改,除非你真的理解了) 识别这个范围内所有满足条件的词组. 比较适合用在未知文字的情况下,进行不定识别.
        
        参数:
            x1 (整形数): 左上角X坐标
            y1 (整形数): 左上角Y坐标
            x2 (整形数): 右下角X坐标
            y2 (整形数): 右下角Y坐标
            color (字符串): 颜色格式串.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度 0.1-1.0
        
        返回值:
            字符串: 识别到的格式串,要用到专用函数来解析
        """
        if not self.obj:
            return ''
        result = self._call_function(107808, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def get_words_no_dict(self, x1, y1, x2, y2, color):
        """
        GetWordsNoDict
        
        根据指定的范围,以及设定好的词组识别参数(一般不用更改,除非你真的理解了) 识别这个范围内所有满足条件的词组. 这个识别函数不会用到字库。只是识别大概形状的位置
        
        参数:
            x1 (整形数): 左上角X坐标
            y1 (整形数): 左上角Y坐标
            x2 (整形数): 右下角X坐标
            y2 (整形数): 右下角Y坐标
            color (字符串): 颜色格式串.注意，RGB和HSV,以及灰度格式都支持.
        
        返回值:
            字符串: 识别到的格式串,要用到专用函数来解析
        """
        if not self.obj:
            return ''
        result = self._call_function(99024, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color)
        return result.decode('gbk') if result else ''

    def hack_speed(self, rate):
        """
        HackSpeed
        
        对目标窗口设置加速功能(类似变速齿轮),必须在绑定参数中有dx.public.hack.speed时才会生效.
        
        参数:
            rate (双精度浮点数): 取值范围大于0. 默认是1.0 表示不加速，也不减速. 小于1.0表示减速,大于1.0表示加速. 精度为小数点后1位. 也就是说1.5 和 1.56其实是一样的.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
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
        """
        ImageToBmp
        
        转换图片格式为24位BMP格式.
        
        参数:
            pic (\_name 字符串): 要转换的图片名
            bmp (\_name 字符串): 要保存的BMP图片名
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(109152, c_long, [c_long, c_char_p, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, bmp_name.encode('gbk') if isinstance(bmp_name, str) else bmp_name)

    def init_cri(self):
        """
        InitCri
        
        初始化临界区,必须在脚本开头调用一次.这个函数是强制把插件内的互斥信号量归0,无论调用对象是否拥有此信号量.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(120240, c_long, [c_long], self.obj)

    def int64_to_int32(self, v):
        """
        Int64ToInt32
        
        强制转换64位整数为32位. (这个函数是给按键精灵设计的,由于按键精灵不支持64位自动化变量,某些返回64位的整数的接口会出错)
        
        参数:
            value (长整形数**): ** 需要转换的64位整数
        
        返回值:
            整形数: 返回的32位整数
        """
        if not self.obj:
            return 0
        return self._call_function(110880, c_long, [c_long, c_longlong], self.obj, v)

    def int_to_data(self, int_value, type):
        """
        IntToData
        
        把整数转换成二进制形式.
        
        参数:
            value (**长整形数**): 需要转化的整型数
            type (**整形数**): 取值如下:\ 0: 4字节整形数 (一般都选这个)\ 1: 2字节整形数\ 2: 1字节整形数\ 3: 8字节整形数
        
        返回值:
            字符串: 字符串形式表达的二进制数据. 可以用于WriteData FindData FindDataEx等接口.
        """
        if not self.obj:
            return ''
        result = self._call_function(122272, c_char_p, [c_long, c_longlong, c_long], self.obj, int_value, type)
        return result.decode('gbk') if result else ''

    def is64_bit(self):
        """
        Is64Bit
        
        判断当前系统是否是64位操作系统
        
        返回值:
            整形数: 0 : 不是64位系统 1 : 是64位系统
        """
        if not self.obj:
            return 0
        return self._call_function(110512, c_long, [c_long], self.obj)

    def is_bind(self, hwnd):
        """
        IsBind
        
        判定指定窗口是否已经被后台绑定. (前台无法判定)
        
        参数:
            hwnd (整形数): 窗口句柄
        
        返回值:
            整形数: 0: 没绑定,或者窗口不存在. 1: 已经绑定.
        """
        if not self.obj:
            return 0
        return self._call_function(119232, c_long, [c_long, c_long], self.obj, hwnd)

    def is_display_dead(self, x1, y1, x2, y2, t):
        """
        IsDisplayDead
        
        判断指定的区域，在指定的时间内(秒),图像数据是否一直不变.(卡屏). (或者绑定的窗口不存在也返回1)
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            t (整形数): 需要等待的时间,单位是秒
        
        返回值:
            整形数: 0 : 没有卡屏，图像数据在变化. 1 : 卡屏. 图像数据在指定的时间内一直没有变化. 或者绑定的窗口不见了.
        """
        if not self.obj:
            return 0
        return self._call_function(114896, c_long, [c_long, c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2, t)

    def is_file_exist(self, file):
        """
        IsFileExist
        
        判断指定文件是否存在.
        
        参数:
            file (字符串): 文件名
        
        """
        if not self.obj:
            return 0
        return self._call_function(113824, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def is_folder_exist(self, folder):
        """IsFolderExist - 偏移: 121184"""
        if not self.obj:
            return 0
        return self._call_function(121184, c_long, [c_long, c_char_p], self.obj, folder.encode('gbk') if isinstance(folder, str) else folder)

    def is_surrpot_vt(self):
        """
        IsSurrpotVt
        
        判断当前CPU是否支持vt,并且是否在bios中开启了vt. 仅支持intel的CPU.
        
        返回值:
            整形数: 0 : 当前cpu不是intel的cpu,或者当前cpu不支持vt,或者bios中没打开vt. 1 : 支持
        """
        if not self.obj:
            return 0
        return self._call_function(106992, c_long, [c_long], self.obj)

    def key_down(self, vk):
        """
        KeyDown
        
        按住指定的虚拟键码
        
        参数:
            vk (\_code **整形数**): 虚拟按键码
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(115120, c_long, [c_long, c_long], self.obj, vk)

    def key_down_char(self, key_str):
        """
        KeyDownChar
        
        按住指定的虚拟键码
        
        参数:
            key (\_str **字符串**): 字符串描述的键码. 大小写无所谓. [点这里查看具体对应关系](#chmtopic401).
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(105600, c_long, [c_long, c_char_p], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str)

    def key_press(self, vk):
        """
        KeyPress
        
        按下指定的虚拟键码
        
        参数:
            vk (\_code 整形数): 虚拟按键码
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(118688, c_long, [c_long, c_long], self.obj, vk)

    def key_press_char(self, key_str):
        """
        KeyPressChar
        
        按下指定的虚拟键码
        
        参数:
            key (\_str** 字符串**): ** 字符串描述的键码. 大小写无所谓**. [点这里查看具体对应关系](#chmtopic401).**
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(116464, c_long, [c_long, c_char_p], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str)

    def key_press_str(self, key_str, delay):
        """
        KeyPressStr
        
        根据指定的字符串序列，依次按顺序按下其中的字符.
        
        参数:
            key (\_str** 字符串**): ** 需要按下的字符串序列. 比如"1234","abcd","7389,1462"等.
            delay (整形数): 每按下一个按键，需要延时多久. 单位毫秒.这个值越大，按的速度越慢。
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102528, c_long, [c_long, c_char_p, c_long], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str, delay)

    def key_up(self, vk):
        """
        KeyUp
        
        弹起来虚拟键vk\_code
        
        参数:
            vk (\_code 整形数): 虚拟按键码
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(113248, c_long, [c_long, c_long], self.obj, vk)

    def key_up_char(self, key_str):
        """
        KeyUpChar
        
        弹起来虚拟键key\_str
        
        参数:
            key (\_str** 字符串**): ** 字符串描述的键码. 大小写无所谓**. [点这里查看具体对应关系](#chmtopic401).**
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(121904, c_long, [c_long, c_char_p], self.obj, key_str.encode('gbk') if isinstance(key_str, str) else key_str)

    def leave_cri(self):
        """
        LeaveCri
        
        和EnterCri对应,离开临界区。此函数是释放调用对象占用的互斥信号量. 注意，只有调用对象占有了互斥信号量，此函数才会有作用. 否则没有任何作用. 如果调用对象在释放时，会自动把本对象占用的互斥信号量释放.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(120816, c_long, [c_long], self.obj)

    def left_click(self):
        """
        LeftClick
        
        按下鼠标左键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(118096, c_long, [c_long], self.obj)

    def left_double_click(self):
        """
        LeftDoubleClick
        
        双击鼠标左键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(101136, c_long, [c_long], self.obj)

    def left_down(self):
        """
        LeftDown
        
        按住鼠标左键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(106736, c_long, [c_long], self.obj)

    def left_up(self):
        """
        LeftUp
        
        弹起鼠标左键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(113680, c_long, [c_long], self.obj)

    def load_ai(self, file):
        """
        LoadAi
        
        加载Ai模块. Ai模块从后台下载. 模块加载仅支持所有的正式版本。具体可以看DmGuard里系统版本的说明.
        
        参数:
            file (** 字符串**): ** ai模块的路径. 比如绝对路径c:\ai.module或者相对路径ai.module等.
        
        返回值:
            整形数: 1  表示成功 -1 打开文件失败 -2 内存初始化失败.  如果是正式版本,出现这个错误可以联系我解决. -3 参数错误 -4 加载错误 -5 Ai模块初始化失败 -6 内存分配失败
        """
        if not self.obj:
            return 0
        return self._call_function(106944, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def load_ai_memory(self, addr, size):
        """
        LoadAiMemory
        
        从内存加载Ai模块. Ai模块从后台下载. 模块加载仅支持所有的正式版本。具体可以看DmGuard里系统版本的说明.
        
        参数:
            data (整形数**): ** ai模块在内存中的地址
            size (整形数**): ** ai模块在内存中的大小
        
        返回值:
            整形数: 1  表示成功 -1 打开文件失败 -2 内存初始化失败. 如果是正式版本,出现这个错误可以联系我解决. -3 参数错误 -4 加载错误 -5 Ai模块初始化失败 -6 内存分配失败
        """
        if not self.obj:
            return 0
        return self._call_function(108256, c_long, [c_long, c_long, c_long], self.obj, addr, size)

    def load_pic(self, pic_name):
        """
        LoadPic
        
        预先加载指定的图片,这样在操作任何和图片相关的函数时,将省去了加载图片的时间。调用此函数后,没必要一定要调用FreePic,插件自己会自动释放. 另外,此函数不是必须调用的,所有和图形相关的函数只要调用过一次，图片会自动加入缓存. 如果想对一个已经加入缓存的图片进行修改，那么必须先用FreePic释放此图片在缓存中占用 的内存，然后重新调用图片相关接口，就可以重新加载此图片. （当图色缓存机制打开时,具体参考[EnablePicCache](#chmtopic352)）
        
        参数:
            pic (\_name 字符串): 文件名 比如"1.bmp|2.bmp|3.bmp" 等,可以使用通配符,比如
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(124128, c_long, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)

    def load_pic_byte(self, addr, size, name):
        """
        LoadPicByte
        
        预先加载指定的图片,这样在操作任何和图片相关的函数时,将省去了加载图片的时间。调用此函数后,没必要一定要调用FreePic,插件自己会自动释放. 另外,此函数不是必须调用的,所有和图形相关的函数只要调用过一次，图片会自动加入缓存. 如果想对一个已经加入缓存的图片进行修改，那么必须先用FreePic释放此图片在缓存中占用 的内存，然后重新调用图片相关接口，就可以重新加载此图片. （当图色缓存机制打开时,具体参考[EnablePicCache](#chmtopic352)） 此函数同LoadPic，只不过LoadPic是从文件中加载图片,而LoadPicByte从给定的内存中加载.
        
        参数:
            addr (整形数): BMP图像首地址.(完整的BMP图像，不是经过解析的. 和BMP文件里的内容一致)
            size (整形数): BMP图像大小.(和BMP文件大小一致)
            pic (\_name 字符串): 文件名,指定这个地址对应的图片名. 用于找图时使用.
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(121408, c_long, [c_long, c_long, c_long, c_char_p], self.obj, addr, size, name.encode('gbk') if isinstance(name, str) else name)

    def lock_display(self, lock):
        """
        LockDisplay
        
        锁定指定窗口的图色数据(不刷新).
        
        参数:
            lock (整形数): 0关闭锁定\ 1 开启锁定
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(108304, c_long, [c_long, c_long], self.obj, lock)

    def lock_input(self, lock):
        """
        LockInput
        
        禁止外部输入到指定窗口
        
        参数:
            lock (整形数): 0关闭锁定\ 1 开启锁定(键盘鼠标都锁定)\ 2 只锁定鼠标\ 3 只锁定键盘\ 4 同1,但当您发现某些特殊按键无法锁定时,比如(回车，ESC等)，那就用这个模式吧. 但此模式会让SendString函数后台失效，或者采用和SendString类似原理发送字符串的其他3方函数失效.\ 5同3,但当您发现某些特殊按键无法锁定时,比如(回车，ESC等)，那就用这个模式吧. 但此模式会让SendString函数后台失效，或者采用和SendString类似原理发送字符串的其他3方函数失效.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(124272, c_long, [c_long, c_long], self.obj, lock)

    def lock_mouse_rect(self, x1, y1, x2, y2):
        """
        LockMouseRect
        
        设置前台鼠标在屏幕上的活动范围.
        
        参数:
            x1 (整形数): 区域的左上X坐标. 屏幕坐标.
            y1 (整形数): 区域的左上Y坐标. 屏幕坐标.
            x2 (整形数): 区域的右下X坐标. 屏幕坐标.
            y2 (整形数): 区域的右下Y坐标. 屏幕坐标.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(119792, c_long, [c_long, c_long, c_long, c_long, c_long], self.obj, x1, y1, x2, y2)

    def match_pic_name(self, pic_name):
        """
        MatchPicName
        
        根据通配符获取文件集合. 方便用于FindPic和FindPicEx
        
        参数:
            pic (\_name 字符串): 文件名 比如"1.bmp|2.bmp|3.bmp" 等,可以使用通配符,比如
        
        返回值:
            字符串: 返回的是通配符对应的文件集合，每个图片以|分割
        """
        if not self.obj:
            return ''
        result = self._call_function(117984, c_char_p, [c_long, c_char_p], self.obj, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name)
        return result.decode('gbk') if result else ''

    def md5(self, text):
        """Md5 - 偏移: 117376"""
        if not self.obj:
            return ''
        result = self._call_function(117376, c_char_p, [c_long, c_char_p], self.obj, text.encode('gbk') if isinstance(text, str) else text)
        return result.decode('gbk') if result else ''

    def middle_click(self):
        """
        MiddleClick
        
        按下鼠标中键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(108560, c_long, [c_long], self.obj)

    def middle_down(self):
        """
        MiddleDown
        
        按住鼠标中键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(109872, c_long, [c_long], self.obj)

    def middle_up(self):
        """
        MiddleUp
        
        弹起鼠标中键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(115072, c_long, [c_long], self.obj)

    def move_dd(self, dx, dy):
        """MoveDD - 偏移: 121840"""
        if not self.obj:
            return 0
        return self._call_function(121840, c_long, [c_long, c_long, c_long], self.obj, dx, dy)

    def move_file(self, src_file, dst_file):
        """
        MoveFile
        
        移动文件.
        
        参数:
            src (\_file 字符串): 原始文件名
            dst (\_file 字符串): 目标文件名.
        
        """
        if not self.obj:
            return 0
        return self._call_function(102272, c_long, [c_long, c_char_p, c_char_p], self.obj, src_file.encode('gbk') if isinstance(src_file, str) else src_file, dst_file.encode('gbk') if isinstance(dst_file, str) else dst_file)

    def move_r(self, rx, ry):
        """
        MoveR
        
        鼠标相对于上次的位置移动rx,ry.   如果您要使前台鼠标移动的距离和指定的rx,ry一致,最好配合[EnableMouseAccuracy](#chmtopic385)函数来使用.
        
        参数:
            rx (整形数): 相对于上次的X偏移
            ry (整形数): 相对于上次的Y偏移
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(113504, c_long, [c_long, c_long, c_long], self.obj, rx, ry)

    def move_to(self, x, y):
        """
        MoveTo
        
        把鼠标移动到目的点(x,y)
        
        参数:
            x (整形数): X坐标
            y (整形数): Y坐标
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(109088, c_long, [c_long, c_long, c_long], self.obj, x, y)

    def move_to_ex(self, x, y, w, h):
        """
        MoveToEx
        
        把鼠标移动到目的范围内的任意一点
        
        参数:
            x (整形数): X坐标
            y (整形数): Y坐标
            w (整形数): 宽度(从x计算起)
            h (整形数): 高度(从y计算起)
        
        返回值:
            字符串: 返回要移动到的目标点. 格式为x,y.  比如MoveToEx 100,100,10,10,返回值可能是101,102
        """
        if not self.obj:
            return ''
        result = self._call_function(120688, c_char_p, [c_long, c_long, c_long, c_long, c_long], self.obj, x, y, w, h)
        return result.decode('gbk') if result else ''

    def move_window(self, hwnd, x, y):
        """
        MoveWindow
        
        移动指定窗口到指定位置
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            x (整形数): X坐标
            y (整形数): Y坐标
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(119648, c_long, [c_long, c_long, c_long, c_long], self.obj, hwnd, x, y)

    def ocr(self, x1, y1, x2, y2, color, sim):
        """
        Ocr
        
        识别屏幕范围(x1,y1,x2,y2)内符合color\_format的字符串,并且相似度为sim,sim取值范围(0.1-1.0), 这个值越大越精确,越大速度越快,越小速度越慢,请斟酌使用!
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (\_format 字符串): 颜色格式串. 可以包含换行分隔符,语法是","后加分割字符串. 具体可以查看下面的示例.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回识别到的字符串
        """
        if not self.obj:
            return ''
        result = self._call_function(110992, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def ocr_ex(self, x1, y1, x2, y2, color, sim):
        """
        OcrEx
        
        识别屏幕范围(x1,y1,x2,y2)内符合color\_format的字符串,并且相似度为sim,sim取值范围(0.1-1.0), 这个值越大越精确,越大速度越快,越小速度越慢,请斟酌使用! 这个函数可以返回识别到的字符串，以及每个字符的坐标.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (\_format 字符串): 颜色格式串.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回识别到的字符串 格式如  "字符0$x0$y0|…|字符n$xn$yn"
        """
        if not self.obj:
            return ''
        result = self._call_function(113168, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def ocr_ex_one(self, x1, y1, x2, y2, color, sim):
        """
        OcrExOne
        
        识别屏幕范围(x1,y1,x2,y2)内符合color\_format的字符串,并且相似度为sim,sim取值范围(0.1-1.0), 这个值越大越精确,越大速度越快,越小速度越慢,请斟酌使用! 这个函数可以返回识别到的字符串，以及每个字符的坐标.这个同OcrEx,另一种返回形式.
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            color (\_format 字符串): 颜色格式串.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        返回值:
            字符串: 返回识别到的字符串 格式如  "识别到的信息|x0,y0|…|xn,yn"
        """
        if not self.obj:
            return ''
        result = self._call_function(112080, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_double], self.obj, x1, y1, x2, y2, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def ocr_in_file(self, x1, y1, x2, y2, pic_name, color, sim):
        """
        OcrInFile
        
        识别位图中区域(x1,y1,x2,y2)的文字
        
        参数:
            x1 (整形数): 区域的左上X坐标
            y1 (整形数): 区域的左上Y坐标
            x2 (整形数): 区域的右下X坐标
            y2 (整形数): 区域的右下Y坐标
            pic (\_name 字符串): 图片文件名
            color (\_format 字符串): 颜色格式串.注意，RGB和HSV,以及灰度格式都支持.
            sim (双精度浮点数): 相似度,取值范围0.1-1.0
        
        """
        if not self.obj:
            return ''
        result = self._call_function(110608, c_char_p, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p, c_double], self.obj, x1, y1, x2, y2, pic_name.encode('gbk') if isinstance(pic_name, str) else pic_name, color.encode('gbk') if isinstance(color, str) else color, sim)
        return result.decode('gbk') if result else ''

    def open_process(self, pid):
        """
        OpenProcess
        
        根据指定pid打开进程，并返回进程句柄.
        
        参数:
            pid (**整形数**): 进程pid
        
        返回值:
            整形数: 进程句柄, 可用于进程相关操作(读写操作等),记得操作完成以后，自己调用CloseHandle关闭句柄.
        """
        if not self.obj:
            return 0
        return self._call_function(124624, c_long, [c_long, c_long], self.obj, pid)

    def play(self, file):
        """
        Play
        
        播放指定的MP3或者wav文件.
        
        参数:
            media (\_file 字符串): 指定的音乐文件，可以采用文件名或者绝对路径的形式.
        
        返回值:
            整形数: 0 : 失败 非0表示当前播放的ID。可以用Stop来控制播放结束.
        """
        if not self.obj:
            return 0
        return self._call_function(105072, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def rgb2_bgr(self, rgb_color):
        """
        RGB2BGR
        
        把RGB的颜色格式转换为BGR(按键格式)
        
        参数:
            rgb (\_color 字符串): rgb格式的颜色字符串
        
        返回值:
            字符串: BGR格式的字符串
        """
        if not self.obj:
            return ''
        result = self._call_function(115744, c_char_p, [c_long, c_char_p], self.obj, rgb_color.encode('gbk') if isinstance(rgb_color, str) else rgb_color)
        return result.decode('gbk') if result else ''

    def read_data(self, hwnd, addr, len):
        """
        ReadData
        
        读取指定地址的二进制数据
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            len (整形数): 二进制数据的长度
        
        返回值:
            字符串: 读取到的数值,以16进制表示的字符串 每个字节以空格相隔 比如"12 34 56 78 ab cd ef"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(111232, c_char_p, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, len)
        return result.decode('gbk') if result else ''

    def read_data_addr(self, hwnd, addr, len):
        """
        ReadDataAddr
        
        读取指定地址的二进制数据
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            len (整形数): 二进制数据的长度
        
        返回值:
            字符串: 读取到的数值,以16进制表示的字符串 每个字节以空格相隔 比如"12 34 56 78 ab cd ef"  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(123584, c_char_p, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, len)
        return result.decode('gbk') if result else ''

    def read_data_addr_to_bin(self, hwnd, addr, len):
        """
        ReadDataAddrToBin
        
        读取指定地址的二进制数据,只不过返回的是内存地址,而不是字符串.适合高级用户.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            len (整形数): 二进制数据的长度
        
        返回值:
            整形数: 读取到的数据指针. 返回0表示读取失败.  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0
        return self._call_function(111792, c_long, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, len)

    def read_data_to_bin(self, hwnd, addr, len):
        """
        ReadDataToBin
        
        读取指定地址的二进制数据,只不过返回的是内存地址,而不是字符串.适合高级用户.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            len (整形数): 二进制数据的长度
        
        返回值:
            整形数: 读取到的数据指针. 返回0表示读取失败.  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0
        return self._call_function(104480, c_long, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, len)

    def read_double(self, hwnd, addr):
        """
        ReadDouble
        
        读取指定地址的双精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
        
        返回值:
            双精度浮点数: 读取到的数值   如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0.0
        return self._call_function(110128, c_double, [c_long, c_long, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr)

    def read_double_addr(self, hwnd, addr):
        """
        ReadDoubleAddr
        
        读取指定地址的双精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
        
        返回值:
            双精度浮点数: 读取到的数值   如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0.0
        return self._call_function(113392, c_double, [c_long, c_long, c_longlong], self.obj, hwnd, addr)

    def read_file(self, file):
        """
        ReadFile
        
        从指定的文件读取内容.
        
        参数:
            file (字符串): 文件
        
        """
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
        """
        ReadFloat
        
        读取指定地址的单精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
        
        返回值:
            单精度浮点数: 读取到的数值   如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0.0
        return self._call_function(100976, c_float, [c_long, c_long, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr)

    def read_float_addr(self, hwnd, addr):
        """
        ReadFloatAddr
        
        读取指定地址的单精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
        
        返回值:
            单精度浮点数: 读取到的数值  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0.0
        return self._call_function(100816, c_float, [c_long, c_long, c_longlong], self.obj, hwnd, addr)

    def read_ini(self, section, key, file):
        """
        ReadIni
        
        从Ini中读取指定信息.
        
        参数:
            section (字符串): 小节名
            key (字符串): 变量名.
            file (字符串): ini文件名.
        
        """
        if not self.obj:
            return ''
        result = self._call_function(102912, c_char_p, [c_long, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file)
        return result.decode('gbk') if result else ''

    def read_ini_pwd(self, section, key, file, pwd):
        """
        ReadIniPwd
        
        从Ini中读取指定信息.可支持加密文件
        
        参数:
            section (字符串): 小节名
            key (字符串): 变量名.
            file (字符串): ini文件名.
            pwd (字符串): 密码
        
        """
        if not self.obj:
            return ''
        result = self._call_function(102064, c_char_p, [c_long, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)
        return result.decode('gbk') if result else ''

    def read_int(self, hwnd, addr, type):
        """
        ReadInt
        
        读取指定地址的整数数值，类型可以是8位，16位  32位 或者64位
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            type (整形数): 整数类型,取值如下
        
        返回值:
            长整形数: 读取到的数值  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0
        return self._call_function(112720, c_longlong, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type)

    def read_int_addr(self, hwnd, addr, type):
        """
        ReadIntAddr
        
        读取指定地址的整数数值，类型可以是8位，16位 32位 或者64位
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            type (整形数): 整数类型,取值如下
        
        返回值:
            长整形数: 读取到的数值  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return 0
        return self._call_function(99712, c_longlong, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, type)

    def read_string(self, hwnd, addr, type, len):
        """
        ReadString
        
        读取指定地址的字符串，可以是GBK字符串或者是Unicode字符串.(必须事先知道内存区的字符串编码方式)
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            type (整形数): 字符串类型,取值如下
            len (整形数): 需要读取的字节数目.如果为0，则自动判定字符串长度.
        
        返回值:
            字符串: 读取到的字符串  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(121472, c_char_p, [c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type, len)
        return result.decode('gbk') if result else ''

    def read_string_addr(self, hwnd, addr, type, len):
        """
        ReadStringAddr
        
        读取指定地址的字符串，可以是GBK字符串或者是Unicode字符串.(必须事先知道内存区的字符串编码方式)
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            type (整形数): 字符串类型,取值如下
            len (整形数): 需要读取的字节数目.如果为0，则自动判定字符串长度.
        
        返回值:
            字符串: 读取到的字符串  如果要想知道函数是否执行成功，请查看[GetLastError](#chmtopic280)函数.
        """
        if not self.obj:
            return ''
        result = self._call_function(118608, c_char_p, [c_long, c_long, c_longlong, c_long, c_long], self.obj, hwnd, addr, type, len)
        return result.decode('gbk') if result else ''

    def reg(self, code, ver):
        """
        Reg
        
        调用此函数来注册，从而使用插件的高级功能.推荐使用此函数.
        
        参数:
            reg (\_code 字符串): 注册码. (从大漠插件后台获取)
            ver (\_info 字符串): 版本附加信息. 可以在后台详细信息查看. 可以任意填写. 可留空. 长度不能超过32. 并且只能包含数字和字母以及小数点. 这个版本信息不是插件版本.
        
        返回值:
            整形数: -1 : 无法连接网络,(可能防火墙拦截,如果可以正常访问大漠插件网站，那就可以肯定是被防火墙拦截) -2 : 进程没有以管理员方式运行. (出现在win7 win8 vista 2008.建议关闭uac) 0 : 失败 (未知错误) 1 : 成功 2 : 余额不足 3 : 绑定了本机器，但是账户余额不足50元. 4 : 注册码错误 5 : 你的机器或者IP在黑名单列表中或者不在白名单列表中. 6 : 非法使用插件. 一般出现在定制插件时，使用了和绑定的用户名不同的注册码.  也有可能是系统的语言设置不是中文简体,也可能有这个错误. 7 : 你的帐号因为非法使用被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） 8 : ver\_info不在你设置的附加白名单中. 77： 机器码或者IP因为非法使用，而被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） `     `封禁是全局的，如果使用了别人的软件导致77，也一样会导致所有注册码均无法注册。解决办法是更换IP，更换MAC. 777： 同一个机器码注册次数超过了服务器限制,被暂时封禁. 请登录后台，插件今日详细消费记录里，相应的机器码是否有次数异常，并立刻优化解决.如果还有问题，可以联系我来解决. -8 : 版本附加信息长度超过了32 -9 : 版本附加信息里包含了非法字母. 空 : 这是不可能返回空的，如果出现空，那肯定是当前使用的版本不对,老的插件里没这个函数导致返回为空.最好参考文档中的标准写法,判断插件版本号.
        """
        if not self.obj:
            return 0
        return self._call_function(121344, c_long, [c_long, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver)

    def reg_ex(self, code, ver, ip):
        """
        RegEx
        
        调用此函数来注册，从而使用插件的高级功能. 可以根据指定的IP列表来注册. 新手不建议使用!
        
        参数:
            reg (\_code 字符串): 注册码. (从大漠插件后台获取)
            ver (\_info 字符串): 版本附加信息. 可以在后台详细信息查看.可留空. 长度不能超过32. 并且只能包含数字和字母以及小数点. 这个版本信息不是插件版本.
            ip (字符串): 插件注册的ip地址.可以用|来组合,依次对ip中的地址进行注册，直到成功. ip地址列表在VIP群中获取.从7.2111开始,这里也可以使用域名的方式。可以自己解析域名到我的IP.\ 比如"1.xxx.com|2.xxx.com"。1.xxx.com和2.xxx.com是自己的域名,解析到我的IP即可.
        
        返回值:
            整形数: -1 : 无法连接网络,(可能防火墙拦截,如果可以正常访问大漠插件网站，那就可以肯定是被防火墙拦截) -2 : 进程没有以管理员方式运行. (出现在win7 win8 vista 2008.建议关闭uac) 0 : 失败 (未知错误) 1 : 成功 2 : 余额不足 3 : 绑定了本机器，但是账户余额不足50元. 4 : 注册码错误 5 : 你的机器或者IP在黑名单列表中或者不在白名单列表中. 6 : 非法使用插件. 一般出现在定制插件时，使用了和绑定的用户名不同的注册码.  也有可能是系统的语言设置不是中文简体,也可能有这个错误. 7 : 你的帐号因为非法使用被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） 8 : ver\_info不在你设置的附加白名单中. 77： 机器码或者IP因为非法使用，而被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） `     `封禁是全局的，如果使用了别人的软件导致77，也一样会导致所有注册码均无法注册。解决办法是更换IP，更换MAC. 777： 同一个机器码注册次数超过了服务器限制,被暂时封禁. 请登录后台，插件今日详细消费记录里，相应的机器码是否有次数异常，并立刻优化解决.如果还有问题，可以联系我来解决. -8 : 版本附加信息长度超过了32 -9 : 版本附加信息里包含了非法字母. -10 : 非法的参数ip 空 : 这是不可能返回空的，如果出现空，那肯定是当前使用的版本不对,老的插件里没这个函数导致返回为空.最好参考文档中的标准写法,判断插件版本号.
        """
        if not self.obj:
            return 0
        return self._call_function(98864, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver, ip.encode('gbk') if isinstance(ip, str) else ip)

    def reg_ex_no_mac(self, code, ver, ip):
        """
        RegExNoMac
        
        调用此函数来注册，从而使用插件的高级功能. 可以根据指定的IP列表来注册.新手不建议使用! 此函数同RegEx函数的不同在于,此函数用于注册的机器码是不带mac地址的.
        
        参数:
            reg (\_code 字符串): 注册码. (从大漠插件后台获取)
            ver (\_info 字符串): 版本附加信息. 可以在后台详细信息查看.可留空. 长度不能超过32. 并且只能包含数字和字母以及小数点. 这个版本信息不是插件版本.
            ip (字符串): 插件注册的ip地址.可以用|来组合,依次对ip中的地址进行注册，直到成功. ip地址列表在VIP群中获取. 从7.2111开始,这里也可以使用域名的方式。可以自己解析域名到我的IP.\ 比如"1.xxx.com|2.xxx.com"。1.xxx.com和2.xxx.com是自己的域名,解析到我的IP即可.
        
        返回值:
            整形数: -1 : 无法连接网络,(可能防火墙拦截,如果可以正常访问大漠插件网站，那就可以肯定是被防火墙拦截) -2 : 进程没有以管理员方式运行. (出现在win7 win8 vista 2008.建议关闭uac) 0 : 失败 (未知错误) 1 : 成功 2 : 余额不足 3 : 绑定了本机器，但是账户余额不足50元. 4 : 注册码错误 5 : 你的机器或者IP在黑名单列表中或者不在白名单列表中. 6 : 非法使用插件. 一般出现在定制插件时，使用了和绑定的用户名不同的注册码.  也有可能是系统的语言设置不是中文简体,也可能有这个错误. 7 : 你的帐号因为非法使用被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） 8 : ver\_info不在你设置的附加白名单中. 77： 机器码或者IP因为非法使用，而被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） `     `封禁是全局的，如果使用了别人的软件导致77，也一样会导致所有注册码均无法注册。解决办法是更换IP，更换MAC. 777： 同一个机器码注册次数超过了服务器限制,被暂时封禁. 请登录后台，插件今日详细消费记录里，相应的机器码是否有次数异常，并立刻优化解决.如果还有问题，可以联系我来解决. -8 : 版本附加信息长度超过了32 -9 : 版本附加信息里包含了非法字母. -10 : 非法的参数ip 空 : 这是不可能返回空的，如果出现空，那肯定是当前使用的版本不对,老的插件里没这个函数导致返回为空.最好参考文档中的标准写法,判断插件版本号.
        """
        if not self.obj:
            return 0
        return self._call_function(107552, c_long, [c_long, c_char_p, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver, ip.encode('gbk') if isinstance(ip, str) else ip)

    def reg_no_mac(self, code, ver):
        """
        RegNoMac
        
        调用此函数来注册，从而使用插件的高级功能.推荐使用此函数. 新手不建议使用! 此函数同Reg函数的不同在于,此函数用于注册的机器码是不带mac地址的.
        
        参数:
            reg (\_code 字符串): 注册码. (从大漠插件后台获取)
            ver (\_info 字符串): 版本附加信息. 可以在后台详细信息查看. 可以任意填写. 可留空. 长度不能超过32. 并且只能包含数字和字母以及小数点. 这个版本信息不是插件版本.
        
        返回值:
            整形数: -1 : 无法连接网络,(可能防火墙拦截,如果可以正常访问大漠插件网站，那就可以肯定是被防火墙拦截) -2 : 进程没有以管理员方式运行. (出现在win7 win8 vista 2008.建议关闭uac) 0 : 失败 (未知错误) 1 : 成功 2 : 余额不足 3 : 绑定了本机器，但是账户余额不足50元. 4 : 注册码错误 5 : 你的机器或者IP在黑名单列表中或者不在白名单列表中. 6 : 非法使用插件. 一般出现在定制插件时，使用了和绑定的用户名不同的注册码.  也有可能是系统的语言设置不是中文简体,也可能有这个错误. 7 : 你的帐号因为非法使用被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） 8 : ver\_info不在你设置的附加白名单中. 77： 机器码或者IP因为非法使用，而被封禁. （如果是在虚拟机中使用插件，必须使用Reg或者RegEx，不能使用RegNoMac或者RegExNoMac,否则可能会造成封号，或者封禁机器） `     `封禁是全局的，如果使用了别人的软件导致77，也一样会导致所有注册码均无法注册。解决办法是更换IP，更换MAC. 777： 同一个机器码注册次数超过了服务器限制,被暂时封禁. 请登录后台，插件今日详细消费记录里，相应的机器码是否有次数异常，并立刻优化解决.如果还有问题，可以联系我来解决. -8 : 版本附加信息长度超过了32 -9 : 版本附加信息里包含了非法字母. 空 : 这是不可能返回空的，如果出现空，那肯定是当前使用的版本不对,老的插件里没这个函数导致返回为空.最好参考文档中的标准写法,判断插件版本号.
        """
        if not self.obj:
            return 0
        return self._call_function(118960, c_long, [c_long, c_char_p, c_char_p], self.obj, code.encode('gbk') if isinstance(code, str) else code, ver.encode('gbk') if isinstance(ver, str) else ver)

    def release_ref(self):
        """
        ReleaseRef
        
        强制降低对象的引用计数。此接口为高级接口，一般使用在高级语言，比如E vc等.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(111072, c_long, [c_long], self.obj)

    def right_click(self):
        """
        RightClick
        
        按下鼠标右键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(101040, c_long, [c_long], self.obj)

    def right_down(self):
        """
        RightDown
        
        按住鼠标右键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(124576, c_long, [c_long], self.obj)

    def right_up(self):
        """
        RightUp
        
        弹起鼠标右键
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(111504, c_long, [c_long], self.obj)

    def run_app(self, path, mode):
        """
        RunApp
        
        运行指定的应用程序.
        
        参数:
            app (\_path 字符串): 指定的可执行程序全路径.
            mode (整形数): 取值如下
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(122832, c_long, [c_long, c_char_p, c_long], self.obj, path.encode('gbk') if isinstance(path, str) else path, mode)

    def save_dict(self, index, file):
        """
        SaveDict
        
        保存指定的字库到指定的文件中.
        
        参数:
            index (整形数): 字库索引序号 取值为0-99对应100个字库
            file (字符串): 文件名
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(115520, c_long, [c_long, c_long, c_char_p], self.obj, index, file.encode('gbk') if isinstance(file, str) else file)

    def screen_to_client(self, hwnd, x, y):
        """
        ScreenToClient
        
        把屏幕坐标转换为窗口坐标
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            x (变参指针): 屏幕X坐标
            y (变参指针): 屏幕Y坐标
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(111392, c_long, [c_long, c_long, POINTER(c_long), POINTER(c_long)], self.obj, hwnd, byref(x) if isinstance(x, c_long) else x, byref(y) if isinstance(y, c_long) else y)

    def select_directory(self):
        """
        SelectDirectory
        
        弹出选择文件夹对话框，并返回选择的文件夹.
        
        """
        if not self.obj:
            return ''
        result = self._call_function(116000, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def select_file(self):
        """
        SelectFile
        
        弹出选择文件对话框，并返回选择的文件.
        
        """
        if not self.obj:
            return ''
        result = self._call_function(118144, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def send_paste(self, hwnd):
        """
        SendPaste
        
        向指定窗口发送粘贴命令. 把剪贴板的内容发送到目标窗口.
        
        参数:
            hwnd (整形数): 指定的窗口句柄. 如果为0,则对当前激活的窗口发送.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(122944, c_long, [c_long, c_long], self.obj, hwnd)

    def send_string(self, hwnd, text):
        """
        SendString
        
        向指定窗口发送文本数据
        
        参数:
            hwnd (整形数): 指定的窗口句柄. 如果为0,则对当前激活的窗口发送.\ 
            text (字符串): 发送的文本数据
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(114832, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, text.encode('gbk') if isinstance(text, str) else text)

    def send_string2(self, hwnd, text):
        """
        SendString2
        
        向指定窗口发送文本数据
        
        参数:
            hwnd (整形数): 指定的窗口句柄. 如果为0,则对当前激活的窗口发送.\ 
            text (字符串): 发送的文本数据
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(99888, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, text.encode('gbk') if isinstance(text, str) else text)

    def send_string_ime(self, text):
        """
        SendStringIme
        
        向绑定的窗口发送文本数据.必须配合dx.public.input.ime属性.
        
        参数:
            text (字符串): 发送的文本数据
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(124000, c_long, [c_long, c_char_p], self.obj, text.encode('gbk') if isinstance(text, str) else text)

    def send_string_ime2(self, hwnd, text, mode):
        """
        SendStringIme2
        
        利用真实的输入法，对指定的窗口输入文字.
        
        参数:
            hwnd整形 (数): 窗口句柄
            text (字符串): 发送的文本数据
            mode整形数 (: 取值意义如下): \ 0 : 向hwnd的窗口输入文字(前提是必须先用模式200安装了输入法)\ 1 : 同模式0,如果由于保护无效，可以尝试此模式.(前提是必须先用模式200安装了输入法)\ 2 : 同模式0,如果由于保护无效，可以尝试此模式. (前提是必须先用模式200安装了输入法)\ 200 : 向系统中安装输入法,多次调用没问题. 全局只用安装一次.\ 300 : 卸载系统中的输入法. 全局只用卸载一次. 多次调用没关系.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(119520, c_long, [c_long, c_long, c_char_p, c_long], self.obj, hwnd, text.encode('gbk') if isinstance(text, str) else text, mode)

    def set_aero(self, enable):
        """
        SetAero
        
        设置开启或者关闭系统的Aero效果. (仅对WIN7及以上系统有效)
        
        参数:
            enable (整形数): 0 关闭\ 1 开启
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(102640, c_long, [c_long, c_long], self.obj, enable)

    def set_client_size(self, hwnd, width, height):
        """
        SetClientSize
        
        设置窗口客户区域的宽度和高度
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            width (整形数): 宽度
            height (整形数): 高度
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(104896, c_long, [c_long, c_long, c_long, c_long], self.obj, hwnd, width, height)

    def set_clipboard(self, data):
        """
        SetClipboard
        
        设置剪贴板的内容
        
        参数:
            value (字符串): 以字符串表示的剪贴板内容
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(104960, c_long, [c_long, c_char_p], self.obj, data.encode('gbk') if isinstance(data, str) else data)

    def set_col_gap_no_dict(self, col_gap):
        """
        SetColGapNoDict
        
        高级用户使用,在不使用字库进行词组识别前,可设定文字的列距,默认列距是1
        
        参数:
            col (\_gap 整形数): 文字列距
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102592, c_long, [c_long, c_long], self.obj, col_gap)

    def set_dict(self, index, dict_name):
        """
        SetDict
        
        设置字库文件
        
        参数:
            index (整形数): 字库的序号,取值为0-99,目前最多支持100个字库
            file (字符串): 字库文件名
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(121280, c_long, [c_long, c_long, c_char_p], self.obj, index, dict_name.encode('gbk') if isinstance(dict_name, str) else dict_name)

    def set_dict_mem(self, index, addr, size):
        """
        SetDictMem
        
        从内存中设置字库.
        
        参数:
            index (整形数): 字库的序号,取值为0-99,目前最多支持100个字库
            addr (整形数): 数据地址
            size (整形数): 字库长度
        
        """
        if not self.obj:
            return 0
        return self._call_function(104704, c_long, [c_long, c_long, c_long, c_long], self.obj, index, addr, size)

    def set_dict_pwd(self, pwd):
        """
        SetDictPwd
        
        设置字库的密码,在SetDict前调用,目前的设计是,所有字库通用一个密码.
        
        参数:
            pwd (字符串): 字库密码
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(104128, c_long, [c_long, c_char_p], self.obj, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def set_display_acceler(self, level):
        """
        SetDisplayAcceler
        
        设置当前系统的硬件加速级别.
        
        参数:
            level整形 (数): 取值范围为0-5. 0表示关闭硬件加速。5表示完全打开硬件加速.
        
        """
        if not self.obj:
            return 0
        return self._call_function(101088, c_long, [c_long, c_long], self.obj, level)

    def set_display_delay(self, t):
        """
        SetDisplayDelay
        
        设置dx截图最长等待时间。内部默认是3000毫秒. 一般用不到调整这个.
        
        参数:
            time (整形数): 等待时间，单位是毫秒。 注意这里不能设置的过小，否则可能会导致截图失败,从而导致图色函数和文字识别失败.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(122784, c_long, [c_long, c_long], self.obj, t)

    def set_display_input(self, mode):
        """
        SetDisplayInput
        
        设定图色的获取方式，默认是显示器或者后台窗口(具体参考BindWindow)
        
        参数:
            mode (字符串): 图色输入模式 取值有以下几种
            2 (\. "pic): file" 指定输入模式为指定的图片,如果使用了这个模式，则所有和图色相关的函数
            3 (\. "mem): addr,size" 指定输入模式为指定的图片,此图片在内存当中. addr为图像内存地址,size为图像内存大小.\ 如果使用了这个模式，则所有和图色相关的函数,均视为对此图片进行处理.\ 比如文字识别 查找图片 颜色 等等一切图色函数.
        
        返回值:
            整形数: 0: 失败
            1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(110944, c_long, [c_long, c_char_p], self.obj, mode.encode('gbk') if isinstance(mode, str) else mode)

    def set_display_refresh_delay(self, t):
        """
        SetDisplayRefreshDelay
        
        设置opengl图色模式的强制刷新窗口等待时间. 内置为400毫秒.
        
        参数:
            time (整形数): 等待时间，单位是毫秒。 这个值越小,强制刷新的越频繁，相应的窗口可能会导致闪烁.
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(111344, c_long, [c_long, c_long], self.obj, t)

    def set_enum_window_delay(self, delay):
        """
        SetEnumWindowDelay
        
        设置EnumWindow  EnumWindowByProcess  EnumWindowSuper FindWindow以及FindWindowEx的最长延时. 内部默认超时是10秒.
        
        参数:
            delay (整形数): 单位毫秒
        
        返回值:
            整形数: 0: 失败
            1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(114720, c_long, [c_long, c_long], self.obj, delay)

    def set_exact_ocr(self, exact_ocr):
        """
        SetExactOcr
        
        高级用户使用,在使用文字识别功能前，设定是否开启精准识别.
        
        参数:
            exact (\_ocr 整形数): 0 表示关闭精准识别
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(123280, c_long, [c_long, c_long], self.obj, exact_ocr)

    def set_exclude_region(self, type, info):
        """
        SetExcludeRegion
        
        设置图色,以及文字识别时,需要排除的区域.(支持所有图色接口,以及文字相关接口,但对单点取色,或者单点颜色比较的接口不支持)
        
        参数:
            mode (整形数): 模式,取值如下:\ 0: 添加排除区域\ 1: 设置排除区域的颜色,默认颜色是FF00FF(此接口的原理是把排除区域设置成此颜色,这样就可以让这块区域失效)\ 2: 清空排除区域
            info (字符串): 根据mode的取值来决定\ 当mode为0时,此参数指添加的区域,可以多个区域,用"|"相连. 格式为"x1,y1,x2,y2|....."\ 当mode为1时,此参数为排除区域的颜色,"RRGGBB"\ 当mode为2时,此参数无效
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(104832, c_long, [c_long, c_long, c_char_p], self.obj, type, info.encode('gbk') if isinstance(info, str) else info)

    def set_exit_thread(self, mode):
        """
        SetExitThread
        
        设置当前对象的退出线程标记，之后除了调用此接口的线程之外，调用此对象的任何接口的线程会被强制退出. 此接口为高级接口，一般用在高级语言,比如e vc等.
        
        参数:
            enable (整形数): 1和2都为开启标记,0为关闭标记。 1和2的区别是,1会解绑当前对象的绑定,2不会.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(101536, c_long, [c_long, c_long], self.obj, mode)

    def set_export_dict(self, index, dict_name):
        """SetExportDict - 偏移: 119392"""
        if not self.obj:
            return 0
        return self._call_function(119392, c_long, [c_long, c_long, c_char_p], self.obj, index, dict_name.encode('gbk') if isinstance(dict_name, str) else dict_name)

    def set_find_pic_multithread_count(self, count):
        """
        SetFindPicMultithreadCount
        
        当执行FindPicXXX系列接口时,当图片个数少于count时,使用单线程查找,否则使用多线程。 这个count默认是4.
        
        参数:
            count (整形数): 图片数量. 最小不能小于2. 因为1个图片必定是单线程. 这个值默认是4.如果你不更改的话.
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(106784, c_long, [c_long, c_long], self.obj, count)

    def set_find_pic_multithread_limit(self, limit):
        """
        SetFindPicMultithreadLimit
        
        当执行FindPicXXX系列接口时,当触发多线程查找条件时,设置开启的最大线程数量. 注意,不可以超过当前CPU核心数.
        
        参数:
            limit (整形数): 最大线程数,不能超过当前CPU核心数. 超过无效. 0表示无限制.
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(107616, c_long, [c_long, c_long], self.obj, limit)

    def set_input_dm(self, input_dm, rx, ry):
        """
        SetInputDm
        
        设置当前对象用于输入的对象. 结合图色对象和键鼠对象,用一个对象完成操作.
        
        参数:
            dm (\_id 整形数): 接口GetId的返回值
            rx (整形数): 两个对象绑定的窗口的左上角坐标的x偏移. 是用dm\_id对应的窗口的左上角x坐标减去当前窗口左上角坐标的x坐标. 一般是0
            ry (整形数): 两个对象绑定的窗口的左上角坐标的y偏移. 是用dm\_id对应的窗口的左上角y坐标减去当前窗口左上角坐标的y坐标. 一般是0
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(108656, c_long, [c_long, c_long, c_long, c_long], self.obj, input_dm, rx, ry)

    def set_keypad_delay(self, type, delay):
        """
        SetKeypadDelay
        
        设置按键时,键盘按下和弹起的时间间隔。高级用户使用。某些窗口可能需要调整这个参数才可以正常按键。
        
        参数:
            type (**字符串**): 键盘类型,取值有以下
            delay (整形数): 延时,单位是毫秒
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(110256, c_long, [c_long, c_char_p, c_long], self.obj, type.encode('gbk') if isinstance(type, str) else type, delay)

    def set_locale(self):
        """
        SetLocale
        
        设置当前系统的非UNICOD字符集. 会弹出一个字符集选择列表,用户自己选择到简体中文即可.
        
        """
        if not self.obj:
            return 0
        return self._call_function(100928, c_long, [c_long], self.obj)

    def set_memory_find_result_to_file(self, file):
        """
        SetMemoryFindResultToFile
        
        设置是否把所有内存查找接口的结果保存入指定文件.
        
        参数:
            file (**字符串**): 设置要保存的搜索结果文件名. 如果为空字符串表示取消此功能.
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(110704, c_long, [c_long, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file)

    def set_memory_hwnd_as_process_id(self, en):
        """
        SetMemoryHwndAsProcessId
        
        设置是否把所有内存接口函数中的窗口句柄当作进程ID,以支持直接以进程ID来使用内存接口.
        
        参数:
            en (**整形数**): 取值如下\ 0 : 关闭 1 : 开启
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(107984, c_long, [c_long, c_long], self.obj, en)

    def set_min_col_gap(self, col_gap):
        """
        SetMinColGap
        
        高级用户使用,在识别前,如果待识别区域有多行文字,可以设定列间距,默认的列间距是0, 如果根据情况设定,可以提高识别精度。一般不用设定。
        
        参数:
            min (\_col\_gap 整形数): 最小列间距
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(110560, c_long, [c_long, c_long], self.obj, col_gap)

    def set_min_row_gap(self, row_gap):
        """
        SetMinRowGap
        
        高级用户使用,在识别前,如果待识别区域有多行文字,可以设定行间距,默认的行间距是1, 如果根据情况设定,可以提高识别精度。一般不用设定。
        
        参数:
            min (\_row\_gap 整形数): 最小行间距
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(122144, c_long, [c_long, c_long], self.obj, row_gap)

    def set_mouse_delay(self, type, delay):
        """
        SetMouseDelay
        
        设置鼠标单击或者双击时,鼠标按下和弹起的时间间隔。高级用户使用。某些窗口可能需要调整这个参数才可以正常点击。
        
        参数:
            type (**字符串**): 鼠标类型,取值有以下
            delay (整形数): 延时,单位是毫秒
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(104592, c_long, [c_long, c_char_p, c_long], self.obj, type.encode('gbk') if isinstance(type, str) else type, delay)

    def set_mouse_speed(self, speed):
        """
        SetMouseSpeed
        
        设置系统鼠标的移动速度.  如图所示红色区域. 一共分为11个级别. 从1开始,11结束。此接口仅仅对前台鼠标有效. ![ref3]
        
        参数:
            speed (整形数): 鼠标移动速度, 最小1，最大11. 居中为6. 推荐设置为6
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(124800, c_long, [c_long, c_long], self.obj, speed)

    def set_param64_to_pointer(self):
        """
        SetParam64ToPointer
        
        这个接口是给E语言设计的. 因为E语言的BUG,导致无法对COM对象调用传入长整数参数(被强制截断成整数),特别设计此接口来兼容长整数的处理.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(99952, c_long, [c_long], self.obj)

    def set_path(self, path):
        """
        SetPath
        
        设置全局路径,设置了此路径后,所有接口调用中,相关的文件都相对于此路径. 比如图片,字库等.
        
        参数:
            path (字符串): 路径,可以是相对路径,也可以是绝对路径
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(123808, c_long, [c_long, c_char_p], self.obj, path.encode('gbk') if isinstance(path, str) else path)

    def set_pic_pwd(self, pwd):
        """
        SetPicPwd
        
        设置图片密码，如果图片本身没有加密，那么此设置不影响不加密的图片，一样正常使用.
        
        参数:
            pwd (字符串): 图片密码
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(123712, c_long, [c_long, c_char_p], self.obj, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def set_row_gap_no_dict(self, row_gap):
        """
        SetRowGapNoDict
        
        高级用户使用,在不使用字库进行词组识别前,可设定文字的行距,默认行距是1
        
        参数:
            row (\_gap 整形数): 文字行距
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(118256, c_long, [c_long, c_long], self.obj, row_gap)

    def set_screen(self, width, height, depth):
        """
        SetScreen
        
        设置系统的分辨率 系统色深
        
        参数:
            width (整形数): 屏幕宽度
            height (整形数): 屏幕高度
            depth (整形数): 系统色深
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(115168, c_long, [c_long, c_long, c_long, c_long], self.obj, width, height, depth)

    def set_show_asm_error_msg(self, show):
        """
        SetShowAsmErrorMsg
        
        设置是否弹出汇编功能中的错误提示,默认是打开.
        
        参数:
            show (整形数): 0表示不打开,1表示打开
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(101392, c_long, [c_long, c_long], self.obj, show)

    def set_show_error_msg(self, show):
        """
        SetShowErrorMsg
        
        设置是否弹出错误信息,默认是打开.
        
        参数:
            show (整形数): 0表示不打开,1表示打开
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(101856, c_long, [c_long, c_long], self.obj, show)

    def set_sim_mode(self, mode):
        """
        SetSimMode
        
        设置前台键鼠的模拟方式. \ 驱动功能支持的系统版本号为(win7/win8/win8.1/win10(10240)/win10(10586)/win10(14393)/win10(15063)/win10(16299)/win10(17134)/win10(17763)/win10(18362)/win10(18363)/win10(19041)/win10(19042) /win10(19043)/ win10(19045)/win11(22000)/win11(22621)/win11(22631)\ 不支持所有的预览版本,仅仅支持正式版本.  除了模式3,其他模式同时支持32位系统和64位系统.
        
        参数:
            mode (整形数): 0 正常模式(默认模式)\ 1 硬件模拟\ 2 硬件模拟2(ps2)（仅仅支持标准的3键鼠标，即左键，右键，中键，带滚轮的鼠标,2键和5键等扩展鼠标不支持）\ 3 硬件模拟3
        
        返回值:
            整形数: 0  : 插件没注册 -1 : 32位系统不支持 -2 : 驱动释放失败. -3 : 驱动加载失败.可能是权限不够. 参考UAC权限设置. 或者是被安全软件拦截.  `     `如果是WIN10 1607之后的系统，出现这个错误，可[参考这里](#chmtopic84) -10: 设置失败 -7 : 系统版本不支持. 可以用winver命令查看系统内部版本号. 驱动只支持正式发布的版本，所有预览版本都不支持. 1  : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(122896, c_long, [c_long, c_long], self.obj, mode)

    def set_uac(self, uac):
        """
        SetUAC
        
        设置当前系统的UAC(用户账户控制).
        
        参数:
            enable (整形数): 取值如下
        
        """
        if not self.obj:
            return 0
        return self._call_function(108608, c_long, [c_long, c_long], self.obj, uac)

    def set_window_size(self, hwnd, width, height):
        """
        SetWindowSize
        
        设置窗口的大小
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            width (整形数): 宽度
            height (整形数): 高度
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(98560, c_long, [c_long, c_long, c_long, c_long], self.obj, hwnd, width, height)

    def set_window_state(self, hwnd, flag):
        """
        SetWindowState
        
        设置窗口的状态
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            flag (整形数): 取值定义如下
            0 (): 关闭指定窗口
            1 (): 激活指定窗口
            2 (): 最小化指定窗口,但不激活
            3 (): 最小化指定窗口,并释放内存,但同时也会激活窗口.(释放内存可以考虑用[FreeProcessMemory](#chmtopic238)函数)
            4 (): 最大化指定窗口,同时激活窗口.
            5 (): 恢复指定窗口 ,但不激活
            6 (): 隐藏指定窗口
            7 (): 显示指定窗口
            8 (): 置顶指定窗口
            9 (): 取消置顶指定窗口
            10 (): 禁止指定窗口
            11 (): 取消禁止指定窗口
            12 (): 恢复并激活指定窗口
            13 (): 强制结束窗口所在进程.
            14 (): 闪烁指定的窗口
            15 (): 使指定的窗口获取输入焦点
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(102736, c_long, [c_long, c_long, c_long], self.obj, hwnd, flag)

    def set_window_text(self, hwnd, text):
        """
        SetWindowText
        
        设置窗口的标题
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            titie (字符串): 标题
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(113008, c_long, [c_long, c_long, c_char_p], self.obj, hwnd, text.encode('gbk') if isinstance(text, str) else text)

    def set_window_transparent(self, hwnd, v):
        """
        SetWindowTransparent
        
        设置窗口的透明度
        
        参数:
            hwnd (整形数): 指定的窗口句柄\ 
            trans (整形数): 透明度 取值(0-255) 越小透明度越大 0为完全透明(不可见) 255为完全显示(不透明)
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(112896, c_long, [c_long, c_long, c_long], self.obj, hwnd, v)

    def set_word_gap(self, word_gap):
        """
        SetWordGap
        
        高级用户使用,在识别词组前,可设定词组间的间隔,默认的词组间隔是5
        
        参数:
            word (\_gap 整形数): 单词间距
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(98624, c_long, [c_long, c_long], self.obj, word_gap)

    def set_word_gap_no_dict(self, word_gap):
        """
        SetWordGapNoDict
        
        高级用户使用,在不使用字库进行词组识别前,可设定词组间的间隔,默认的词组间隔是5
        
        参数:
            word (\_gap 整形数): 单词间距
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(123392, c_long, [c_long, c_long], self.obj, word_gap)

    def set_word_line_height(self, line_height):
        """
        SetWordLineHeight
        
        高级用户使用,在识别词组前,可设定文字的平均行高,默认的词组行高是10
        
        参数:
            line (\_height 整形数): 行高
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(101296, c_long, [c_long, c_long], self.obj, line_height)

    def set_word_line_height_no_dict(self, line_height):
        """
        SetWordLineHeightNoDict
        
        高级用户使用,在不使用字库进行词组识别前,可设定文字的平均行高,默认的词组行高是10
        
        参数:
            line (\_height 整形数): 行高
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(103792, c_long, [c_long, c_long], self.obj, line_height)

    def show_scr_msg(self, x1, y1, x2, y2, msg, color):
        """ShowScrMsg - 偏移: 112208"""
        if not self.obj:
            return 0
        return self._call_function(112208, c_long, [c_long, c_long, c_long, c_long, c_long, c_char_p, c_char_p], self.obj, x1, y1, x2, y2, msg.encode('gbk') if isinstance(msg, str) else msg, color.encode('gbk') if isinstance(color, str) else color)

    def show_task_bar_icon(self, hwnd, is_show):
        """
        ShowTaskBarIcon
        
        显示或者隐藏指定窗口在任务栏的图标.
        
        参数:
            hwnd (整形数): 指定的窗口句柄
            is (\_show 整形数): 0为隐藏,1为显示
        
        """
        if not self.obj:
            return 0
        return self._call_function(119328, c_long, [c_long, c_long, c_long], self.obj, hwnd, is_show)

    def sort_pos_distance(self, all_pos, type, x, y):
        """
        SortPosDistance
        
        根据部分Ex接口的返回值，然后对所有坐标根据对指定坐标的距离(或者指定X或者Y)进行从小到大的排序.
        
        参数:
            all (\_pos 字符串): 坐标描述串。 一般是FindStrEx,FindStrFastEx,FindStrWithFontEx, FindColorEx, FindMultiColorEx,和FindPicEx的返回值.
            type (整形数): 取值为0或者1
            x (整形数): 横坐标 
            y (整形数): 纵坐标\ 注意:如果x为65535并且y为0时，那么排序的结果是仅仅对x坐标进行排序,如果y为65535并且x为0时，那么排序的结果是仅仅对y坐标进行排序.
        
        """
        if not self.obj:
            return ''
        result = self._call_function(117120, c_char_p, [c_long, c_char_p, c_long, c_long, c_long], self.obj, all_pos.encode('gbk') if isinstance(all_pos, str) else all_pos, type, x, y)
        return result.decode('gbk') if result else ''

    def speed_normal_graphic(self, en):
        """
        SpeedNormalGraphic
        
        设置是否对前台图色进行加速. (默认是关闭). (对于不绑定，或者绑定图色为normal生效)( 仅对WIN8以上系统有效)
        
        参数:
            enable (整形数): \ 0 : 关闭\ 1 : 打开
        
        返回值:
            整形数: 0: 失败
            1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(101184, c_long, [c_long, c_long], self.obj, en)

    def stop(self, id):
        """
        Stop
        
        停止指定的音乐.
        
        参数:
            id (整形数): Play返回的播放id.
        
        返回值:
            整形数: 0 : 失败 1 : 成功.
        """
        if not self.obj:
            return 0
        return self._call_function(100880, c_long, [c_long, c_long], self.obj, id)

    def string_to_data(self, string_value, type):
        """
        StringToData
        
        把字符串转换成二进制形式.
        
        参数:
            value (**字符串**): 需要转化的字符串
            type (**整形数**): 取值如下:\ 0: 返回Ascii表达的字符串\ 1: 返回Unicode表达的字符串
        
        返回值:
            字符串: 字符串形式表达的二进制数据. 可以用于WriteData FindData FindDataEx等接口.
        """
        if not self.obj:
            return ''
        result = self._call_function(114768, c_char_p, [c_long, c_char_p, c_long], self.obj, string_value.encode('gbk') if isinstance(string_value, str) else string_value, type)
        return result.decode('gbk') if result else ''

    def switch_bind_window(self, hwnd):
        """
        SwitchBindWindow
        
        在不解绑的情况下,切换绑定窗口.(必须是同进程窗口)
        
        参数:
            hwnd (整形数): 需要切换过去的窗口句柄
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(109920, c_long, [c_long, c_long], self.obj, hwnd)

    def terminate_process(self, pid):
        """
        TerminateProcess
        
        根据指定的PID，强制结束进程.
        
        参数:
            pid (**整形数**): 进程ID.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(112032, c_long, [c_long, c_long], self.obj, pid)

    def terminate_process_tree(self, pid):
        """
        TerminateProcessTree
        
        根据指定的PID，强制结束进程以及此进程创建的所有子进程.
        
        参数:
            pid (**整形数**): 进程ID.
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(114240, c_long, [c_long, c_long], self.obj, pid)

    def un_bind_window(self):
        """
        UnBindWindow
        
        解除绑定窗口,并释放系统资源.一般在OnScriptExit调用
        
        返回值:
            整形数: 0: 失败 1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(101904, c_long, [c_long], self.obj)

    def un_load_driver(self):
        """
        UnLoadDriver
        
        卸载插件相关的所有驱动. 仅对64位系统的驱动生效.
        
        """
        if not self.obj:
            return 0
        return self._call_function(105696, c_long, [c_long], self.obj)

    def use_dict(self, index):
        """
        UseDict
        
        表示使用哪个字库文件进行识别(index范围:0-99) 设置之后，永久生效，除非再次设定
        
        参数:
            index (整形数): 字库编号(0-99)
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(104656, c_long, [c_long, c_long], self.obj, index)

    def ver(self):
        """
        Ver
        
        返回当前插件版本号
        
        返回值:
            字符串: 当前插件的版本描述字符串
        """
        if not self.obj:
            return ''
        result = self._call_function(100320, c_char_p, [c_long], self.obj)
        return result.decode('gbk') if result else ''

    def virtual_alloc_ex(self, hwnd, addr, size, type):
        """
        VirtualAllocEx
        
        在指定的窗口所在进程分配一段内存.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (长整形数): 预期的分配地址。 如果是0表示自动分配，否则就尝试在此地址上分配内存.
            size (**整形数**): 需要分配的内存大小.
            type (**整形数**): 需要分配的内存类型，取值如下:\ 0 : 可读可写可执行\ 1 : 可读可执行，不可写\ 2 : 可读可写,不可执行
        
        返回值:
            长整形数: 分配的内存地址，如果是0表示分配失败.
        """
        if not self.obj:
            return 0
        return self._call_function(99104, c_longlong, [c_long, c_long, c_longlong, c_long, c_long], self.obj, hwnd, addr, size, type)

    def virtual_free_ex(self, hwnd, addr):
        """
        VirtualFreeEx
        
        释放用VirtualAllocEx分配的内存.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): VirtualAllocEx返回的地址
        
        返回值:
            整形数: 0 : 失败 1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(105120, c_long, [c_long, c_long, c_longlong], self.obj, hwnd, addr)

    def virtual_protect_ex(self, hwnd, addr, size, type, old_protect):
        """
        VirtualProtectEx
        
        修改指定的窗口所在进程的地址的读写属性,修改为可读可写可执行.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (长整形数): 需要修改的地址
            size (**整形数**): 需要修改的地址大小.
            type (**整形数**): 修改的地址读写属性类型，取值如下:\ 0 : 可读可写可执行,此时old\_protect参数无效\ 1 : 修改为old\_protect指定的读写属性
            old (\_protect**整形数**): 指定的读写属性
        
        返回值:
            整形数: 0 : 失败 1 : 修改之前的读写属性
        """
        if not self.obj:
            return 0
        return self._call_function(108912, c_long, [c_long, c_long, c_longlong, c_long, c_long, c_long], self.obj, hwnd, addr, size, type, old_protect)

    def virtual_query_ex(self, hwnd, addr, pmbi):
        """
        VirtualQueryEx
        
        获取指定窗口，指定地址的内存属性.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (长整形数): 需要查询的地址
            pmbi (**整形数**): 这是一个地址,指向的内容是MEMORY\_BASIC\_INFORMATION32或者MEMORY\_BASIC\_INFORMATION64.\ 取决于要查询的进程是32位还是64位. 这个地址可以为0,忽略这个参数.\ 下面是这2个结构体在vc下的定义:
        
        返回值:
            字符串: 查询的结果以字符串形式.  内容是"BaseAddress,AllocationBase,AllocationProtect,RegionSize,State,Protect,Type" 数值都是10进制表达.
        """
        if not self.obj:
            return ''
        result = self._call_function(101632, c_char_p, [c_long, c_long, c_longlong, c_long], self.obj, hwnd, addr, pmbi)
        return result.decode('gbk') if result else ''

    def wait_key(self, key_code, time_out):
        """
        WaitKey
        
        等待指定的按键按下 (前台,不是后台)
        
        参数:
            vk (\_code 整形数): 虚拟按键码,当此值为0，表示等待任意按键。 鼠标左键是1,鼠标右键时2,鼠标中键是4.
            time (\_out 整形数): 等待多久,单位毫秒. 如果是0，表示一直等待
        
        返回值:
            整形数: 0:超时 1:指定的按键按下 (当vk\_code不为0时) 按下的按键码:(当vk\_code为0时)
        """
        if not self.obj:
            return 0
        return self._call_function(114528, c_long, [c_long, c_long, c_long], self.obj, key_code, time_out)

    def wheel_down(self):
        """
        WheelDown
        
        滚轮向下滚
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(112848, c_long, [c_long], self.obj)

    def wheel_up(self):
        """
        WheelUp
        
        滚轮向上滚
        
        返回值:
            整形数: 0:失败 1:成功
        """
        if not self.obj:
            return 0
        return self._call_function(102688, c_long, [c_long], self.obj)

    def write_data(self, hwnd, addr, data):
        """
        WriteData
        
        对指定地址写入二进制数据
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            data (字符串): 二进制数据，以字符串形式描述，比如"12 34 56 78 90 ab cd"
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(123040, c_long, [c_long, c_long, c_char_p, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, data.encode('gbk') if isinstance(data, str) else data)

    def write_data_addr(self, hwnd, addr, data):
        """
        WriteDataAddr
        
        对指定地址写入二进制数据
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            data (字符串): 二进制数据，以字符串形式描述，比如"12 34 56 78 90 ab cd"
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(105744, c_long, [c_long, c_long, c_longlong, c_char_p], self.obj, hwnd, addr, data.encode('gbk') if isinstance(data, str) else data)

    def write_data_addr_from_bin(self, hwnd, addr, data, len):
        """
        WriteDataAddrFromBin
        
        对指定地址写入二进制数据,只不过直接从数据指针获取数据写入,不通过字符串. 适合高级用户.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            data (整形数): 数据指针
            len (整形数): 数据长度
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(121120, c_long, [c_long, c_long, c_longlong, c_long, c_long], self.obj, hwnd, addr, data, len)

    def write_data_from_bin(self, hwnd, addr, data, len):
        """
        WriteDataFromBin
        
        对指定地址写入二进制数据,只不过直接从数据指针获取数据写入,不通过字符串. 适合高级用户.
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            data (整形数): 数据指针
            len (整形数): 数据长度
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(118304, c_long, [c_long, c_long, c_char_p, c_long, c_long], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, data, len)

    def write_double(self, hwnd, addr, double_value):
        """
        WriteDouble
        
        对指定地址写入双精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            v (双精度浮点数): 双精度浮点数
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(116048, c_long, [c_long, c_long, c_char_p, c_double], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, double_value)

    def write_double_addr(self, hwnd, addr, double_value):
        """
        WriteDoubleAddr
        
        对指定地址写入双精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            v (双精度浮点数): 双精度浮点数
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(115232, c_long, [c_long, c_long, c_longlong, c_double], self.obj, hwnd, addr, double_value)

    def write_file(self, file, content):
        """
        WriteFile
        
        向指定文件追加字符串.
        
        参数:
            file (字符串): 文件
            content (字符串): 写入的字符串.
        
        """
        if not self.obj:
            return 0
        return self._call_function(105536, c_long, [c_long, c_char_p, c_char_p], self.obj, file.encode('gbk') if isinstance(file, str) else file, content.encode('gbk') if isinstance(content, str) else content)

    def write_float(self, hwnd, addr, float_value):
        """
        WriteFloat
        
        对指定地址写入单精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            v (单精度浮点数): 单精度浮点数
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(111920, c_long, [c_long, c_long, c_char_p, c_float], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, float_value)

    def write_float_addr(self, hwnd, addr, float_value):
        """
        WriteFloatAddr
        
        对指定地址写入单精度浮点数
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            v (单精度浮点数): 单精度浮点数
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(117312, c_long, [c_long, c_long, c_longlong, c_float], self.obj, hwnd, addr, float_value)

    def write_ini(self, section, key, v, file):
        """
        WriteIni
        
        向指定的Ini写入信息.
        
        参数:
            section (字符串): 小节名
            key (字符串): 变量名.
            value (字符串): 变量内容
            file (字符串): ini文件名.
        
        """
        if not self.obj:
            return 0
        return self._call_function(101232, c_long, [c_long, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, v.encode('gbk') if isinstance(v, str) else v, file.encode('gbk') if isinstance(file, str) else file)

    def write_ini_pwd(self, section, key, v, file, pwd):
        """
        WriteIniPwd
        
        向指定的Ini写入信息.支持加密文件
        
        参数:
            section (字符串): 小节名
            key (字符串): 变量名.
            value (字符串): 变量内容
            file (字符串): ini文件名.
            pwd (字符串): 密码.
        
        """
        if not self.obj:
            return 0
        return self._call_function(115872, c_long, [c_long, c_char_p, c_char_p, c_char_p, c_char_p, c_char_p], self.obj, section.encode('gbk') if isinstance(section, str) else section, key.encode('gbk') if isinstance(key, str) else key, v.encode('gbk') if isinstance(v, str) else v, file.encode('gbk') if isinstance(file, str) else file, pwd.encode('gbk') if isinstance(pwd, str) else pwd)

    def write_int(self, hwnd, addr, type, v):
        """
        WriteInt
        
        对指定地址写入整数数值，类型可以是8位，16位 32位 或者64位
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            type (整形数): 整数类型,取值如下
            v (长整形数): 整形数值
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(112416, c_long, [c_long, c_long, c_char_p, c_long, c_longlong], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type, v)

    def write_int_addr(self, hwnd, addr, type, v):
        """
        WriteIntAddr
        
        对指定地址写入整数数值，类型可以是8位，16位 32位 或者64位
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            type (整形数): 整数类型,取值如下
            v (长整形数): 整形数值
        
        返回值:
            整形数: 0 : 失败
            1 : 成功
        """
        if not self.obj:
            return 0
        return self._call_function(100240, c_long, [c_long, c_long, c_longlong, c_long, c_longlong], self.obj, hwnd, addr, type, v)

    def write_string(self, hwnd, addr, type, v):
        """
        WriteString
        
        对指定地址写入字符串，可以是Ascii字符串或者是Unicode字符串
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr (字符串): 用字符串来描述地址，类似于CE的地址描述，数值必须是16进制,里面可以用[ ] + -这些符号来描述一个地址。+表示地址加，-表示地址减\ 模块名必须用<>符号来圈起来
            type (整形数): 字符串类型,取值如下
            v (字符串): 字符串
        
        返回值:
            整形数: 0: 失败
            1: 成功
        """
        if not self.obj:
            return 0
        return self._call_function(115936, c_long, [c_long, c_long, c_char_p, c_long, c_char_p], self.obj, hwnd, addr.encode('gbk') if isinstance(addr, str) else addr, type, v.encode('gbk') if isinstance(v, str) else v)

    def write_string_addr(self, hwnd, addr, type, v):
        """
        WriteStringAddr
        
        对指定地址写入字符串，可以是Ascii字符串或者是Unicode字符串
        
        参数:
            hwnd (**整形数**): 窗口句柄或者进程ID. 默认是窗口句柄. 如果要指定为进程ID,需要调用[SetMemoryHwndAsProcessId](#chmtopic457).
            addr长整形 (数): 地址
            type (整形数): 字符串类型,取值如下
            v (字符串): 字符串
        
        返回值:
            整形数: 0: 失败
            1: 成功
        """
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

