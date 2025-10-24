"""
大漠插件32位DLL服务端
用于64位Python通过进程间通信调用32位DLL
"""
import os
import socket
import pickle
import struct
import sys
import traceback
from ctypes import windll, CDLL, c_long, c_char_p, c_double, c_float, c_longlong, POINTER, byref, create_string_buffer, CFUNCTYPE


class DmSoftServer:
    """32位大漠DLL服务端"""
    
    def __init__(self):
        self.obj = None
        self.dm_dll = None
        self.dm_handle = None
        self.dm_dll_path = "xd47243.dll"
        self.crack_dll_path = "Go.dll"
        self.initialized = False
        
    def initialize(self):
        """初始化大漠插件"""
        try:
            if not os.path.exists(self.dm_dll_path):
                return {"success": False, "error": f"DLL 文件不存在: {self.dm_dll_path}"}
            
            self.dm_dll = CDLL(self.dm_dll_path)
            self.dm_handle = windll.kernel32.LoadLibraryA(self.dm_dll_path.encode())
            
            if not self.dm_handle:
                return {"success": False, "error": f"加载大漠插件失败: {self.dm_dll_path}"}
            
            # 加载破解 DLL
            if not self._load_crack_dll(self.crack_dll_path, self.dm_handle):
                return {"success": False, "error": f"加载破解 DLL 失败: {self.crack_dll_path}"}
            
            # 创建大漠对象
            self.obj = self._call_function(98304, c_long, [])
            if not self.obj:
                return {"success": False, "error": "创建大漠对象失败"}
            
            # 注册大漠插件
            ret = self._call_function(121344, c_long, [c_long, c_char_p, c_char_p], 
                                     self.obj, b"", b"")
            if ret == 1:
                self.initialized = True
                return {"success": True}
            else:
                return {"success": False, "error": f"大漠注册失败，返回值: {ret}"}
                
        except Exception as e:
            return {"success": False, "error": f"初始化失败: {str(e)}\n{traceback.format_exc()}"}
    
    def _call_function(self, offset, restype, argtypes, *args):
        """调用 DLL 指定偏移地址的函数"""
        func_addr = self.dm_handle + offset
        func_type = CFUNCTYPE(restype, *argtypes)
        func = func_type(func_addr)
        return func(*args)
    
    def _load_crack_dll(self, crack_dll_path, dm_handle):
        """加载破解 DLL 并调用 Go 函数"""
        try:
            if not os.path.exists(crack_dll_path):
                return False
            
            crack_dll = CDLL(crack_dll_path)
            if not crack_dll:
                return False
            
            go_func = crack_dll.Go
            go_func.argtypes = [c_long]
            go_func.restype = None
            go_func(dm_handle)
            
            return True
        except Exception as e:
            print(f"加载破解 DLL 异常: {str(e)}")
            return False
    
    def call_method(self, method_name, offset, restype_str, argtypes_str, args):
        """调用大漠方法"""
        try:
            if not self.initialized:
                return {"success": False, "error": "大漠插件未初始化"}
            
            # 将字符串转换回ctypes类型
            restype = self._str_to_ctype(restype_str)
            argtypes = [self._str_to_ctype(t) for t in argtypes_str]
            
            # 准备参数
            prepared_args = [self.obj]
            for arg, argtype in zip(args, argtypes[1:]):  # 跳过第一个obj参数
                if argtype == c_char_p and isinstance(arg, str):
                    prepared_args.append(arg.encode('gbk'))
                else:
                    prepared_args.append(arg)
            
            # 调用函数
            result = self._call_function(offset, restype, argtypes, *prepared_args)
            
            # 返回原始结果，不做decode处理，让客户端统一处理
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": f"调用方法失败: {str(e)}\n{traceback.format_exc()}"}
    
    def _str_to_ctype(self, type_str):
        """将字符串转换为ctypes类型"""
        type_map = {
            'c_long': c_long,
            'c_char_p': c_char_p,
            'c_double': c_double,
            'c_float': c_float,
            'c_longlong': c_longlong
        }
        return type_map.get(type_str, c_long)


def send_response(conn, data):
    """发送响应数据"""
    serialized = pickle.dumps(data)
    length = len(serialized)
    conn.sendall(struct.pack('!I', length))
    conn.sendall(serialized)


def recv_request(conn):
    """接收请求数据"""
    length_data = conn.recv(4)
    if not length_data:
        return None
    length = struct.unpack('!I', length_data)[0]
    data = b''
    while len(data) < length:
        chunk = conn.recv(min(length - len(data), 4096))
        if not chunk:
            return None
        data += chunk
    return pickle.loads(data)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python dmsoft_server.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    
    # 检查是否为32位Python
    is_64bit = struct.calcsize("P") * 8 == 64
    print(f"Python位数: {64 if is_64bit else 32}位")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    
    if is_64bit:
        print("错误: 此服务端必须在32位Python中运行")
        print("请使用32位Python执行此脚本")
        sys.exit(1)
    
    server = DmSoftServer()
    
    # 创建socket服务器
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', port))
    sock.listen(1)
    
    print(f"32位DLL服务端已启动，监听端口: {port}")
    print("等待客户端连接...")
    
    try:
        conn, addr = sock.accept()
        print(f"客户端已连接: {addr}")
        
        while True:
            try:
                request = recv_request(conn)
                if not request:
                    break
                
                cmd = request.get('cmd')
                
                if cmd == 'initialize':
                    response = server.initialize()
                    send_response(conn, response)
                    
                elif cmd == 'call_method':
                    response = server.call_method(
                        request['method_name'],
                        request['offset'],
                        request['restype'],
                        request['argtypes'],
                        request['args']
                    )
                    send_response(conn, response)
                    
                elif cmd == 'shutdown':
                    send_response(conn, {"success": True})
                    break
                    
                else:
                    send_response(conn, {"success": False, "error": f"未知命令: {cmd}"})
                    
            except Exception as e:
                print(f"处理请求异常: {str(e)}")
                traceback.print_exc()
                try:
                    send_response(conn, {"success": False, "error": str(e)})
                except:
                    break
        
    finally:
        sock.close()
        print("服务端已关闭")


if __name__ == "__main__":
    main()

