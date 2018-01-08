# coding: utf-8

from flask import request, abort


class Validation():
    '''
    requestのバリデーションをまとめている
    バリデーションはControllerメソッド名と同じ名前にして連動させている
    Query parameterは page= という場合に、キーはあっても値がない場合であっても、
    if not request.args.get('board_id') これが成立する。
    Boay parameterの場合は if 'message_id' not in data:
    このようにチェックしないとすり抜けてしまう。
    '''

    def before_request(self):
        '''
        POST, PUT, DELETEの場合はapplicaton/jsonとしてリクエストされているかをチェック
        '''
        if (request.method == 'POST' or
                request.method == 'PUT' or
                request.method == 'DELETE'):
            if not request.is_json:
                abort(400, {
                    'code': 'invalid_format',
                    'message': 'MIME type must be JSON.'
                })

    def add_message(self):
        '''
        こういうデータが渡されることを想定
        { "id": number }'
        '''

        errors = []

        # Body param の存在チェック
        if not request.data:
            errors.append({
                'field': 'body parameter',
                'code': 'missing'
            })

        # Body paramがなければ下記の処理はそもそもできない
        else:
            # get_jsonはbodyデータをdictに変換する
            data = request.get_json()

            # Body Param チェック
            if 'message_id' not in data:
                errors.append({
                    'field': 'message_id',
                    'code': 'missing'
                })
            else:
                # idのvalueがnumericかチェック。isnumericは文字列型オブジェクトに
                # 対してのみ実行できるので、文字列型に変換する
                if not str(data['message_id']).isnumeric():
                    errors.append({
                        'field': 'message_id',
                        'code': 'invalid'
                    })

        if errors:
            abort(400, {
                'code': 'invalid_parameter',
                'message': 'Validation Failed',
                'errors': errors
            })

    def list_messages(self):
        ''''''

        errors = []

        # 全部ない場合はだめ。いづれかのパラメータは存在すべき
        if (not request.args.get('board_id') and not
                request.args.get('page') and not
                request.args.get('feedback_from_admin')):
            errors.append({
                'field': 'query parameter',
                'code': 'missing'
            })

        # 逆に全部あるのもだめ
        if (request.args.get('board_id') and
            request.args.get('page') and
            request.args.get('feedback_from_admin')):
            errors.append({
                'field': 'query parameter',
                'code': 'invalid'
            })

        # pageが存在するのであれば、feedback_from_adminもないとだめ
        if request.args.get('page'):
            if not request.args.get('feedback_from_admin'):
                errors.append({
                    'field': 'query parameter',
                    'code': 'missing'
                })

        if request.args.get('board_id'):
            if not request.args.get('board_id').isnumeric():
                errors.append({
                    'field': 'board_id',
                    'code': 'invalid'
                })

        # ?page=x クエリーパラメータに付与された値は常にstrで渡ってくる
        if request.args.get('page'):
            if not request.args.get('page').isnumeric():
                errors.append({
                    'field': 'page',
                    'code': 'invalid'
                })

        if request.args.get('feedback_from_admin'):
            if not request.args.get('feedback_from_admin').isnumeric():
                errors.append({
                    'field': 'feedback_from_admin',
                    'code': 'invalid'
                })
            # 取り得る値は0, 1, 2のいづれかのみである
            if request.args.get('feedback_from_admin').isnumeric():
                if not int(request.args.get('feedback_from_admin')) in [0, 1, 2]:
                    errors.append({
                        'field': 'feedback_from_admin',
                        'code': 'invalid'
                    })

        if errors:
            abort(400, {
                'code': 'invalid_parameter',
                'message': 'Validation Failed',
                'errors': errors
            })

    def edit_message(self, message_spam_id):

        errors = []

        # message_spam_idはstr型で受け取るので、isnumericで直接チェックすればよい
        if not message_spam_id.isnumeric():
            errors.append({
                'field': 'message_spam_id',
                'code': 'invalid'
            })

        # Body param の存在チェック
        if not request.data:
            errors.append({
                'field': 'body parameter',
                'code': 'missing'
            })

        else:
            # get_jsonはbodyデータをdictに変換する
            data = request.get_json()

            # Body Param チェック
            if 'feedback_from_admin' not in data:
                errors.append({
                    'field': 'feedback_from_admin',
                    'code': 'missing'
                })
            else:
                # feedback_from_adminが取り得る値はintの1か2のみ。
                if data['feedback_from_admin'] not in [1, 2]:
                    errors.append({
                        'field': 'feedback_from_admin',
                        'code': 'invalid'
                    })

        if errors:
            abort(400, {
                'code': 'invalid_parameter',
                'message': 'Validation Failed',
                'errors': errors
            })
