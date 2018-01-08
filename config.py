# coding: utf-8

import os
import logging

from app import app

# Flaskの標準設定一覧
# http://flask.pocoo.org/docs/0.12/config/

# 設定値ファイル
# 次のように読み込むとことができる
# app.config.from_object('config.BaseConfig')
# 参照するときは次のようにする
# app.config['USERNAME']


class CommonConfig(object):
    ENVIRONMENT = os.environ.get('ENVIRONMENT')

    if ENVIRONMENT == 'development':
        DEBUG = True
        app.logger.setLevel(logging.DEBUG)
        LOG_LEVEL = logging.DEBUG
    else:
        DEBUG = False
        app.logger.setLevel(logging.INFO)
        LOG_LEVEL = logging.INFO

    JSON_AS_ASCII = False
    API_VERSION = '/v1/spam'

    # For scraping headers
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
        'Accept-Language': 'ja'
    }

    # 追加したい時は | で区切れば良い。e.g. 'LINE|Skype'
    # 大文字・小文字は区別しないようにしている
    PATTERN_BLACKLIST_KEYWORDS_COMPILE = 'LINE'
    PATTERN_BLACKLIST_KEYWORDS_SEARCH = '^LINE'
    URL_PATTERN = r"https?:\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+"

    # LOG
    # LogフォーマットはLTSVを採用する
    # ログの内容 参考: http://flask.pocoo.org/docs/0.12/errorhandling/#complex-log-formatting
    LOG_PATH = 'logs/app.log'
    LOG_FORMAT = 'time:%(asctime)s\tlevel:%(levelname)s\tfile:%(filename)s\tmodule:%(module)s\tmethod:%(funcName)s\tline:%(lineno)d\tmessage:%(message)s'

    # Mecabの辞書
    # supervisorをrootで起動する以上はhomeがrootのhomeになるので
    # os.path.expanduser('~') が使えない。
    if ENVIRONMENT == 'development':
        NEOLOGD_PATH = os.path.expanduser('~') + '/mecab-ipadic-neologd/mecab-ipadic-neologd'
    else:
        NEOLOGD_PATH = '/home/lancers/mecab-ipadic-neologd/mecab-ipadic-neologd'


    # URL
    URL_WORK_DETAIL = 'https://www.lancers.jp/work/detail/{0}'
    URL_USER_DETAIL = 'https://www.lancers.jp/profile/{0}'
    URL_BOARD_ADMIN = 'https://krgn.lancers.jp/admin/messages/board/{0}'
    URL_USER_ADMIN  = 'https://krgn.lancers.jp/admin/users/edit/{0}'

    # Chatwork Room Id
    ROOM_ID_WORKS = '83551854'
    ROOM_ID_MSG = '84380698'
    ROOM_ID_HEALTH_CHECK = '91580849'

    # Score threshold
    SCORE_THRESHOLD_WORKS = 2.0
    SCORE_THRESHOLD_MSG_SPAM = 2.190
    SCORE_THRESHOLD_MSG_SCRAPE = 0.00

    cpu_count = os.cpu_count()
    if ENVIRONMENT == 'development':
        POOL_PROCESS_NUM = os.cpu_count()
    elif cpu_count == 1:
        POOL_PROCESS_NUM = 1
    else:
        POOL_PROCESS_NUM = cpu_count - 1

    # REDIS_KEY_NAME
    # Type: string

    PJT_LAST_PULLED = 'spam:pjt:last_pulled'
    MSG_LAST_PULLED = 'spam:msg:last_pulled'

    PICKLE_PJT_MLM_TFIDF = 'spam:pickle:pjt:mlm:tfidf'
    PICKLE_PJT_MLM_LSA = 'spam:pickle:pjt:mlm:lsa'
    PICKLE_PJT_MLM_CLF = 'spam:pickle:pjt:mlm:clf'

    PICKLE_PJT_VL_TFIDF = 'spam:pickle:pjt:vl:tfidf'
    PICKLE_PJT_VL_LSA = 'spam:pickle:pjt:vl:lsa'
    PICKLE_PJT_VL_CLF = 'spam:pickle:pjt:vl:clf'

    PICKLE_MSG_MLM_TFIDF = 'spam:pickle:msg:mlm:tfidf'
    PICKLE_MSG_MLM_LSA = 'spam:pickle:msg:mlm:lsa'
    PICKLE_MSG_MLM_CLF = 'spam:pickle:msg:mlm:clf'

    # Type: List
    QUEUE_BASE_PJT = 'spam:queue:base:pjt'
    QUEUE_BASE_MSG = 'spam:queue:base:msg'
    QUEUE_CHATWORK_PJT = 'spam:queue:chatwork:pjt'
    QUEUE_CHATWORK_MSG = 'spam:queue:chatwork:msg'

    # Type: hash
    DATASETS_PJT_MLM_POS = 'spam:ds:pjt:mlm:pos'
    DATASETS_PJT_MLM_NEG = 'spam:ds:pjt:mlm:neg'
    DATASETS_PJT_VL_POS = 'spam:ds:pjt:vl:pos'
    DATASETS_PJT_VL_NEG = 'spam:ds:pjt:vl:neg'
    #DATASETS_TASKS_VL_POS = 'spam:ds:tsk:vl:pos'
    #DATASETS_TASKS_NEG = 'spam:ds:tsk:neg'
    DATASETS_MSG_POS = 'spam:ds:msg:pos'
    DATASETS_MSG_NEG = 'spam:ds:msg:neg'

    # 一時保存場所 Noun: 名詞
    # Type: hash
    DATASETS_TMP_PJT_POS = 'spam:ds:tmp:pjt:mlm:pos'
    DATASETS_TMP_PJT_NEG = 'spam:ds:tmp:pjt:mlm:neg'
    DATASETS_TMP_MSG_POS = 'spam:ds:tmp:msg:pos'
    DATASETS_TMP_MSG_NEG = 'spam:ds:tmp:msg:neg'

    # {0}部分には日時を入れる
    REPORT_PJT_PATH = 'storage/reports/{0}_report_pjt.csv'
    REPORT_MSG_PATH = 'storage/reports/{0}_report_msg.csv'

    # Type: set
    REPORT_PJT = 'spam:report:pjt'
    REPORT_MSG = 'spam:report:msg'
    MSG_DETECTED_USER_ID = 'spam:msg:detected:user:id'
    URL_BLACKLIST = 'spam:url:blacklist'


