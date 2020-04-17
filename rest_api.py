#!/usr/bin/env python3

from flask import Flask

from serial_reader import BackgroundSerialReader
from data_processing import DataProcessing

app = Flask(__name__)

data_processing = DataProcessing()

@app.route('/')
def get_latest_data():
    return data_processing.pop_latest_data()

if __name__ == '__main__':

    serial_reader = BackgroundSerialReader(data_processing.on_new_data)
    serial_reader.start()

    app.run()
    serial_reader.interrupt()