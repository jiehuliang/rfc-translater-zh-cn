
import os
import re
import json
import time
import uuid
import requests
import hashlib
import time
from tqdm import tqdm # pip install tqdm
from datetime import datetime, timedelta, timezone
CST = timezone(timedelta(hours=+9), 'CST')
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException
from src.trans_youdao import youdao_trans

# 必须使用小写注册规则
trans_rules = {
    'abstract': '摘要',
    'introduction': '前言',
    'acknowledgement': '致辞',
    'acknowledgements': '致辞',
    'status of this memo': '文档状态',
    'copyright notice': '版权提示',
    'table of contents': '目录',
    'conventions': '约定',
    'terminology': '术语',
    'discussion': '讨论',
    'references': '参考文献',
    'normative references': '引用标准',
    'informative references': '参考资料',
    'contributors': '贡献者',
    'where': '不过',
    'where:': '不过：',
    'assume:': '假设：',
    "the key words \"must\", \"must not\", \"required\", \"shall\", \"shall not\", \"should\", \"should not\", \"recommended\", \"may\", and \"optional\" in this document are to be interpreted as described in rfc 2119 [rfc2119].": 
        "本文档的关键词 \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", 以及 \"OPTIONAL\" 在RFC 2119 [RFC2119]进行解释和描述。",
    "the key words \"must\", \"must not\", \"required\", \"shall\", \"shall not\", \"should\", \"should not\", \"recommended\", \"not recommended\", \"may\", and \"optional\" in this document are to be interpreted as described in bcp 14 [rfc2119] [rfc8174] when, and only when, they appear in all capitals, as shown here.": 
        "本文档的关键词 \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", 以及 \"OPTIONAL\" 在BCP 14 [RFC2119] [RFC8174]进行解释和描述，只有在全部大写的情况下，进行解释。",
    "this document is subject to bcp 78 and the ietf trust's legal provisions relating to ietf documents (https://trustee.ietf.org/license-info) in effect on the date of publication of this document. please review these documents carefully, as they describe your rights and restrictions with respect to this document. code components extracted from this document must include simplified bsd license text as described in section 4.e of the trust legal provisions and are provided without warranty as described in the simplified bsd license.": 
        "本文件受BCP 78和ietf信托的法律规定的约束，该法律规定与ietf文件（https://trustee.ietf.org/license-info）有关，并于本文件发布之日生效。请仔细阅读这些文件，因为它们描述了您在本文件中的权利和限制。从本文档提取的代码组件必须包括Simplified BSDlicense文本，如第4.e节所述的信托法律条款，并提供无担保的描述Simplified BSDlicense。",
}

class TransMode:
    PY_GOOGLETRANS  = 1
    SELENIUM_GOOGLE = 2
    YOUDAO_DIC      = 3


# 翻译类的抽象
class Translator:

    def __init__(self, total, desc=''):
        self.count = 0
        self.total = total
        # 进度条
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}{postfix}]"
        self.bar = tqdm(total=total, desc=desc, bar_format=bar_format)

    def increment_count(self, incr=1):
        # 用于进度条的输出
        self.count += incr
        self.bar.update(incr)

    def output_progress(self, len, wait_time):
        # 在进度条中添加详细信息
        self.bar.set_postfix(len=len, sleep=('%.1f' % wait_time))

    def close(self):
        return True


class TranslatorGoogletrans(Translator):
    # py-googletrans

    def __init__(self, total, desc=''):
        from googletrans import Translator as GoogleTranslater # pip install googletrans
        super(TranslatorGoogletrans, self).__init__(total, desc)

        self.translator = GoogleTranslater()

    def translate(self, text, dest='zh-CN'):
        # 使用翻译规则(trans_rules)翻译特定术语
        ja = trans_rules.get(text.lower())
        if ja:
            return ja
        # 为了在URL编码处理中避免错误，在&的后面填上空白
        text = re.sub(r'&(#?[a-zA-Z0-9]+);', r'& \1;', text)
        # 翻译流程
        ja = self.translator.translate(text, dest='zh-CN')
        # 翻译间隔
        wait_time = 3 + len(text) / 100 # IMPORTANT!!!
        # 向进度条添加更多信息
        self.output_progress(len=len(text), wait_time=wait_time)
        time.sleep(wait_time)
        return ja.text

    def translate_texts(self, texts, dest='zh-CN'):
        # 在 & 后面插入一个空格以避免 URL 编码错误
        texts = list(map(lambda text: re.sub(r'&(#?[a-zA-Z0-9]+);', r'& \1;', text), texts))
        # 翻译流程
        texts_ja = self.translator.translate(texts, dest='zh-CN')
        res = [text_ja.text for text_ja in texts_ja]
        total_len = sum([len(t) for t in texts])
        # 翻译间隔
        wait_time = 5 + total_len / 1000 # IMPORTANT!!!
        # 向进度条添加更多信息
        self.output_progress(len=total_len, wait_time=wait_time)
        time.sleep(wait_time)
        # 对于特定术语，使用翻译规则进行翻译 (trans_rules)
        for i, text in enumerate(texts):
            ja = trans_rules.get(text.lower())
            if ja:
                res[i] = ja
        # 将函数括号 () 转换为半角
        res = [re.sub(r'（）', '()', text_ja) for text_ja in res]
        return res


