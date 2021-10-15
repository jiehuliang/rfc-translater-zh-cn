
import os
import re
import json
import textwrap
import requests
from lxml import html
from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')

# 表示段落跨页的文字
BREAK = '\n\x07\n'

class Paragraph:
    # 具有段落信息的类。在这里进行代码或图表的判定。
    #
    # Properties:
    # * text: 分段的文章
    # * indent: 段落缩进数
    # * is_code: 无论是代码还是图表的标志。True时不进行翻译处理
    # * is_section_title: 是否为标题的标志
    # * is_toc: 是否为目录的标志

    def __init__(self, text, is_code=None):
        # 段落文章(缩进除外)
        self.text = textwrap.dedent(text.lstrip('\n').rstrip())
        # 缩进数的获取
        self.indent = _get_line_len_diff(text, self.text)
        # 代码、图表的判断
        self.is_code = is_code
        if not self.is_code:
            self.is_code = (
                not self._find_list_pattern(self.text)
                and self._find_code_pattern(self.text))
        # 标题判断
        self.is_section_title = (
            self.indent <= 2 and
            self._find_section_title_pattern(self.text))
        # 目录判断
        self.is_toc = self._find_toc_pattern(self.text)
        # 注释判断（|  Note: 因为一定会被图表判定，所以要修正）
        if self._find_note(self.text):
            self.is_code = False  # 不是代码图表
            self.indent += 3  # “|”只增加的幅度
            self.text = self._convert_note_from_figure_to_text(self.text)  # 清除“|”

        # 被分类为多个时的优先顺序:目录>部分>图和代码
        if self.is_toc:
            self.is_code = True
            self.is_section_title = False
        elif self.is_code and self.is_section_title:
            self.is_code = False

        # BREAK的替换(段落跨页时的处理)
        if self.is_code:
            # 图表、代码的时候，换成换行
            self.text = self.text.replace(BREAK, '\n')
        else:
            # 写文章的时候，换成一个空白(页码之间多余的空白也去掉)
            self.text = re.sub(BREAK + r'\s+', ' ', self.text)

        # 文章的处理
        if not self.is_code:
            self.text = re.sub(r'([a-zA-Z])-\n *', r'\1-', self.text)  # 连字符
            self.text = re.sub(r'\n *', ' ', self.text)  # 把多行合并成一行
            self.text = re.sub(r' +', ' ', self.text)  # 把连续的空白整理成一个

    def __str__(self):
        return 'Paragraph: level: %d, is_code: %s\n%s' % \
            (self.indent, self.is_code, self.text)

    # 目录的判断
    def _find_toc_pattern(self, text):
        return (re.search(r'\.{6}|(?:\. ){6}', text) or
               # 1. 从Introduction开始，到Authors' Addresses结束
               (re.search(r'\A\s*1\. +(?:Introduction|Overview)', text, re.MULTILINE) and
                re.search(r'Author(?:s\'|\'s) Address(?:es)?\s*\Z', text, re.MULTILINE)))

    # 分条书写等的判定
    def _find_list_pattern(self, text):
        return re.match(r'(?:[-o*+]|\d{1,2}\.) +[a-zA-Z]', text)

    # 图表、源代码、公式的判断
    def _find_code_pattern(self, text):
        if (re.search(r'\A\s*As described in \[RFC\d+\],', text)):  # For RFC9015
            return False

        if (re.search(r'---|__|~~~|\+\+\+|\*\*\*|\+-\+-\+-\+|=====', text)  # fig
                or re.search(r'\.{4}|(?:\. ){4}', text)  # TOC
                or text.find('+--') >= 0  # directory tree
                or re.search(r'^\/\*|\/\* | \*\/$', text)  # src
                or re.search(r'(?:enum|struct) \{', text)  # tls
                or text.find('::=') >= 0  # syntax
                or re.search(r'": (?:[\[\{\"\']|true,|false,)', text)  # json
                or re.search(r'= +[\[\(\{<*%#&]', text) # src, syntax
                or len(re.compile(r'[;{}]$', re.MULTILINE).findall(text)) >= 2  # src
                or len(re.compile(r'^</', re.MULTILINE).findall(text)) >= 2  # xml
                or re.search(r'[/|\\] +[/|\\]', text)  # figure
                or len(re.compile(r'^\s*\|', re.MULTILINE).findall(text)) >= 3  # table
                or len(re.compile(r'\*\s*$', re.MULTILINE).findall(text)) >= 3  # table
                or len(re.compile(r'^\s*/', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'^\s*;', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'^\s*\[', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'\]\s*$', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'^\s*:', re.MULTILINE).findall(text)) >= 3  # src
                or len(re.compile(r'^\s*o ', re.MULTILINE).findall(text)) >= 4  # list
                or re.match(r'^E[Mm]ail: ', text)  # Authors' Addresses
                or re.search(r'(?:[0-9A-F]{2} ){8} (?:[0-9A-F]{2} ){7}[0-9A-F]{2}', text)  # hexdump
                or re.search(r'000 {2,}(?:[0-9a-f]{2} ){16} ', text)  # hexdump
                or re.search(r'[0-9a-zA-Z]{32,}$', text)  # hex
                or re.search(r'" [\|/] "', text)  # BNF syntax
                or re.match(r'^\s*[-\w\d]+\s+=\s+[-\w\d /]{1,40}$', text) # syntax
                or re.match(r'^\s*[-\w\d]+\s+=\s+"[-\w\d ]{1,20}"$', text) # syntax
                or re.search(r'^\s*[-\w\d]+\s+=\s+1\*.', text) # syntax
                or len(re.compile(r'^\s*Content-Type:\s+[a-z]+/[a-z]+\s*$', re.MULTILINE).findall(text)) >= 1 # HTML
                or len(re.compile(r'^\s*[SC]: ', re.MULTILINE).findall(text)) >= 2 # server-client
                or len(re.compile(r'^\s*-- ', re.MULTILINE).findall(text)) >= 2 # syntax
                or len(re.compile(r'^\s*[0-9a-f]0: ', re.MULTILINE).findall(text)) >= 3 # hexdump
                or len(re.compile(r'^\s*(?:IN   |OUT  ).', re.MULTILINE).findall(text)) >= 2 # SNMP Dispatcher
                ):
            return True

        # 检测公式和程序
        # 当符号大于或等于(3 +行数-1)
        # (但是，圆括号的前提是前面没有空白)
        # (但负数的前提是之前有空白)
        lines_num = len(text.split("\n"))
        threshold = 3 + (lines_num - 1) * 1
        if (len(re.findall(r'[~+*/=!#<>{}^@:;]|[^ ]\(| -', text)) >= threshold
                and (not re.search(r'[.,:]\)?$', text)) # 文末が「.,:」ではない
                ):
            return True

        return False

    # 标题的判断
    def _find_section_title_pattern(self, text):
        # "N." 出现时作为标题进行检测
        if len(text.split('\n')) >= 2:
            return False
        if text.endswith('.'):
            return False
        if text.endswith(':'):
            return False
        if text.endswith(','):
            return False
        if re.match(r'^Appendix [A-F](?:\. [-a-zA-Z0-9\'\. ]+)?$', text):
            return True
        return re.match(r'^(?:\d{1,2}\.)+(?:\d{1,2})? |^[A-Z]\.(?:\d{1,2}\.)+(?:\d{1,2})? |^[A-Z]\.\d{1,2} ', text)

    # 注释的正则表达式
    REGEX_PATTERN_NOTE1 = r'\A\s*\|  Note(?:\(\*\d\))?:'  # 第一行
    REGEX_PATTERN_NOTE2 = r'\A\s*\|  '                    # 第二行以后
    # 注释的判断
    def _find_note(self, text):
        # |  Note: 和 |  Note (*1): 作为开头时，视为注释。
        lines = text.split("\n")
        if not re.search(self.__class__.REGEX_PATTERN_NOTE1, lines[0]):
            return False
        for line in lines[1:]:
            if not re.search(self.__class__.REGEX_PATTERN_NOTE2, line):
                return False
        return True

    # 把注释从图表转换成文本
    def _convert_note_from_figure_to_text(self, text):
        # 消除的该类行头字符串“|”。
        lines_with_pipe = text.split("\n")
        lines_without_pipe = []
        for line in lines_with_pipe:
            tmp = re.sub(self.__class__.REGEX_PATTERN_NOTE2, ' ', line)
            lines_without_pipe.append(tmp)
        return ''.join(lines_without_pipe)


