#!/usr/bin/env python3

import threading

class DataProcessing():

    def __init__(self):
        self.lastest_data = None
        self.lock = threading.Lock()

    def on_new_data(self, data):
        with self.lock:
            self.lastest_data = data

    def pop_latest_data(self):
        with self.lock:
            data = self.lastest_data
            self.lastest_data = None
            return data