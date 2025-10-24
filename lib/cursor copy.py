from bit_api import *
import time
from playwright.sync_api import sync_playwright, Playwright
from gemini import call_gemini_api
import requests
from haozhuyun import HaoZhuYunAPI
import psutil
# INSERT_YOUR_CODE
import random
import string
from imap_email import get_cursor_code_timeout

def run(playwright: Playwright):
    while 1:
        
        # 获取所有可用的移动设备（使用 is_mobile 字段）
        mobile_devices = [k for k, v in playwright.devices.items() if v.get("is_mobile", False)]
        
        # 如果找不到，使用预定义的移动设备列表
        if not mobile_devices:
            # 常见的移动设备列表
            mobile_devices = [
                "iPhone 13", "iPhone 13 Pro", "iPhone 13 Pro Max",
                "iPhone 12", "iPhone 12 Pro", "iPhone 11",
                "Pixel 5", "Pixel 4", "Galaxy S21", "Galaxy S20"
            ]
            # 过滤出实际存在的设备
            mobile_devices = [d for d in mobile_devices if d in playwright.devices]
        
        if not mobile_devices:
            print("警告: 未找到移动设备配置，使用默认桌面配置")
            device = {}
        else:
            # 随机选择一个移动设备
            random_device_name = random.choice(mobile_devices)
            print(f"正在使用的移动设备模拟: {random_device_name}")
            # 获取该设备的描述信息
            device = playwright.devices[random_device_name]

        ip, port = get_proxy_ip_port()
        browser = playwright.chromium.launch(headless=False, proxy={"server": f"{ip}:{port}"})

        # 使用设备的属性创建一个新的浏览器上下文
        context = browser.new_context(**device)

        page = context.new_page()
        page.goto('https://cursor.com/cn/dashboard')

        page.wait_for_selector('span:has-text("使用 Google 继续")', timeout=20000)
        
        # 生成随机邮箱
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{username}@lisonzz.top"

        # 填写邮箱输入框
        page.fill('input[type="email"][name="email"]', email)
        # 点击“继续”按钮
        page.click('button[type="submit"]')

        # INSERT_YOUR_CODE
        # 等待“邮箱登录验证码”文本出现（邮箱登录页面加载）
        page.wait_for_selector('span:has-text("邮箱登录验证码")', timeout=20000)

        # INSERT_YOUR_CODE
        # 点击“邮箱登录验证码”按钮
        page.click('button[name="intent"][value="magic-code"]')

        # 等待人机验证复选框出现，点击复选框
        page.wait_for_selector('input[type="checkbox"]', timeout=60000)
        page.locator('input[type="checkbox"]').click()

        # INSERT_YOUR_CODE
        # 等待“没有收到验证码”这几个字出现，如果1分钟还没出现则报错
        try:
            page.wait_for_selector('text=没有收到验证码', timeout=60000)
        except Exception as e:
            raise RuntimeError("超过1分钟仍未出现'没有收到验证码'提示，流程终止") from e

        code = get_cursor_code_timeout()
        if code:
            # 先聚焦到第一个输入框
            first_input = page.locator('input[data-test="otp-input"][data-index="0"]')
            first_input.click()
            
            # 逐个输入每个字符
            for i, digit in enumerate(code):
                print(f"输入第 {i+1} 个验证码: {digit}")
                page.keyboard.type(digit)
                time.sleep(0.1)  # 短暂延迟，让页面自动跳转
            
            time.sleep(0.2)
        else:
            print("未能获取到有效的邮箱验证码")
            browser.close()
            continue


        # 接码平台获取手机号
        api = HaoZhuYunAPI()
        api.login()
        phone_result = api.get_phone(59550)
        phone_number = phone_result.get("phone")  
        # phone_number = "18229272020" 

        # 输入手机号
        page.fill('input[placeholder="请输入手机号"]', phone_number)
        # 点击“获取验证码”按钮
        page.click('button.get-verifcode')
        
        # 等待验证码图片加载完毕
        page.wait_for_selector('.shumei_captcha_loaded_img_bg', timeout=10000)

        # 获取验证码图片和题目文本
        captcha_img_url = page.get_attribute('.shumei_captcha_loaded_img_bg', 'src')
        captcha_tip = page.inner_text('.shumei_captcha_slide_tips')

        # 下载验证码图片到本地
        img_bytes = requests.get(captcha_img_url).content
        response_text = call_gemini_api(captcha_tip[2:]+"的中心坐标占图片宽度和高度的比例，返回x比例,y比例，用逗号分隔：如x,y，不要返回其他内容", image_data=img_bytes)
        x, y = response_text.split(',')
        # INSERT_YOUR_CODE
        # 计算页面中验证码图片的实际点击位置（基于79%和30%的比例），并模拟点击
        bounding_box = page.locator('.shumei_captcha_loaded_img_bg').bounding_box()
        if bounding_box:
            x = bounding_box['x'] + float(x)*bounding_box['width']
            y = bounding_box['y'] + float(y)*bounding_box['height']
            page.mouse.click(x, y)
        else:
            print("未能获取验证码图片的位置，无法点击。")
            

        # 获取验证码
        message_result = api.wait_for_message(59550, phone_number, max_wait_time=120, check_interval=5)
        if message_result.get("code") == "0":
            print(f"验证码: {message_result.get('yzm')}")
            print(f"完整短信: {message_result.get('sms')}\n")
            cancel_recv_result = api.cancel_recv(59550, phone_number)
            print(f"释放号码结果: {cancel_recv_result}\n")
        else:
            print("验证码未收到，拉黑该号码...")
            blacklist_result = api.add_blacklist(59550, phone_number)
            print(f"拉黑结果: {blacklist_result}\n")

        # INSERT_YOUR_CODE
        # 在输入框输入验证码
        if message_result.get("code") == "0" and message_result.get("yzm"):
            page.fill('input[placeholder="请输入验证码"]', message_result.get("yzm"))
        else:
            print("未能获取到有效验证码，无法输入。")


        # 点击“登录 / 注册”按钮
        page.click('button.login-btn.el-button--primary')
        # 等待页面加载完成
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # INSERT_YOUR_CODE
        # 进入页面：https://bigmodel.cn/usercenter/proj-mgmt/apikeys
        page.goto("https://bigmodel.cn/usercenter/proj-mgmt/apikeys")
        page.wait_for_load_state("networkidle")
        
        # INSERT_YOUR_CODE
        # 点击“添加新的API Key”按钮
        page.click('button.el-button.el-button--primary.el-button--small span:has-text("添加新的API Key")')
        # 等待页面加载完成
        page.wait_for_load_state("networkidle")

        # INSERT_YOUR_CODE
        # 输入123：
        page.fill('input[placeholder="请输入API key名称"]', "123")

        # 点击“确定”按钮
        page.click('button.el-button.el-button--default.el-button--small.el-button--primary span:has-text("确定")')

        # 获取API Key
        # 等待API Key元素出现并获取其文本
        page.wait_for_selector('div.api-key-value')
        api_key_element = page.query_selector('div.api-key-value')
        api_key = api_key_element.inner_text().strip() if api_key_element else None
        if api_key:
            print(f"获取到的API Key: {api_key}")
        else:
            print("未能成功获取API Key。")

        time.sleep(2)  
        browser.close()


def main():
    with sync_playwright() as playwright:
        run(playwright)

if __name__ == "__main__":
    main()