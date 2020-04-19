#!/usr/bin/env python3

import threading
import time

from flask import Flask, abort, jsonify

from config import COUNTERS_FILE_PATH, COUNTERS_FILE_SAVE_PERIOD_MIN
from serial_reader import BackgroundSerialReader
from data_processing import DataProcessing, PersistentCounters

app = Flask(__name__)

class Pipeline():

    def __init__(self):
        self.counters = PersistentCounters(COUNTERS_FILE_PATH)
        self.save_counters_at = None

        self.data_processing = DataProcessing(self.counters)

        self.serial_reader = BackgroundSerialReader(self.on_new_data)

        self.latest_data = None
        self.lock = threading.Lock()

    def on_new_data(self, data):
        data = self.data_processing.process(data)
        with self.lock:
            self.latest_data = data

        now = time.monotonic()
        if self.save_counters_at is None or now > self.save_counters_at:
            self.counters.save()
            self.save_counters_at = now + COUNTERS_FILE_SAVE_PERIOD_MIN * 60

    def get_latest_data(self):
        with self.lock:
            data = self.latest_data
            self.latest_data = None
            return data

    def start(self):
        self.serial_reader.start()

    def stop(self):
        self.serial_reader.interrupt()
        self.counters.save()

pipeline = Pipeline()

@app.route('/')
def get_latest_data():
    data = pipeline.get_latest_data()
    if data is None:
        abort(500, description="No fresh data available")
    return jsonify(data)

if __name__ == '__main__':

    pipeline.start()
    app.run()
    pipeline.stop()
