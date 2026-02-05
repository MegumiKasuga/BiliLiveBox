import requests, PIL, qrcode

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
    :return: 状态字典，包含code(是否登录成功), message(服务器下发的信息), num(状态码，参看顶上的字典)和status(状态码对应的状态)
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

    return {"code": code, "message": msg, "num": num, "status": qr_code_codes.get(num, "Unknown status")}

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
    img.save(byte_io, format='PNG')
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

# 样例用法
gen = gen_qrcode()
qr_code_url, qrcode_key = gen
show_qrcode_image(gen_qrcode_image(qr_code_url))