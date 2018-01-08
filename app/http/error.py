# coding: utf-8

from flask import jsonify
from app import app


class Error():
    '''
    HTTP Response Error
    '''

    def __init__(self):
        self.status = None
        self.code = None
        self.message = None
        self.errors = None

    def _ready(self, log_level='info'):
        if log_level == 'critical':
            app.logger.critical(str(self.status) + ' ' + self.message)
        else:
            app.logger.info(str(self.status) + ' ' + self.message)

        error = {
            'status': self.status,
            'code': self.code,
            'message': self.message
        }

        if self.errors:
            error['errors'] = self.errors

        return jsonify(error), self.status

    def bad_request(self, message):
        self.status = 400
        if 'errors' in message:
            self.code = message['code']
            self.message = message['message']
            self.errors = message['errors']
        else:
            self.code = message['code']
            self.message = message['message']

        return self._ready()

    def unauthorized(self, message):
        self.status = 403
        self.code = 'unauthorized'
        self.message = message

        return self._ready()

    def forbidden(self, message):
        self.status = 403
        self.code = 'forbidden'
        self.message = message

        return self._ready()

    def not_found(self, message):
        self.status = 404
        self.code = 'not_found'
        self.message = str(message)

        return self._ready()

    def method_not_allowed(self, message):
        self.status = 405
        self.code = 'method_not_allowed'
        self.message = message

        return self._ready()

    def request_timeout(self, message):
        self.status = 408
        self.code = 'request_timeout'
        self.message = message

        return self._ready()

    def conflict(self, message):
        self.status = 409
        self.code = 'conflict'
        self.message = message

        return self._ready()

    def internal_server_error(self, message):
        self.status = 500
        self.code = 'internal_server_error'
        self.message = str(message)

        return self._ready('critical')
