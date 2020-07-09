#!/usr/bin/env python3

import os
import json

class DataProcessing():

    def __init__(self, counters):
        self.counters = counters
        self.prev_ticks = {}

    # Données utiles, préconisations:
    #
    # Vecs: volume d’eau froide à l’entrée du ballon solaire
    # Tef: température de l’eau froide
    # Tec: température de l’eau chaude directement à la sortie du ballon
    # TODO Consommation électrique

    # FIXME Pourquoi température eau froide entre 30 et 45 °C

    def process(self, data):

        labels = [
            'Vecs_pulses',
            'Vep_pulses',
            'Eax_pulses',
            'Teh', # Haut du ballon
            'Teb', # Bas du ballon
            'Tec', # Eau chaude
            'Tef', # Eau froide
            'Tep', # TODO Eau sortant du circuit des panneaux (code arduino) vs Température des panneaux (rapport)
            'Txe', # TODO Entrée échangeur?
            'Txs', # TODO Sortie échangeur?
        ]
        data = dict(zip(labels, data))

        # Handle counter resets

        counted = ['Vecs_pulses', 'Vep_pulses', 'Eax_pulses']
        have_counters_been_reset = False

        for label in counted:
            if not label in self.prev_ticks or data[label] < self.prev_ticks[label]:
                have_counters_been_reset = True
                break

        for label in counted:
            curr = data[label]
            if not have_counters_been_reset:
                diff = data[label] - self.prev_ticks.get(label, 0)
                self.counters.update(label, diff)
            data[label] = self.counters.get(label)
            self.prev_ticks[label] = curr

        # FIXME rapport de stage 1 tick = 0.250 litres
        #       code Arduino V1  1 tick = 0.375 litres
        #       code Arduino V2  1 tick = 0.500 litres

        data['Vecs'] = data['Vecs_pulses']
        data['Vep'] = data['Vep_pulses']
        data['Eax'] = data['Eax_pulses'] / 800
        data['Epst'] = 0
        data['Eut'] = 0
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

    class TestDataProcessing(unittest.TestCase):

        def setUp(self):
            self.counters = PersistentCounters()
            self.processing = DataProcessing(self.counters)
            self.mocked_data = [0, 0, 0,
                                52.37, 47.02, 43.94, 37.66, 18.15, 48.62, 47.08]

        def set_mocked_data(self, label, value):
            if label == 'Vecs_pulses':
                self.mocked_data[0] = value
            else:
                raise NotImplementedError

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

    unittest.main()
