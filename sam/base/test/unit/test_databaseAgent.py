#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid
import logging

import pickle
import base64

from sam.base.databaseAgent import DatabaseAgent
from sam.base.loggerConfigurator import LoggerConfigurator

MANUAL_TEST = True
logging.basicConfig(level=logging.INFO)


class TestDatabaseAgentClass(object):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        logConfigur = LoggerConfigurator(__name__, './log',
            'testDBAgent.log', level='debug')
        cls.logger = logConfigur.getLogger()

        cls.dbA = DatabaseAgent(host = "localhost",
            user = "dbAgent", passwd = "123")
        cls.dbA.connectDB(db = "Orchestrator")
        cls.REQUEST_UUID = uuid.uuid1()
        cls.testObject = {'key':1}

        if cls.dbA.hasTable("Orchestrator", "Request"):
            cls.dbA.dropTable("Request")

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """

    def test_createTable(self):
        self.dbA.createTable("Request",
            # """
            # runoob_id INT UNSIGNED AUTO_INCREMENT,
            # runoob_title VARCHAR(100) NOT NULL,
            # runoob_author VARCHAR(40) NOT NULL,
            # submission_date DATE,
            # PRIMARY KEY ( runoob_id )
            # """
            """
            USER_ID INT UNSIGNED AUTO_INCREMENT,
            FIRST_NAME  CHAR(20) NOT NULL,
            LAST_NAME  CHAR(20),
            AGE INT,  
            SEX CHAR(1),
            INCOME FLOAT,
            REQUEST_UUID VARCHAR(36),
            PICKLE BLOB,
            submission_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY ( USER_ID ),
            INDEX REQUEST_UUID_INDEX (REQUEST_UUID(36)),
            INDEX FIRST_NAME_INDEX (FIRST_NAME(20)),
            INDEX AGE_INDEX (AGE),
            INDEX INCOME_INDEX (INCOME)
            """
            )

    def test_insert(self):
        self.dbA.insert("Request", 
            " AGE, SEX, FIRST_NAME, LAST_NAME, INCOME, REQUEST_UUID, PICKLE ",
            " 20, 'M', 'Mac', 'Mohan', 2000, '{0}', '{1}'".format(
                self.REQUEST_UUID, self._encodeObject2Pickle(self.testObject))
            )
        results = self.dbA.query("Request", "*")
        assert results[0][:-1] == ('1L', 'Mac', 'Mohan', '20L', 'M', 2000.0,
            str(self.REQUEST_UUID), 'gAJ9cQBVA2tleXEBSwFzLg==' )
        assert self._decodePickle2Object(results[0][7]) == self.testObject

    def test_update(self):
        self.dbA.update("Request", "AGE = 10", " SEX = 'M'")
        results = self.dbA.query("Request", "*")
        assert results[0][:-1] == ('1L', 'Mac', 'Mohan', '10L', 'M', 2000.0,
            str(self.REQUEST_UUID), 'gAJ9cQBVA2tleXEBSwFzLg==')
        assert type(uuid.UUID(results[0][6])) == type(uuid.uuid1())

    def test_delete(self):
        self.dbA.delete("Request", " SEX = 'M'")
        results = self.dbA.query("Request", "*")
        assert results == ()

    def test_dropTable(self):
        self.dbA.dropTable("Request")
        assert self.dbA.hasTable("Orchestrator", "Request") == False

    def _encodeObject2Pickle(self, pObject):
        return base64.b64encode(pickle.dumps(pObject,-1))

    def _decodePickle2Object(self, pickledStr):
        return pickle.loads(base64.b64decode(pickledStr))
