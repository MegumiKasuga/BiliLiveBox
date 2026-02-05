from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.PublicKey.RSA import RsaKey
import binascii
import time

pub_key: RsaKey = None

def read_rsa_pub_key():
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