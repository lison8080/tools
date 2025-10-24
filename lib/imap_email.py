import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re
import time


def get_email_code(host='imap.qq.com', address='2168933744@qq.com', password='ypwzsvrrzhdhdhhh', number=3):


    # 连接到QQ邮箱的IMAP服务器
    mail = imaplib.IMAP4_SSL(host)

    # 登录邮箱
    mail.login(address, password)

    # 选择收件箱
    mail.select("inbox")

    # 搜索所有邮件
    status, messages = mail.search(None, 'ALL')

    # 获取邮件ID列表
    mail_ids = messages[0].split()

    subjectlist = []
    bodylist = []
    datelist = []
    # 逐个处理邮件
    for mail_id in mail_ids[-number:]:
        # 获取邮件
        status, msg_data = mail.fetch(mail_id, '(RFC822)')
        
        # 解析邮件内容
        msg = email.message_from_bytes(msg_data[0][1])
        
        # 解码邮件标题
        subject, encoding = decode_header(msg['Subject'])[0]
        if isinstance(subject, bytes):
            # 如果是字节类型，解码为字符串
            subject = subject.decode(encoding if encoding else 'utf-8')


    # INSERT_YOUR_CODE
        # 打印邮件内容
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset()
                    try:
                        body = part.get_payload(decode=True).decode(charset if charset else 'utf-8', errors='replace')
                    except Exception:
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    break
        else:
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                charset = msg.get_content_charset()
                try:
                    body = msg.get_payload(decode=True).decode(charset if charset else 'utf-8', errors='replace')
                except Exception:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

        # 获取并打印邮件发送的时间
        email_date = msg.get("Date")
        email_date = parsedate_to_datetime(email_date)
        # 转换为中国时间（东八区）
        china_tz = timezone(timedelta(hours=8))
        if email_date.tzinfo is None:
            email_date = email_date.replace(tzinfo=timezone.utc).astimezone(china_tz)
        else:
            email_date = email_date.astimezone(china_tz)

        subjectlist.append(subject)
        bodylist.append(body)
        datelist.append(email_date)
    # 关闭连接
    mail.logout()
    return subjectlist, bodylist, datelist
 
 
def get_code_6_digits_from_body(body):
    match = re.search(r'\b\d{6}\b', body)
    if match:
        code_6_digits = match.group()
        return code_6_digits
    else:
        return None

def get_cursor_code(old_date):
    subjectlist, bodylist, datelist = get_email_code(number=1)
    for i in range(len(subjectlist)):

        # 已改为中国时间，直接比较时间即可，无需修改tzinfo
        if "Cursor。您的一次性验证码是" in bodylist[i]:
            # Ensure old_date is offset-aware (China timezone), like datelist[i]
            if old_date.tzinfo is None:
                china_tz = timezone(timedelta(hours=8))
                old_date_aware = old_date.replace(tzinfo=china_tz)
            else:
                old_date_aware = old_date
            if old_date_aware <= datelist[i]:
                return get_code_6_digits_from_body(bodylist[i])


def get_cursor_code_timeout(timeout=60):
    start_time = time.time()
    old_date = datetime.now()
    attempt = 0
    while True:
        # INSERT_YOUR_CODE
        # 打印现在是第几次获取
        attempt = attempt + 1
        print(f"正在进行第 {attempt} 次获取验证码...{int(time.time() - start_time)}/{timeout}秒")
        code = get_cursor_code(old_date)
        if code:
            print(f"获取验证码成功: {code}")
            return code
        if time.time() - start_time >= timeout:
            print(f"超过{timeout}秒，获取验证码失败")
            return None
        time.sleep(2)  


# print(get_cursor_code_timeout())

