# coding: utf-8

import csv
from datetime import datetime

from app import app
from app.mysql.messages import Messages as Message
from app.mysql.message_spams import MessageSpams as MessageSpam


class Report():
    '''

    '''

    def __init__(self, obj=None):
        self.obj = obj

    def _get_items(self):
        '''
        @return list of dict
        '''

        with MessageSpam(role='master') as m:
            msgs = m.get_for_report()

        items = []
        '''
        こういう形にすればよい
        [
            {'id': 1, 'created': 'created1',...},
            {'id': 2, 'created': 'created2',...},
        ]
        '''
        for msg in msgs:
            items.append({
                msg['created'],
                msg['score'],
                (msg['description'].decode('utf-8'))[0:24],
                msg['send_user_id'],
                msg['send_user_nickname'],
                msg['predict'],
                msg['feedback_from_admin'],
                msg['status']
            })

        return items

    def export_kpi(self, after_this_date=None):
        '''
        伏せ字にしたマルチメッセージ数/公開されていたマルチメッセージ数
        マルチメッセージ数の減少推移
        1日を1つの単位とする
        '''

        with Message(role='slave') as m:
            messages = m.get_pos()

        items = {}
        # 日付ごとにカウントする
        for msg in messages:
            created = str(msg['created'].date())

            if created in items:
                items[created].append(1)
            else:
                items[created] = [1]

        for key, val in items.items():
            print('{0}, {1}'.format(key, len(val)))

    def export_csv(self, obj_type=None):
        '''
        @param str obj_type obj_type must be msg, pjt or tsk
        '''

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if self.obj == 'pjt':
            header = [
                'spam',
                'spam_type',
                'obj_type',
                'biz_filter',
                'score',
                'vocabulary',
                'work.id',
                'work.created',
                'work.title',
                'work.description',
                'work.url',
                'user.url',
                'user.nickname',
                'user.status'
            ]

            csv_file = app.config['REPORT_PJT_PATH'].format(now)

        elif self.obj == 'msg':
            header = [
                'created',
                'score',
                'description',
                'send_user_id',
                'send_user_nickname',
                'predict',
                'feedback_from_admin',
                'user.status'
            ]

            csv_file = app.config['REPORT_MSG_PATH'].format(now)

        elif obj_type == 'tsk':
            pass

        else:
            raise Exception('Arg: obj_type must be msg, pjt or tsk')

        # Get items
        items = self._get_items()

        '''
        writerowsにはこういう形式でデータを渡せば良い
        [
            {'id': 1, 'created': 'created1',...},
            {'id': 2, 'created': 'created2',...},
        ]
        '''

        # aは追記、wは上書き
        with open(csv_file, 'a', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header)
            # ヘッダーを書き込む
            w.writeheader()
            # 本文を書き込む
            w.writerows(items)
