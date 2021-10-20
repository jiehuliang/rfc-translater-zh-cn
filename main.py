
import sys
from src.fetch_rfc import fetch_rfc, RFCNotFound
from src.trans_rfc import trans_rfc, TransMode
from src.make_html import make_html
from src.make_index import make_index
from src.fetch_index import diff_remote_and_local_index
from src.make_json_from_html import make_json_from_html

def main(rfc_number, transmode):
    print('RFC %d:' % rfc_number)

    try:
        fetch_rfc(rfc_number)
    except RFCNotFound as e:
        print('Exception: RFCNotFound!')
        filename = "html/rfc%d-not-found.html" % rfc_number
        with open(filename, "w") as f:
            f.write('')
        return
    except Exception as e:
        print(e)
        filename = "html/rfc%d-error.html" % rfc_number
        with open(filename, "w") as f:
            f.write('')
        return

    res = trans_rfc(rfc_number, transmode)
    if res is False: return False
    make_html(rfc_number)

def continuous_main(transmode, begin=None, end=None, only_first=False):
    numbers = list(diff_remote_and_local_index())
    if begin and end:  # 设置开始和结束区间
        numbers = [x for x in numbers if begin <= x <= end]
    elif begin:  # 设置开始区间
        numbers = [x for x in numbers if begin <= x]

    if only_first:  # 只选择最开始的RFC
        numbers = numbers[0:1]

    for rfc_number in numbers:
        res = main(rfc_number, transmode)
        if res is False:
            break

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rfc', type=str, help='RFC number')
    parser.add_argument('--file', type=str, help='read RFC number from file')
    parser.add_argument('--fetch', action='store_true', help='only fetch RFC')
    parser.add_argument('--trans', action='store_true', help='only translate')
    parser.add_argument('--make', action='store_true', help='only make HTML')
    parser.add_argument('--make-json', action='store_true', help='make JSON from HTML')
    parser.add_argument('--begin', type=int, help='begin rfc number')
    parser.add_argument('--end', type=int, help='end rfc number')
    parser.add_argument('--make-index', dest='make_index',
                        action='store_true', help='make index.html')
    parser.add_argument('--transtest', action='store_true')
    parser.add_argument('--force', '-f', action='store_true')
    parser.add_argument('--transmode', type=str)
    parser.add_argument('--only-first', action='store_true')
    args = parser.parse_args()

    # 指定RFC（多个RFC的情况下，使用逗号隔开）
    RFCs = None
    if args.rfc:
        RFCs = [int(rfc_number) for rfc_number in args.rfc.split(",")]

    if args.file:
        f = open(args.file, "r")
        RFCs = [int(rfc_number) for rfc_number in f.readlines()]

    # 选择翻译工具:默认为Selenium+谷歌翻译
    transmode = TransMode.BAIDU_TRANS
    if args.transmode == 'py-googletrans':
        transmode = TransMode.PY_GOOGLETRANS
    
    if args.transmode == 'baidu':
        transmode = TransMode.BAIDU_TRANS

    if args.make_index:
        # 创建index.html
        print("[+] 创建index.html")
        make_index()
    elif args.transtest:
        # 翻译测试
        from src.trans_rfc import trans_test
        res = trans_test(transmode)
        print('Translate test result:', res)
    elif args.fetch and args.begin and args.end:
        # 通过指定范围获取RFC
        print("[+] RFC %d - %d 获取" % (args.begin, args.end))
        numbers = list(diff_remote_and_local_index())
        numbers = [x for x in numbers if args.begin <= x <= args.end]
        for rfc_number in numbers:
            fetch_rfc(rfc_number)
    elif args.fetch and RFCs:
        # 获取指定的RFC
        for rfc in RFCs:
            print("[+] RFC %d 获取" % rfc)
            fetch_rfc(rfc, args.force)
    elif args.trans and RFCs:
        # 翻译RFC
        for rfc in RFCs:
            print("[+] RFC %d 翻译" % rfc)
            trans_rfc(rfc, transmode)
    elif args.make and args.begin and args.end:
        # 创建指定范围的html文件，(rfcXXXX.html)
        print("[+] RFC %d - %d 生成HTML文件" % (args.begin, args.end))
        for rfc_number in range(args.begin, args.end):
            make_html(rfc_number)
    elif args.make and RFCs:
        # 创建指定RFC的HTML(RFCxxxx.HTML)
        for rfc in RFCs:
            make_html(rfc)
    elif args.make_json and RFCs:
        # 将指定的RFC的JSON翻译修改后的HTML反向制作
        for rfc in RFCs:
            make_json_from_html(rfc)

    elif RFCs:
        # 指定范围，按顺序获取、翻译、制作RFC
        for rfc in RFCs:
            print("translating RFC %d" % rfc)
            main(rfc, transmode)
    else:
        # 按顺序获取、翻译、制作未翻译的RFC
        continuous_main(transmode, begin=args.begin, end=args.end, 
                        only_first=args.only_first)
