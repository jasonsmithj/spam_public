# coding: utf-8

import pytz
from datetime import datetime

from app import app
from app.mysql.connect import Connect


class Works():
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
            app.logger.warning('Work mysql connection closing is failed')
            return False

    def get_latest_pjt(self):
        '''
        一番新しいpjtを取得する
        @return dict
        '''

        query = ('''
            SELECT
            Work.id
            FROM works as Work
            WHERE type = 'project'
            order by Work.id desc
            limit 1
        ''')

        self.m.execute(query)
        return self.m.fetchone()

    def get_for_local(self, after_this_id):
        '''
        指定日時以降に作成された送信者のpjtを取得
        @param int after_this_id
        @return list
        '''

        if not after_this_id:
            app.logger.debug('after_this_id を手動でRedisにsetすること')
            return

        query = ('''
            SELECT
            Work.id
            FROM works as Work
            WHERE
            Work.type = 'project' AND
            Work.id > {0}
            order by Work.id asc
        '''.format(after_this_id))

        self.m.execute(query)
        return self.m.fetchall()

    def get_work_user(self, work_id):
        '''
        work id とそのworkを作ったuserを取得する
        @return dic
            e.g. {'id': 1594834, ...
        '''
        query = ('''
            SELECT
            Work.id,
            Work.created,
            Work.title,
            Work.description,
            Work.type,
            Work.status as work_status,
            User.id as user_id,
            User.created as user_created,
            User.nickname,
            User.status as user_status
            FROM works AS Work
            INNER JOIN users as User ON Work.user_id = User.id
            WHERE Work.id = {0}
        '''.format(work_id))

        self.m.execute(query)
        return self.m.fetchone()

    def get(self, min_datetime=None, max_datetime=None):
        '''
        違反検知の対象となるworkを取得
        ランサーストアは対象外とする
        Localで動かすバッチで使用する専用のメソッド
        @param string min_datetime
        @param string max_datetime
        @return list
          e.g. [{'id': 391778,...
        '''

        if min_datetime:
            min_datetime = min_datetime
        else:
            # 何も指定されなければ、実行時の00:00:00とする
            now = datetime.now(pytz.timezone('Asia/Tokyo'))
            min_datetime = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        if max_datetime:
            max_datetime = max_datetime
        else:
            # 指定されていなければ現時点をセット
            now = datetime.now(pytz.timezone('Asia/Tokyo'))
            max_datetime = now.strftime('%Y-%m-%d %H:%M:%S')

        query = ('''
            SELECT
            Work.id,
            Work.created as created,
            Work.title,
            Work.description,
            Work.type,
            Work.violation_status,
            Work.status as work_status,
            User.id as user_id,
            User.created as user_created,
            User.nickname,
            User.status as user_status
            FROM works as Work
            INNER JOIN users as User on Work.user_id = User.id
            LEFT JOIN menus_works as MenuWorks on Work.id = MenuWorks.work_id
            where
            MenuWorks.id is null AND
            Work.type = 'project' AND
            Work.created between '{0}' AND '{1}'
        '''.format(min_datetime, max_datetime))

        self.m.execute(query)
        return self.m.fetchall()

    def get_works(self, user_id):
        '''
        過去にworkを作成したか、violationを作ったことがあるかを調べるためのSQL
        @return list
          e.g. [{'id': 391778,
                'created': datetime.datetime(2014, 8, 3, 12, 28, 48),...
        '''
        query = ('''
            SELECT
            Work.id,
            Work.violation_status
            FROM works AS Work
            WHERE
            Work.user_id = {0}
        '''.format(user_id))

        self.m.execute(query)
        return self.m.fetchall()

    def get_pos(self, min_datetime=None, max_datetime=None):
        '''
        users.statusがblackedのユーザが作成したworkを取得する
        blackedというのは、退会処理させられるとセットされる値
        重複内容が多いが、2017-09-06時点で19,469件あった
        重複を取り除くと 3,595 になった。重複を取り除く計算に丸二日かかった
        @param string max_datetime
        @param string min_datetime
        @return list
          e.g. [{'id': 391778,
                'created': datetime.datetime(2014, 8, 3, 12, 28, 48),...
        '''

        if min_datetime:
            min_datetime = min_datetime
        else:
            # 一番古いblackedが作成したレコードは'2014-08-03 12:28:48'から存在するが、
            # CCチームが基準を定めて本格対応し始めたのが2017-02-01 00:00:00からなので
            # 2017-02-01 00:00:00以降のデータのみを対象とする
            min_datetime = '2017-02-01 00:00:00'

        if max_datetime:
            max_datetime = max_datetime
        else:
            # 指定されていなければ現時点をセット
            now = datetime.now(pytz.timezone('Asia/Tokyo'))
            max_datetime = now.strftime('%Y-%m-%d %H:%M:%S')

        query = ('''
            SELECT
            Work.id,
            Work.user_id,
            Work.created,
            Work.title,
            Work.description,
            Work.type,
            Work.violation_status
            FROM works as Work
            INNER JOIN users on Work.user_id = users.id
            WHERE
            users.status = "blacked" AND
            Work.created between '{0}' AND '{1}' AND
            Work.type = 'project'
            order by id desc
        '''.format(min_datetime, max_datetime))

        self.m.execute(query)
        return self.m.fetchall()

    def get_neg(self, max_datetime=None, min_datetime=None):
        '''
        クライアントが作った良質なworkをmlmのnegativeとする
        @param string max_datetime
        @param string min_datetime
        @return list
          e.g. [{'id': 391778,...
        '''

        if min_datetime:
            min_datetime = min_datetime
        else:
            min_datetime = '2016-09-01 00:00:00'

        if max_datetime:
            max_datetime = max_datetime
        else:
            # 指定されていなければ現時点をセット
            now = datetime.now(pytz.timezone('Asia/Tokyo'))
            max_datetime = now.strftime('%Y-%m-%d %H:%M:%S')

        query = ('''
            SELECT
            Work.id,
            Work.user_id,
            Work.created,
            Work.title,
            Work.description,
            Work.type,
            Work.violation_status
            FROM works as Work
            INNER JOIN users as User on Work.user_id = User.id
            INNER JOIN user_profiles as UPro on User.id = UPro.user_id
            INNER JOIN work_infos as WorkInfo on Work.id = WorkInfo.work_id
            LEFT JOIN menus_works as MenuWorks on Work.id = MenuWorks.work_id
            WHERE
            User.status = "active" AND
            User.deleted = '' AND
            UPro.purpose = 1 AND
            UPro.feedback_count > 20 AND
            Work.type = 'project' AND
            Work.violation_status = '' AND
            Work.status = 'completed' AND
            WorkInfo.view_count >= 5 AND
            Work.private = 0 AND
            Work.expert = 0 AND
            Work.award_early = 0 AND
            Work.open_level IN (0, 10) AND
            MenuWorks.id is null AND
            Work.created BETWEEN '{0}' AND '{1}'
        '''.format(min_datetime, max_datetime))

        self.m.execute(query)
        return self.m.fetchall()

    def _get_vl_pos(self, min_datetime=None, max_datetime=None, work_type='project'):
        '''
        violation_statusは99%がotherになっている。
        @param string max_datetime
        @param string min_datetime
        @return list
          e.g. [{'id': 391778,...
        '''

        if min_datetime:
            min_datetime = min_datetime
        else:
            # 一番古いblackedが作成したレコードは'2011-07-20 16:53:38'から存在するが、
            # CCチームが基準を定めて本格対応し始めたのが'2016-10-01 00:00:00'0からなので
            # '2016-10-01 00:00:00'以降のデータのみを対象とする
            min_datetime = '2016-10-01 00:00:00'

        if max_datetime:
            max_datetime = max_datetime
        else:
            # 指定されていなければ現時点をセット
            now = datetime.now(pytz.timezone('Asia/Tokyo'))
            max_datetime = now.strftime('%Y-%m-%d %H:%M:%S')

        query = ('''
            SELECT
            Work.id,
            Work.user_id,
            Work.created,
            Work.title,
            Work.description,
            Work.type,
            Work.violation_status
            FROM works AS Work
            INNER JOIN users on Work.user_id = users.id
            WHERE
            users.status != "blacked" AND
            Work.violation_status = 'other' AND
            Work.created between '{0}' AND '{1}' AND
            Work.type = '{2}'
            order by id desc
        '''.format(min_datetime, max_datetime, work_type))

        self.m.execute(query)
        return self.m.fetchall()

    def _get_vl_neg(self, max_datetime=None, min_datetime=None):
        '''
        Negative data for violation
        @param string max_datetime
        @param string min_datetime
        @return list
          e.g. [{'id': 391778,...
        '''

        app.config.from_object('config.Whitelists')

        if min_datetime:
            min_datetime = min_datetime
        else:
            min_datetime = '2017-08-01 00:00:00'

        if max_datetime:
            max_datetime = max_datetime
        else:
            # 指定されていなければ現時点をセット
            now = datetime.now(pytz.timezone('Asia/Tokyo'))
            max_datetime = now.strftime('%Y-%m-%d %H:%M:%S')

        query = ('''
            SELECT
            Work.id,
            Work.user_id,
            Work.created,
            Work.title,
            Work.description,
            Work.type,
            Work.violation_status
            FROM works as Work
            INNER JOIN users as User on Work.user_id = User.id
            INNER JOIN user_profiles as UPro on User.id = UPro.user_id
            INNER JOIN work_infos as WorkInfo on Work.id = WorkInfo.work_id
            LEFT JOIN menus_works as MenuWorks on Work.id = MenuWorks.work_id
            WHERE
            User.status = "active" AND
            User.deleted = '' AND
            Work.type = 'project' AND
            Work.violation_status = '' AND
            Work.status = 'completed' AND
            Work.created BETWEEN '{0}' AND '{1}' AND
            MenuWorks.id is null
        '''.format(min_datetime, max_datetime))

        self.m.execute(query)
        return self.m.fetchall()
