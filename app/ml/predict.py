# coding: utf-8

import json
import pickle
import gzip
import pytz
from datetime import datetime
from app import app
from app.mysql.works import Works as Mysql_works
from app.mysql.work_spams import WorkSpams
from app.mysql.messages import Messages as Mysql_messages
from app.mysql.message_spams import MessageSpams
from app.redis.connect import Connect
from app.ml.biz_filter import BizFilter
from app.ml.wakati import Wakati
from app.utility.chatwork import Chatwork
from app.utility.scraper import Scraper
from app.utility.websocket import Websocket


class Predict():
    '''
    対象がスパムか否かを予測する
    '''

    def __init__(self, vect=None, lsa=None, clf=None):
        '''
        @param str body
        @param str
        '''
        self.vect = vect
        self.lsa = lsa
        self.clf = clf

    def _factory_msg(self, message_id):
        '''
        メソッド名は要変更。思いつかないからこんな名前にしている。
        @param int message_id
        @return dict
            message_idが属するboardのmessageを全て取得し、owner_idのmessage
            だけを抽出する。こういう形で返す
            {
                'message_id': xxx
                'board_id': xxx,
                'user_id': xxx,
                'nickname': xxx,
                'description': [xxx, xxx,...],
                'biz_filter': None
            }
        '''
        # message_idが属するboardのmessageを全て取得
        with Mysql_messages(role='slave') as m:
            messages = m.get_messages(message_id)

        # fileが送信されただけの時は、descriptionが空になるので、
        # messagesは空のリストになる
        if not messages:
            return None

        item = {'message_id': None}

        for msg in messages:

            # message_idの作成者が受信者の場合は、mlmの文脈においては一律スキップ
            if msg['id'] == message_id and msg['owner_id'] != msg['user_id_b']:
                return None

            # owner_id（送信者）側だけを抽出する
            if msg['owner_id'] != msg['user_id_b']:
                continue
            if not msg['description']:
                continue

            if not item['message_id']:
                item['message_id'] = message_id
                item['board_id'] = msg['board_id']
                item['user_id'] = msg['owner_id']
                item['nickname'] = msg['nickname'].decode('utf-8')
                item['description'] = []
                item['biz_filter'] = None

            item['description'].append(msg['description'].decode('utf-8'))

        if not item['message_id']:
            return {}
        else:
            return item

    def _create_pjt(self, item):
        '''
        予測した結果をSave
        @param dict item
        @return int id item created
        '''

        with WorkSpams() as ws:
            item_id = ws.create({
                item['work_id'],
                item['score'],
                item['predict']
            })

        return item_id

    def _create_msg(self, item):
        '''
        予測した結果をSave
        @param dict item
        @return int id item created
        '''

        if not item['biz_filter']:
            biz_filter = None
        else:
            biz_filter = json.dumps(item['biz_filter'])

        with MessageSpams() as ms:
            item_id = ms.create((
                item['board_id'],
                item['message_id'],
                item['score'],
                item['predict'],
                biz_filter
            ))

        return item_id

    def _get_vocabulary(self, vect, transform):
        '''
        TF-IDF値の高い単語を取得する
        次元圧縮後の特徴を使うのでTF-IDF値の高い値が使用されているとは限らないが、
        参考にはなるので保存する
        @return str
            e.g. ロゴ 社名 バイク 当社 希望 デザイン 高級
        '''
        vocabulary = {}
        for word, idx in vect.vocabulary_.items():
            vocabulary.update({idx: word})

        mapping = {}
        for i, idx in enumerate(transform.indices):
            mapping.update({
                idx: transform.data[i]
            })
        # [(280, 0.54154458428514252), (76, 0.35013283716664145),...
        m_sorted = [(key, val) for key, val in sorted(
            mapping.items(),
            key=lambda x:x[1],
            reverse=True
        )]

        return ' '.join([vocabulary[m_s[0]] for m_s in m_sorted][0:18])

    def _get_score(self, clf, lsa):
        '''
        @param lsa lsaで次元圧縮した値を渡すこと
        @return str
        '''
        score = clf.decision_function(lsa)
        return str(score[0])

    def _notify_msg(self, item, debug=False):
        '''
        通知済みのユーザは２度通知しない
        @param dict item
        @return int 200 | None
        '''

        if not debug:
            r = Connect(role='slave').open()
            # 検知済みuserの取得
            # @return set型
            spam_user_ids = r.smembers(app.config['MSG_DETECTED_USER_ID'])

            # 通知済みのuserの場合は通知しない
            if str(item['user_id']) in spam_user_ids:
                return None

            # 違反判定されたmessageの作成者の場合は追加して、次から通知しないようにする
            r_m = Connect().open()
            r_m.sadd(app.config['MSG_DETECTED_USER_ID'], item['user_id'])

        chatwork = Chatwork()
        res = chatwork.post(
            app.config['ROOM_ID_MSG'],
            '''---{0}-----------------------------------\nScore: {1}\nVocabulary: {2}\nBoard Url: {3}\nUser Edit Url: {4}'''.format(
                datetime.now(
                    pytz.timezone('Asia/Tokyo')
                ).strftime("%Y-%m-%d %H:%M:%S"),
                item['score'],
                item['vocabulary'],
                app.config['URL_BOARD_ADMIN'].format(item['board_id']),
                app.config['URL_USER_ADMIN'].format(item['user_id'])
            )
        )

        return res

    def _predict(self, body):
        '''
        @param str body
        @return dict
        '''
        # decode_responses=Falseにするためにメソッド内で呼び出している
        con = Connect(role='slave', decode_responses=False)
        r_s = con.open()

        with r_s.pipeline(transaction=False) as pipe:
            pipe.get(self.vect)
            pipe.get(self.lsa)
            pipe.get(self.clf)
            pickles = pipe.execute()

        # バイナリーに戻す
        vect = pickle.loads(gzip.decompress(pickles[0]))
        lsa = pickle.loads(gzip.decompress(pickles[1]))
        clf = pickle.loads(gzip.decompress(pickles[2]))

        # TFIDFはiterableな値しか受けつけないので、リストで渡す
        tfidf = vect.transform([body])
        lsa_reduced = lsa.transform(tfidf)
        predict = clf.predict(lsa_reduced)

        score = self._get_score(clf, lsa_reduced)

        vocabulary = self._get_vocabulary(vect, tfidf)

        # 1はspam、0はspamではない
        return {
            # 1度に1つの対象をpredictすることを想定しているので、0番目を返す
            # predict[0]は <class 'numpy.int64'>型になっているのでintにする
            'predict': int(predict[0]),
            'score': score,
            'vocabulary': vocabulary
        }

    def _detect_pjt(self, work_id):
        '''

        '''

        with Mysql_works(role='slave') as m:
            work = m.get_work_user(work_id)

        if not work['title'] or not work['description']:
            return

        predict = {
            'id': work['id']
        }

        # Bussiness Filter
        bf = BizFilter()
        res_bf = bf.pjt(work)

        if res_bf['predict'] == 0:
            return None

        wakati = Wakati()

        item = self._predict(wakati.parse(
            work['title'].decode('utf-8') + ' ' +
            work['description'].decode('utf-8')
        ))

        # 1はspam、0はspamではない
        if item['predict'] == 1:
            return None

        predict['predict'] = 0
        predict['obj_type'] = 'pjt'
        predict['spam_type'] = 'None'
        predict['biz_filter'] = 'None'
        predict['score'] = item['score']
        predict['vocabulary'] = item['vocabulary']

        # predict結果を保存
        # self._create_pjt(item, predict)

        if float(item['score']) >= app.config['SCORE_THRESHOLD_WORKS']:
            chatwork = Chatwork()
            chatwork.post(
                app.config['ROOM_ID_WORKS'],
                '''---{0}-----------------------------------\nTitle: {1}\nScore: {2}\nVocabulary: {3}\nWork Url: {4}\nUser Url: {5}'''.format(
                    item['created'].strftime("%Y-%m-%d %H:%M:%S"),
                    (item['title'].decode('utf-8'))[0:30],
                    predict['score'],
                    predict['vocabulary'],
                    app.config['URL_WORK_DETAIL'].format(str(work['id'])),
                    app.config['URL_USER_ADMIN'].format(work['user_id'])
                ))

    def _detect_msg(self, message_id):
        '''
        # 2.90以上だとほぼほぼspam。
        # 0.x台はspamではないことが多い
        # 1.x~1.9は、一斉送信営業メールである確率が高い
        @param int message_id
        '''

        item = self._factory_msg(message_id)

        if not item:
            return None

        # ビジネスルールの適用
        # msgの場合は分かち書きする前に適用する
        # bf = BizFilter()
        # res_bf = bf.msg(' '.join(data[1]))

        predicted = self._predict(
            Wakati().parse(' '.join(item['description'])))

        '''
        itemに対して_predictの結果をマージ
        マージ後のitemの中身はこんな感じ
        {
            'message_id': '15076626',
            'board_id': 3204962,
            'user_id': 1538229,
            'nickname': 'roger3gogo',
            'description': ['desc1', 'desc2', 'desc3'],
            'biz_filter': None,
            'predict': 0,
            'score': '-1.26858170292',
            'vocabulary': '依頼 記事 税込...'
        }
        '''
        item.update(predicted)

        score = float(item['score'])

        # SCORE_THRESHOLD_MSG_SCRAPE未満であれば何もしない。終了
        if score < app.config['SCORE_THRESHOLD_MSG_SCRAPE']:
            return None

        # spamだとは断定できないが、怪しい場合は、urlチェック
        if score >= app.config['SCORE_THRESHOLD_MSG_SCRAPE'] and \
            score < app.config['SCORE_THRESHOLD_MSG_SPAM']:

            sc = Scraper()
            # urlを探したいだけだからスペースはいらない
            res_sc = sc.run(''.join(item['description']))

            # url_blacklistに含まれるURLが存在しなければ何もしない。終了
            if not res_sc['url']['url_blacklist']:
                return None

            item['biz_filter'] = res_sc

        # Create message_spams record
        self._create_msg(item)

        # Notification to Chatwork
        self._notify_msg(item)

        # Emit to Client
        Websocket().emit_spam_update_message({
            'board_id': item['board_id'],
            'message_id': int(item['message_id']),
            'feedback_from_admin': 0,
            'feedback_from_user': 0,
            'predict': item['predict']
        })

    def debug(self, message_id):
        '''
        @param int message_id
        '''

        item = self._factory_msg(message_id)

        if not item:
            return None

        predicted = self._predict(
            Wakati().parse(' '.join(item['description'])))

        item.update(predicted)

        print(item)

        # 2.90以上だとほぼほぼspam。
        # 0.x台はspamではないことが多い
        # 1.x~2.89は、一斉送信営業メールである確率が高い
        if float(item['score']) >= app.config['SCORE_THRESHOLD_MSG']:
            # Notification to Chatwork
            self._notify_msg(item, debug=True)

    def run(self, obj):
        '''
        Queueからmessage_idを取得してspamかどうかを予測する
        @param str obj msg or pjt
        @return None
        '''

        r = Connect().open()
        msg_id = r.lpop(app.config['QUEUE_BASE_MSG'])

        # キューが空であれば何もしない
        if not msg_id:
            return None

        try:
            self._detect_msg(int(msg_id))
        except Exception as e:
            app.sentry.captureException(str(e))
            app.logger.error(
                'predict message is failed. Reason: {0}'.format(e))
            # 失敗した場合はキューに戻す
            r.rpush(app.config['QUEUE_BASE_MSG'], msg_id)
            raise
