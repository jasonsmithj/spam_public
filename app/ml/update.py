# coding: utf-8

import os
import pytz
from datetime import datetime, timedelta
from multiprocessing import Pool

from app import app
from app.ml.overlap import Overlap
from app.ml.wakati import Wakati
from app.mysql.works import Works as Mysql_works
from app.mysql.messages import Messages as Mysql_messages
from app.redis.connect import Connect
from app.redis.objects import Objects as Redis_objects


class Update:
    '''
    positive, negativeデータを更新する
    '''

    def __init__(self, key_name=None, obj_type=None, days_ago=2):
        self.key_name = key_name
        self.days_ago = int(days_ago)

        if obj_type not in ['pjt_mlm', 'pjt_vl', 'msg']:
            raise Exception('obj_type must be pjt_mlm, pjt_vl or msg')

        self.obj_type = obj_type

    def _get_date(self):
        '''
        2日前と今日の17:00:00を取得
        @return tuple str:days_ago, str:today_five
        '''
        # 2日前の17:00:00を文字列として取得
        now = datetime.now(pytz.timezone('Asia/Tokyo'))
        days_ago = (now - timedelta(days=self.days_ago)).replace(
            hour=17, minute=00, second=00, microsecond=00
        ).strftime("%Y-%m-%d %H:%M:%S")

        # 本日17:00:00を文字列として取得
        now = datetime.now(pytz.timezone('Asia/Tokyo'))
        today_five = now.replace(
            hour=17, minute=00, second=00, microsecond=00
        ).strftime("%Y-%m-%d %H:%M:%S")

        return days_ago, today_five,

    def _get_pjt(self, work_type=None):
        '''
        @return list of tuple
            [(b_id, [b_body]),...]
        '''

        days_ago, today_five = self._get_date()

        # 2日前以降、本日17:00:00までのPositiveデータを取得
        with Mysql_works(role='slave') as m:
            if work_type == 'mlm':
                items = m.get_pos(days_ago, today_five)

            if work_type == 'vl':
                items = m.get_vl_pos(days_ago, today_five)

        works = []
        # Convert to list of tuple
        for item in items:
            if not item['title'] or not item['description']:
                continue

            # わざわざ変数に入れる必要はないが、1行が長くならないようにするための対応
            title = item['title'].decode('utf-8')
            desc = item['description'].decode('utf-8')

            works.append((item['id'], [title + ' ' + desc]))

        return works

    def _get_msg(self):
        '''
        @return list of tuple
            [(b_id, [b_body]),...]
        '''

        days_ago, today_five = self._get_date()

        with Mysql_messages(role='slave') as m:
            msg_latest = m.get_pos(days_ago, today_five)

        # 同じboard_idのdescriptionをまとめる。こういう形式にする。
        # [{'board_id1': ['description1', 'description2']},
        #  {'board_id2': ['description']},...}]
        boards_dict = {}
        for item in msg_latest:
            if item['board_id'] in boards_dict:
                boards_dict[item['board_id']].append(
                    item['description'].decode('utf-8')
                )
            else:
                boards_dict[item['board_id']] = [
                    item['description'].decode('utf-8')
                ]

        # Convert to list of tuple
        return [(b_id, b_body) for b_id, b_body in boards_dict.items()]

    def _add(self, item):
        '''
        @param tuple
            e.g. (b_id, [b_body, b_body])
        @return dict
        '''

        if self.obj_type == 'pjt_mlm' or self.obj_type == 'pjt_vl':
            # 比較対象のitemsをセット
            # 追加しようとしているデータ集合の中に重複しているものが全然あるので、追加するたびに、
            # redisから全部取得 >> 追加しようとしているデータとの重複チェック >> セット
            # redisから全部取得 >> ... というredisとのi/oが無駄に多い処理を行う
            with Redis_objects() as r:
                items_c = r.get(self.key_name, reversed_flag=False)

            wakati = Wakati()
            item_tup = (item[0], wakati.parse(' '.join(item[1])),)

        if self.obj_type == 'msg':
            with Redis_objects() as r:
                items_c = r.get(self.key_name, reversed_flag=False)

            # descriptionを連結して、分かち書きにする
            # ('board_id', 'dec1 dec2 dec3')
            wakati = Wakati()
            item_tup = (item[0], wakati.parse(' '.join(item[1])),)

        overlap = Overlap()
        is_overlap = overlap.is_overlap(item_tup, items_c)

        if os.environ.get('ENVIRONMENT') == 'development':
            # False/:board_idだと重複していないテキストだということ
            print('{0}, Overlap: {1}/{2}'.format(
                self.key_name,
                str(is_overlap),
                str(item[0])
            ))

        if not is_overlap:
            # ここでhmset実行
            Connect().open().hmset(self.key_name, {
                item_tup[0]: item_tup[1]
            })

    def run(self):
        '''
        @param string key_name
        @return None
        '''

        con = Connect(role='slave')
        r_s = con.open()

        if not r_s.exists(self.key_name):
            raise Exception('The key dose not exist in Redis')

        # GET DATA
        if self.obj_type == 'pjt_mlm':
            items = self._get_pjt(work_type='mlm')

        if self.obj_type == 'pjt_vl':
            items = self._get_pjt(work_type='vl')

        if self.obj_type == 'msg':
            items = self._get_msg()

        with Pool(processes=app.config['POOL_PROCESS_NUM']) as pool:
            pool.map(self._add, items)
