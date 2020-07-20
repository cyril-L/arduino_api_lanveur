#!/usr/bin/env python3

import os
import json
from energy_modeling import model_water_energy

RAW_DATA_LABELS = [
    'Vecs_pulses',
    'Vep_pulses',
    'Eax_pulses',
    'Teh', # Haut du ballon
    'Teb', # Bas du ballon
    'Tec', # Eau chaude
    'Tef', # Eau froide
    'Tep', # Température des panneaux
    'Txe', # Entrée échangeur
    'Txs', # Sortie échangeur
]

class DataProcessing():

    def __init__(self, counters):
        self.counters = counters
        self.prev_counters = {}

        self.prev_volume_solar = None
        self.prev_volume_used = None

    # Données utiles, préconisations:
    #
    # Vecs: volume d’eau froide à l’entrée du ballon solaire
    # Tef: température de l’eau froide
    # Tec: température de l’eau chaude directement à la sortie du ballon

    def process(self, data):

        data = dict(zip(RAW_DATA_LABELS, data))

        volume_solar = data['Vep_pulses'] / 1000 # m³
        volume_used = data['Vecs_pulses'] / 1000 # m³

        if self.prev_volume_solar is not None and volume_solar > self.prev_volume_solar:
            volume_diff = volume_solar - self.prev_volume_solar
            energy_diff = model_water_energy(volume_diff, data['Txe'], data['Txs'])
            self.counters.update('Epst', energy_diff) # J

        if self.prev_volume_used is not None and volume_used > self.prev_volume_used:
            volume_diff = volume_used - self.prev_volume_used
            energy_diff = model_water_energy(volume_diff, data['Tef'], data['Tec'])
            self.counters.update('Eut', energy_diff) # J

        self.prev_volume_solar = volume_solar
        self.prev_volume_used = volume_used

        # Handle counter resets

        counted = ['Vecs_pulses', 'Vep_pulses', 'Eax_pulses']
        have_counters_been_reset = False

        for label in counted:
            if not label in self.prev_counters or data[label] < self.prev_counters[label]:
                have_counters_been_reset = True
                break

        for label in counted:
            curr = data[label]
            if not have_counters_been_reset:
                diff = data[label] - self.prev_counters.get(label, 0)
                self.counters.update(label, diff)
            data[label] = self.counters.get(label)
            self.prev_counters[label] = curr

        data['Vecs'] = data['Vecs_pulses'] # l
        data['Vep'] = data['Vep_pulses'] # l
        data['Eax'] = data['Eax_pulses'] / 800 # kWh
        data['Epst'] = self.counters.get('Epst') / 3600 / 1000 # kWh
        data['Eut'] = self.counters.get('Eut') / 3600 / 1000 # kWh
        data['Epd'] = 0

        return data

class PersistentCounters():

    def __init__(self, filepath=None):
        self.filepath = filepath
        if filepath is not None and os.path.isfile(filepath):
            with open(filepath, 'r') as file:
                self.values = json.load(file)
        else:
            self.values = {}

    def save(self):
        with open(self.filepath, 'w') as file:
            file.write(json.dumps(self.values, indent=2))

    def update(self, name, diff):
        prev_value = self.values.get(name, 0)
        curr_value = prev_value + diff
        self.values[name] = curr_value

    def get(self, name):
        return self.values.get(name, 0)

    def reset(self, name, value):
        self.values[name] = value

if __name__ == '__main__':

    import unittest
    from energy_modeling import cp

    class TestDataProcessing(unittest.TestCase):

        def setUp(self):
            self.counters = PersistentCounters()
            self.processing = DataProcessing(self.counters)
            self.mocked_data = [0, 0, 0,
                                52.37, 47.02, 43.94, 37.66, 18.15, 48.62, 47.08]

        def set_mocked_data(self, label, value):
            for i, mocked_data_label in enumerate(RAW_DATA_LABELS):
                if label == mocked_data_label:
                    self.mocked_data[i] = value
                    return
            raise ValueError

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
            self.counters = PersistentCounters()
            self.counters.reset('Vecs_pulses', 100)

            # The arduino is already running, counting ticks
            self.set_mocked_data('Vecs_pulses', 2)

            # We start the interface
            self.processing = DataProcessing(self.counters)
            self.processing.process(self.mocked_data)

            # For now we do not increase persistent counters when not connected
            # TODO this behavior might change
            # A temporary counter have to be saved too to allow counting when not connected

            self.assertEqual(self.counters.get('Vecs_pulses'), 100)

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
            self.assertEqual(0, data['Eut'])

            # Increasing 1 kg of water of a K
            self.set_mocked_data('Vecs_pulses', 1)

            data = self.processing.process(self.mocked_data)
            self.assertAlmostEqual(-cp, data['Eut'] * 1000 * 3600)

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

    unittest.main()
