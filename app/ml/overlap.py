# coding: utf-8

import difflib
import os
from multiprocessing import Pool

from app import app
from app.redis.objects import Objects as Redis_objects
from app.redis.connect import Connect


class Overlap():
    '''
    重複テキストを削除するための処理
    Redisに保存されているデータを削除する
    '''

    def is_overlap(self, item, items_comparision):
        '''
        重複度が90%以上のものがあるかないかを返す
        80%や70%のように削りすぎるのもよくないということがわかった
        重複していればTrueを返す。
        @param tuple item
          e.g. (id, 'body')
        @param list of tuple items_comparision
          e.g. [(id, body),...]
        @return bool
        '''

        for item_c in items_comparision:

            # 自分自身の場合はスキップ
            if item[0] == item_c[0]:
                continue

            s = difflib.SequenceMatcher(None, item[1], item_c[1])

            # 90%以上重複しているテキストは重複しているものとする
            if s.ratio() > 0.9:
                return True

        return False

    def _remove(self, item):
        '''
        @param tuple item
            e.g. (id, body)
        '''

        with Redis_objects() as r:
            items_c = r.get(self.key_name, reversed_flag=False)

        if os.environ.get('ENVIRONMENT') == 'development':
            items_c_len = len(items_c)
            # 全て表示させると遅くなるので、3の倍数の時だけ出力
            if (items_c_len % 3) == 0:
                print('{0}, Laps: {1}/{2}'.format(
                    self.key_name, str(items_c_len), self.items_len)
                )

        del_items = set([])

        for item_c in items_c:
            # 自分自身の場合はスキップ
            # 対処済みitemの場合はスキップ
            if item[0] == item_c[0] or int(item[0]) > int(item_c[0]):
                continue

            s = difflib.SequenceMatcher(None, item[1], item_c[1])

            if s.ratio() > 0.9:
                del_items.add(item_c[0])

        # 一周ごとにまとめて削除
        if del_items:
            Connect().open().hdel(self.key_name, *del_items)

    def remove_myself(self, key_name):
        '''
        初期時に使用するためのメソッド
        重複データをredisから消す
        重複を含めて、key_nameに全てのデータが入っているものとする
        @param string key_name
        '''

        app.logger.debug('remove_myself start')

        self.key_name = key_name

        # 全て取得
        with Redis_objects() as r:
            # @return list of tuple
            # e.g. [(id, body),...]
            items = r.get(key_name, reversed_flag=False)

        self.items_len = str(len(items))

        with Pool(processes=app.config['POOL_PROCESS_NUM']) as pool:
            # chunksizeを設定しなければ、mapに1つずつitemsのデータが渡される
            # chunksizeに100を指定すれば、100個ずつ渡される。10倍くらいの差が出る
            pool.map(self._remove, items, chunksize=100)

        app.logger.debug('remove_myself finish')
