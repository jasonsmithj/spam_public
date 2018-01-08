# coding: utf-8

import re

from app import app
from app.mysql.works import Works as Mysql_works


class BizFilter():
    '''
    predictする前に実行するビジネスフィルター
    '''

    def __init__(self):
        app.config.from_object('config.Whitelists')

    def _user_whitelist(self):
        '''
        ホワイトリストユーザが作成した依頼は 0 とする。
        @return bool
        '''

        for pattern in app.config['REGEX_USERS_WHITELIST']:
            if re.search(pattern, self.item['nickname'].decode('utf-8')):
                return {
                    'predict': 0,
                    'reason': 'whitelist_user'
                }

        for nickname in app.config['USERS_WHITELIST']:
            if nickname == self.item['nickname'].decode('utf-8'):
                return {
                    'predict': 0,
                    'reason': 'whitelist_user'
                }

        return False

    def _keyword_whitelist(self):
        '''
        REGEX_WORKS_HEAD_WORDSで指定した文字列がdescriptionの先頭にあれば 0 とする。
        @return bool
        '''

        for pattern in app.config['REGEX_WORKS_HEAD_WORDS']:
            m = re.search(pattern, self.item['description'].decode('utf-8'))
            if m:
                return {
                    'predict': 0,
                    'reason': 'whitelist_keyword: {0}'.format(m.group(0))
                }

        for keyword in app.config['KEYWORDS_WHITELIST']:
            if keyword in self.item['description'].decode('utf-8'):
                return {
                    'predict': 0,
                    'reason': 'whitelist_keyword: {0}'.format(keyword)
                }

        return False

    def _length_body(self):
        '''
        60文字以下の場合は 0 とする
        @return bool
        '''
        if len(self.item['description'].decode('utf-8')) < 60:
            return {
                'predict': 0,
                'reason': 'less_than_60'
            }

        return False

    def _is_honorific(self, doc):
        '''
        honorific: 敬称
        @param str doc
        @return bool
        '''
        for h in ['さま', '様', 'さん']:
            if h in doc[0:24]:
                return True

        return False

    def _to_sama(self):
        '''
        - 過去にworkを作成したことがある
        - 過去に一度もviolationを作ったことがない
        - titleまたはdescriptionの先頭24文字以内にさま, 様がある
        上記の場合は 0 とする。
        @return bool or dict
        '''

        is_honorific = self._is_honorific(
            self.item['title'].decode('utf-8')
        )

        if not is_honorific:
            is_honorific = self._is_honorific(
                self.item['description'].decode('utf-8')
            )

        if is_honorific:
            with Mysql_works() as m:
                works = m.get_works(self.item['user_id'])

            for work in works:
                if work['violation_status']:
                    return False

            return {
                'predict': 0,
                'reason': 'さん、さま、様が含まれる'
            }

        else:
            return False

    def _msg_(self, doc):
        '''
        仮入金前に連絡先のやりとりをするのは禁止
        仮入金後ならLINE IDの交換をしても良い
        分かち書きする前に指定したキーワードが含まれていれば違反とする
        url,
        '''
        # url
        # https?://[\w/:%#\$&\?\(\)~\.=\+\-]+
        # /(?:^|[\s　]+)((?:https?|ftp):\/\/[^\s　]+)/
        # (https?|ftp)(:\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+)
        m = re.search(r"([\d{1,3}]+.[\d{1,3}]+.[\d{1,3}]+.[\d{1,3}]+)", doc)
        if m:
            return {
                'predict': 1,
                'biz_filter': 'url',
                'reason': m.groups(0)
            }

        # IP address
        # 本当は0-255までなどのルールがあるが、そこまで厳密にするつもりはないので、
        # 単純に 数.数.数.数 という文字列を抽出する
        m = re.search(r"([\d{1,3}]+.[\d{1,3}]+.[\d{1,3}]+.[\d{1,3}]+)", doc)
        if m:
            return {
                'predict': 1,
                'biz_filter': 'ip_address',
                'reason': m.groups()[0]
            }

        # 電話番号、携帯電話番号　それぞれのハイフン有り無し両方の4パターンを網羅
        m = re.search(r"((?:0\d{1,4})?-?\d{1,4}-?\d{1,4})", doc)
        if m:
            return {
                'predict': 1,
                'biz_filter': 'tel',
                'reason': m.groups()[0]
            }

        # e-mail
        m = re.search(r"([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$)", doc)
        if m:
            return {
                'predict': 1,
                'biz_filter': 'mail_address',
                'reason': m.groups()[0]
            }

        # LINE ID
        # LINE IDに法則性はないので、LINE ID, line idなどが含まれてるかをチェックする
        # らxん, LIxN などのパターンが考えられる

    def pjt(self, item):
        '''
        @param dict item
        @return dict
        '''
        self.item = item

        res = self._user_whitelist()
        if res:
            return res

        res = self._keyword_whitelist()
        if res:
            return res

        res = self._length_body()
        if res:
            return res

        res = self._to_sama()
        if res:
            return res

        return {
            'predict': None,
            'reason': None
        }

    def msg(self, item):
        '''
        @param dict item
        @return dict
        '''
        self.item = item

        res = self._keyword_whitelist()
        if res:
            return res

        res = self._length_body()
        if res:
            return res

        res = self._is_honorific(item['description'].decode('utf-8'))
        if res:
            return {
                'predict': 0,
                'reason': 'さん、さま、様が含まれる'
            }

        return {
            'predict': None,
            'reason': None
        }
