#!/usr/bin/env python3
#
# Copyright 2020 Cyril Lugan, https://cyril.lugan.fr
# Licensed under the EUPL v1.2, https://eupl.eu/1.2/en/
# ==============================================================================
"""Check energy computation with real data from zabbix_to_csv.py.

- Compute the amount of energy that have added to cause the change of stored water temperature
- Remove added energies (solar, auxiliary) and consumed energy (used hot water)
- Remove estimated cooling losses
- The remaining shows what is missing in the equation

Usage:
    ./plot_error.py 2020-08-01.csv
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import energy_modeling
import config

SAMPLE_INTERVAL = 60
T_AMBIANT = 19  # °C

pd.plotting.register_matplotlib_converters()

parser = argparse.ArgumentParser()
parser.add_argument('csv_file', type=str,
                    help="CSV file from zabbix_to_csv.py")
args = parser.parse_args()

df = pd.read_csv(args.csv_file)

df['date'] = pd.to_datetime(df['clock'], unit='s')

# Plot temperatures

df['T_stored'] = energy_modeling.model_stored_temp(df['Teb'], df['Teh'])

df_temps = pd.melt(df,
                   id_vars=['clock'],
                   value_vars=[ c for c in df.columns if c[0] == 'T'],
                   var_name='label',
                   value_name='temperature')

ax = sns.relplot(x='clock', y="temperature", kind="line", hue="label", data=df_temps)
ax.set(xlabel='Time', ylabel='Temperature (°C)')

# Plot energies and compute error

df['E_added'] = energy_modeling.model_water_energy(config.STORED_WATER_VOLUME,
                                                        df['T_stored'] - df.iloc[0]['T_stored'])
df['E_added'] = df['E_added'] / 3600 / 1000 # kWh

df['E_solar_added'] = (df['Epst'] - df.iloc[0]['Epst']) # kWh
df['E_aux_added'] = (df['Eax'] - df.iloc[0]['Eax']) # kWh
df['E_consumed'] = -(df['E'] - df.iloc[0]['E']) # kWh

# Cooling power is estimated, assuming the given ambiant temperature
df['P_cooling'] = energy_modeling.model_cooling_power(df['T_stored'], T_AMBIANT, energy_modeling.UA)
df['E_cooling'] = df['P_cooling'].cumsum() * SAMPLE_INTERVAL # Integrate power
df['E_cooling'] = df['E_cooling'] / 3600 / 1000 # kWh

# derivation example
#df['power'] = df['energy'].diff() / SAMPLE_INTERVAL

df['E_error'] = (df['E_added']
                 - df['E_solar_added']
                 - df['E_aux_added']
                 - df['E_consumed']
                 - df['E_cooling'])

df_energy = pd.melt(df,
                    id_vars=['date'],
                    value_vars=[ c for c in df.columns if 'E_' in c],
                    var_name='label',
                    value_name='energy')

ax = sns.relplot(x='date', y="energy", kind="line", hue="label", data=df_energy)
ax.set(xlabel='Time', ylabel='Added energy (kWh)')

plt.show()
