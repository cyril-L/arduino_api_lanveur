#!/usr/bin/env python3

import threading
import datetime as dt

class DataProcessing():

    def __init__(self):
        self.lastest_data = None
        self.lock = threading.Lock()

    def on_new_data(self, data):
        with self.lock:
            self.lastest_data = data
            self.lastest_data.insert(0, dt.datetime.utcnow())

    def pop_latest_data(self):
        with self.lock:
            data = self.lastest_data
            self.lastest_data = None
            return data