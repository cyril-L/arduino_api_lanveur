#!/usr/bin/env python3

import logging
import threading
import time
import serial

SERIAL_PORT     = "/dev/ttyACM0"
SERIAL_BAUDRATE = 9600
SERIAL_TIMEOUT  = 2

SERIAL_RECONNECT_TIMEOUT = 5

class SerialReader():

    def __init__(self, ioserial):
        self.ioserial = ioserial

    def read_data_line(self):
        line = self.ioserial.readline()
        if len(line) == 0:
            logging.error("Serial port timeout")
            # pyserial returns an empty line on timeout,
            # Continuous data is expected in our case,
            # raise an exception to be handled at upper level
            raise TimeoutError("Serial port timeout")
        data = self.parse_data_line(line)
        if data is None:
            logging.warning("Unable to parse data line ({})".format(line))
        return data

    @staticmethod
    def parse_data_line(line):
        try:
            # converts bytes to string
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            return None
        line = line.strip("; \r\n")
        line = line.split(";")
        if len(line) != 11:
            return None
        try:
            return [int(line[0]),
                    int(line[1]),
                    int(line[2]),
                    int(line[3]),
                    float(line[4]),
                    float(line[5]),
                    float(line[6]),
                    float(line[7]),
                    float(line[8]),
                    float(line[9]),
                    float(line[10])]
        except ValueError:
            return None

class BackgroundSerialReader():

    def __init__(self, on_data_callback,
                 serial_device=SERIAL_PORT,
                 serial_baudrate=SERIAL_BAUDRATE,
                 serial_timeout=SERIAL_TIMEOUT):
        self.serial_device = serial_device
        self.serial_timeout = serial_timeout
        self.serial_baudrate = serial_baudrate
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
                logging.error(e)
                time.sleep(SERIAL_RECONNECT_TIMEOUT)

    def data_reader_loop(self, arduino_serial):
        reader = SerialReader(arduino_serial)
        while not self.is_interrupted:
            try:
                data = reader.read_data_line()
                if data is not None:
                    self.callback(data)
            except TimeoutError:
                logging.error("Reseting Arduino")
                # Reset Arduino
                arduino_serial.setDTR(False)
                time.sleep(1)
                arduino_serial.flushInput()
                arduino_serial.setDTR(True)

    def open_serial_port(self):
        return serial.Serial(port=self.serial_device,
                             baudrate=self.serial_baudrate,
                             timeout=self.serial_timeout)

if __name__ == '__main__':

    import argparse
    import unittest
    import io
    import sys
    import datetime as dt

    class TestSerialReader(unittest.TestCase):

        def test_returns_parsed_data(self):
            serial = io.BytesIO(b';    225   ;   84    ;    10570  ;  5285       ;       52.37   ;     47.02   ;     43.94   ;     37.66   ;     18.15   ;     48.62   ;     47.08   ;       \r\n')
            reader = SerialReader(serial)
            data = reader.read_data_line()
            expected = [225, 84, 10570, 5285, 52.37, 47.02, 43.94, 37.66, 18.15, 48.62, 47.08]
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
            serial = io.BytesIO(b';  D1 Impuls et Volume (L)  ;    D2 Impuls et Volume (l)  ;  S1 H ballon (\xc2\xb0C) ; S2 B ballon (\xc2\xb0C) ;  S3 Sortie ballon(\xc2\xb0C) ;  S4 Eau froide (\xc2\xb0C) ;  S5 sortie Panneaux(\xc2\xb0C) ; Entrer Echang (\xc2\xb0C) ; Sortie Echang(\xc2\xb0C)\r\n')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

        def test_returns_none_on_corrupted_data(self):
            # Typical line read when connecting to the Arduino
            serial = io.BytesIO(b';     52.37   ;     46.52   ;     22.83   ;     58.89   ;     57.05   ;       6478  ;  3239       ;       63.20   ;     56.12   ;     52.37   ;     46.52   ;     22.83   ;     58.89   ;     57.05   ;\r\n')
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
            serial = MockSerialTimeout()
            reader = SerialReader(serial)
            with self.assertLogs(level='ERROR'):
                with self.assertRaises(TimeoutError):
                    reader.read_data_line()

    class TestBackgroundSerialReader(unittest.TestCase):

        def test_handles_timeout(self):
            # TODO
            pass

        def test_handles_arduino_not_connected(self):
            # TODO
            # Retry until up again
            # Keep counting ticks
            pass

        def test_handles_serial_error(self):
            # TODO
            pass

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