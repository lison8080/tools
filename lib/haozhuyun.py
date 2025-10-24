"""
豪猪云接码平台API封装
官方文档: https://api.haozhuyun.com
更新时间: 2025-10-18
"""

import requests
import time
from typing import Optional, Dict, Any


class HaoZhuYunAPI:
    """豪猪云接码平台API封装类"""
    
    def __init__(self,):
        """
        初始化接码平台API
        
        Args:
            username: API账号
            password: API密码
            server: 服务器地址，默认 api.haozhuyun.com
                   可选: api.haozhuma.com
        """
        self.username = "234d1a0e749f6382e117e8671fc2e9903705920d5b3773276d43958513acaf83",
        self.password = "234d1a0e749f6382df3c5309b7d0a5a00b37f9217841c9c2adcb644eb7bcbeb6",
        self.server   = "api.haozhuyun.com"
        self.token = None
        self.base_url = f"https://{self.server}/sms/"
        
    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送HTTP请求的内部方法
        
        Args:
            params: 请求参数字典
            
        Returns:
            响应JSON数据
        """
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "code": "-1",
                "msg": f"请求失败: {str(e)}"
            }
        except Exception as e:
            return {
                "code": "-1",
                "msg": f"未知错误: {str(e)}"
            }
    
    def login(self) -> Dict[str, Any]:
        """
        登录获取token令牌
        注意: token为固定值，只需登录一次获取后即可，不要每次都调用
        
        Returns:
            {
                "code": "0",
                "msg": "success",
                "token": "2f05a475cc82f05a4cc82f05a475cc8"
            }
        """
        params = {
            "api": "login",
            "user": self.username,
            "pass": self.password
        }
        
        result = self._request(params)
        
        # 如果登录成功，保存token
        if result.get("code") == 0 or result.get("code") == "0":
            self.token = result.get("token")
            print(f"✓ 登录成功，Token: {self.token}")
        else:
            print(f"✗ 登录失败: {result.get('msg')}")
            
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取本账号信息（余额、最大区号数量）
        
        Returns:
            {
                "code": "0",
                "msg": "success",
                "money": "36.00",
                "num": 50
            }
        """
        if not self.token:
            return {"code": "-1", "msg": "请先登录获取token"}
        
        params = {
            "api": "getSummary",
            "token": self.token
        }
        
        return self._request(params)
    
    def get_phone(self, 
                  sid: int,
                  isp: Optional[int] = None,
                  province: Optional[str] = None,
                  ascription: Optional[int] = None,
                  paragraph: Optional[str] = None,
                  exclude: Optional[str] = None,
                  uid: Optional[str] = None,
                  author: Optional[str] = None) -> Dict[str, Any]:
        """
        获取手机号码
        
        Args:
            sid: 项目ID（必填）
            isp: 运营商，1=中国移动（可选）
            province: 号码省份，如 44=广东（可选）
            ascription: 号码类型，1=只取虚拟，2=只取实卡（可选）
            paragraph: 只取号段，多个用|连接，如 "1380|1580"（可选）
            exclude: 排除号段，多个用|连接（可选）
            uid: 只取该对接码（可选）
            author: 开发者账号，获取消费分成50%（可选）
            
        Returns:
            {
                "code": "0",
                "msg": "成功",
                "sid": "1000",
                "shop_name": "淘宝网",
                "country_name": "cn",
                "country_code": "cn",
                "country_qu": "+86",
                "uid": null,
                "phone": "手机号",
                "sp": "移动",
                "phone_gsd": "广东"
            }
        """
        if not self.token:
            return {"code": "-1", "msg": "请先登录获取token"}
        
        params = {
            "api": "getPhone",
            "token": self.token,
            "sid": sid
        }
        
        # 添加可选参数
        if isp is not None:
            params["isp"] = isp
        if province is not None:
            params["Province"] = province
        if ascription is not None:
            params["ascription"] = ascription
        if paragraph is not None:
            params["paragraph"] = paragraph
        if exclude is not None:
            params["exclude"] = exclude
        if uid is not None:
            params["uid"] = uid
        if author is not None:
            params["author"] = author
            
        return self._request(params)
    
    def specify_phone(self, 
                      sid: int, 
                      phone: str,
                      author: Optional[str] = None) -> Dict[str, Any]:
        """
        指定号码（再次使用某个号码）
        使用场景: 当某个号码需要再次接码，需要调用该接口进行占用，然后请求读取短信接口
        
        Args:
            sid: 项目ID
            phone: 号码
            author: 开发者账号（可选）
            
        Returns:
            {
                "code": "0",
                "msg": "成功",
                "sid": "22563",
                "country_name": "中国",
                "country_code": "cn",
                "country_qu": "+86",
                "phone": "132548966",
                "sp": "联通",
                "phone_gsd": "上海 上海"
            }
        """
        if not self.token:
            return {"code": "-1", "msg": "请先登录获取token"}
        
        params = {
            "api": "getPhone",
            "token": self.token,
            "sid": sid,
            "phone": phone
        }
        
        if author is not None:
            params["author"] = author
            
        return self._request(params)
    
    def get_message(self, sid: int, phone: str) -> Dict[str, Any]:
        """
        获取验证码
        建议每15秒查询一次
        
        Args:
            sid: 项目ID
            phone: 号码
            
        Returns:
            {
                "code": "0",
                "msg": "成功",
                "sms": "【游戏】您正在申请手机注册，验证码为：5184，1440分钟内有效！",
                "yzm": "123456"
            }
        """
        if not self.token:
            return {"code": "-1", "msg": "请先登录获取token"}
        
        params = {
            "api": "getMessage",
            "token": self.token,
            "sid": sid,
            "phone": phone
        }
        
        return self._request(params)
    
    def cancel_recv(self, sid: int, phone: str) -> Dict[str, Any]:
        """
        释放指定手机号
        不来码或者号码是老号可以调用此接口进行释放
        注意: 下次获取号码还会出来，如果不想号码再分配给你请调用拉黑接口
        
        Args:
            sid: 项目ID
            phone: 号码
            
        Returns:
            {
                "code": "0",
                "data": "null",
                "msg": "释放成功"
            }
        """
        if not self.token:
            return {"code": "-1", "msg": "请先登录获取token"}
        
        params = {
            "api": "cancelRecv",
            "token": self.token,
            "sid": sid,
            "phone": phone
        }
        
        return self._request(params)
    
    def cancel_all_recv(self) -> Dict[str, Any]:
        """
        释放全部手机号
        
        Returns:
            {
                "code": "200",
                "data": "null",
                "msg": "success"
            }
        """
        if not self.token:
            return {"code": "-1", "msg": "请先登录获取token"}
        
        params = {
            "api": "cancelAllRecv",
            "token": self.token
        }
        
        return self._request(params)
    
    def add_blacklist(self, sid: int, phone: str) -> Dict[str, Any]:
        """
        拉黑指定手机号
        如果这个号码不符合使用要求或是不来码，不想这个号码再分配出来，请调用本接口拉黑
        
        Args:
            sid: 项目ID
            phone: 号码
            
        Returns:
            {
                "code": "0",
                "data": "null",
                "msg": "success"
            }
        """
        if not self.token:
            return {"code": "-1", "msg": "请先登录获取token"}
        
        params = {
            "api": "addBlacklist",
            "token": self.token,
            "sid": sid,
            "phone": phone
        }
        
        return self._request(params)
    
    def wait_for_message(self, 
                        sid: int, 
                        phone: str,
                        max_wait_time: int = 180,
                        check_interval: int = 15) -> Dict[str, Any]:
        """
        等待接收验证码（自动轮询）
        
        Args:
            sid: 项目ID
            phone: 号码
            max_wait_time: 最大等待时间（秒），默认180秒（3分钟）
            check_interval: 检查间隔（秒），默认15秒
            
        Returns:
            成功返回验证码信息，超时返回超时信息
        """
        start_time = time.time()
        attempt = 0
        
        print(f"开始等待验证码，号码: {phone}")
        
        while True:
            attempt += 1
            elapsed_time = int(time.time() - start_time)
            
            # 检查是否超时
            if elapsed_time >= max_wait_time:
                print(f"✗ 超时：等待{elapsed_time}秒未收到验证码")
                return {
                    "code": "-1",
                    "msg": f"超时：等待{elapsed_time}秒未收到验证码，建议拉黑该号码"
                }
            
            # 获取验证码
            result = self.get_message(sid, phone)
            
            if result.get("code") == "0" or result.get("code") == 0:
                print(f"✓ 成功接收验证码: {result.get('yzm')}")
                return result
            
            # 显示进度
            print(f"第{attempt}次查询，已等待{elapsed_time}秒，{max_wait_time - elapsed_time}秒后超时...")
            
            # 等待下一次检查
            time.sleep(check_interval)