class TranslatorSeleniumGoogletrans(Translator):
    # Selenium + Google

    def __init__(self, total, desc=''):
        super(TranslatorSeleniumGoogletrans, self).__init__(total, desc)

        WEBDRIVER_EXE_PATH = os.getenv('WEBDRIVER_EXE_PATH',
            default=r'C:\Users\R10839\AppData\Local\Programs\Python\Python39\Scripts\geckodriver.exe')
        options = Options()
        options.add_argument('--headless')
        browser = webdriver.Firefox(executable_path=WEBDRIVER_EXE_PATH, options=options)
        browser.implicitly_wait(3)
        self._browser = browser

    def translate(self, text, dest='zh-CN'):
        if len(text) == 0:
            return ""
        # 对于特定术语，使用翻译规则进行翻译 (trans_rules)
        ja = trans_rules.get(text.lower())
        if ja:
            return ja
        # 「%」网址编码
        text = text.replace('%', '%25')
        # 「|」网址编码
        text = text.replace('|', '%7C')
        # 「/」网址编码
        text = text.replace('/', '%2F')

        browser = self._browser
        # 将想要翻译的句子嵌入URL后访问
        text_for_url = urllib.parse.quote_plus(text, safe='')
        # url = "https://translate.google.cn/#view=home&op=translate&sl=auto&tl=en&text={0}".format(text_for_url)
        url = "https://translate.google.cn/?sl=en&tl=zh-CN&&text={0}op=translate".format(text_for_url)
        
        browser.get(url)
        # 等待几秒钟
        wait_time = 3 + len(text) / 1000
        time.sleep(wait_time)
        # 提取翻译结果
        elems = browser.find_elements_by_css_selector("span[jsname='W297wb']")
        ja = "".join(elem.text for elem in elems)
        # 向进度条添加更多信息
        self.output_progress(len=len(text), wait_time=wait_time)
        return ja

    def translate_texts(self, texts, dest='zh-CN'):
        res = []
        for text in texts:
            ja = self.translate(text)
            res.append(ja)
            self.increment_count()
        return res

    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()

