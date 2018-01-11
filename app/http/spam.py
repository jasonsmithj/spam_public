# coding: utf-8

from flask import request, abort

from app import app
from app.http.response import Response
from app.redis.connect import Connect
from app.mysql.message_spams import MessageSpams
from app.ml.predict import Predict
from app.ml.wakati import Wakati


class Spam():
    '''
    queryパラメータ、bodyパラメータは、validationクラスによってチェックが済んでいる
    ものとする。なので、当クラス内でパラメータチェックは行わない。
    '''

    def add(self):
        '''

        '''

        data = request.get_json()

        pr = Predict(
            vect=app.config['PICKLE_MSG_MLM_TFIDF'],
            lsa=app.config['PICKLE_MSG_MLM_LSA'],
            clf=app.config['PICKLE_MSG_MLM_CLF'])

        body = Wakati().parse(data['body'])

        res = pr._predict(body)

        items = {
            'spam': {
                'probability': res['score'],
                'vocabulary': res['vocabulary'],
            }
        }

        return Response().parse(items)