class Whitelists(object):
    '''
    ホワイトリスト方式
    SQLの in ()に渡すときにリストだとエラーになるので、タプルで保持する
    '''
    # このホワイトリストに入っているユーザが作成した依頼は白にする
    # 要素が1以下になるとSQLエラーになるので、最低2つ以上の要素を持たせること
    # 1以下になるならダミーのxxxとかでもいいから２以上にすること
    REGEX_USERS_WHITELIST = (
        # Lancers社で使用しているアカウント
        'e-lancers_order[0-9]+$',
        'lancers_order[0-9]+$',
        # Quant社で使用しているアカウント
        'd-communication[0-9]+$',
    )
    USERS_WHITELIST = (
        'webciel', 'fit_001', 'lancers_order', 'lancers_C_writer',
        'magallanica500', 'oeponta', 'mikata200', 'n-madialab', 'doggy-kun'
    )
    # このホワイトリストに入っているキーワードが含まれている場合は白にする。
    KEYWORDS_WHITELIST = ('BUYMA', 'buyma', 'バイマ', 'ばいま',)

    REGEX_WORKS_HEAD_WORDS = (
        u'^よろしくお願い',
        u'^宜しくお願い',
        u'^お世話に',
        u'^いつもお世話に',
        u'^ご提案',
        u'^この度はご協力頂き',
        u'^お待たせしております',
    )

