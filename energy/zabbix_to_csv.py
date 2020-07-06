#!/usr/bin/env python3

from pyzabbix import ZabbixAPI
import datetime as dt
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--date', type=str,
                    help="Get a single day (YYYY-MM-DD)")
parser.add_argument('--from', type=str,
                    help="Get multiple days from date (YYYY-MM-DD), first by default")
parser.add_argument('--till', type=str,
                    help="Get multiple days till date (YYYY-MM-DD), now by default")
args = vars(parser.parse_args())

def parse_date(s):
    return dt.datetime.strptime(s, '%Y-%m-%d')

if args['date']:
    time_from = parse_date(args['date'])
    time_till = time_from + dt.timedelta(days=1)
else:
    if args['from']:
        time_from = parse_date(args['from'])
    else:
        time_from = dt.datetime(2020, 4, 20, 0, 0)
    if args['till']:
        time_till = parse_date(args['till']) + dt.timedelta(days=1)
    else:
        time_till = dt.datetime.now()

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
}

csv_header = ['clock'] + list(zabbix_items.values())
print(','.join(csv_header))

def datetime_to_zabbix(date):
    return int(time.mktime(date.timetuple()))

while time_from < time_till:

    time_till_limited = min(time_till, time_from + dt.timedelta(days=1))

    history = zapi.history.get(itemids=list(zabbix_items.keys()),
                               time_from=datetime_to_zabbix(time_from),
                               time_till=datetime_to_zabbix(time_till_limited),
                               output='extend',
                               limit='50000',
                               history=0,
                               )

    time_from = time_till_limited

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