import sys

import pytest
from ryu.controller import dpset

from sam.ryu.topoCollector import TopoCollector

class TestTopoCollectorClass(object):
    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """