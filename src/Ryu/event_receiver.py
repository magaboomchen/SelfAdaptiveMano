# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
import event_sender

class EventReceiver(app_manager.RyuApp):
    _EVENTS = [event_sender.TestEvent]

    # Catch a user defined event with "set_ev_cls" decorator
    @set_ev_cls(event_sender.TestEvent)
    def _test_event_handler(self, ev):
        self.logger.info('*** Received event: ev.msg = %s', ev.msg)