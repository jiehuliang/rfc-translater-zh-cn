# -*- coding: utf-8 -*-

import sys
import uuid
import requests
import hashlib
import time
from importlib import reload

import time

reload(sys)

YOUDAO_URL = 'https://openapi.youdao.com/api'
APP_KEY = '3dcc08b081cdc226'
APP_SECRET = 'iz9GtkJziUmGiMzgu6lFzdtaOHirYMFA'

def encrypt(signStr):
    hash_algorithm = hashlib.sha256()
    hash_algorithm.update(signStr.encode('utf-8'))
    return hash_algorithm.hexdigest()


def truncate(q):
    if q is None:
        return None
    size = len(q)
    return q if size <= 20 else q[0:10] + str(size) + q[size - 10:size]


def do_request(data):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    return requests.post(YOUDAO_URL, data=data, headers=headers)

def youdao_trans(query_string, dst='zh-CHS'):  
    data = {}
    data['from'] = 'en'
    data['to'] = dst
    data['signType'] = 'v3'
    curtime = str(int(time.time()))
    data['curtime'] = curtime
    salt = str(uuid.uuid1())
    signStr = APP_KEY + truncate(query_string) + salt + curtime + APP_SECRET
    sign = encrypt(signStr)
    data['appKey'] = APP_KEY
    data['q'] = query_string
    data['salt'] = salt
    data['sign'] = sign
    data['vocabId'] = "1B1BCBC625BA45688824BE573C91CF7B"

    try:
        response = do_request(data)
        res_json = response.json()
        # result = []
        # result.append(res_json['translation'])
        return res_json['translation']
    except:
        result = []
        result.append(query_string)
        result.append('translate error, please retry')
        return result

if __name__ == '__main__':
    youdao_trans("test")