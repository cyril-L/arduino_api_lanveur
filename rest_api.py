#!/usr/bin/env python3

from flask import Flask, abort, jsonify

from serial_reader import BackgroundSerialReader
from data_processing import DataProcessing


app = Flask(__name__)

data_processing = DataProcessing()

@app.route('/')
def get_latest_data():
    data = data_processing.pop_latest_data()
    if data is not None:
        return jsonify(data)
    else:
        abort(500, description="No fesh data available")

if __name__ == '__main__':

    serial_reader = BackgroundSerialReader(data_processing.on_new_data)
    serial_reader.start()

    app.run()
    serial_reader.interrupt()