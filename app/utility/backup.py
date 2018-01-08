# coding: utf-8

import pickle
import gzip

from app import app
from app.redis.connect import Connect
from app.mysql.messages import Messages as Mysql_messages


class Backup():
    '''
    ローカルで準備したデータセットをpickleで固めて、redisにimportするためのクラス
    '''

    def __init__(self):
        # unittestしやすいようにディレクトリとファイル名を分けている
        self.directory = 'storage/pickles'
        self.file = '/{0}.pickle.gz'

    def dump(self):
        '''
        # Redisからデータセットを取り出し、pickle >> gzip >> ファイル書き出し
        Convert to pickle
        '''

        path = self.directory + self.file

        con = Connect(host='api', role='slave')
        r = con.open()

        ds_pjt_mlm_pos = r.hgetall(app.config['DATASETS_PJT_MLM_POS'])
        ds_pjt_mlm_neg = r.hgetall(app.config['DATASETS_PJT_MLM_NEG'])
        ds_msg_pos = r.hgetall(app.config['DATASETS_MSG_POS'])
        ds_msg_neg = r.hgetall(app.config['DATASETS_MSG_NEG'])
        url_blacklist = r.smembers(app.config['URL_BLACKLIST'])

        ds_pjt_mlm_pos_pickle = pickle.dumps(
            ds_pjt_mlm_pos, pickle.HIGHEST_PROTOCOL)

        ds_pjt_mlm_neg_pickle = pickle.dumps(
            ds_pjt_mlm_neg, pickle.HIGHEST_PROTOCOL)

        ds_msg_pos_pickle = pickle.dumps(
            ds_msg_pos, pickle.HIGHEST_PROTOCOL)

        ds_msg_neg_pickle = pickle.dumps(
            ds_msg_neg, pickle.HIGHEST_PROTOCOL)

        url_blacklist_pickle = pickle.dumps(
            url_blacklist, pickle.HIGHEST_PROTOCOL)

        try:
            with gzip.open(path.format('ds_pjt_mlm_pos'), 'wb') as f:
                f.write(ds_pjt_mlm_pos_pickle)

            with gzip.open(path.format('ds_pjt_mlm_neg'), 'wb') as f:
                f.write(ds_pjt_mlm_neg_pickle)

            with gzip.open(path.format('ds_msg_pos'), 'wb') as f:
                f.write(ds_msg_pos_pickle)

            with gzip.open(path.format('ds_msg_neg'), 'wb') as f:
                f.write(ds_msg_neg_pickle)

            with gzip.open(path.format('url_blacklist'), 'wb') as f:
                f.write(url_blacklist_pickle)
        except Exception as e:
            app.sentry.captureException(str(e))
            app.logger.error(str(e))
            return

        app.logger.debug('Export finished')

    def _import(self):
        '''Import from pickle'''
        path = self.directory + self.file

        # データセットを取り出して、dumpして、Redisにrestore
        try:
            with gzip.open(path.format('ds_pjt_mlm_pos'), 'rb') as f:
                ds_pjt_mlm_pos_pickle = f.read()

            with gzip.open(path.format('ds_pjt_mlm_neg'), 'rb') as f:
                ds_pjt_mlm_neg_pickle = f.read()

            with gzip.open(path.format('ds_msg_pos'), 'rb') as f:
                ds_msg_pos_pickle = f.read()

            with gzip.open(path.format('ds_msg_neg'), 'rb') as f:
                ds_msg_neg_pickle = f.read()

            with gzip.open(path.format('url_blacklist'), 'rb') as f:
                url_blacklist_pickle = f.read()
        except Exception as e:
            app.logger.error(e)
            return

        ds_pjt_mlm_pos = pickle.loads(ds_pjt_mlm_pos_pickle)
        ds_pjt_mlm_neg = pickle.loads(ds_pjt_mlm_neg_pickle)
        ds_msg_pos = pickle.loads(ds_msg_pos_pickle)
        ds_msg_neg = pickle.loads(ds_msg_neg_pickle)
        url_blacklist = pickle.loads(url_blacklist_pickle)

        r = Connect(host='api', role='master').open()

        with r.pipeline(transaction=True) as pipe:
            pipe.delete(app.config['DATASETS_PJT_MLM_POS'])
            pipe.delete(app.config['DATASETS_PJT_MLM_NEG'])
            pipe.delete(app.config['DATASETS_MSG_POS'])
            pipe.delete(app.config['DATASETS_MSG_NEG'])
            pipe.delete(app.config['URL_BLACKLIST'])

            pipe.hmset(app.config['DATASETS_PJT_MLM_POS'], ds_pjt_mlm_pos)
            pipe.hmset(app.config['DATASETS_PJT_MLM_NEG'], ds_pjt_mlm_neg)
            pipe.hmset(app.config['DATASETS_MSG_POS'], ds_msg_pos)
            pipe.hmset(app.config['DATASETS_MSG_NEG'], ds_msg_neg)
            for url in url_blacklist:
                pipe.sadd(app.config['URL_BLACKLIST'], url)

            pipe.execute()

    def _set(self):
        # MSG_LAST_PULLEDに最新のmessage.idをセットする
        with Mysql_messages(role='slave') as m:
            msg = m.get_latest()

        r = Connect(host='api', role='master').open()
        r.set(app.config['MSG_LAST_PULLED'], msg['id'])

    def restore(self):
        ''''''
        try:
            self._import()
            self._set()
        except Exception as e:
            app.sentry.captureException(str(e))
            print(str(e))
            return None

        print('restore is done')
