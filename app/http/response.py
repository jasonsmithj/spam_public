# coding: utf-8

import uuid

from flask import request, jsonify


class Response():

    def _formalize(self, items):
        '''
        レスポンスのためのメタデータを付与する
        @param dict items
        '''
        items['id'] = uuid.uuid4()
        items['self_link'] = request.url

    def parse(self, items):

        self._formalize(items)

        # Noneはjsonに変換するとnullになる
        return jsonify(items)
