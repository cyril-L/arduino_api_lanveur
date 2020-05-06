#!/usr/bin/env Rscript

library(ggplot2)

source("utils.R")

options(error=traceback)

sample_period <- 60 # s
v_stored_water <- 0.3 # m³
p_aux_heating <- 3000 # W
t_ambiant <- 20 # °C

# Specific heat capacity
# amount of energy that must be added, in the form of heat, to one unit of mass of the substance in order to cause an increase of one unit in its temperature.
# The SI unit of specific heat is joule per kelvin and kilogram, J/(K kg).
# For example, at a temperature of 25 °C (the specific heat capacity can vary with the temperature),
# the heat required to raise the temperature of 1 kg of water by 1 K (equivalent to 1 °C) is 4179.6 joules,
# meaning that the specific heat of water is 4179.6 J·kg−1·K−1.[3]

cp <- 4179.6 # J·kg−1·K−1

degToJoules <- cp * v_stored_water * 1000
joulesToDeg <- 1 / degToJoules

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
#   |        Z|  Solar header
#   |         |  Botom water     (Teb)
#   \----+----/
#        |
#        +---- Cold water        (Tef)
#
# Only storage water is modeled for now
#
# TODO model 4 different water layers
# https://docs.izuba.fr/v4/fr/index.php/Ballon_(Biblioth%C3%A8que)?toc-id=48

model_stored_temp <- function(df) { return((df$Teh + df$Teb) / 2) }

df <- read_data('2020-04-27.csv')

# Perte d’énergie dans le ballon par refroidissement

df$t_stored <- model_stored_temp(df)

cooling <- (df$t_stored[length(df$t_stored)] - df$t_stored[1]) / (df$clock[length(df$clock)] - df$clock[1]) # K/s

# Comparing with NF EN 12977-3 (not read for now)
# UA Coefficient de pertes thermiques (ex. 1.667 W/K)
# Us perte thermique du ballon de stockage (< 20 W / m³·K)
# Cr constante de refroidissement par jour (ex. 0,103 Wh/l.K.j)

UA <- -(cooling * degToJoules) / mean(df$t_stored - t_ambiant) # W/K
Us <- UA / v_stored_water # Us
Cr <- 85400 * Us / (3600 * 1000)

model_cooling_power <- function(temp_inside, temp_outside) {
  power <- (temp_outside - temp_inside) * UA
  print(summary(power)) # W
  return(power)
}

# Computing lost temperature by using the cooling model
# The model is expected to be used on t_stored
# Teh and Teb shown to see how its error when applied to those temperatures

Teb0 <- df$Teb[1]
Teh0 <- df$Teh[1]
t_stored0 <- df$t_stored[1]
df$e_cooling_h <- integrate(model_cooling_power(df$Teh, t_ambiant))
df$e_cooling_b <- integrate(model_cooling_power(df$Teb, t_ambiant))
df$e_cooling_mean <- integrate(model_cooling_power(df$t_stored, t_ambiant))



ggplot(df) +
  geom_line(aes(clock, Teb, color="Teb")) +
  geom_line(aes(clock, Teh, color="Teh")) +
  geom_line(aes(clock, t_stored, color="t_stored")) +
  geom_line(aes(clock, e_cooling_b * joulesToDeg + Teb0, color="Teb model")) +
  geom_line(aes(clock, e_cooling_h * joulesToDeg + Teh0, color="Teh model")) +
  geom_line(aes(clock, e_cooling_mean * joulesToDeg + t_stored0, color="t_stored model")) +
  ggtitle(sprintf("Cooling model\nUA %.2f W / K\nUs %.2f W / m³·K\nCr %.2f Wh / l·K·j", UA, Us, Cr)) +
  scale_x_clock_hours(df$clock) +
  scale_y_temperature()
  #scale_x_continuous(name="Time (s)", breaks=seq(0, 100000, by = 3600), minor_breaks=seq(0, 10000, by = 15*60)) +
  #xlab("Time (s)") +

# Il faut 1,163 kWh (énergie) pour augmenter d’un °C un m3 d’eau (1,163 kWh/m3.°C). Avec Cm = 4,18 Kj/kg °C, on arrive à 1.1611 kWh/m3.°C
# Cm = 4,18 Kj/kg °C
# 1 kWh = 3 600 kJ
# 1 kJ = 1/3600 kWh
# Cm = 4.18 / 3600 = 0.001161 kWh/kg°C
# 1 l = 1 kg
# 1 000 l = 1 m3 = 1 000 kg
# Cm = 4.18 / 3600 = 0.001161 kWh/kg°C * 1 000 / 1 000 = 1.1611 kWh/m3.°C

# mecs <- 300 # kg (300 L)
# joulesToDeg <- 1 / (mecs * cp)

df$dTeh <- derivate(df$Teh, df$clock) # °C / s

df <- read.table('lanveur.csv', header = TRUE, sep = ",", fill = TRUE)

df$clock <- df$clock - df$clock[1]

df <- df[df$clock < 5e5, ]

# df <- df[df$clock > 950000 & df$clock < 1000000, ]