class Paragraphs:
    # 段落(Paragraph)合集
    #
    # Properties:
    # * paragraphs: 段落(Paragraph)元组

    def __init__(self, text, ignore_header=True):
        # Arguments:
        # * text: 包含所有段落的一个字符串(分段\n\n)
        # * ignore_header: 第一段不翻译

        # 连续两个以上换行的部分是分段，所以按分段分割字符串
        chunks = re.compile(r'\n\n+').split(text)
        self.paragraphs = []
        for i, chunk in enumerate(chunks):
            # 第一段是作者信息等元信息，所以不翻译
            is_header = (i == 0 and ignore_header)
            # 把字符串分成段落，然后再添加到元组中
            paragraph = Paragraph(chunk, is_code=is_header)
            self.paragraphs.append(paragraph)

    def __getitem__(self, key):
        assert isinstance(key, int)
        return self.paragraphs[key]

    def __iter__(self):
        return iter(self.paragraphs)

# 求单一行的两个字符串缩进差的函数
def _get_indent(text):
    return len(text) - len(text.lstrip())

# 求多行的两个字符串缩进之差的函数
def _get_line_len_diff(text1, text2):
    first_line1 = text1.split('\n')[0]
    first_line2 = text2.split('\n')[0]
    return abs(len(first_line1) - len(first_line2))


