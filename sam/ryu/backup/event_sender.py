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
from ryu.controller import event
from ryu.lib import hub

# A user defined event class
class TestEvent(event.EventBase):
    def __init__(self, msg):
        super(TestEvent, self).__init__()
        self.msg = msg

class EventSender(app_manager.RyuApp):
    # Register user defined events which this RyuApp would generate
    _EVENTS = [TestEvent]

    def _periodic_event_loop(self):
        while True:
            hub.sleep(1)
            # 2 event: get topology event; update fib event
            ev = TestEvent('TEST EVENT')
            self.logger.info('*** Send event: event.msg = %s', ev.msg)
            # send mod msg to ryuapp
            self.send_event_to_observers(ev)

    def start(self):
        super(EventSender, self).start()
        # Start user defined event loop
        self.threads.append(hub.spawn(self._periodic_event_loop))