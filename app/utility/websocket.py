# coding: utf-8

import msgpack

from app.redis.connect import Connect


class Websocket():
    '''
    socket.io-redisの形式に則り、redisに直接publishする
    https://github.com/socketio/socket.io-redis#protocol
    pythonにもsocket.io-redisクライアントはあるにはあるが、これとか。
    https://github.com/GameXG/socket.io-python-emitter
    ただ、Of, Inがまともに動いておらず、socket.io-redisは言ってしまえばただのredisへの
    publishなので、自分で実装して直接publishする
    '''

    def emit_spam_update_message(self, args):
        '''
        spam_update_messageイベントをemitする
        @param dict args
        @return int
            Returns the number of subscribers the message was delivered to.
        '''

        r = Connect(host='pubsub', role='master').open()

        channel_name = 'socket.io#/#{0}#'.format(args['board_id'])

        # socket.io-redisのイベント名、渡すデータはこのような形である。
        data_packed = msgpack.packb([
            'emitter',
            {
                # socket.ioはv1からバイナリ形式のデータ、つまり、画像・動画も送信できる
                # ようになった。文字列型と区別するためにtypeキーがある。
                # 文字列型は2で、バイナリ型は5を指定する
                'type': 2,
                'data': [
                    'spam_update_message', {
                        'board_id': args['board_id'],
                        'message_id': args['message_id'],
                        'feedback_from_admin': args['feedback_from_admin'],
                        'feedback_from_user': args['feedback_from_user'],
                        'predict': args['predict'],
                    }
                ],
                # namespaceのこと
                'nsp': '/'
            },
            {
                'rooms': [args['board_id']],
                'flags': []
            }
        ])

        return r.publish(channel_name, data_packed)
