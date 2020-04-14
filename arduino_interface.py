#!/usr/bin/env python3

import logging

class SerialReader():

    def __init__(self, ioserial):
        self.ioserial = ioserial

    def read_data_line(self):
        line = self.ioserial.readline()
        data = self.parse_data_line(line)
        if data is None:
            logging.warning(f"Unable to parse data line ({line})")
        return data

    @staticmethod
    def parse_data_line(line):
        try:
            # converts bytes to string
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            return None
        line = line.strip(";\r\n")
        line = line.split(";")
        if len(line) != 11:
            return None
        try:
            return {
                'v1': int(line[2]),
                'v2': int(line[3]),
                't1': float(line[4]),
                't2': float(line[5]),
                't3': float(line[6]),
                't4': float(line[7]),
                't5': float(line[8]),
                't6': float(line[9]),
                't7': float(line[10])
            }
        except ValueError:
            return None

if __name__ == '__main__':

    import unittest
    import io

    class TestSerialReader(unittest.TestCase):

        def test_read_data_line(self):
            serial = io.BytesIO(b';    110   ;   41    ;    6478  ;  3239       ;       63.14   ;     56.12   ;     52.31   ;     46.65   ;     22.28   ;     58.77   ;     56.86   ;\r\n')
            reader = SerialReader(serial)
            data = reader.read_data_line()
            expected = {
                'v1': 6478,
                'v2': 3239,
                't1': 63.14,
                't2': 56.12,
                't3': 52.31,
                't4': 46.65,
                't5': 22.28,
                't6': 58.77,
                't7': 56.86
            }
            self.assertEqual(data, expected)

        def test_ignore_header(self):
            # First line sent by the Arduino
            serial = io.BytesIO(b';  D1 Impuls et Volume (L)  ;    D2 Impuls et Volume (l)  ;  S1 H ballon (\xc2\xb0C) ; S2 B ballon (\xc2\xb0C) ;  S3 Sortie ballon(\xc2\xb0C) ;  S4 Eau froide (\xc2\xb0C) ;  S5 sortie Panneaux(\xc2\xb0C) ; Entrer Echang (\xc2\xb0C) ; Sortie Echang(\xc2\xb0C)\r\n')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

        def test_ignore_corrupted_data(self):
            # Typical line read when connecting to the Arduino
            serial = io.BytesIO(b';     52.37   ;     46.52   ;     22.83   ;     58.89   ;     57.05   ;       6478  ;  3239       ;       63.20   ;     56.12   ;     52.37   ;     46.52   ;     22.83   ;     58.89   ;     57.05   ;\r\n')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

        def test_ignore_invalid_unicode(self):
            # Do not crash when reading some binary garbage
            serial = io.BytesIO(b'\x80\x81')
            reader = SerialReader(serial)
            with self.assertLogs(level='WARN'):
                data = reader.read_data_line()
            self.assertIsNone(data)

    unittest.main()