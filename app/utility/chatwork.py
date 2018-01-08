# coding: utf-8

import os
import json
import requests

from app import app
from app.redis.connect import Connect


class Chatwork():

    def __init__(self):
        self.url = 'https://api.chatwork.com/v2/'
        self.headers = {
            'X-ChatWorkToken': os.environ.get('CHATWORK_TOKEN')
        }

    def is_connect(self):
        '''
        疎通確認用
        chatworkは5分で100回のAPI呼び出し制限があるので、無駄にこのメソッドを呼び出さないこと
        @return bool
        '''

        # Works Room
        url_works = self.url + 'rooms/{0}'.format(app.config['ROOM_ID_WORKS'])
        # Messages Room
        url_messages = self.url + 'rooms/{0}'.format(app.config['ROOM_ID_MSG'])

        try:
            r_works = requests.get(url_works, headers=self.headers)
            r_messages = requests.get(url_messages, headers=self.headers)
            if r_works.status_code == 200 and r_messages.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            app.sentry.captureException(str(e))
            app.logger.error(
                'Chawtwork is_connect is failed. Reason: {0}'.format(e))
            return False

    def _send(self, room_id, body):
        '''
        @param int room_id
        @param string body
        @return int 正常に完了すれば200が返る。それ以外は500を返すようにしている
        '''

        url = self.url + 'rooms/{0}/messages'.format(room_id)
        payload = {
            'body': body
        }

        try:
            res = requests.post(
                url,
                headers=self.headers,
                data=payload
            )
            return res.status_code
        except Exception as e:
            app.sentry.captureException(str(e))
            # chatworkに接続できない場合はjsonで1つの文字列にしてキューに入れる
            # 接続できない場合はConnectionErrorが発生する
            Connect().open().rpush(
                app.config['QUEUE_CHATWORK_MSG'],
                json.dumps({'room_id': room_id, 'body': body}))

            app.logger.error(
                'Chawtwork _send is failed. Reason: {0}'.format(e))
            return 500

    def post(self, room_id, body):
        '''
        @param int room_id
        @param string body
        @return int 正常に完了すれば200が返る
        chatworkにメッセージを送る
        '''

        r = Connect().open()

        # キューに入っているのがあればまとめてpostする
        # lrangeは値がなければ空のlistを返す
        items_len = r.llen(app.config['QUEUE_CHATWORK_MSG'])
        if items_len >= 1:
            for i in range(items_len):
                item = r.lpop(app.config['QUEUE_CHATWORK_MSG'])
                item = json.loads(item)
                self._send(item['room_id'], item['body'])

        return self._send(room_id, body)
