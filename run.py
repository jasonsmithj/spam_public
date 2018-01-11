# coding: utf-8

import os

# gunicornで起動するときはルートディレクトリで下記コマンドを実行する。
# runはこのファイル名のこと
#
# gunicornで直接起動する場合
# gunicorn --workers=2 --bind 0.0.0.0:5000 --access-logfile - --reload run:app
#
from app import app
# コントローラーはこの場所で読み込む
from app import controller

if __name__ == '__main__':
    '''
    run.pyは開発時に使うだけであって、テスト環境以上では
    gunicornを使ってアプリケーションを起動すること。
    外部からアクセスできるようにする場合は、hostに0.0.0.0を設定すれば良い
    host='0.0.0.0'
    debugをtrueにすることで、コードを修正したときに自動的に再起動してくれる
    '''
    if os.environ.get('ENVIRONMENT') != 'development':
        raise Exception('テスト環境以上ではWSGI, gunicornなど, を使って起動すること')

    app.run(
        host='127.0.0.1',
        port=8000,
        debug=True,
    )
