# coding: utf-8

import os

from flask import jsonify, abort

from app.mysql.connect import Connect as Mysql_con
from app.redis.connect import Connect as Redis_con
from app.utility.chatwork import Chatwork


class Connection():
    '''
    アプリケーションの稼働を確認するためのヘルスチェックエンドポイント
    @return json
    '''

    def get_ping(self):
        # Connection with MYSQL Master
        mysql_res_m_con = Mysql_con(role='master')
        mysql_res_m = mysql_res_m_con.is_connect()
        mysql_res_m_con.close()

        # Connection with MYSQL Slave
        mysql_res_s_con = Mysql_con(role='slave')
        mysql_res_s = mysql_res_s_con.is_connect()
        mysql_res_s_con.close()

        # Connection with Redis API Master
        redis_res_m = Redis_con(host='api', role='master').is_connect()

        # Connection with Redis API Slave
        redis_res_s = Redis_con(host='api', role='slave').is_connect()

        # Connection with Redis PubSub
        redis_res_pubsub_s = Redis_con(host='pubsub').is_connect()

        if os.getenv('ENVIRONMENT') != 'development':
            # Connection with Chatwork
            chatwork_res = Chatwork().is_connect()
            if not chatwork_res:
                return abort(500, 'Chatwork Connection Error')

        if not mysql_res_m:
            return abort(500, 'MYSQL Master Connection Error')
        if not mysql_res_s:
            return abort(500, 'MYSQL Slave Connection Error')
        if not redis_res_m:
            return abort(500, 'Redis API Master Connection Error')
        if not redis_res_s:
            return abort(500, 'Redis API Slave Connection Error')
        if not redis_res_pubsub_s:
            return abort(500, 'Redis PubSub Master Connection Error')

        return jsonify({'ping': 'pong'})
