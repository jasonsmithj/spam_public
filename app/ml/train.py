# coding: utf-8

import pickle
import gzip
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.decomposition import TruncatedSVD

from app import app
from app.redis.objects import Objects as Redis_objects
from app.redis.connect import Connect


class Train():
    '''
    モデルを学習させる.updateバッチ実行完了後に実行すること
    worksとmessagesのtfidfパラメータは同じで問題なし
    '''

    def __init__(self, tfidf_key=None, lsa_key=None, clf_key=None):
        ''''''
        self.tfidf_key = tfidf_key
        self.lsa_key = lsa_key
        self.clf_key = clf_key

    def set_datasets(self, pos_key=None, neg_key=None, add_key=None):
        '''
        データセットをセットする
        msgにworkのmlmを追加すると精度が2%上がった。逆は意味なかった。
        '''

        self.items = {
            'x': [],
            'y': []
        }

        # 新しいデータから順に取得する
        with Redis_objects() as obj:
            items_pos = obj.get(pos_key)
            items_neg = obj.get(neg_key)
            if add_key:
                items_add_pos = obj.get(add_key)

        for item_p in items_pos:
            self.items['x'].append(item_p[1])
            # spamであることを1と表現する
            self.items['y'].append(1)

        if add_key:
            for item_add_p in items_add_pos:
                self.items['x'].append(item_add_p[1])
                self.items['y'].append(1)

        i = 0
        # posデータと同じ数だけ取得する
        pos_len = len(self.items['x'])

        for item_n in items_neg:
            self.items['x'].append(item_n[1])
            # spamでないことを0と表現する
            self.items['y'].append(0)

            if i > pos_len:
                break

            i = i + 1

    def run(self):
        '''
        @return None
        '''

        if not self.items['x'] or not self.items['y']:
            raise Exception('Must be called set_datasets before Train.train')

        app.config.from_object('config.Words')

        vect = TfidfVectorizer(
            analyzer='word',
            max_df=0.5,
            min_df=5,
            max_features=1280,
            stop_words=app.config['STOP_WORDS'],
            ngram_range=(1, 1))

        tfidf_fit = vect.fit(self.items['x'])

        # 分類器が理解できる形式に変換
        tfidf_transform = vect.transform(self.items['x'])

        # TruncatedSVDはKernelPCAと違って標準化する必要がない
        # n_componentsが次元数を表している
        # LSAは100次元でも1000次元でも大して精度は変わらない。
        # 1000次元にすると処理時間がいっきに長くなる
        lsa = TruncatedSVD(n_components=128, random_state=0)
        lsa_fit = lsa.fit(tfidf_transform)
        lsa_transform = lsa.transform(tfidf_transform)

        # Grid searchで導き出したパラメータたち
        clf = PassiveAggressiveClassifier(
            C=0.1, class_weight=None, fit_intercept=True,
            loss='hinge', n_iter=5, n_jobs=-1, random_state=0,
            shuffle=True, verbose=0, warm_start=False
        )

        clf_fit = clf.fit(lsa_transform, self.items['y'])

        # Convert to binary
        tfidf_pickle = gzip.compress(
            pickle.dumps(tfidf_fit, pickle.HIGHEST_PROTOCOL)
        )

        lsa_pickle = gzip.compress(
            pickle.dumps(lsa_fit, pickle.HIGHEST_PROTOCOL)
        )

        clf_pickle = gzip.compress(
            pickle.dumps(clf_fit, pickle.HIGHEST_PROTOCOL)
        )

        r = Connect().open()
        with r.pipeline(transaction=False) as pipe:
            pipe.set(self.tfidf_key, tfidf_pickle)
            pipe.set(self.lsa_key, lsa_pickle)
            pipe.set(self.clf_key, clf_pickle)
            pipe.execute()