class Words(object):
    '''
    直感で追加していく。職人技の賜物
    '''
    # \sはタブとかスペースなどの空白系をまとめたもの
    REMOVE_WORDS = (
        '\s',
        '依頼タイトル',
        '依頼概要',
        '依頼詳細',
        '依頼の目的/概要',
        '依頼の目的・背景',
        '依頼の特徴',
        '概要・特徴',
        '開発の継続性',
        '対応ページ数',
        '用意してある素材',
        '重視する点',
        '希望スキル',
        '希望CMS',
        '補足説明',
        '分からないので、相談して決めさせていただければと思います。',
        '設定なし',
        'なし',
        '作業内容',
        '作業範囲',
        '用意してあるもの',
        '参考URL',
        '希望開発言語',
        'ジャンル',
        '記事のジャンル',
        '記事タイプ',
        '納品方法',
        '納品方法について',
        '禁止事項',
        '作業時の注意点',
        'その他注意点',
        '作業・単価の補足',
        '作業の締め切り',
        '募集の締め切り',
        '画像の入手方法',
        '画像枚数',
        '記事単価',
        '文字数',
        '記事数',
        '連絡方法',
        '報酬',
        '内容',
        '応募時の要望事項',
        '今後の流れ',
        '追記',
        '利用用途',
        '応募と採用について',
        'キーワード',
        '記事タイトル',
        '記事本文',
        '設定テーマ',
        'オプション',
        '文体',
        'サンプルURL',
        '読者ターゲット',
        '書き手の設定',
        '支払方式',
        '目安予算',
        '希望納期',
        '添付ファイル',
        'NGワード',
        '作業単価×件数',
        '作業公開',
        '一人あたりの制限',
        'フレームワーク',
        '対応OS',
        '主な機能',
        '参考アプリ',
        '開発の範囲',
        '開発の進捗状況',
        'サイトの種類',
        '期待する効果',
        'ターゲット像',
        'ページ数',
        '年代',
        '性別',
        'その他',
        'スマホ対応の有無',
        '納品後のサポート',
        '用意している',
        '用意していない',
        'サイト名称',
        'スマホ対応',
        '必要なページ',
        '希望する色',
        'サイズ',
        '希望イメージ',
        '依頼金額',
        'ECサイトの出店先',
        'CMS導入',
        '改善サイト',
        '対策ワード',
        '希望ロゴ種類',
        'ロゴ表記名称',
        '商標登録予定',
        '商標登録予定なし',
        '商標登録予定あり',
        '記載項目',
        '1本あたりの時間',
        '動画の本数',
        '撮影日数',
        '撮影予定地',
        'アニメーションの有無',
        'テロップの有無',
        'あり',
        'なし',
        'ランサーに相談しながら決めたい',
        '範囲を指定する',
        '参考動画',
        'ランサーに相談',
        '撮影あり',
        '撮影なし',
        '言語',
        '翻訳分野',
        '総ワード数',
        'ワード単価',
        '納品形式',
        '今回のみ依頼したい',
        '継続的に依頼したい',
        '時間報酬制',
        '固定報酬制',
        'ZIPファイルによる納品',
        'オンラインストレージへのアップロード',
        '指定のサーバへのアップロード',
        '男性',
        '女性',
        '以上',
        'わからない方はこちら（ランサーにお任せ）',
        '継続的に開発を依頼したい',
        '対応するページ数を指定する',
        '素材を用意していない方はこちら（ランサーにお任せ）',
        'この開発の後も、継続的に依頼したいと思っております。',
        '予算',
        '納期',
        'クオリティ',
        '柔軟な対応',
        'こまめな連絡',
        '業務経験',
        '知識',
        '納品ファイル',
        '用意してある素材を指定する',
        'はじめまして',
        '初めまして',
        'ご覧いただき',
        'ご覧頂き',
        'こんにちは',
        '何卒',
        'お願いいたします',
        'お願い致します',
        'よろしくお願いいたします'
        'よろしくお願い致します',
        'よろしくお願いします'
        'どうぞよろしくお願いいたします',
        '宜しくお願いします',
        '宜しくお願い致します',
        'ご迷惑をおかけしますが',
        'この度はご協力頂き',
        'ありがとうございます',
        'ありがとうございました',
        '有難うございます',
        '有難うございました',
        'いつもお世話になっております',
        'お世話になっております',
        'お世話になります',
        'あらかじめ',
        'ご了承ください',
        'ご不明点がありましたら',
        'ご欄頂きましてありがとうございます',
        '気軽に',
        'お問い合わせ',
        'ください',
        '皆様からの',
        '応募を',
        '心より',
        'お待ちしています',
        'ご応募お待ちしております',
        '画像の用意は不要です',
        '===(Lancersサポートチーム)===',
        u'利用規約違反の恐れにより、ステータスを「一時停止」として、クライアント様と調整中です。',
        'Lancersサポートチーム：利用規約違反の恐れのある依頼内容の一部が非公開となりました',
        'Lancersサポートチーム',
        'サポートチーム',
        'ランサーズ',
        'ランサー',
        'Lancers',
        'lancers',
        'lancer',
        # (), !, ?は正規表現で意味を持っているので、バックスラッシュでエスケープする必要がある。
        '\(\)',
        '（）',
        '\!',
        '！',
        '○',
        '●',
        '？',
        '\?',
        '※',
        '<span>'
    )

    # 下記サイトに日本語の推奨stop wordsがまとめられている
    # http://svn.sourceforge.jp/svnroot/slothlib/CSharp/Version1/SlothLib/NLP/Filter/StopWord/word/Japanese.txt
    STOP_WORDS = (
        'あそこ', 'あたり', 'あちら', 'あっち', 'あと', 'あな', 'あなた', 'あれ', 'いくつ',
        'いつ', 'いま', 'いや', 'いろいろ', 'うち', 'おおまか', 'おまえ', 'おれ', 'がい',
        'かく', 'かたち', 'かやの', 'から', 'がら', 'きた', 'くせ', 'ここ', 'こっち',
        'こと', 'ごと', 'こちら', 'ごっちゃ', 'これ', 'これら', 'ごろ', 'さまざま', 'さらい',
        'さん', 'しかた', 'しよう', 'すか', 'ずつ', 'すね', 'すべて', 'ぜんぶ', 'そう',
        'そこ', 'そちら', 'そっち', 'そで', 'それ', 'それぞれ', 'それなり', 'たくさん',
        'たち', 'たび', 'ため', 'だめ', 'ちゃ', 'ちゃん', 'てん', 'とおり', 'とき', 'どこ',
        'どこか', 'ところ', 'どちら', 'どっか', 'どっち', 'どれ', 'なか', 'なかば', 'なに',
        'など', 'なん', 'はじめ', 'はず', 'はるか', 'ひと', 'ひとつ', 'ふく', 'ぶり', 'べつ',
        'へん', 'ぺん', 'ほう', 'ほか', 'まさ', 'まし', 'まとも', 'まま', 'みたい', 'みつ',
        'みなさん', 'みんな', 'もと', 'もの', 'もん', 'やつ', 'よう', 'よそ', 'わけ',
        'わたし', 'ハイ', '上', '中', '下', '字', '年', '月', '日', '時', '分', '秒',
        '週', '火', '水', '木', '金', '土', '国', '都', '道', '府', '県', '市', '区',
        '町', '村', '各', '第', '方', '何', '的', '度', '文', '者', '性', '体', '人',
        '他', '今', '部', '課', '係', '外', '類', '達', '気', '室', '口', '誰', '用',
        '界', '会', '首', '男', '女', '別', '話', '私', '屋', '店', '家', '場', '等',
        '見', '際', '観', '段', '略', '例', '系', '論', '形', '間', '地', '員', '線',
        '点', '書', '品', '力', '法', '感', '作', '元', '手', '数', '彼', '彼女', '子',
        '内', '楽', '喜', '怒', '哀', '輪', '頃', '化', '境', '俺', '奴', '高', '校',
        '婦', '伸', '紀', '誌', 'レ', '行', '列', '事', '士', '台', '集', '様', '所',
        '歴', '器', '名', '情', '連', '毎', '式', '簿', '回', '匹', '個', '席', '束',
        '歳', '目', '通', '面', '円', '玉', '枚', '前', '後', '左', '右', '次', '先',
        '春', '夏', '秋', '冬', '一', '二', '三', '四', '五', '六', '七', '八', '九',
        '十', '百', '千', '万', '億', '兆', '下記', '上記', '時間', '今回', '前回',
        '場合', '一つ', '年生', '自分', 'ヶ所', 'ヵ所', 'カ所', '箇所', 'ヶ月', 'ヵ月',
        'カ月', '箇月', '名前', '本当', '確か', '時点', '全部', '関係', '近く', '方法',
        '我々', '違い', '多く', '扱い', '新た', 'その後', '半ば', '結局', '様々',
        '以前', '以後', '以降', '未満', '以上', '以下', '幾つ', '毎日', '自体',
        '向こう', '何人', '手段', '同じ', '感じ', 'お願い', 'おねがい', 'まじめ', 'いただき',
        'おの', 'ばらつき', 'づつ', 'なり', 'そのままで', 'お待ち', 'お話し', 'まいの',
        'お知らせ', 'よろしくお願いします', 'てつ', 'やり取り', 'お話', 'いくら', 'なのか',
        'かなり', '本円', 'お仕事', 'ご存知', '曜日', ' 幸い', 'しない', 'ます', 'inc',
        'client', 'そのため', '他', 'たま', '日日', 'うえ', 'おご', 'こまめ', 'おかけ',
        'いかが', 'との', 'とんでも', 'ござ', '商品', 'くだ', 'さい', 'した', 'する',
        'いらっしゃる', 'ござる', 'なる', 'くる', 'やる', 'なさる', 'いただける', '思う',
        'なん', 'いかが',
    )
