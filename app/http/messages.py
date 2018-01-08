# coding: utf-8

from flask import request, abort

from app import app
from app.http.response import Response
from app.redis.connect import Connect
from app.mysql.message_spams import MessageSpams
from app.utility.websocket import Websocket


class Messages():
    '''
    queryパラメータ、bodyパラメータは、validationクラスによってチェックが済んでいる
    ものとする。なので、当クラス内でパラメータチェックは行わない。
    '''

    def add(self):
        '''

        '''

        data = request.get_json()

        try:
            Connect().open().rpush(
                app.config['QUEUE_BASE_MSG'], data['message_id'])
        except Exception as e:
            app.sentry.captureException(str(e))
            abort(500, 'add_messages is failed. Reason: {0}'.format(e))

        return '', 200

    def list(self):
        '''
        複数のmessage_spamを取得する
        board_idから取得する場合とfeedback_from_admin=0で取得する2パターンある。
        board_idの場合は、旧メッセージ・スマホページで参照される。
        feedback_from_adminの場合は、管理画面から参照される。
        validationによってboard_idかfeedback_from_adminのどちらかが存在することは
        保証されている
        '''

        items = {'message_spams': None}

        # board_idで取得する場合
        board_id = request.args.get('board_id')
        if board_id:
            with MessageSpams(role='slave') as m:
                msgs = m.list_with_board_id(board_id)
                msgs = m.parse(msgs)

            items['message_spams'] = msgs

        # 管理ページの場合
        f_admin = request.args.get('feedback_from_admin')
        if f_admin:

            if request.args.get('page'):
                page_int = int(request.args.get('page'))
                if page_int > 0:
                    page = page_int
                else:
                    page = 1
            else:
                page = 1

            with MessageSpams(role='slave') as m:
                msgs = m.list_for_admin_page(page)
                msgs = m.parse(msgs)
                count = m.count()

            if page == 1 and count > 50 * page:
                previous_url = None
                next_url = request.base_url + \
                    '?page=' + str(page+1) + \
                    '&feedback_from_admin=0'

            elif page == 1 and count <= 50 * page:
                previous_url = None
                next_url = None

            elif page >= 2:
                previous_url = request.base_url + \
                   '?page=' + str(page-1) + \
                   '&feedback_from_admin=0'

                if count > 50 * page:
                    next_url = request.base_url + \
                       '?page=' + str(page+1) + \
                       '&feedback_from_admin=0'
                else:
                    next_url = None

            items['count'] = count
            items['previous'] = previous_url
            items['next'] = next_url
            items['message_spams'] = msgs

        return Response().parse(items)

    def edit(self, message_spam_id):
        '''特定のmessage_spamを編集する。
        feedback_from_adminカラムのみ変更を許可している'''

        data = request.get_json()

        try:
            with MessageSpams(role='slave') as m:
                item_exist = m.is_exist(message_spam_id)

            if item_exist:
                with MessageSpams(role='master') as m:
                    m.edit((data['feedback_from_admin'], message_spam_id,))

                with MessageSpams(role='slave') as m:
                    item = m.get_detail(message_spam_id)

                    data = {
                        'id': item['id'],
                        'board_id': item['board_id'],
                        'board_title': item['board_title'].decode('utf-8'),
                        'message_id': item['message_id'],
                        'description': item['description'].decode('utf-8'),
                        'send_user_id': item['send_user_id'],
                        'send_user_nickname':
                            item['send_user_nickname'].decode('utf-8'),
                        'send_user_status':
                            item['send_user_status'].decode('utf-8'),
                        'receive_user_id': [],
                        'predict': item['predict'],
                        'feedback_from_admin': item['feedback_from_admin'],
                        'feedback_from_user': item['feedback_from_user']
                    }

                    board_users = m.get_board_users(item['board_id'])

                for board_user in board_users:
                    data['receive_user_id'].append(
                        board_user['user_id'])

                # emti spam_update_message event
                Websocket().emit_spam_update_message(data)

                return Response().parse({'message_spams': data})

        except Exception as e:
            app.sentry.captureException(str(e))
            abort(500, 'edit_messages is failed. Reason: {0}'.format(e))

        return Response().parse({'message_spams': {}})
