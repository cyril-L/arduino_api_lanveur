#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.optimize

pd.plotting.register_matplotlib_converters()

df = pd.read_csv("2020-may-june.csv")

df['date'] = pd.to_datetime(df['clock'], unit='s')

SAMPLE_INTERVAL = 60
V_STORED_WATER = 0.3  # m³
T_AMBIANT = 19  # °C

# Specific heat capacity
# amount of energy that must be added, in the form of heat, to one unit of mass of the substance in order to cause an increase of one unit in its temperature.
# The SI unit of specific heat is joule per kelvin and kilogram, J/(K kg).
# For example, at a temperature of 25 °C (the specific heat capacity can vary with the temperature),
# the heat required to raise the temperature of 1 kg of water by 1 K (equivalent to 1 °C) is 4179.6 joules,
# meaning that the specific heat of water is 4179.6 J·kg−1·K−1.[3]

cp = 4179.6 # J / kg·K

# How much joules are needed to increase the temperature of 1 m³ of water by 1 °C

rho = 1000 # kg / m³

def degToJoules(deg):
    return deg * cp * V_STORED_WATER * rho # K.J/K

def joulesToDeg(joules):
    return joules / (cp * V_STORED_WATER * rho) # J.K/J

# modeling like
#
#        +---- Hot water         (Tec)
#        |
#   /----+----\
#   |         |  Top water       (Teh)
#   |        Z|  Electric Heater
#   |         |
#   |         |  Storage water   (t_stored)
#   |         |
#   |        Z|  Solar header    (in Txe, out Txs)
#   |         |  Botom water     (Teb)
#   \----+----/
#   /    |    \
#        +---- Cold water        (Tef)
#
# Only storage water is modeled for now
#
# TODO model 4 different water layers
# https://docs.izuba.fr/v4/fr/index.php/Ballon_(Biblioth%C3%A8que)?toc-id=48

def model_stored_temp(df):
    return (df['Teb'] + df['Teh']) / 2

df['T_stored'] = model_stored_temp(df)

df['energy'] = degToJoules(df['T_stored'] - df.iloc[0]['T_stored'])
df['power'] = df['energy'].diff() / SAMPLE_INTERVAL
# Moving average on 10 min to smooth computed power
df['power'] = df['power'].rolling(window=60).mean()

# Comparing with NF EN 12977-3 (not read for now)
# UA Coefficient de pertes thermiques (ex. 1.667 W/K)
# Us perte thermique du ballon de stockage (< 20 W / m³·K)
# Cr constante de refroidissement par jour (ex. 0,103 Wh/l.K.j)

UA = 3.5
Us = UA / V_STORED_WATER # Us
Cr = 85400 * Us / (3600 * 1000)

def model_cooling_power(temp_inside, temp_outside, UA):
    return (temp_outside - temp_inside) * UA  # W

df['cooling_power'] = model_cooling_power(df['T_stored'], T_AMBIANT, UA)

def model_flow(df, var):
    return df[var].diff() / 1000 / SAMPLE_INTERVAL

df['F_solar'] = 4 * model_flow(df, 'Vep') # m³/s
df['F_hot_water'] = model_flow(df, 'Vecs') # m³/s

# P(W) = qv * rho * cp * (Ts - Ti)

# qv : débit volumique, m3/s
# rho : masse volumique eau, 1000 kg/m3
# cp : capacité calorifique de l'eau, 4185 J / kg.°C
# Ts : Température de sortie du ballon, °C
# Ti : Température d'entrée du ballon, °C

def model_flowing_power(flow, exchanger_in, exchanger_out):
  return flow * rho * cp * (exchanger_in - exchanger_out)

df['solar_power'] = model_flowing_power(df['F_solar'], df['Txe'], df['Txs'])
df['solar_power'] = df['solar_power'].rolling(window=60).mean()

df['consumed_power'] = model_flowing_power(df['F_hot_water'], df['Tef'], df['Tec'])
df['consumed_power'] = df['consumed_power'].rolling(window=60).mean()

df['power_error'] = df['power'] - df['cooling_power'] - df['solar_power'] - df['consumed_power']

df_powers = pd.melt(df, id_vars=['date'], value_vars=[ c for c in df.columns if 'power' in c], var_name='label', value_name='power')

#sns.relplot(x='clock', y="power_SMA", kind="line", data=df)
sns.relplot(x='date', y="power", kind="line", hue="label", data=df_powers)

#df_temps = pd.melt(df, id_vars=['clock'], value_vars=[ c for c in df.columns if c[0] == 'T'], var_name='label', value_name='temperature')

#sns.relplot(x='clock', y="temperature", kind="line", hue="label", data=df_temps)
# sns.relplot(x="total_bill", y="tip", data=tips);

# Set the width and height of the figure
# plt.figure(figsize=(16,6))

# Line chart showing how FIFA rankings evolved over time 
# sns.relplot(data=df, x="clock", y="Teb")
#sns.lineplot(data=df, x="clock", y="Teh")

plt.show()
