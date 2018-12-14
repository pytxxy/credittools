# -*- coding:UTF-8 -*-

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from Crypto.PublicKey import RSA
import base64
import binascii
import tempfile
import os
import subprocess
import codecs


# 当前python RSA解密只支持pkcs1格式密钥，所以使用python进行解密前，必须先将pkcs8格式密钥转换成pkcs1格式的，然后在 python 中使用该密钥进行解密。
# 将pkcs8格式密钥转换成pkcs1格式时，需要保证pkcs8密钥是完整的包含了头尾，然后再使用命令：
# openssl rsa -in pkcs8.pem -out pkcs1.pem
# 执行操作(在windows上可以安装openssl win32版本，或者如果安装了git，可以在git bash环境中手动执行该命令)，其中pkcs8.pem为完整的包含了头尾的pkcs8格式密钥文件，
# pkcs1.pem为输出的完整的包含了头尾的pkcs1格式密钥文件。更详细信息可参考网址：https://www.jianshu.com/p/08e41304edab
# 该步操作当前已经集成到demo中了，但需要确保openssl已经正常安装并已经添加到系统路径PATH中，能够正常调用。


def read_file_content(file_name, encoding_='utf-8'):
    fh = codecs.open(file_name, encoding=encoding_)
    # Read ALL
    data = fh.read()
    fh.close()
    
    return data


def write_to_file(name, data, encoding='utf-8'):
    fh = codecs.open(name, 'w', encoding=encoding)
    fh.write(data)
    fh.close()
    
    
# 将pkcs8_key先写文件，转换完成之后再读文件获取转换后的内容
def convert_pkcs8_to_pkcs1_with_cmd(pkcs8_key):
    pkcs1_key = None
    temp_dir = tempfile.gettempdir()
    dir_name = 'pkcs8to1'
    work_dir = os.path.join(temp_dir, dir_name)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
        
    src_file_name = 'pkcs8.pem'
    dst_file_name = 'pkcs1.pem'
    src_file = os.path.join(work_dir, src_file_name)
    if os.path.exists(src_file):
        os.remove(src_file)
        
    write_to_file(src_file, pkcs8_key)
    
    dst_file = os.path.join(work_dir, dst_file_name)
    cmd_fmt = 'openssl rsa -in {} -out {}'
    cmd_str = cmd_fmt.format(src_file, dst_file)
    rtn = subprocess.check_call(cmd_str, shell=True)
    if rtn != 0:
        return pkcs1_key
    
    pkcs1_key = read_file_content(dst_file)
    return pkcs1_key
    

def convert_pkcs8_to_pkcs1_with_key_spec(key_spec):
    key_begin = '-----BEGIN PRIVATE KEY-----\n'
    key_end = '\n-----END PRIVATE KEY-----\n'
    pkcs8_key = key_begin + key_spec + key_end
    pkcs1_key = convert_pkcs8_to_pkcs1_with_cmd(pkcs8_key)
    
    return pkcs1_key


def convert_pkcs8_to_pkcs1(pkcs8_key):
    pkcs1_key = convert_pkcs8_to_pkcs1_with_cmd(pkcs8_key)
    return pkcs1_key


# 公钥加密
def encrypt_with_rsa(message, public_pem):
    rsakey = RSA.importKey(public_pem)
    cipher = Cipher_pkcs1_v1_5.new(rsakey)
    cipher_text = base64.b64encode(cipher.encrypt(message))
    return cipher_text


# 私钥解密
def decrypt_with_rsa(cipher_text, private_pem):
    rsakey = RSA.importKey(private_pem)
    cipher = Cipher_pkcs1_v1_5.new(rsakey)
    # 伪随机数生成器
    random_generator = Random.new().read
    text = cipher.decrypt(base64.b64decode(cipher_text), random_generator)
    return text.decode()


class AESECB:
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_ECB
        self.bs = 16  # block size
        self.pad = lambda s: s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)
        self.unpad = lambda s : s[0:-ord(s[-1])]

    def encrypt(self, text):
        generator = AES.new(self.key, self.mode)  # ECB模式无需向量iv
        enc_bytes = bytes(self.pad(text), 'utf-8')
        crypt = generator.encrypt(enc_bytes)
        result = binascii.b2a_hex(crypt)
        return result

    def decrypt(self, text):
        generator = AES.new(self.key, self.mode)  # ECB模式无需向量iv
        decrypt_bytes = binascii.a2b_hex(text)
        meg = generator.decrypt(decrypt_bytes)
        result = self.unpad(meg.decode('utf-8'))
        
        return result


def decrypt_by_private_key(encrypt_aes_key, private_key):
    return decrypt_with_rsa(encrypt_aes_key, private_key)


def decrypt_with_key_base64(encrypt_education_info, decrypt_aes_key):
    aes = AESECB(base64.b64decode(decrypt_aes_key))
    return aes.decrypt(encrypt_education_info)
