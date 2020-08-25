#!/usr/bin/env python3
#
# Copyright 2020 Cyril Lugan, https://cyril.lugan.fr
# Licensed under the EUPL v1.2, https://eupl.eu/1.2/en/
# ==============================================================================
"""Download data from zabbix as csv.

Usage:
    ./zabbix_to_csv.py 2020-08-01 > out.csv
    ./zabbix_to_csv.py 2020-08-01 2020-08-31 > out.csv
"""
from pyzabbix import ZabbixAPI
import datetime as dt
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('date', type=str,
                    help="Day to retreive or range start (YYYY-MM-DD)")
parser.add_argument('date_range_end', type=str,
                    help="Range end (YYYY-MM-DD)",
                    nargs="?")
args = parser.parse_args()

def parse_date(s):
    return dt.datetime.strptime(s, '%Y-%m-%d')

time_from = parse_date(args.date)

if args.date_range_end is None:
    time_to = time_from + dt.timedelta(days=1)
else:
    time_to = parse_date(args.date_range_end) + dt.timedelta(days=1)

zapi = ZabbixAPI("https://zabbix.empower-lorient.fr/zabbix/")
zapi.login("guest", "")

zabbix_items = {
    '29301': 'Tep',
    '29297': 'Teb',
    '29300': 'Teh',
    '29302': 'Txe',
    '29303': 'Txs',
    '29298': 'Tec',
    '29299': 'Tef',
    '29304': 'Vecs',
    '29306': 'Vep',
    '29319': 'E', # Énergie soutirée (eau chaude sanitaire)
    '29313': 'Eax', # Énergie auxiliaire approtée
    '29317': 'Epst', # Énergie solaire apportée
}

csv_header = ['clock'] + list(zabbix_items.values())
print(','.join(csv_header))

def datetime_to_zabbix(date):
    return int(time.mktime(date.timetuple()))

while time_from < time_to:

    time_to_limited = min(time_to, time_from + dt.timedelta(days=1))

    history = zapi.history.get(itemids=list(zabbix_items.keys()),
                               time_from=datetime_to_zabbix(time_from),
                               time_till=datetime_to_zabbix(time_to_limited),
                               output='extend',
                               limit='50000',
                               history=0,
                               )

    time_from = time_to_limited

    dataframe = {}

    for item in history:
        clock = int(item['clock'])
        value = float(item['value'])
        name = zabbix_items[item['itemid']]
        if not clock in dataframe:
            dataframe[clock] = {name : float('nan') for name in zabbix_items.values()}
        dataframe[clock][name] = value

    dataframe = list(dataframe.items())
    dataframe.sort()

    for clock, values in dataframe:
        values['clock'] = clock
        values = [str(values[name]) for name in csv_header]
        print(','.join(values))