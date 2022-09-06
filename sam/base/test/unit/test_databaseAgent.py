#!/usr/bin/python
# -*- coding: UTF-8 -*-

import uuid

from sam.base.pickleIO import PickleIO
from sam.base.databaseAgent import DatabaseAgent
from sam.base.loggerConfigurator import LoggerConfigurator


class TestDatabaseAgentClass(object):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """
        logConfigur = LoggerConfigurator(__name__, './log',
            'testDBAgent.log', level='debug')
        cls.logger = logConfigur.getLogger()

        cls.pIO = PickleIO()

        cls.dbA = DatabaseAgent(host = "localhost",
            user = "dbAgent", passwd = "123")
        cls.dbA.connectDB(db = "Orchestrator")

        cls.REQUEST_UUID = uuid.uuid1()
        cls.testObject = {'key':1}

        if cls.dbA.hasTable("Orchestrator", "Request"):
            cls.dbA.dropTable("Orchestrator")
            cls.dbA.dropTable("Request")

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """

    def test_createTable(self):
        self.dbA.createTable("Request",
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
            (20, 'M', 'Mac', 'Mohan', 2000, self.REQUEST_UUID,
                    self._encodeObject2Pickle(self.testObject))
            )
        results = self.dbA.query("Request", "*")
        assert results[0][:-2] == (1, 'Mac', 'Mohan', 20, 'M', 2000.0,
            str(self.REQUEST_UUID) )
        assert self._decodePickle2Object(results[0][7]) == self.testObject

    def test_update1(self):
        self.dbA.update("Request", "AGE = (10)", " SEX = 'M'")
        results = self.dbA.query("Request", "*")
        assert results[0][:-2] == (1, 'Mac', 'Mohan', 10, 'M', 2000.0,
            str(self.REQUEST_UUID))
        assert self._decodePickle2Object(results[0][7]) == self.testObject
        assert type(uuid.UUID(results[0][6])) == type(uuid.UUID)

    def test_update2(self):
        request = {"requestID":1}
        self.dbA.update("Request",
                        "AGE = (10)",
                        " REQUEST_UUID = '{0}' ".format(self.REQUEST_UUID))
        results = self.dbA.query("Request", "*")
        assert results[0][:-2] == (1, 'Mac', 'Mohan', 10, 'M', 2000.0,
            str(self.REQUEST_UUID))
        assert self._decodePickle2Object(results[0][7]) == self.testObject
        assert type(uuid.UUID(results[0][6])) == type(UUID)

    def test_update3(self):
        request = {"requestID":1}
        self.dbA.update("Request",
                        " PICKLE = ('{0}') ".format(self._encodeObject2Pickle(request).decode()),
                        " REQUEST_UUID = '{0}' ".format(self.REQUEST_UUID))
        results = self.dbA.query("Request", "*")
        assert results[0][:-2] == (1, 'Mac', 'Mohan', 10, 'M', 2000.0,
            str(self.REQUEST_UUID))
        assert self._decodePickle2Object(results[0][7]) == request
        assert type(uuid.UUID(results[0][6])) == type(UUID)

    def test_update4(self):
        request = {"requestID":1}
        self.dbA.update("Request", "AGE = (10), FIRST_NAME = ('Mike')", " SEX = 'M'")
        results = self.dbA.query("Request", "*")
        assert results[0][:-2] == (1, 'Mike', 'Mohan', 10, 'M', 2000.0,
            str(self.REQUEST_UUID))
        assert self._decodePickle2Object(results[0][7]) == request
        assert type(uuid.UUID(results[0][6])) == type(UUID)

    def test_delete(self):
        self.dbA.delete("Request", " SEX = 'M'")
        results = self.dbA.query("Request", "*")
        assert results == ()

    def test_dropTable(self):
        self.dbA.dropTable("Request")
        assert self.dbA.hasTable("Orchestrator", "Request") == False

    def _encodeObject2Pickle(self, pObject):
        return self.pIO.obj2Pickle(pObject)

    def _decodePickle2Object(self, pickledStr):
        return self.pIO.pickle2Obj(pickledStr)
