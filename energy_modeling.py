#!/usr/bin/env python3
#
# Copyright 2020 Cyril Lugan, https://cyril.lugan.fr
# Licensed under the EUPL v1.2, https://eupl.eu/1.2/en/
# ==============================================================================
"""Energy related compuration, using SI units.

Modeling like

       +---- Hot water         (Tec)
       |
  +----+----+
  |         |  Top water       (Teh)
  |        Z|  Electric Heater
  |         |
  |         |  Storage water   (t_stored)
  |         |
  |        Z|  Solar header    (in Txe, out Txs)
  |         |  Botom water     (Teb)
  +----+----+
  /    |    \
       +---- Cold water        (Tef)

Only storage water is modeled for now, a more advanced model would consider stratification.
https://docs.izuba.fr/v4/fr/index.php/Ballon_(Biblioth%C3%A8que)?toc-id=48
"""

import config

def model_stored_temp(temp_bottom, temp_top):
    """Estimates storage temperature."""
    return (temp_bottom + temp_top) / 2

# Can be compared with NF EN 12977-3 (not read for now)
# UA Coefficient de pertes thermiques (ex. 1.667 W/K)
# Us perte thermique du ballon de stockage (< 20 W / m³·K)
# Cr constante de refroidissement par jour (ex. 0,103 Wh/l.K.j)

UA = 3.5 # Estimated from measurements
Us = UA / config.STORED_WATER_VOLUME # Us
Cr = 85400 * Us / (3600 * 1000)

def model_cooling_power(temp_inside, temp_outside, UA):
    """Estimates heat lost in the environment."""
    return (temp_outside - temp_inside) * UA  # W

# Specific heat capacity
# Amount of energy that must be added, in the form of heat,
# to increase the temperature of 1 m³ of water by 1 °C

cp = 4179.6 # J / kg·K
rho = 1000 # kg / m³

def model_water_energy(volume, temperature_increase):
    """Amount of energy that must be added to cause an increase of the given temperature."""
    return volume * rho * cp * temperature_increase # J

def model_water_temperature(volume, energy_added):
    """Increase of temperature caused when adding the given amount of energy."""
    return energy_added / (cp * volume * rho) # K