class TranslatorYouDaotrans(Translator):
    # 有道翻译
    def __init__(self, total, desc=''):
        super(TranslatorYouDaotrans, self).__init__(total, desc)

    def translate(self, text, dest='zh-CN'):
        return youdao_trans(text, dest)

    def translate_texts(self, texts, dest='zh-CN'):
        res = []
        for text in texts:
            ja = youdao_trans(text, dest)
            res.append(ja)
            self.increment_count()
        return res

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def trans_rfc(number, mode):

    input_dir = 'data/%04d' % (number//1000%10*1000)
    input_file = '%s/rfc%d.json' % (input_dir, number)
    output_file = '%s/rfc%d-trans.json' % (input_dir, number)
    midway_file = '%s/rfc%d-midway.json' % (input_dir, number)

    if os.path.isfile(midway_file):  # 中途恢复任何已翻译的文件
        with open(midway_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)
    else:
        with open(input_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)

    desc = 'RFC %d' % number
    if mode == TransMode.PY_GOOGLETRANS:
        translator = TranslatorGoogletrans(total=len(obj['contents']), desc=desc)
    elif mode == TransMode.SELENIUM_GOOGLE:
        translator = TranslatorSeleniumGoogletrans(total=len(obj['contents']), desc=desc)
    else:
        translator = TranslatorYouDaotrans(total=len(obj['contents']), desc=desc)
    is_canceled = False

    try:
        # 标题翻译
        if not obj['title'].get('ja'):  # 跳过已翻译的段落
            titles = obj['title']['text'][0].split(':', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj['title']['ja'] = "RFC %d" % number
            else:
                text = titles[1]
                ja = translator.translate(text)
                obj['title']['ja'] = "RFC %d - %s" % (number, ja)

        # 段落翻译
        #   一次翻译多个段落
        CHUNK_NUM = 15
        for obj_contents in chunks(list(enumerate(obj['contents'])), CHUNK_NUM):

            texts = []     # 原文
            pre_texts = [] # 原文的序言（项目符号等）

            for i, obj_contents_i in obj_contents:

                # 跳过已经翻译的段落和图表而不翻译
                if (obj_contents_i.get('ja') or (obj_contents_i.get('raw') == True)):
                    texts.append('')
                    pre_texts.append('')
                    continue

                text = obj_contents_i['text']

                # 以具有象征意义的字符开头的句子是要点，因此通过排除前面的字符进行翻译。
                # 「-」「o」「*」「+」「$」「A.」「A.1.」「a)」「1)」「(a)」「(1)」「[1]」「[a]」「a.」
                pattern = r'^([\-o\*\+\$] |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |\(?[0-9a-z]\) |\[[0-9a-z]{1,2}\] |[a-z]\. )(.*)$'
                m = re.match(pattern, text)
                if m:
                    pre_texts.append(m[1])
                    texts.append(m[2])
                else:
                    pre_texts.append('')
                    texts.append(text)

            if mode == TransMode.PY_GOOGLETRANS:
                translator.increment_count(len(texts))

            texts_ja = translator.translate_texts(texts)

            # 存储翻译结果
            for (i, obj_contents_i), pre_text, text_ja in \
                    zip(obj_contents, pre_texts, texts_ja):
                obj['contents'][i]['ja'] = pre_text + ''.join(text_ja)

        print("", flush=True)

    except json.decoder.JSONDecodeError as e:
        print('[-] googletrans is blocked by Google :(')
        print('[-]', datetime.now(CST))
        is_canceled = True
    except NoSuchElementException as e:
        print('[-] Google Translate is blocked by Google :(')
        print('[-]', datetime.now(CST))
        is_canceled = True
    except KeyboardInterrupt as e:
        print('Interrupted!')
        is_canceled = True
    finally:
        translator.close()

    if not is_canceled:
        with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        # 删除不再需要的文件
        os.remove(input_file)
        if os.path.isfile(midway_file):
            os.remove(midway_file)
        return True
    else:
        with open(midway_file, 'w', encoding="utf-8", newline="\n") as f:
            # 生成半翻译文件
            json.dump(obj, f, indent=2, ensure_ascii=False)
        return False


def trans_test(mode=TransMode.SELENIUM_GOOGLE):
    if mode == TransMode.PY_GOOGLETRANS:
        translator = TranslatorGoogletrans(total=1)
        ja = translator.translate('test', dest='ja')
        return ja == 'テスト'
    elif mode == TransMode.SELENIUM_GOOGLE:
        translator = TranslatorSeleniumGoogletrans(total=1)
        ja = translator.translate('test', dest='ja')
        print('result:', ja)
        return ja in ('テスト', 'しけん')
    else:
        translator = TranslatorYouDaotrans(total=1)
        res = translator.translate('test', dest='zh-CHS')
        print('result:', res)
        return res in ('测试', '考试')



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(total=1)
    parser.add_argument('text', help='english text')
    args = parser.parse_args()

    translator = TranslatorGoogletrans(total=1)
    ja = translator.translate(args.text, dest='zh-CN')
    print(ja)


# googletrans:
#如果连续访问的话，会显示以下消息，以IP地址为单位被封锁，所以要注意。
#从您使用的计算机网络中检测出与平时不同的流量。
#之后请试着再发送一次请求。这个页面被显示的理由
#这个页面被认为违反了您的计算机网络的使用规定。
#请求被自动检测的时候显示。
#区块在这些请求被停止后很快就会被解除。
#该流量包括自动发送请求的非法软件、浏览器插件、
#有可能是根据或脚本产生的。如果网络连接是共享的，
#因为有可能发生在使用相同IP地址的其他电脑上，
#请和管理者商量。详情请看这边。
#如果使用机器人使用的高级搜索词，或者非常快速地发送请求，
#有时会显示这个页面。
# IP地址:XX.XX.XX.XX
#时间:2019-10-16 t03:56:15
# url: https://translate.google.com/translate_a/single?…