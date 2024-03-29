#!/usr/bin/python
# -*- coding: UTF-8 -*-

DATABASE_TYPE_PYMYSQL = "DATABASE_TYPE_PYMYSQL"
DATABASE_TYPE_MYSQLDB = "DATABASE_TYPE_MYSQLDB"

import sys
if sys.version > '3':
    dbType = DATABASE_TYPE_PYMYSQL
    import pymysql
    pymysql.install_as_MySQLdb()
else:
    dbType = DATABASE_TYPE_MYSQLDB
    import MySQLdb

from sam.base.loggerConfigurator import LoggerConfigurator
from sam.base.exceptionProcessor import ExceptionProcessor


class DatabaseAgent(object):
    def __init__(self, host, user, passwd):
        logConfigur = LoggerConfigurator(__name__, './log',
            'databaseAgent.log', level='warning')
        self.logger = logConfigur.getLogger()

        self.host = host
        self.user = user
        self.passwd = passwd
        self.cursor = None
        self.db = None

    def isConnectingDB(self):
        if self.db != None:
            if sys.version > '3':
                try:
                    self.db.ping(reconnect=False)
                except Exception as ex:
                    # ExceptionProcessor(self.logger).logException(ex)
                    self.logger.debug("Unconnection.")
                    return False
                return True
            else:
                return self.db.is_connected()
        else:
            return False

    def connectDB(self, db):
        if sys.version > '3':
            self.db = pymysql.connect(host=self.host, user=self.user,
                                        password=self.passwd, database=db)
        else:
            self.db = MySQLdb.connect(host = self.host, user = self.user,
                                        passwd = self.passwd, db = db)
        self.cursor = self.db.cursor()

    def createTable(self, tableName, fields, engine=None, charset=None):
        #TODO: check whether existed this table?

        sql = """CREATE TABLE {0} ({1})""".format(tableName, fields)
        if engine != None:
            sql = sql + " ENGINE={0} ".format(engine)
        if charset != None:
            sql = sql + " DEFAULT CHARSET={0}".format(charset)
        self.logger.debug("createTable, sql={0}".format(sql))
        self.cursor.execute(sql)

    def hasTable(self, db, tableName):
        sql = """
            SELECT * FROM information_schema.tables WHERE table_schema = '{0}'
            AND table_name = '{1}' LIMIT 1; """.format(db, tableName)
        # self.logger.debug("sql: {0}".format(sql))
        self.cursor.execute(sql)
        results = self.cursor.fetchall()
        # self.logger.debug("hasTable results:{0}".format(results))
        if results == ():
            # self.logger.debug("hasTable: False")
            return False
        else:
            # self.logger.debug("hasTable: True")
            return True

    def dropTable(self, tableName):
        sql = "DROP TABLE IF EXISTS {0}".format(tableName)
        self.cursor.execute(sql)

    def insert(self, tableName, fields, insertDataTuple):
        try:
            valuesNum = len(insertDataTuple)
            sqlInsertQuery = """ INSERT INTO {0}
                    ({1}) VALUES ({2})""".format(tableName, fields, 
                                            '%s,'*(valuesNum-1)+'%s')
            self.logger.debug("insert, sqlInsertQuery={0} " \
                                "insertDataTuple={1}".format(
                                    sqlInsertQuery, insertDataTuple))
            result = self.cursor.execute(sqlInsertQuery, insertDataTuple)
            self.db.commit()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
            self.db.rollback()
            raise ValueError("insert sql failed, sql is {0}".format(sqlInsertQuery))

    def query(self, tableName, fields, condition=None):
        sql = """SELECT {0} FROM {1} """.format(
            fields, tableName
        )
        if condition != None:
            sql = sql + " WHERE {0} ".format(condition)
        # self.logger.debug("query sql: {0}".format(sql))
        self.cursor.execute(sql)
        results = self.cursor.fetchall()
        # self.logger.debug("query results:{0}".format(results))
        return results

    def update(self, tableName, fieldsValues, condition=None):
        sql = "UPDATE {0} SET {1} ".format(tableName, fieldsValues)
        if condition != None:
            sql = sql + " WHERE {0} ".format(condition)
        try:
            self.logger.debug("db update sql is {0}".format(sql))
            self.cursor.execute(sql)
            self.db.commit()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
            self.db.rollback()
            raise ValueError("update sql failed, sql is {0}".format(sql))

    def delete(self, tableName, condition):
        sql = "DELETE FROM {0} WHERE {1}".format(tableName, condition)
        self.logger.debug("delete, sql={0}".format(sql))
        try:
            self.cursor.execute(sql)
            self.db.commit()
        except Exception as ex:
            ExceptionProcessor(self.logger).logException(ex)
            self.db.rollback()
            raise ValueError("delete sql failed, sql is {0}".format(sql))

    def disconnect(self):
        self.db.close()
        self.db = None
        self.cursor = None

    def __del__(self):
        self.logger.info("Delete DatabaseAgent.")
        if self.db != None:
            self.disconnect()
            self.db = None
