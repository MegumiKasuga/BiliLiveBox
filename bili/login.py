import time

import requests, PIL, qrcode, os

from bili.session import Session

qr_code_codes = {
    0    : "Login successful",                              # 成功登录
    86101: "QR code not scanned",                           # 二维码已生成但未扫码
    86090: "QR code scanned, waiting for confirmation",     # 已扫码但未确认
    86038: "QR code expired",                               # 二维码过期
}

def gen_qrcode() -> tuple[str, str]:
    """
        生成二维码的函数
        :return: 二维码的URL和二维码的key(URL用于生成具体的二维码图片，key用于轮询二维码状态)
    """
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    if data['code'] == 0:
        qr_code_url = data['data']['url']
        qrcode_key = data['data']['qrcode_key']
        return qr_code_url, qrcode_key
    else:
        raise Exception("Failed to generate QR code: " + data.get('message', 'Unknown error'))


def check_qrcode_status(qrcode_key: str) -> dict:
    """
        检查二维码状态的函数
    :param qrcode_key: 用于轮询二维码状态的key
    :return: 状态字典，包含
        code(是否登录成功),
        message(服务器下发的信息), '
        num(状态码，参看顶上的字典),
        status(状态码对应的状态),
        cookies(登录成功后的Cookies，失败则为None)
    """
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }
    params = {
        "qrcode_key": qrcode_key
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    code = data['code']
    msg = data['message']
    num = int(data['data']['code'])
    cookies = None

    if code == 0 and num == 0:
        cookies = response.cookies.get_dict()

    return {"code": code, "message": msg, "num": num, "status": qr_code_codes.get(num, "Unknown status"), "cookies": cookies}


def gen_qrcode_image(url: str) -> bytes:
    """
        生成二维码图片的函数
    :param url: 给定的二维码URL
    :return: 二维码图片的字节数据
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    from io import BytesIO
    byte_io = BytesIO()
    img.save(byte_io)
    return byte_io.getvalue()


def show_qrcode_image(image_bytes: bytes) -> None:
    """
    显示二维码图片(在本地图片查看器显示)
    :param image_bytes: 二维码图片的字节数据
    """
    from PIL import Image
    from io import BytesIO
    image = Image.open(BytesIO(image_bytes))
    image.show()

def save_cookies(cookies: dict, filepath: str) -> None:
    """
    保存Cookies到本地文件
    :param cookies: Cookies字典
    :param filepath: 保存的文件路径
    """
    import json
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=4)



def login_by_qrcode(sleep_time: float, timeout: float,
                    qrcode_display_func,
                    login_successful_func,
                    not_scanned_func,
                    not_confirmed_func,
                    force_break_loop_func,
                    should_regen_qrcode_func) -> Session | None:
    """
    通过二维码登录的主函数

    :param sleep_time:                  每次轮询获取登录状态的间隔时间(秒)
    :param timeout:                     超过这个时间之后，放弃登录(秒)，传入0或负数表示不限制时间
    :param qrcode_display_func:         用于显示二维码图片的函数，传入参数为二维码图片的字节数据
    :param login_successful_func:       登录成功时执行操作的函数，传入参数为登录状态字典
    :param not_scanned_func:            二维码已生成但未扫描时执行操作的函数，传入参数为登录状态字典
    :param not_confirmed_func:          二维码已扫描但未确认时执行操作的函数，传入参数为登录状态字典
    :param force_break_loop_func:       用于强制中断轮询的函数，传入参数为登录状态字典，返回True表示中断
    :param should_regen_qrcode_func:    用于判断是否需要重新生成二维码的函数，传入参数为登录状态字典，返回True表示需要重新生成
    :return:                            登录成功后的Session对象，登录失败或中断(超时)则返回None
    """
    if sleep_time <= 0:
        sleep_time = 1.0
    waited_time = 0.0
    qr_code_url, qrcode_key = gen_qrcode()
    qrcode_display_func(gen_qrcode_image(qr_code_url))

    while True:
        code_statue = check_qrcode_status(qrcode_key)
        if force_break_loop_func(code_statue) or (0 < timeout <= waited_time):
            return None
        if code_statue['code'] == 0 and code_statue['num'] == 0:
            login_successful_func(code_statue)
            return Session(login_time=time.gmtime(), cookies=code_statue['cookies'])
        elif code_statue['num'] == 86038:
            if should_regen_qrcode_func(code_statue):
                qr_code_url, qrcode_key = gen_qrcode()
                qrcode_display_func(gen_qrcode_image(qr_code_url))
                waited_time += sleep_time
                time.sleep(sleep_time)
                continue
        elif code_statue['num'] == 86101:
            not_scanned_func(code_statue)
        elif code_statue['num'] == 86090:
            not_confirmed_func(code_statue)
        time.sleep(sleep_time)
        waited_time += sleep_time


def login_by_session_file(session_file_path: str) -> Session | None:
    """
    通过本地Session文件登录的函数
    :param session_file_path: 存储Session信息的文件路径
    :return: 成功加载Session对象，失败则返回None
    """
    import json
    if os.path.exists(session_file_path):
        with open(session_file_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
            return Session(login_time=session_data['login_time'], cookies=session_data['cookies'])
    else:
        return None


login_by_qrcode(sleep_time=5, timeout=600,
                qrcode_display_func=lambda img_bytes: show_qrcode_image(img_bytes),
                login_successful_func=lambda status: print("Login successful!"),
                not_scanned_func=lambda status: print("Please scan the QR code."),
                not_confirmed_func=lambda status: print("Please confirm the login on your device."),
                force_break_loop_func=lambda status: False,
                should_regen_qrcode_func=lambda status: True)