# coding: utf-8

import time
import requests
from multiprocessing import Process

from app import app
from app.mysql.messages import Messages
from app.redis.connect import Connect


class Simulate():
    '''
    DBからworks, messagesデータを取得し、Redisキューに入れるための処理
    ローカル環境でテストしたいときに使う
    '''

    def __init__(self):
        '''実行時点での最新のmessage.idをセットする'''
        with Messages(role='slave') as m:
            item_latest = m.get_latest()

        r = Connect().open()
        r.set(app.config['MSG_LAST_PULLED'], item_latest['id'])

    def _get(self):
        '''
        最後に取得した以降に作成されたデータを取得
        @return list
        '''

        r = Connect().open()
        last_pulled_id = r.get(app.config['MSG_LAST_PULLED'])

        with Messages(role='slave') as m:
            items = m.get_for_local(last_pulled_id)

        if not items:
            return []

        r.set(app.config['MSG_LAST_PULLED'], items[-1]['id'])

        return items

    def _send(self, message_id):
        ''''''
        url = 'http://127.0.0.1:8000/v1/spam/messages'
        headers = {
            'Content-Type': 'application/json'
        }
        payload = {
            'message_id': message_id
        }

        res = requests.post(
            url,
            headers=headers,
            json=payload
        )

        if res.status_code != 200:
            app.logger.debug('Send missed')

        return res.status_code

    def _excecute(self):
        ''''''
        items = self._get()
        if not items:
            return

        for item in items:
            self._send(item['id'])

        app.logger.debug('{0}個のメッセージをキューに格納した'.format(len(items)))

    def run(self):
        ''''''

        app.logger.debug('run_simulate start')

        while True:
            try:
                p = Process(target=self._excecute)
                p.start()
                p.join()
            except Exception as e:
                app.sentry.captureException(str(e))
                raise

            time.sleep(20)