# df <- df[df$clock > 940000 & df$clock < 950000, ]

# Swap Txs and Tep
# df$tmp <- df$Tep
# df$Tep <- df$Txs
# df$Txs <- df$tmp

# Swap Txs and Txe
df$tmp <- df$Txe
df$Txe <- df$Txs
df$Txs <- df$tmp

# Fixes V 0.25 to 1
# df$Vecs <- df$Vecs * 25
# df$Vep <- df$Vep * 25

df$flowEcs <- derivate(df$Vecs / 1000) # m³/s
df$flowP <- derivate(df$Vep / 1000) # m³/s

# P(W) = qv * rho * cp * (Ts - Ti)

# qv : débit volumique, m3/s
# rho : masse volumique eau, 1000 kg/m3
# cp : capacité calorifique de l'eau, 4185 J / kg.°C
# Ts : Température de sortie du ballon, °C
# Ti : Température d'entrée du ballon, °C

rho <- 1000 # kg / m3
cp <- 4185 # J / kg.°C

df$powerP <- df$flowP * rho * cp * (df$Txe - df$Txs) # W
df$powerEcs <- df$flowEcs * rho * cp * (df$Tef - df$Tec) # W

df$energyP <- integrate(df$powerP) # J (W.s)
df$energyEcs <- integrate(df$powerEcs) # J (W.s)

# expected temperature rising rate
# when 300 L of water heated with a 3 kW resistance

# cp = J / (kg.°C)
# m.cp = J / °C = W.s / °C
# °C / s = W / (m . cp)

aux_heating_rate <- p_aux_heating / (rho * v_stored_water * cp)

# suspect heating when
# 10 min moving average above expected rising rate / 4
# determined empiracally by comparing expected temperature increase with the recorded one

moving_avg <- function(x, n){filter(x, rep(1 / n, n), sides = 2)}

# Teh variation
df$dTeh <- derivate(df$Teh) # °C / s

df$x <- moving_avg(df$dTeh, 100)

dfnight <- df[df$clock > 3e5 & df$clock < 3.5e5, ]
print((min(dfnight$Teh) - max(dfnight$Teh)) / (max(dfnight$clock) - min(dfnight$clock)))

df$lost <- -8.012821e-05
df$lost <- integrate(df$lost)

df$suspected_aux_heating = moving_avg(df$dTeh, 10) > aux_heating_rate / 4

# Heater regulation has not been observed above

df$suspected_aux_heating[df$Teh > 51] <- FALSE

# Ignore data when water is flowing

df$flowing <- moving_avg(df$flowP + df$flowEcs, 10) != 0

df$suspected_aux_heating[df$flowing] <- FALSE

df$powerAux <- 0
df$powerAux[df$suspected_aux_heating] <- p_aux_heating
df$energyAux <- integrate(df$powerAux)

# Il faut 1,163 kWh (énergie) pour augmenter d’un °C un m3 d’eau (1,163 kWh/m3.°C). Avec Cm = 4,18 Kj/kg °C, on arrive à 1.1611 kWh/m3.°C
# Cm = 4,18 Kj/kg °C
# 1 kWh = 3 600 kJ
# 1 kJ = 1/3600 kWh
# Cm = 4.18 / 3600 = 0.001161 kWh/kg°C
# 1 l = 1 kg
# 1 000 l = 1 m3 = 1 000 kg
# Cm = 4.18 / 3600 = 0.001161 kWh/kg°C * 1 000 / 1 000 = 1.1611 kWh/m3.°C

mecs <- 300 # kg (300 L)
joulesToDeg <- 1 / (mecs * cp)

# W.s ~ J
# kW.s ~ J / 1000
# kW.h ~ J / 1000 / 3600

joulesTokWh <- 1 / (1000 * 3600)

Te0 = (df$Teh[1] + df$Teb[1]) / 2

ggplot(df) +
  geom_ribbon(aes(clock, ymin=Teb, ymax=Teh, color="T°C ballon"), fill="red", alpha = 0.15) +
  geom_line(aes(clock, Teh), color='red') +
  geom_line(aes(clock, Teb), color='red') +
  geom_ribbon(aes(clock, ymin=Txs, ymax=Txe, fill=Txs > Txe)) +
  geom_line(aes(clock, Txe), color='black') +
  geom_line(aes(clock, Txs), color='black') +
  # geom_line(aes(clock, energyP * joulesToDeg + Te0, color="energyP")) +
  # geom_line(aes(clock, energyEcs * joulesToDeg + Te0, color="energyEcs")) +
  # geom_line(aes(clock, energyAux * joulesToDeg + Te0, color="energyAux")) +
  geom_line(aes(clock, (energyAux + energyP + energyEcs) * joulesToDeg + lost + Te0, color="Tsim")) +
  scale_fill_manual(values = c("green", "red"), name = "fill")

ggplot(df) +
  geom_line(aes(clock, energyP * joulesTokWh, color="energyP")) +
  geom_line(aes(clock, energyEcs * joulesTokWh, color="energyEcs")) +
  geom_line(aes(clock, energyAux * joulesTokWh, color="energyAux"))