# 使用示例
if __name__ == "__main__":
    # 初始化API
    api = HaoZhuYunAPI()
    
    # 1. 登录获取token（只需执行一次）
    login_result = api.login()
    print(f"登录结果: {login_result}\n")
    
    # 2. 获取账号信息
    summary = api.get_summary()
    print(f"账号信息: {summary}")
    print(f"余额: {summary.get('money')}元")
    print(f"最大区号数量: {summary.get('num')}\n")
    
    # 3. 获取号码
    sid = 59550  # 项目ID，请替换为实际的项目ID
    phone_result = api.get_phone(sid)
    print(f"获取号码结果: {phone_result}\n")
    
    if phone_result.get("code") == "0":
        phone = phone_result.get("phone")
        print(f"获得号码: {phone}")
        # 4. 等待接收验证码（自动轮询，每15秒检查一次，最多等待3分钟）
        message_result = api.wait_for_message(sid, phone, max_wait_time=30, check_interval=5)
        
        if message_result.get("code") == "0":
            print(f"验证码: {message_result.get('yzm')}")
            print(f"完整短信: {message_result.get('sms')}\n")
            cancel_recv_result = api.cancel_recv(sid, phone)
            print(f"释放号码结果: {cancel_recv_result}\n")
        else:
            # 超过3分钟没收到验证码，拉黑该号码
            print("验证码未收到，拉黑该号码...")
            blacklist_result = api.add_blacklist(sid, phone)
            print(f"拉黑结果: {blacklist_result}\n")
    


    # 5. 再次使用某个号码的流程
    # old_phone = "13800138000"  # 之前使用过的号码
    # specify_result = api.specify_phone(sid, old_phone)
    # if specify_result.get("code") == "0":
    #     message = api.wait_for_message(sid, old_phone)
    #     print(f"验证码: {message.get('yzm')}")
    
    # 6. 释放号码（可选）
    # api.cancel_recv(sid, phone)
    
    # 7. 释放所有号码（可选）
    # api.cancel_all_recv()

