#!/usr/bin/env python3
#
# Copyright 2020 Cyril Lugan, https://cyril.lugan.fr
# Licensed under the EUPL v1.2, https://eupl.eu/1.2/en/
# ==============================================================================
"""Makes human readable values of interest from a raw data line.

Reads: [0, 1, 0, 52.37, 47.02, 43.94, 37.66, 18.15, 16, 15]
Exposes: {
    'Vecs_pulses': 0, …,
    'Teh': 52.37, …,
    'Epst': 0.001161, # kWh
    …
}

Typical usage example:

    persistent_counters = PersistentCounters("counters.json")
    self.data_processing = DataProcessing(persistent_counters)
    serial_reader = BackgroundSerialReader(self.callback)
    serial_reader.start()

    def callback(self, raw_data):
        print(self.data_processing.process(raw_data))

Run directly for unit tests:

    python data_processing.py
"""

import os
import json
import time

from energy_modeling import model_water_energy
import config

# Hard coded labels corresponding to a raw Arduino values
RAW_DATA_LABELS = [
    'Vecs_pulses', # Used water meter pulses "volume eau chaude sanitaire"
    'Vep_pulses', # Solar system water meter pulses "volume eau panneaux"
    'Eax_pulses', # Auxiliary eletrical heater meter pulses "énergie auxiliaire"
    'Teh', # Stored water top temperature "température eau haut"
    'Teb', # Stored water top temperature "température eau bas"
    'Tec', # Hot water output temperature "température eau chaude"
    'Tef', # Cold water input temperature "température eau froide"
    'Tep', # Temperature insde panels "température eau panneaux"
    'Txe', # Exchanger input temperature "température exchanger entrée"
    'Txs', # Exchanger output temperature "température exchanger sortie"
]

class DataProcessing():
    """Label and process values for raw Arduino list"""

    def __init__(self, counters, time_provider=time.monotonic):
        """
        Args:
            time_provider: Monotonically increasing time function in seconds.
                           Intended to be overriten in unit tests.
        """
        self.counters = counters
        self.prev_counters = {}

        self.time_provider = time_provider

        self.prev_volume_solar = None
        self.prev_volume_used = None
        self.prev_time = None

    def process(self, data):
        """
        Args:
            data: Ordered list of unlabeled raw values parsed from the Arduino.
        """
        data = self.label_data(data)

        self.update_persistent_counters(data)
        self.compute_energies(data)
        self.format_values(data)

        return data

    def label_data(self, data):
        """
        Args:
            data: Ordered list of unlabeled raw values parsed from the Arduino.

        Returns:
            Labeled dict of raw values.
        """
        data = dict(zip(RAW_DATA_LABELS, data))
        data['timestamp'] = int(time.time())
        return data

    def update_persistent_counters(self, data):
        """Remembers persistent pulses counters, updates data in place.

        Args:
            data: Labeled dict of raw values.
        """

        counted = ['Vecs_pulses', 'Vep_pulses', 'Eax_pulses']
        have_counters_been_reset = False

        for label in counted:
            # Assume a decreasing counter means the Arduino has been reset
            if not label in self.prev_counters or data[label] < self.prev_counters[label]:
                have_counters_been_reset = True
                break

        for label in counted:
            curr = data[label]
            if not have_counters_been_reset:
                diff = data[label] - self.prev_counters.get(label, 0)
                self.counters.update(label, diff)
            else:
                # For now we ingore pulses counted by the Arduino when not reading it.
                # ie. if we connect to the Arduino, and its count is already x, we
                # do not increate persistent counters by x, we start counting from there.
                pass
            data[label] = self.counters.get(label)
            self.prev_counters[label] = curr

    def compute_energies(self, data):
        """Adds energy computations in the given data, using SI units.

        Args:
            data: Labeled dict of raw values.
        """

        current_time = self.time_provider() # s

        volume_solar = data['Vep_pulses'] / config.SOLAR_WATER_METER_TICKS_PER_L / 1000 # m³
        volume_used = data['Vecs_pulses'] / config.USED_WATER_METER_TICKS_PER_L / 1000 # m³

        # Computes solar energy when circulating volume changes
        # A deacresing volume can be seen on Arduino resets

        if self.prev_volume_solar is not None and volume_solar > self.prev_volume_solar:
            volume_diff = volume_solar - self.prev_volume_solar
            energy_diff = model_water_energy(volume_diff, data['Txe'] - data['Txs'])
            self.counters.update('Epst', energy_diff) # J

            # Count separately when the solar system takes heat from the stored temperature,
            # usually to cool the pannels

            if energy_diff < 0:
                self.counters.update('Esd', -energy_diff) # J
                if self.prev_time is not None:
                    duration = current_time - self.prev_time
                    self.counters.update('Hsd', duration) # s

        # Computes used water energy when used volume changes
        # A deacresing volume can be seen on Arduino resets

        if self.prev_volume_used is not None and volume_used > self.prev_volume_used:
            volume_diff = volume_used - self.prev_volume_used
            energy_diff = model_water_energy(volume_diff, data['Tec'] - data['Tef'])
            self.counters.update('E', energy_diff) # J

        self.prev_volume_solar = volume_solar
        self.prev_volume_used = volume_used
        self.prev_time = current_time

    def format_values(self, data):
        """Convert to human readable units for the upstream interface.

        Args:
            data: Labeled dict of values, modified in place.
        """
        data['Vecs'] = data['Vecs_pulses'] / config.SOLAR_WATER_METER_TICKS_PER_L # l
        data['Vep'] = data['Vep_pulses'] / config.USED_WATER_METER_TICKS_PER_L # l

        # Auxiliary electric heater energy
        data['Eax'] = data['Eax_pulses'] / config.AUX_ENERGY_METER_TICKS_PER_KWH # kWh

        # Solar pannels energy
        data['Epst'] = self.counters.get('Epst') / 3600 / 1000 # kWh

        # Used hot water energy
        data['E'] = self.counters.get('E') / 3600 / 1000 # kWh

        # Useful solar energy
        data['Esu'] = data['E'] - data['Eax'] # kWh / m²

        # Useful solar productivity
        data['Ps'] = data['Esu'] / config.SOLAR_PANNEL_AREA # kWh / m²

        # Energy dissipated in the solar panels
        data['Esd'] = self.counters.get('Esd') / 3600 / 1000 # kWh

        # Duration of energy dissipation with the solar panels
        data['Hsd'] = self.counters.get('Hsd') / 3600 # h

