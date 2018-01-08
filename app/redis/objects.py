# coding: utf-8

from app import app
from app.redis.connect import Connect


class Objects():
    '''
    コンテキストマネージャで呼び出すこと。
    '''

    def __init__(self, role='slave'):
        self.role = role

    def __enter__(self):
        self.con = Connect(role=self.role)
        self.r = self.con.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        '''
        redisの場合はcloseに値するメソッドが用意されていない。
        ただ、将来の拡張性を想定して、コンテキストマネージャ型にしておく
        '''
        if exc_type is None:
            pass
        else:
            app.logger.warning('Message Redis connection closing is failed')
            return False

    def get(self, key_name, reversed_flag=True):
        '''
        hgetallで取得するデータを逆順で取れるようにするためにこのメソッドを用意している
        @param string key_name
        @param bool reversed_flag
        @return list of tuple
            e.g. [(id1, 'body1',...}]
        '''
        objects = self.r.hgetall(key_name)

        # Trueが指定されたら逆順にする
        if reversed_flag:
            # 小難しいが、key=lambda x: int(x[0]) こうすることで、id部分で逆順に並べ変えてくれる
            # redisには数値もstringで入っているので、int()変換してあげる必要がある
            o_sorted = [(o_id, o_body) for o_id, o_body in sorted(
                objects.items(),
                key=lambda x:x[0], reverse=True
            )]
        else:
            o_sorted = [(o_id, o_body) for o_id, o_body in objects.items()]

        return o_sorted
