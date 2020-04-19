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

    def process(self, data):

        values = data[2:] # discard the first values (ticks converted to liters)
        labels = [
            'Vecs_ticks',  # TODO lequel est Vecs?
            'Vep_ticks',
            'Teh', # Haut du ballon
            'Teb', # Bas du ballon
            'Tec', # Eau chaude
            'Tef', # Eau froide
            'T5',  # TODO Eau sortant du circuit des panneaux (code arduino) vs Température des panneaux (rapport)
            'T6',  # TODO Entrée échangeur?
            'T7',  # TODO Sortie échangeur?
        ]
        data = dict(zip(labels, values))

        # Handle counter resets

        counted = ['Vecs_ticks', 'Vep_ticks']
        have_counters_been_reset = False

        for label in counted:
            if not label in self.prev_ticks or data[label] < self.prev_ticks[label]:
                have_counters_been_reset = True
                break

        for label in counted:
            curr = data[label]
            if have_counters_been_reset:
                diff = curr
            else:
                diff = curr - self.prev_ticks[label]
            data[label] = self.counters.update_and_get(label, diff)
            self.prev_ticks[label] = curr

        # # TODO rapport de stage 1 tick = 0.25 litre, pas cohérent avec les valeurs dans le code
        # 1 tick = 0.25 liter
        data['Vecs'] = data['Vecs_ticks'] / 4
        data['Vep'] = data['Vep_ticks']  / 4

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

    def update_and_get(self, name, diff):
        prev_value = self.values.get(name, 0)
        curr_value = prev_value + diff
        self.values[name] = curr_value
        return curr_value

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
            self.mocked_data = [225, 84, 10570, 5285,
                                52.37, 47.02, 43.94, 37.66, 18.15, 48.62, 47.08]

        def set_mocked_data(self, label, value):
            if label == 'Vecs_ticks':
                self.mocked_data[2] = value
            else:
                raise NotImplementedError

        def test_label_raw_data_line(self):
            data = self.processing.process(self.mocked_data)
            expected = {
                'Vecs_ticks': 10570,
                'Vep_ticks':   5285,
                'Teh': 52.37,
                'Teb': 47.02,
                'Tec': 43.94,
                'Tef': 37.66,
                'T5' : 18.15,
                'T6' : 48.62,
                'T7' : 47.08,
            }
            for label, expected_value in expected.items():
                self.assertEqual(data[label], expected_value)

        def test_increases_counters_on_first_data(self):

            self.counters.reset('Vecs_ticks', 10)
            self.set_mocked_data('Vecs_ticks', 2)
            self.processing.process(self.mocked_data)

            self.assertEqual(self.counters.get('Vecs_ticks'), 10 + 2)

        def test_replaces_raw_data_values_with_counters(self):

            self.counters.reset('Vecs_ticks', 10)
            self.set_mocked_data('Vecs_ticks', 2)
            data = self.processing.process(self.mocked_data)

            self.assertEqual(data['Vecs_ticks'], 10 + 2)

        def test_assume_reset_when_any_counter_deacreases(self):

            # Reading ticks from 0 to 4
            for i in range(5):
                self.set_mocked_data('Vecs_ticks', i)
                data = self.processing.process(self.mocked_data)

            # 4 ticks should have been counted
            self.assertEqual(data['Vecs_ticks'], 4)

            # If the ticks decreases, assume a reset and keep counting
            self.set_mocked_data('Vecs_ticks', 1)
            data = self.processing.process(self.mocked_data)

            self.assertEqual(data['Vecs_ticks'], 5)

    unittest.main()