class PersistentCounters():
    """Keeps track of multiple persistent values by saving them to disk in a json file"""

    def __init__(self, filepath):
        self.filepath = filepath
        if filepath is not None and os.path.isfile(filepath):
            with open(filepath, 'r') as file:
                self.values = json.load(file)
        else:
            # This is just supposed to happen in unit tests
            self.values = {}

    def save(self):
        """Save values to in a json file"""

        if self.filepath is None:
            raise AttributeError('No file has been provided')
        with open(self.filepath, 'w') as file:
            file.write(json.dumps(self.values, indent=2))

    def update(self, name, diff):
        """Updates a persistent value by adding the given diff"""

        prev_value = self.values.get(name, 0)
        curr_value = prev_value + diff
        self.values[name] = curr_value

    def get(self, name):
        """Returns a persistent value"""

        return self.values.get(name, 0)

    def reset(self, name, value):
        """Resets a value to the given value"""

        self.values[name] = value

if __name__ == '__main__':

    import unittest
    from energy_modeling import cp

    class TestDataProcessing(unittest.TestCase):

        def setUp(self):
            """Setup objects to be used before each test"""
            self.counters = PersistentCounters(None)
            self.processing = DataProcessing(self.counters, self.get_mocked_time)
            self.mocked_data = [0, 0, 0,
                                52.37, 47.02, 43.94, 37.66, 18.15, 48.62, 47.08]
            self.mocked_time = 0

        def set_mocked_data(self, label, value):
            """Simulate data sent from the Arduino"""
            for i, mocked_data_label in enumerate(RAW_DATA_LABELS):
                if label == mocked_data_label:
                    self.mocked_data[i] = value
                    return
            raise ValueError

        def set_mocked_time(self, value_s):
            """Simulate time"""
            self.mocked_time = value_s

        def get_mocked_time(self):
            return self.mocked_time

        def test_label_raw_data_line(self):
            data = self.processing.process(self.mocked_data)
            expected = {
                'Vecs_pulses': 0,
                'Vep_pulses': 0,
                'Eax_pulses': 0,
                'Teh': 52.37,
                'Teb': 47.02,
                'Tec': 43.94,
                'Tef': 37.66,
                'Tep': 18.15,
                'Txe': 48.62,
                'Txs': 47.08,
            }
            for label, expected_value in expected.items():
                self.assertEqual(data[label], expected_value)

        def test_increases_counters_on_first_data(self):

            # Let say some persitent counter have been set
            self.counters = PersistentCounters(None)
            self.counters.reset('Vecs_pulses', 100)

            # The arduino is already running, counting ticks
            self.set_mocked_data('Vecs_pulses', 2)

            # We start the interface
            self.processing = DataProcessing(self.counters)
            self.processing.process(self.mocked_data)

            # For now, increasing persistent counters when not connected
            # is not supported

            self.assertEqual(self.counters.get('Vecs_pulses'), 100)

            # Only ticks happening after the connection are counted

            self.set_mocked_data('Vecs_pulses', 3)
            self.processing.process(self.mocked_data)
            self.assertEqual(self.counters.get('Vecs_pulses'), 101)

        def test_replaces_raw_data_values_with_counters(self):

            self.counters.reset('Vecs_pulses', 10)
            self.set_mocked_data('Vecs_pulses', 2)
            data = self.processing.process(self.mocked_data)

            self.assertEqual(data['Vecs_pulses'], self.counters.get('Vecs_pulses'))

        def test_assume_reset_when_any_counter_deacreases(self):

            # Reading ticks from 0 to 4
            for i in range(5):
                self.set_mocked_data('Vecs_pulses', i)
                data = self.processing.process(self.mocked_data)

            # 4 ticks should have been counted
            self.assertEqual(data['Vecs_pulses'], 4)

            # If the ticks decreases, assume a reset and keep counting
            self.set_mocked_data('Vecs_pulses', 0)
            self.processing.process(self.mocked_data)

            self.set_mocked_data('Vecs_pulses', 1)
            data = self.processing.process(self.mocked_data)

            self.assertEqual(data['Vecs_pulses'], 5)

        def test_used_water_energy(self):

            self.set_mocked_data('Vecs_pulses', 0)
            self.set_mocked_data('Tef', 15)
            self.set_mocked_data('Tec', 16)

            data = self.processing.process(self.mocked_data)
            self.assertEqual(0, data['E'])

            # Using 1 kg of water which temperature has been increased by a K
            self.set_mocked_data('Vecs_pulses', 1)

            data = self.processing.process(self.mocked_data)
            self.assertAlmostEqual(cp, data['E'] * 1000 * 3600)

        def test_solar_water_energy(self):

            self.set_mocked_data('Vep_pulses', 0)
            self.set_mocked_data('Txe', 16)
            self.set_mocked_data('Txs', 15)

            data = self.processing.process(self.mocked_data)
            self.assertEqual(0, data['Epst'])

            # Increasing 1 kg of water of a K
            self.set_mocked_data('Vep_pulses', 1)

            data = self.processing.process(self.mocked_data)
            self.assertAlmostEqual(cp, data['Epst'] * 1000 * 3600)

        def test_solar_dissipated_energy_not_counted_when_positive(self):

            self.set_mocked_data('Vep_pulses', 0)
            self.set_mocked_data('Txe', 16)
            self.set_mocked_data('Txs', 15)

            data = self.processing.process(self.mocked_data)
            self.assertEqual(0, data['Esd'])

            # Increasing 1 kg of water of a K
            self.set_mocked_data('Vep_pulses', 1)

            data = self.processing.process(self.mocked_data)

            self.assertEqual(0, data['Esd'])

        def test_solar_dissipated_energy_counted_when_negative(self):

            self.set_mocked_data('Vep_pulses', 0)
            self.set_mocked_data('Txe', 15)
            self.set_mocked_data('Txs', 16)

            data = self.processing.process(self.mocked_data)
            self.assertEqual(0, data['Esd'])

            # Decreasing 1 kg of water of a K in one min
            self.set_mocked_data('Vep_pulses', 1)
            self.set_mocked_time(60)

            data = self.processing.process(self.mocked_data)

            # Energy is counted and positive
            self.assertGreater(data['Esd'], 0)
            self.assertAlmostEqual(cp, data['Esd'] * 1000 * 3600)

            # Time between consecutive values is used to compute dissipation time
            self.assertEqual(data['Hsd'], 1 / 60)

    unittest.main()
