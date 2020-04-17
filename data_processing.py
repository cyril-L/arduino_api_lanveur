#!/usr/bin/env python3

import threading
import datetime as dt
import os
import time
import json

CACHE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cache.json")
CACHE_WRITE_PERIOD_MIN = 10

class DataProcessing():

    def __init__(self):
        self.lastest_data = None
        self.lock = threading.Lock()

    def on_new_data(self, data):
        data = self.process(data)
        with self.lock:
            self.lastest_data = data

    def pop_latest_data(self):
        with self.lock:
            data = self.lastest_data
            self.lastest_data = None
            return data

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

        # TODO rapport de stage 1 tick = 0.25 litre, pas cohérent avec les valeurs dans le code
        # 1 tick = 0.25 liter
        data['Vecs'] = data['Vecs_ticks'] / 4
        data['Vep']  = data['Vep_ticks']  / 4

        data['Stamp_utc'] = dt.datetime.utcnow()
        return data