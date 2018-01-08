# coding: utf-8

from app import app
from app.mysql.connect import Connect


class WorkSpams():
    ''''''

    def __init__(self, role='master'):
        self.role = role

    def __enter__(self):
        self.con = Connect(role=self.role)
        self.m = self.con.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None:
            self.con.close()
        else:
            app.logger.warning('WorkSpams mysql connection closing is failed')
            return False

    def create(self):
        '''

        '''
        query = ('''
            INSERT
        ''')

        self.m.execute(query)

    def get(self):
        '''

        '''
        pass

    def list(self):
        '''

        '''
        pass

    def edit(self):
        '''

        '''
        pass
