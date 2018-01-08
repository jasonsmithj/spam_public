# coding: utf-8

import re
import pytz
from datetime import datetime, timedelta

from app import app
from app.mysql.connect import Connect


class MessageSpams():
    ''''''

    def __init__(self, role='master'):
        self.role = role

    def __enter__(self):
        self.con = Connect(role=self.role)
        self.m = self.con.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None:
            self.con.close()
        else:
            app.logger.warning(
                'MessageSpams mysql connection closing is failed'
            )
            return False

    def _get_spam_status(self, ms):
        '''unit testしやすいようにメソッド化した'''
        if ms['feedback_from_admin'] == 1:
            spam = 2
        elif ms['feedback_from_admin'] == 2:
            spam = 0
        elif ms['feedback_from_user'] == 1:
            spam = 1
        elif ms['predict'] == 1:
            spam = 1
        else:
            spam = 0

        return spam

    def parse(self, mss):
        '''
        本来はここに書くような内容のメソッドではないと思うが、とりあえずここで。
        APIで返す用にパースする。
        SQLの結果をそのまま使いたいことも将来的にはあるだろうから、別メソッドとして分離し、
        呼び出し側でparseを呼び出すスタイルにする
        @param list of dict mss
        @return list
        '''

        items = []

        # 空だった場合
        if not mss:
            return items

        # byte型をそのまま返すことはできないので変換
        # spam項目を追加
        for ms in mss:
            # 非常に稀にdescriptionが空のケースが存在する
            if ms:
                description = re.sub(
                    '\s', '', ms['description'].decode('utf-8'))
            else:
                description = ms['description']

            items.append({
                ms['message_id']: {
                    'id': ms['id'],
                    'created': ms['created'].strftime("%Y-%m-%d %H:%M:%S"),
                    'board_id': ms['board_id'],
                    'message_id': ms['message_id'],
                    'description': description,
                    'send_user_id': ms['send_user_id'],
                    'send_user_nickname':
                        ms['send_user_nickname'].decode('utf-8'),
                    'send_user_status': ms['send_user_status'].decode('utf-8'),
                    'spam': self._get_spam_status(ms)
                }
            })

        return items

    def create(self, args):
        '''
        @param tuple args
        @return int insertされたレコードのID
        '''

        query = ('''
            INSERT INTO message_spams
            (created, modified, board_id, message_id, score, predict, biz_filter)
            VALUES
            (NOW(), NOW(), {0}, {1}, {2}, {3}, '{4}')
        '''.format(args[0], args[1], args[2], args[3], args[4]))

        self.m.execute(query)
        self.con.commit()

        return self.m.lastrowid

    def list_with_board_id(self, board_id):
        '''
        特定のboard_idの全てのmessagesを全て取得する
        message_spamsとleft joinする。
        @param int board_id
        @return list of dict
        '''
        query = ('''
            SELECT
            MsgSpam.id,
            Message.created,
            Message.board_id,
            Board.title,
            Message.id as message_id,
            Message.description,
            Message.user_id as send_user_id,
            User.nickname as send_user_nickname,
            User.status as send_user_status,
            MsgSpam.predict,
            MsgSpam.feedback_from_admin,
            MsgSpam.feedback_from_user
            FROM messages as Message
            LEFT JOIN message_spams as MsgSpam on Message.id = MsgSpam.message_id
            INNER JOIN users as User on User.id = Message.user_id
            INNER JOIN boards as Board on Board.id = MsgSpam.board_id
            WHERE
            Message.board_id = {0}
        '''.format(board_id))

        self.m.execute(query)
        return self.m.fetchall()

    def list_for_admin_page(self, page=1):
        '''
        @param int page
        @return list of dict
            e.g. [{'id': 8,...},...])
        '''
        # オフセット値 = (ページ番号 - 1) * 1ページあたりの表示件数
        offset = (page - 1) * 50
        query = ('''
            SELECT
            MsgSpam.id,
            MsgSpam.created,
            MsgSpam.board_id,
            Board.title,
            MsgSpam.message_id,
            Message.description,
            Message.user_id as send_user_id,
            User.nickname as send_user_nickname,
            User.status as send_user_status,
            MsgSpam.predict,
            MsgSpam.feedback_from_admin,
            MsgSpam.feedback_from_user
            FROM message_spams as MsgSpam
            INNER JOIN messages as Message on Message.id = MsgSpam.message_id
            INNER JOIN users as User on User.id = Message.user_id
            INNER JOIN boards as Board on Board.id = MsgSpam.board_id
            WHERE MsgSpam.feedback_from_admin = 0
            ORDER BY id DESC
            LIMIT 50 OFFSET {0}
        '''.format(offset))

        self.m.execute(query)
        return self.m.fetchall()

    def count(self):
        '''
        API: list messagesのレスポンスで使用する
        @return int
        '''
        query = ('''
            SELECT
            count(*) as count
            FROM message_spams as MsgSpam
            WHERE
            MsgSpam.feedback_from_admin = 0
        ''')

        self.m.execute(query)
        res = self.m.fetchone()
        return res['count']

    def get_for_report(self):
        '''
        blacked判定されるuserは1日遅れでもいるだろうから、blacked判定が確定されるのが、
        1日前だと仮定して、1日前のデータをレポーティングする
        2日前の17:00:00 ~ 昨日の17:00:00 のデータを取得する
        '''

        now = datetime.now(pytz.timezone('Asia/Tokyo'))

        # 2日前の17:00:00
        five_two_days_ago = (now - timedelta(days=2)).replace(
            hour=17, minute=00, second=00, microsecond=00
        ).strftime("%Y-%m-%d %H:%M:%S")

        # 昨日の17:00:00
        five_yesterday = (now - timedelta(days=1)).replace(
            hour=17, minute=00, second=00, microsecond=00
        ).strftime("%Y-%m-%d %H:%M:%S")

        query = ('''
            SELECT
            MsgSpam.id,
            MsgSpam.created,
            MsgSpam.board_id,
            MsgSpam.message_id,
            MsgSpam.score,
            Message.description,
            Message.user_id as send_user_id,
            User.nickname as send_user_nickname,
            User.status as send_user_status,
            MsgSpam.predict,
            MsgSpam.feedback_from_admin,
            MsgSpam.feedback_from_user
            FROM message_spams as MsgSpam
            INNER JOIN messages as Message on Message.id = MsgSpam.message_id
            INNER JOIN users as User on User.id = Message.user_id
            WHERE
            MsgSpam.created between '{0}' AND '{1}'
        '''.format(five_two_days_ago, five_yesterday))

        self.m.execute(query)
        return self.m.fetchall()

    def is_exist(self, message_spam_id):
        '''
        @param int message_spam_id
        @return bool
        '''
        query = ('''
            SELECT
            MsgSpam.id
            FROM message_spams as MsgSpam
            WHERE
            MsgSpam.id = {0}
        '''.format(message_spam_id))

        self.m.execute(query)
        res = self.m.fetchone()

        if res:
            return True
        else:
            return False

    def get_detail(self, message_spam_id):
        '''
        そもそもmessage_spamsテーブルには送信者のmessageしか保存されない
        @param int message_spam_id
        @return dict
        '''
        query = ('''
            SELECT
            MsgSpam.id,
            MsgSpam.created,
            MsgSpam.board_id,
            Board.title as board_title,
            MsgSpam.message_id,
            MsgSpam.predict,
            MsgSpam.feedback_from_admin,
            MsgSpam.feedback_from_user,
            MsgSpam.biz_filter,
            Message.description,
            Message.user_id as send_user_id,
            User.nickname as send_user_nickname,
            User.status as send_user_status
            FROM message_spams as MsgSpam
            INNER JOIN messages as Message on Message.id = MsgSpam.message_id
            INNER JOIN users as User on User.id = Message.user_id
            INNER JOIN boards as Board on Board.id = MsgSpam.board_id
            WHERE
            MsgSpam.id = {0}
        '''.format(message_spam_id))

        self.m.execute(query)
        return self.m.fetchone()

    def get_board_users(self, board_id):
        '''
        @param int board_id
        @return list of dict
        '''
        query = ('''
            SELECT
            BoardUser.user_id
            FROM board_users as BoardUser
            WHERE
            BoardUser.board_id = {0}
        '''.format(board_id))

        self.m.execute(query)
        return self.m.fetchall()

    def edit(self, args):
        '''
        v1.0の時点では、feedback_from_adminのみ許可している
        @param tuple args
        @return int insertされたレコードのID
        '''

        query = ('''
            UPDATE message_spams SET
            feedback_from_admin = {0},
            modified = NOW()
            WHERE id = {1}
        '''.format(args[0], args[1]))

        self.m.execute(query)
        self.con.commit()

        return self.m.lastrowid
