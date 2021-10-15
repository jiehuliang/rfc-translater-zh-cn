
# RFC Translater

### 目的
1. 因为RFC的英语太难读了，所以想读谷歌翻译的并排句子。
[RFC的日语翻译链接集](https://www.nic.ad.jp/ja/tech/rfc-jp-links.html)那么，原文和日语翻译是分开的，有个问题是很难判断日语翻译是否正确。
2. RFC的正文是换行的，如果不删除换行之后再粘贴到谷歌翻译中，就不能正确翻译。解决删除换行的麻烦

### 步骤
1. RFC的索引获取 https://tools.ietf.org/rfc/index (fetch_index)
1. RFC筛选 https://datatracker.ietf.org/doc/html/rfcXXXX (fetch_rfc)
2. 去除每个部分的分割和换行 (fetch_rfc)
3. 用谷歌翻译把英语变成日语 (trans_rfc)
4. 生成按小节排列英文、日文的页面 (make_html)
5. 对有名的RFC和点击率高的网页，进行翻译修改等工作 (人工)

### 注意事項
- 有时我们无法很好地理解多页的图和表格。
- 当一个图或表格中包含空行时，它也不能很好地解释。
- 如果RFC的HTML是特殊结构，它也不能很好地解释(特别是编号小的RFC)
- 以RFC2220以后为对象 (http://rfc-jp.nic.ad.jp/copyright/translate.html)

<br>

## 当你想修改翻译时，

感谢您使用本网站。
翻译修改的顺序如下。

### 翻译修改者

1. 在GitHub上Fork。
2. 剪掉早午餐。取个合适的名字。
3. html/rfcXXXX.html的翻译修改。。
   - updated_byを「翻译编辑 : 自動生成 + 一部修正」这样。如果你想留下你的名字「一部修正(tex2e)」请这样写。
   - 使用`<h5>`。第一个写英文，第二个写日文。
      ```html
      <div class="row">
        <div class="col-sm-12 col-md-6">
          <h5 class="text mt-2">
      1.  Introduction
          </h5>
        </div>
        <div class="col-sm-12 col-md-6">
          <h5 class="text mt-2">
      1. 前言
          </h5>
        </div>
      </div>
      ```
   - 文章は`<p>`を使います。「indent-X」class中指定缩进的深度。
      ```html
      <div class="row">
        <div class="col-sm-12 col-md-6">
          <p class="text indent-3">
      Hello, world!
          </p>
        </div>
        <div class="col-sm-12 col-md-6">
          <p class="text indent-3">
      你好，世界！
          </p>
        </div>
      </div>
      ```
   - 图表`<pre>`使用。只有英文。
      ```html
      <div class="row">
        <div class="col-sm-12 col-md-12">
          <pre class="text text-monospace">
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- - - - - - - - -
          |  Option Type  |  Opt Data Len |  Option Data
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- - - - - - - - -
          </pre>
        </div>
      </div>
      ```
4. 在浏览器中打开修改后的HTML，检查是否显示正确。
5. push到Fork过的资料库中。
6. 在GitHub上发布PullRequest。

### 管理者

1. 检查PullRequest的修改差异，只检查是否正确进行了HTML转移，以及是否存在与XSS相关的字符串(`script`， `a`， `img`， `javascript`等)
2. 如果没有问题就Merge，本地pull
3. `main.py --make-json --rfc <目标RFC>` 用HTML反向创建JSON，确认变更差异
4. `main.py --make --rfc <目标RFC>` 用JSON反向创建HTML，确认变更差异
5. 推送到资料库

<br>

## 面向开发者

### 实现功能
- 只翻译文章，直接表示图和表
- 即使文章是分页的，也要翻译成一个段落
- 也反映缩进的深度
- 分条标记(o + * -等)的符号
- 标题(1.2. ~等)文字要大
- 即使滚动原本(英语RFC)的链接也总是显示
- 对于被取消的RFC，显示被取消和到修改版RFC的链接（例：RFC2246, RFC2616）

動作環境：Python3 + Windows or MacOS

```
pip install requests lxml
pip install Mako
pip install tqdm
pip install googletrans==4.0.0-rc1
pip install selenium
pip install beautifulsoup4
```

Windowsの場合は、py -m pip に読み替えてください。

**注意：翻译工作非常花时间。翻译一个RFC短则需要5分钟，长则需要30分钟到1个小时。**
在开发初期，我启动多个实例，24小时同时运行，这样做了半年左右。

2021/02/27 补充:因为googletrans3.0.0不太好用，所以改用Selenium的谷歌翻译。
如果你想使用传统的方法， `--transmode py-googletrans` 请指定。

SeleniumではFirefoxを使用しているため、geckodriver のダウンロードが必要です。
geckodriverの配置場所を環境変数 WEBDRIVER_EXE_PATH に指定してから実行してください。
詳細は src/trans_rfc.py の WEBDRIVER_EXE_PATH を参照ください。

```bash
python main.py --rfc 123 # RFC 123翻译(获取+翻译+生成HTML)
python main.py --rfc 123 --fetch # 获取RFC
python main.py --rfc 123 --trans # 翻译RFC
python main.py --rfc 123 --make # 生成HTML
python main.py --begin 2220 --end 10000 # RFC 2220〜10000 按顺序翻译
python main.py --make --begin 2220 --end 10000 # RFC 2220〜10000 生成的HTML
python main.py # 按顺序翻译未翻译的RFC
python main.py --begin 8000 --only-first # RFC 8000从开头选择一个以后的未翻译RFC进行翻译

python main.py --rfc 123 --transmode selenium       # Seleniumを使用してGoogle翻訳(デフォルト)
python main.py --rfc 123 --transmode py-googletrans # googletransを使用してGoogle翻訳
```

生成物：
1. fetch_rfc（取得） ... data/A000/B00/rfcABCD.json (段落区切りで取り出した文章)
2. trans_rfc（翻訳） ... data/A000/B00/rfcABCD-trans.json (各文章の翻訳を加えたもの)
3. make_html（生成） ... html/rfcABCD.html (原文と翻訳を並べて表示するHTML)

```bash
python main.py --make-index # インデックスページの作成
```

ローカルで成果物の確認

```bash
python -m http.server
# localhost:8000/htmlにアクセス
```

RFCを解析した結果、本来プログラムとして解釈すべき部分を文章として解釈してしまった場合、プログラムのインデントを削除してJSON化するツール：
[https://tex2e.github.io/rfc-translater/html/format.html](https://tex2e.github.io/rfc-translater/html/format.html)


<br>

---

#### Figs

各RFCから図のみを集めて公開するサイト「RFC Figs」について

```bash
# 1000個のRFC毎に図を集め、JSONファイルで保存する
python3 figs/collect_figures.py --begin 0000 --end 0999 -w figs/data/0000.json
...
python3 figs/collect_figures.py --begin 7000 --end 7999 -w figs/data/7000.json

# JSONをHTMLに変換する
python3 figs/make_html.py 0000
...
python3 figs/make_html.py 7000

# インデックスページの作成
python3 figs/make_index.py
```