# 当RFC获取链接中没有数据时，要抛出RFCNotFound异常。
# 如果抛出这个异常，就会生成html/rfcXXXX-not-found.html。
class RFCNotFound(Exception):
    pass

# 除此之外的异常(例如关于HTML结构的错误)是抛出Exception。
# class Exception:


# 删除文中的a标签(RFC链接等)
def _cleanhtml(raw_html):
    cleaner = re.compile(rb'<a href="./rfc\d+[^"]*"[^>]*>')
    cleantext = re.sub(cleaner, b'', raw_html)
    return cleantext

# [EntryPoint]
# RFC获取
def fetch_rfc(number, force=False):
    # url = 'https://www.rfc-editor.org/rfc/rfc%d.html' % number
    # url = 'https://datatracker.ietf.org/doc/html/rfc%d' % number
    # url = 'https://ftp.ripe.net/mirrors/rfc/rfc%d.html' % number
    url = 'https://datatracker.ietf.org/doc/html/rfc%d' % number


    # tmpres = os.popen('curl -x 127.0.0.1:10809 %s' % url).readlines()
    output_dir = 'data/%04d' % (number//1000%10*1000)
    output_file = '%s/rfc%d.json' % (output_dir, number)

    # 如果文件已经存在，则直接返回，除非使用了--force选项
    if not force and os.path.isfile(output_file):
        return 0

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    proxy = '127.0.0.1:10809'
    proxies = {
        "http": "http://%(proxy)s/" % {'proxy': proxy},
        "https": "http://%(proxy)s/" % {'proxy': proxy}
    }

    # 获取RFC页面的内容
    headers = {'User-agent': '', 'referer': url}
    page = requests.get(url, headers, timeout=(36.2, 180), proxies=proxies)
    # f = open(output_file,'w', encoding='utf8')
    # f.write(page.text)
    tree = html.fromstring(_cleanhtml(page.content))

    # 获取标题
    title = tree.xpath('//title/text()')
    if len(title) == 0:
        raise RFCNotFound

    if not force:
        # 设置标题
        # MEMO: RFC的HTML结构发生变化的时候，研究一下这里是否可以搞定

        # <span class="h1">标题</span>
        # content_h1 = tree.xpath('//span[@class="h1"]/text()') # 6/17 因为有通过换行分割成多个的情况所以废止
        # <meta name="description" content="标题 (RFC)">
        content_description = tree.xpath('//meta[@name="description"]/@content')

        # if len(content_h1) > 0:
        #     title = "RFC %s - %s" % (number, content_h1[0]) # 6/17 因为有通过换行分割成多个的情况所以废止
        if len(content_description) > 0:
            tmp = content_description[0]
            tmp = re.sub(r' ?\(RFC ?\)$', '', tmp)
            title = "RFC %s - %s" % (number, tmp)
        else:
            raise Exception("Cannot extract RFC Title!")

    else:
        # 有force选项的时候，即使标题不存在也要执行
        title = "RFC %s" % number

    # 获取文章内容
    # MEMO: RFC的HTML结构发生变化的时候，研究一下这里是否可以搞定
    contents = tree.xpath(
        '//pre[not(contains(@class,"meta-info"))]/text() | '    # 正文(但正文开头的元信息除外)
        '//pre[not(contains(@class,"meta-info"))]/a/text() | '  # 正文中的链接
        # 小节的标题
        '//pre/span[@class="h1" or @class="h2" or @class="h3" or '
                   '@class="h4" or @class="h5" or @class="h6"]//text() |'
        '//pre/span/a[@class="selflink"]/text() |'  # 标题编号
        '//a[@class="invisible"]'  # 页的划分
    )

    # 在分页时，段落跨页的处理(RFC8650 ~不再分页，所以没有关系)
    contents_len = len(contents)
    for i, content in enumerate(contents):
        # 进行分页
        if (isinstance(content, html.HtmlElement) and
                content.get('class') == 'invisible'):

            contents[i-1] = contents[i-1].rstrip() # 除去前页末尾的空白
            contents[i+0] = '' # 去除分页
            if i + 1 >= contents_len:
                continue
            contents[i+1] = '' # 去除多余的换行
            if i + 2 >= contents_len:
                continue
            contents[i+2] = '' # 去除多余的空白
            if i + 3 >= contents_len:
                continue
            if not isinstance(contents[i+3], str):
                continue
            contents[i+3] = contents[i+3].lstrip('\n') # 去除下一页开头的换行

            # 对应跨页文章的处理
            first, last = 0, -1
            prev_last_line = contents[i-1].split('\n')[last]    # 上一页的最后一行
            next_first_line = contents[i+3].split('\n')[first]  # 下一页的第一行
            indent1 = _get_indent(prev_last_line)
            indent2 = _get_indent(next_first_line)
            # print('newpage:', i)
            # print('  ', indent1, prev_last_line)
            # print('  ', indent2, next_first_line)

            # 当有以下条件时，判断段落跨页
            #   1) 上一页最后一段的降字幅度与下一页第一段的降字幅度相同时
            #   2) 前一页的最后一段是句子结尾的“。”或“;”不是的时候
            if (not prev_last_line.endswith('.') and
                not prev_last_line.endswith(';') and
                    re.match(r'^ *[a-zA-Z0-9(]', next_first_line) and
                    indent1 == indent2):
                # 内容跨页时，插入BREAK
                # BREAK在写文章的时候替换为空白，在写代码的时候替换为换行。
                contents[i+3] = BREAK + contents[i+3]
            else:
                # 内容不能跨页的情况下，插入分段(两个换行)
                contents[i+0] = '\n\n'

    # 不显示页码
    contents[-1] = re.sub(r'.*\[Page \d+\]$', '', contents[-1].rstrip()).rstrip()
    # 合并段落
    text = ''.join(contents).strip()

    # 把字符串转换成段落的排列
    paragraphs = Paragraphs(text)

    # 将段落信息转换成JSON
    obj = {
        'title': {'text': title},
        'number': number,
        'created_at': str(datetime.now(JST)),
        'updated_by': '',
        'contents': [],
    }
    for paragraph in paragraphs:
        obj['contents'].append({
            'indent': paragraph.indent,
            'text': paragraph.text,
        })
        if paragraph.is_section_title:
            obj['contents'][-1]['section_title'] = True
        if paragraph.is_code:
            obj['contents'][-1]['raw'] = True
        if paragraph.is_toc:
            obj['contents'][-1]['toc'] = True

    # 保存JSON文件
    json_file = open(output_file, 'w', encoding="utf-8")
    json.dump(obj, json_file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    fetch_rfc(args.rfc_number)
