from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.PublicKey.RSA import RsaKey
from bili import constants
from functools import reduce
from hashlib import md5

import binascii
import urllib.parse
import time
import requests

"""
    The contents below came from BiliBili-Api-Collect, 
    a project owned by @SocialSisterYi (https://github.com/SocialSisterYi)
    Licensed under CC-BY-NC 4.0, with modifications to fit the needs of this project.
    Project link: https://github.com/SocialSisterYi/bilibili-API-collect.git
    range: [
        mixinKeyEncTab, 
        get_mixin_key,
        enc_wbi,
        get_wbi_keys,
        get_correspond_path
    ]
"""


mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

pub_key: RsaKey = None


def get_mixin_key(orig: str):
    """
        对 imgKey 和 subKey 进行字符顺序打乱编码
        :param orig: 原始的 imgKey + subKey 字符串
    """
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]


def enc_wbi(params: dict, img_key: str, sub_key: str):
    """
        为请求参数进行 wbi 签名
        :param params:    请求参数字典
        :param img_key:   从导航接口获取的 img_key
        :param sub_key:   从导航接口获取的 sub_key
        :return:          带有 w_rid 和 wts 的请求参数字典
    """
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params


def get_wbi_keys() -> tuple[str, str]:
    """
        获取最新的 img_key 和 sub_key
        :return:  一个包含 img_key 和 sub_key 的元组
    """
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=constants.headers)
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key


def read_rsa_pub_key() -> None:
    """
        从本地文件读取 RSA 公钥
    """
    global pub_key
    with open('../rsa_pub_key.txt', 'r') as f:
        raw_key = f.read()
        pub_key = RSA.import_key(raw_key)

def get_correspond_path(time_stamp):
    if pub_key is None:
        read_rsa_pub_key()
    cipher = PKCS1_OAEP.new(pub_key, SHA256)
    encrypted = cipher.encrypt(f'refresh_{time_stamp}'.encode())
    return binascii.b2a_hex(encrypted).decode()