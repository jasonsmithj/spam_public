# coding: utf-8

import MeCab
import unicodedata
import re

from app import app


class Wakati():
    '''
    MeCabを使った分かち書き
    固有名詞等の辞書には mecab-ipadic-neologd を採用している
    文字列の正規化は下記ページを参照
    https://github.com/neologd/mecab-ipadic-neologd/wiki/Regexp.ja
    '''

    def __init__(self):
        # ハッシュタグまで探すことができる。
        # e.g. https://www.google.com?id=1&name=taro#page2
        self.url_pattern = \
            app.config['URL_PATTERN']

    def _unicode_normalize(self, cls, s):
        pt = re.compile('([{}]+)'.format(cls))

        def norm(c):
            return unicodedata.normalize('NFKC', c) if pt.match(c) else c

        s = ''.join(norm(x) for x in re.split(pt, s))
        s = re.sub('－', '-', s)
        return s

    def _remove_extra_spaces(self, s):
        s = re.sub('[ 　]+', ' ', s)
        blocks = ''.join(('\u4E00-\u9FFF',  # CJK UNIFIED IDEOGRAPHS
                          '\u3040-\u309F',  # HIRAGANA
                          '\u30A0-\u30FF',  # KATAKANA
                          '\u3000-\u303F',  # CJK SYMBOLS AND PUNCTUATION
                          '\uFF00-\uFFEF'   # HALFWIDTH AND FULLWIDTH FORMS
                          ))
        basic_latin = '\u0000-\u007F'

        def remove_space_between(cls1, cls2, s):
            p = re.compile('([{}]) ([{}])'.format(cls1, cls2))
            while p.search(s):
                s = p.sub(r'\1\2', s)
            return s

        s = remove_space_between(blocks, blocks, s)
        s = remove_space_between(blocks, basic_latin, s)
        s = remove_space_between(basic_latin, blocks, s)
        return s

    def _remove_numeric(self, s):
        '''
        文から数字を取り除く。数字が文の類似度に関係していないという推測の元、取り除く
        _unicode_normalizeが全角を半角にするので、そのあとに実行すること
        '''
        s = re.sub('[0-9０-９]', '', s)
        s = re.sub('[一二三四五六七八九十壱弐参拾百千万萬億兆〇]+', '', s)
        return s

    def _convert_url(self, s):
        '''
        与えられた文字列にURLが含まれる場合、その部分を"url"に置き換える。
        chatwork.comはよく使われるが、スパムである可能性が低いので取り除くだけにする
        mecabの辞書には url は URL として大文字で登録されているようなので、
        replace(xx, 'url')とするとparseメソッドの返り値としては URL になる。
        なので、最初から大文字を指定しておく
        '''
        for m in re.finditer(self.url_pattern, s):
            if m:
                if 'chatwork.com' in m.group():
                    s = s.replace(m.group(), '')
                s = s.replace(m.group(), 'URL')

        return s

    def remove_remove_words(self, s):
        # Read remove words
        app.config.from_object('config.Words')

        for word in app.config['REMOVE_WORDS']:
            s = re.sub(word, '', s)
        return s

    def _normalize_neologd(self, s):
        # 文字列の先頭と末尾から空白・改行を除去する
        s = s.strip()
        # 最初の段階でURLに対しての処理を実行する
        s = self._convert_url(s)
        s = self.remove_remove_words(s)
        s = self._remove_numeric(s)

        s = self._unicode_normalize('０-９Ａ-Ｚａ-ｚ｡-ﾟ', s)

        def maketrans(f, t):
            return {ord(x): ord(y) for x, y in zip(f, t)}

        s = re.sub('[˗֊‐‑‒–⁃⁻₋−]+', '-', s)  # normalize hyphens
        s = re.sub('[﹣－ｰ—―─━ー]+', 'ー', s)  # normalize choonpus
        s = re.sub('[~∼∾〜〰～]', '', s)  # remove tildes
        s = s.translate(
            maketrans(
                '!"#$%&\'()*+,-./:;<=>?@[¥]^_`{|}~｡､･｢｣',
                '！”＃＄％＆’（）＊＋，－．／：；＜＝＞？＠［￥］＾＿｀｛｜｝〜。、・「」'
            )
        )

        s = self._remove_extra_spaces(s)
        # keep ＝,・,「,」
        s = self._unicode_normalize(
            '！”＃＄％＆’（）＊＋，－．／：；＜＞？＠［￥］＾＿｀｛｜｝〜',
            s
        )
        s = re.sub('[’]', '\'', s)
        s = re.sub('[”]', '"', s)

        return s

    def parse(self, doc):
        '''
        日本語を分かち書きにするためのメソッド
        動詞と名詞の基本形だけを抜き出す
        @param string doc
        @return string 分かち書きにしたdocumentを返す
        '''

        if not doc:
            return ''

        # -Ochasenを指定するとtabで区切られる。こんな感じ。
        # ['C言語\tシーゲンゴ\tC言語\t名詞-固有名詞-一般\t\t']
        tagger = MeCab.Tagger(
            '-Ochasen -d {0}'.format(app.config['NEOLOGD_PATH'])
        )

        # 正規化した上で分形態素解析して、1行ごとに区切ってリスト化する
        words = tagger.parse(self._normalize_neologd(doc)).split('\n')

        # 対象にしない品詞たち
        parts = ['非自立', '接尾', '代名詞', '数']

        val = []
        for word in words:
            # EOS, ''の場合は無視
            if word == 'EOS' or word == '':
                continue

            # タブで区切り、リスト化
            word_info = word.split('\t')

            # word_info[3]に品詞が格納されている
            part = word_info[3].split('-')

            if part[-1] in parts:
                continue

            if len(part) >= 3:
                if part[-2] in parts:
                    continue

            if part[0] in ['名詞']:
                # 3番目に基本形が格納されている
                val.append(word_info[2])

        # ホワイトスペースでつなげて1つの文字列にする
        return ' '.join(val)
