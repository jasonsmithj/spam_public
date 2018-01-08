# -*- coding: utf-8 -*-

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    KFold,
    GridSearchCV,
)
from sklearn.svm import LinearSVC
from sklearn.linear_model import SGDClassifier, PassiveAggressiveClassifier
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix,
    accuracy_score,
    classification_report,
)
from app import app
from app.redis.objects import Objects as Redis_objects
from app.mysql.messages import Messages


class Optimize():
    '''
    TF-IDFで算出したベクトル値を次元圧縮（128次元）するために、KernelPCA, LSA,
    Random Projectionのそれぞれを試してみたところ、LSAが速度と精度のバランスが最も良い。
    KernelPCAはLSAと同じ精度が出るが、処理コストが高すぎる。
    Random Projectionは速いが、精度がKernelPCA、LSAと比べて10%低い。
    LSAはKernelPCAとほぼ同じ精度でRandom Projectionより少し遅いくらい。
    LSAは100次元でも1000次元でも大して精度は変わらない。
    もっというと、64次元でもそれほど変わらなかった。ちょっと下がるくらい
    なお、1000次元にすると処理時間がだいぶ長くなる。
    なので128次元で固定する
    '''

    def __init__(self):
        self.items = {
            'x': [],
            'y': []
        }

    def set_data(self, key_pos, key_neg):
        '''
        学習データをセットする
        @param str key_pos
        @param str key_neg
        @return None
        '''
        with Redis_objects() as r:
            items_pos = r.get(key_pos)
            items_neg = r.get(key_neg)
            items_pjt_pos = r.get('spam:ds:tmp:pjt:mlm:pos')

        for item_p in items_pos:
            self.items['x'].append(item_p[1])
            self.items['y'].append(1)

        for item_p in items_pjt_pos:
            self.items['x'].append(item_p[1])
            self.items['y'].append(1)

        i = 0
        items_pos_len = len(self.items['x'])
        for item_n in items_neg:
            self.items['x'].append(item_n[1])
            self.items['y'].append(0)
            # posデータと同じ数だけを取得する
            if i > items_pos_len:
                break
            i = i + 1

    def _tfidf(self):
        '''
        TF-IDFベクトル値を算出
        '''

        app.config.from_object('config.Words')

        vect = TfidfVectorizer(
            analyzer='word',
            max_df=0.5,
            min_df=5,
            stop_words=app.config['STOP_WORDS'],
            max_features=1280,
            ngram_range=(1, 1))

        return vect.fit_transform(self.items['x']).toarray()

    def _pa_param(self):
        '''
        2011年の論文になるが、Gmailの優先boxで使われていた(いる)学習モデル
        '''
        pipe = Pipeline([
            ('rp', TruncatedSVD(random_state=0)),
            ('clf', PassiveAggressiveClassifier(
                n_jobs=-1,
                random_state=0,
                shuffle=True
            ))
        ])

        param_grid = [
            {
                'rp__n_components': [128],
                'clf__C': [0.1],
                # 'clf__loss': ['hinge', 'squared_hinge']
            }
        ]

        return pipe, param_grid

    def _sgd_param(self):
        # KernelPCAは処理が重すぎる。けど次元が少なくても精度が良い。
        # RandomProjectionaは処理はだいぶ早いけど、精度が結構落ちる。
        # TruncatedSVDはGood。
        # 固定したいパラメータはこの時点で設定する
        pipe = Pipeline([
            ('rp', TruncatedSVD(random_state=0)),
            ('clf', SGDClassifier(n_jobs=-1, random_state=0, shuffle=True))
        ])

        param_grid = [
            {
                # autoを含めるとエラーになった。
                # LSAは100次元でも1000次元でも大して精度は変わらない。
                # ただ、1000次元にすると処理時間がだいぶ長くなる。
                # なので、128次元にしない理由がない
                'rp__n_components': [128],
                'clf__alpha': [0.00001, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100],
                # 'clf__penalty': ['l2', 'l1', 'elasticnet']
            }
        ]

        return pipe, param_grid

    def _svc_param(self):
        '''

        '''
        pipe = Pipeline([
            ('rp', TruncatedSVD(random_state=0)),
            ('clf', LinearSVC(random_state=0))
        ])

        param_grid = [
            {
                'rp__n_components': [128],
                'clf__C': [0.00001, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100],
                # 'clf__class_weight': [None, 'balanced'],
                # 'clf__fit_intercept': [True, False],
                # 'clf__dual': [True, False],
                # 'clf__penalty': ['l1', 'l2'],
                # 'clf__multi_class': ['ovr', 'multinomial']
            }
        ]

        return pipe, param_grid

    def _rf_param(self):
        # 固定したいパラメータはこの時点で設定する
        pipe = Pipeline([
            ('rp', TruncatedSVD(random_state=0)),
            ('clf', RandomForestClassifier(n_jobs=-1, random_state=0))
        ])

        # 次元削減でn_componentsを2にしたらmax_depthは2になる
        param_grid = [
            {
                'rp__n_components': [128],
                'clf__n_estimators': [10, 100, 1000],
                'clf__max_depth': [10, 40, 60, 80, 100]
            }
        ]

        return pipe, param_grid

    def cross_validation(self):
        '''
        cross_validationを実行する場合のサンプル
        grid_searchの中にcross_validationが組み込まれているのでcross_validationを
        使うことはあまりない。
        '''

        x = self._tfidf()

        clf = SGDClassifier(
            alpha=0.1, average=False, class_weight=None, epsilon=0.1,
            eta0=0.0, fit_intercept=True, l1_ratio=0.15,
            learning_rate='optimal', loss='hinge', n_iter=5, n_jobs=-1,
            penalty='l2', power_t=0.5, random_state=0, shuffle=True,
            verbose=0, warm_start=False
        )

        # KFoldが標準的。よく使われる。
        kfold = KFold(n_splits=3, shuffle=True, random_state=0)
        # shuffle_split = ShuffleSplit(test_size=.5, train_size=.5, n_splits=3)

        scores = cross_val_score(
            clf,
            x,
            self.items['y'],
            cv=kfold,
            n_jobs=-1
        )

        print('Cross validation score: {}'.format(scores))

    def grid_search(self, clf):
        '''
        正解率に基づいてモデルを評価する
        @param string clf
        @return None
        '''
        x = self._tfidf()

        if clf == 'pa':
            pipe, param_grid = self._pa_param()
        elif clf == 'sgd':
            pipe, param_grid = self._sgd_param()
        elif clf == 'svc':
            pipe, param_grid = self._svc_param()
        elif clf == 'rf':
            pipe, param_grid = self._rf_param()
        else:
            raise Exception('Invalid argument')

        # 学習用とテスト用データに分ける
        x_train, x_test, y_train, y_test = \
            train_test_split(x, self.items['y'], random_state=0)

        # verbose=1は冗長なメッセージを出力するか否か。数字が大きいほど冗長になる
        # cvにintを指定すればKFoldで分割する
        grid = GridSearchCV(
            pipe,
            param_grid,
            scoring='accuracy',
            cv=5,
            n_jobs=-1,
        )

        grid.fit(x_train, y_train)

        print('\nBest cross validatoin score: {}'.format(grid.best_score_))
        print('\nBest parameter: {}'.format(grid.best_params_))
        print('\nBest estimator: \n{}'.format(grid.best_estimator_))

        y_pred = grid.predict(x_test)
        self._scores(y_test, y_pred)

    def _scores(self, y_test, y_pred):
        '''
        混同行列 二値分類ではこの指標でモデルを評価すると良い。
        true positive positiveだと正しく判断できた
        true negative negativeだと正しく判断できた
        false positive 間違ってpositiveだと判断した。正しくはnegative
        false negative 間違ってnegativeだと判断した。正しくはpositive ここが一番ダメ。
        confusion_matrixの出力は下記の順番になる
        [[ TN FP
           FN TP ]]
        @param y_test
        @param y_pred
        '''

        confusion = confusion_matrix(y_test, y_pred)
        ac_score = accuracy_score(y_test, y_pred)
        cl_report = classification_report(
            y_test, y_pred,
            target_names=['Not spam', 'spam']
        )

        print('\nConfusion matrix: \n{}'.format(confusion))
        print('\nTest accuracy score: {}'.format(ac_score))
        print('\nReport: \n{}', cl_report)

    def count_words_msg(self, patterns=None):
        '''
        For messages
        特定のキーワードがいくつposとnegにそれぞれ含まれているかを数える
        @param tuple pattern
        @return None
        '''

        with Messages() as m:
            msg_pos = m.get_pos()
            msg_neg = m.get_neg()

        if patterns is None:
            patterns = ('line', 'LINE', 'Line', 'ライン')

        i = 0
        j = 0
        boards_p = {}
        boards_n = {}

        for p in msg_pos:
            if p['board_id'] in boards_p:
                boards_p[p['board_id']].append(
                    p['description'].decode('utf-8')
                )
            else:
                boards_p[p['board_id']] = [
                    p['description'].decode('utf-8')
                ]

        for board_id, board_body in boards_p.items():
            p_desc = ' '.join(board_body)
            for pattern in patterns:
                if pattern in p_desc:
                    i = i + 1

        for n in msg_neg:
            if n['board_id'] in boards_n:
                boards_n[n['board_id']].append(
                    n['description'].decode('utf-8')
                )
            else:
                boards_n[n['board_id']] = [n['description'].decode('utf-8')]

        for board_id, board_body in boards_n.items():
            n_desc = ' '.join(board_body)
            for pattern in patterns:
                if pattern in n_desc:
                    j = j + 1

        print('URL in pos: {0}/{1}, URL in neg: {2}/{3}'.format(
            str(i),
            str(len(boards_p)),
            str(j),
            str(len(boards_n))
        ))
