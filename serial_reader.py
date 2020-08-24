#!/usr/bin/env python3
#
# Copyright 2020 Cyril Lugan.
# Licensed under the EUPL v1.2 (see https://eupl.eu/1.2/en/)
# ==============================================================================
"""Parses data from the Arduino, streamed on a serial port.

Reads rows of values form the Arduino on the serial port,
exposes them as lists of unlabeled values,
handles parsing errors, reconnection and Arduino reset.

Reads: b'10570 ; 5285 ; 225 ; 52.37 ; 47.02 ; 43.94 ; 37.66 ; 18.15 ; 48.62 ; 47.08 ; \r\n'
Exposes: [10570, 5285, 225, 52.37, 47.02, 43.94, 37.66, 18.15, 48.62, 47.08]

Typical usage example:

    def callback(data):
        print(data)

    serial_reader = BackgroundSerialReader(callback)
    serial_reader.start()

Run directly for unit tests:

    python serial_reader.py --unit-test

Run directly to test connection with the Arduino

    python serial_reader.py --arduino
"""

import logging
import threading
import time
import serial

from config import SERIAL_DEVICE, SERIAL_BAUDRATE, FRESH_DATA_TIMEOUT_S, SERIAL_RECONNECT_TIMEOUT_S

class SerialReader():

    def __init__(self, ioserial):
        self.ioserial = ioserial
        self.ioserial.flush()

    def read_data_line(self):
        line = self.ioserial.readline()
        if len(line) == 0:
            logging.error("Serial timeout")
            # pyserial returns an empty line on timeout,
            # Continuous data is expected in our case,
            # raise an exception to be handled at upper level
            raise TimeoutError
        data = self.parse_data_line(line)
        if data is None:
            logging.warning("Unable to parse data line ({})".format(line))
        return data

    @staticmethod
    def parse_data_line(line):
        """
        Args:
            line: utf-8 encoded row of 10 values from the Arduino, separated by semicolons.

        Returns:
            A parsed list of values, None if parsing failed.
        """
        try:
            # converts bytes to string
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            return None
        line = line.strip("; \r\n")
        line = line.split(";")
        if len(line) != 10:
            return None
        try:
            return [int(line[0]),
                    int(line[1]),
                    int(line[2]),
                    float(line[3]),
                    float(line[4]),
                    float(line[5]),
                    float(line[6]),
                    float(line[7]),
                    float(line[8]),
                    float(line[9])]
        except ValueError:
            return None

    def reset_arduino(self):
        """Outputs serial control signals used to reset the Arduino."""
        logging.warning("Reseting Arduino")
        self.ioserial.setDTR(False)
        time.sleep(1)
        self.ioserial.flushInput()
        self.ioserial.setDTR(True)

class BackgroundSerialReader():
    """Runs SerialReader in a thread, reconnect automatically on errors and timeout.

    As it recon
    """

    def __init__(self, on_data_callback,
                 serial_device=SERIAL_DEVICE,
                 serial_baudrate=SERIAL_BAUDRATE,
                 fresh_data_timeout=FRESH_DATA_TIMEOUT_S):
        self.serial_device = serial_device
        self.serial_baudrate = serial_baudrate
        self.fresh_data_timeout_duration = fresh_data_timeout
        self.callback = on_data_callback
        self.thread = threading.Thread(target=self.main_loop)
        self.is_interrupted = False

    def start(self):
        self.thread.start()

    def join(self):
        self.thread.join()

    def interrupt(self):
        self.is_interrupted = True
        self.thread.join()

    def main_loop(self):
        while not self.is_interrupted:
            try:
                with self.open_serial_port() as arduino_serial:
                    self.data_reader_loop(arduino_serial)
            except (FileNotFoundError, serial.serialutil.SerialException) as e:
                logging.warning(e)
                logging.warning("Retrying in {} s".format(SERIAL_RECONNECT_TIMEOUT_S))
                time.sleep(SERIAL_RECONNECT_TIMEOUT_S)

    def data_reader_loop(self, arduino_serial):
        reader = SerialReader(arduino_serial)
        self.reset_timeout()

        while not self.is_interrupted:
            serial_timeout = False
            try:
                data = reader.read_data_line()
            except TimeoutError:
                serial_timeout = True

            if serial_timeout or self.has_timedout():
                logging.warning("No valid data received in the last {} s".format(
                    self.fresh_data_timeout_duration))
                reader.reset_arduino()
                self.reset_timeout()
            elif data is not None:
                self.callback(data)
                self.reset_timeout()

    def open_serial_port(self):
        return serial.Serial(port=self.serial_device,
                             baudrate=self.serial_baudrate,
                             timeout=self.fresh_data_timeout_duration)

    def has_timedout(self):
        return time.monotonic() > self.fresh_data_timeout

    def reset_timeout(self):
        self.fresh_data_timeout = time.monotonic() + self.fresh_data_timeout_duration

if __name__ == '__main__':

    import argparse
    import unittest
    import io
    import sys
    import datetime as dt

    class TestSerialReader(unittest.TestCase):

        def test_returns_parsed_data(self):
            serial = io.BytesIO(b'10570 ; 5285 ; 225 ; 52.37 ; 47.02 ; 43.94 ; 37.66 ; 18.15 ; 48.62 ; 47.08 ; \r\n')
            reader = SerialReader(serial)
            data = reader.read_data_line()
            expected = [10570, 5285, 225, 52.37, 47.02, 43.94, 37.66, 18.15, 48.62, 47.08]
            self.assertEqual(data, expected)

        def test_returns_none_on_invalid_data(self):
            # First line sent by the Arduino
            serial = io.BytesIO(b'Invalid data\r\n')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

        def test_returns_none_on_header(self):
            # First line sent by the Arduino
            serial = io.BytesIO(b'Vecs pulses ; Vep pulses  ; Eaux pulses ; Vep ; Teh ;  Teb ;  Tec ;  Tef ; Tep ; Txe ; Txs ; \r\n')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

        def test_returns_none_on_corrupted_data(self):
            # Typical line read when connecting to the Arduino
            serial = io.BytesIO(b'52.37 ; 46.52 ; 22.83 ; 58.89 ; 57.05 ; 6478 ; 3239 ; 225 ; 63.20 ; 56.12 ; 52.37 ; 46.52 ; 22.83 ; 58.89 ; 57.05 ; \r\n')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

        def test_handles_invalid_unicode(self):
            # Do not crash when reading some binary garbage
            serial = io.BytesIO(b'\x80\x81')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

        def test_raises_an_exception_on_timeout(self):
            class MockSerialTimeout():
                def readline(self):
                    return b''
                def flush(self):
                    pass
            serial = MockSerialTimeout()
            reader = SerialReader(serial)
            with self.assertLogs(level='ERROR'):
                with self.assertRaises(TimeoutError):
                    reader.read_data_line()

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--unit-test",
                        help="Run unit tests without connecting to the Arduino",
                        action='store_true')
    parser.add_argument("-a", "--arduino",
                        help="Connect to the Arduino and print data",
                        action='store_true')
    args = parser.parse_args()

    if args.arduino and not args.unit_test:
        def callback(data):
            data.insert(0, dt.datetime.now())
            data = [str(element) for element in data]
            print(", ".join(data))
        serial_reader = BackgroundSerialReader(callback)
        serial_reader.start()
        try:
            serial_reader.join()
        except KeyboardInterrupt:
            serial_reader.interrupt()

    elif args.unit_test and not args.arduino:
        sys.argv.pop()
        unittest.main()

    else:
        parser.print_help(sys.stderr)