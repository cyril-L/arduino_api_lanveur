#!/usr/bin/env python3

import config

# Specific heat capacity
# amount of energy that must be added, in the form of heat, to one unit of mass of the substance in order to cause an increase of one unit in its temperature.
# The SI unit of specific heat is joule per kelvin and kilogram, J/(K kg).
# For example, at a temperature of 25 °C (the specific heat capacity can vary with the temperature),
# the heat required to raise the temperature of 1 kg of water by 1 K (equivalent to 1 °C) is 4179.6 joules,
# meaning that the specific heat of water is 4179.6 J·kg−1·K−1.[3]

cp = 4179.6 # J / kg·K

# How much joules are needed to increase the temperature of 1 m³ of water by 1 °C

rho = 1000 # kg / m³

def deg_to_joules(deg):
    return deg * cp * config.STORED_WATER_VOLUME * rho # K.J/K

def joules_to_deg(joules):
    return joules / (cp * config.STORED_WATER_VOLUME * rho) # J.K/J

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
# A more advanced model would consider stratification
# https://docs.izuba.fr/v4/fr/index.php/Ballon_(Biblioth%C3%A8que)?toc-id=48

def model_stored_temp(temp_bottom, temp_top):
    return (temp_bottom + temp_top) / 2

# Comparing with NF EN 12977-3 (not read for now)
# UA Coefficient de pertes thermiques (ex. 1.667 W/K)
# Us perte thermique du ballon de stockage (< 20 W / m³·K)
# Cr constante de refroidissement par jour (ex. 0,103 Wh/l.K.j)

UA = 3.5
Us = UA / config.STORED_WATER_VOLUME # Us
Cr = 85400 * Us / (3600 * 1000)

def model_cooling_power(temp_inside, temp_outside, UA):
    return (temp_outside - temp_inside) * UA  # W

# def model_flow(diff_liters, diff_time):
#     return diff_liters / 1000 / diff_time

# P(W) = qv * rho * cp * (Ts - Ti)

# qv : débit volumique, m3/s
# rho : masse volumique eau, 1000 kg/m3
# cp : capacité calorifique de l'eau, 4185 J / kg.°C
# Ts : Température de sortie du ballon, °C
# Ti : Température d'entrée du ballon, °C

def model_water_energy(volume, temp_water_in, temp_water_out):
  return volume * rho * cp * (temp_water_in - temp_water_out)
