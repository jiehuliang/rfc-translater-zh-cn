# This code shows an example of text translation from English to Simplified-Chinese.
# This code runs on Python 2.7.x and Python 3.x.
# You may install `requests` to run this code: pip install requests
# Please refer to `https://api.fanyi.baidu.com/doc/21` for complete api document

import requests
import random
import json
import time
from hashlib import md5

# Set your own appid/appkey.
appid = '20211015000973918'
appkey = 'iZvfyQ9yYN8mpzwqnMJG'

# For list of language codes, please refer to `https://api.fanyi.baidu.com/doc/21`

# Generate salt and sign
def make_md5(s, encoding='utf-8'):
    return md5(s.encode(encoding)).hexdigest()

def bd_translate(query_str):
    from_lang = 'en'
    to_lang =  'zh'
    endpoint = 'http://api.fanyi.baidu.com'
    path = '/api/trans/vip/translate'
    url = endpoint + path
    salt = random.randint(32768, 65536)
    sign = make_md5(appid + query_str + str(salt) + appkey)
    
    # Build request
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'appid': appid, 'q': query_str, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}

    time.sleep(1)
    # Send request
    try:
        r = requests.post(url, params=payload, headers=headers)
        response = r.json()
        # result = []
        # result.append(response['trans_result'][0]['src'])
        # result.append(response['trans_result'][0]['dst'])        
        return response['trans_result'][0]['dst']
    except:
        result = []
        result.append(query_str)
        result.append('translate error, please retry')
        return result
