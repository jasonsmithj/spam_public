# coding: utf-8

import pytz
from datetime import datetime

from app import app
from app.mysql.connect import Connect


class Messages():
    '''
    コンテキストマネージャで呼び出すこと。
    '''

    def __init__(self, role='master'):
        self.role = role

    def __enter__(self):
        self.con = Connect(role=self.role)
        self.m = self.con.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        '''
        意図的にcloseしてあげないとすぐこのエラーが発生する。
        ReferenceError: weakly-referenced object no longer exists
        '''
        if exc_type is None:
            self.con.close()
        else:
            app.logger.warning('Message mysql connection closing is failed')
            return False

    def get_for_local(self, after_this_id):
        '''
        指定日時以降に作成された送信者のmessagesを取得
        @param int after_this_id
        @return list
        '''

        if not after_this_id:
            app.logger.debug('after_this_id を手動でRedisにsetすること')
            return

        query = ('''
            SELECT
            Message.id
            FROM messages as Message
            WHERE
            Message.id > {0}
            order by Message.id asc
        '''.format(after_this_id))

        self.m.execute(query)
        return self.m.fetchall()

    def get_latest(self):
        '''
        一番新しいmessageを取得する
        restore時に使用する
        '''

        query = ('''
            SELECT
            Message.id
            FROM messages as Message
            order by Message.id desc
            limit 1
        ''')

        self.m.execute(query)
        return self.m.fetchone()

    def get_messages(self, message_id):
        '''
        messageが属するboardのメッセージを全て取得する
        user_id_aとuser_id_bが同じであれば同じユーザが作成したmessageとなる
        @param list board_ids
        @return list of dict
        '''

        query = ('''
            SELECT
            Msg_B.id,
            Board.owner_id,
            User.nickname,
            Message.user_id as user_id_a,
            Msg_B.user_id as user_id_b,
            Msg_B.board_id,
            Msg_B.description
            FROM messages as Message
            INNER JOIN messages as Msg_B on Message.board_id = Msg_B.board_id
            INNER JOIN boards as Board on Board.id = Msg_B.board_id
            INNER JOIN users as User on User.id = Msg_B.user_id
            WHERE
            Msg_B.description != 'send file' AND
            Msg_B.description != '' AND
            Msg_B.description IS NOT NULL AND
            Message.id = {0}
        '''.format(message_id))

        self.m.execute(query)
        return self.m.fetchall()

    def get_pos(self, min_datetime=None, max_datetime=None):
        '''
        blackedユーザのmessagesを取得
        2017-09-13時点で約12万件ある
        Message.user_id = Board.owner_id を指定することで、
        送信者のmessageのみを取得する
        @param string max_datetime
        @param string min_datetime
        @return list
          e.g. [{'id': 391778,...
        '''

        if min_datetime:
            min_datetime = min_datetime
        else:
            # MLMに関して、CCチームが基準を定めて本格対応し始めたのが
            # 2017-02-01 00:00:00からなので2017-02-01 00:00:00以降の
            # データのみを対象とする
            min_datetime = '2017-02-01 00:00:00'

        if max_datetime:
            max_datetime = max_datetime
        else:
            # 指定されていなければ現時点をセット
            max_datetime = datetime.now(
                pytz.timezone('Asia/Tokyo')
            ).strftime('%Y-%m-%d %H:%M:%S')

        query = ('''
            SELECT
            Message.id,
            Message.user_id,
            Message.created,
            Message.board_id,
            Message.description
            FROM messages as Message
            INNER JOIN users as User on Message.user_id = User.id
            INNER JOIN boards as Board on Board.id = Message.board_id
            WHERE
            User.status = "blacked" AND
            Message.user_id = Board.owner_id AND
            Message.created between '{0}' AND '{1}' AND
            Message.description != 'send file' AND
            Message.description != '' AND
            Message.description IS NOT NULL
        '''.format(min_datetime, max_datetime))

        self.m.execute(query)
        return self.m.fetchall()

    def get_neg(self, min_datetime=None, max_datetime=None):
        '''
        クライアントユーザの不正ではないmessagesを取得
        feedback_countを指定することで違反メッセージを作成するようなユーザではない
        であろうことを保証している。min_datetimeはpositiveに合わせる
        Message.user_id = Board.owner_id を指定することで、
        送信者のmessageのみを取得する
        @param string max_datetime
        @param string min_datetime
        @return list
          e.g. [{'id': 391778,...
        '''

        if min_datetime:
            min_datetime = min_datetime
        else:
            min_datetime = '2017-02-01 00:00:00'

        if max_datetime:
            max_datetime = max_datetime
        else:
            # 指定されていなければ現時点をセット
            max_datetime = datetime.now(
                pytz.timezone('Asia/Tokyo')
            ).strftime('%Y-%m-%d %H:%M:%S')

        query = ('''
            SELECT
            Message.id,
            Message.user_id,
            Message.created,
            Message.board_id,
            Message.description
            FROM messages as Message
            INNER JOIN users as User on Message.user_id = User.id
            INNER JOIN user_profiles as UPro on User.id = UPro.user_id
            INNER JOIN boards as Board on Board.id = Message.board_id
            WHERE
            User.status = "active" AND
            User.created between '2015-01-01 00:00:00' AND '2016-12-31 23:59:59' AND
            User.deleted = '' AND
            UPro.actived > '2017-10-01 00:00:00' AND
            UPro.lancers_check = 1 AND
            UPro.identification = 1 AND
            UPro.phone_check = 'checked' AND
            UPro.feedback > 4 AND
            UPro.feedback_count > 10 AND
            Message.created between '{0}' AND '{1}' AND
            Message.description != 'send file' AND
            Message.description != '' AND
            Message.description IS NOT NULL AND
            Message.user_id = Board.owner_id
        '''.format(min_datetime, max_datetime))

        self.m.execute(query)
        return self.m.fetchall()
