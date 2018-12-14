# -*- coding:UTF-8 -*- # 标识为


from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

import socket
import re

regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def is_website_online(host):
    """ This function checks to see if a website is available by checking
        for socket info. If the website gets something in return, 
        we know it's available.
    """
    try:
        socket.gethostbyname(host)
    except socket.gaierror:
        return False
    else:
        return True

# import requests
# 
# def url_ok(url):
#     r = requests.head(url)
#     return r.status_code == 200

def check_url_validity(url):
    val = URLValidator()
    is_valid = False
    try:
        val(url)
    except ValidationError as e:
        print(e)
    else:
        is_valid = True
    
    return is_valid
    
if __name__ == '__main__':
    url = 'http://www.google.com'
    if check_url_validity(url):
        display_format = 'url{{{0}}} is valid'
        print((display_format.format(url)))
    
    url = 'rtmp://cdn.myntv.cn/live/mytv1'
    print((is_website_online(url)))
#     print(url_ok(url))