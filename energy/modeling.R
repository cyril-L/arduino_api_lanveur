#!/usr/bin/env Rscript

library(ggplot2)

source("utils.R")

options(error=traceback)

v_stored_water <- 0.3 # m³
t_ambiant <- 15 # °C

# Specific heat capacity
# amount of energy that must be added, in the form of heat, to one unit of mass of the substance in order to cause an increase of one unit in its temperature.
# The SI unit of specific heat is joule per kelvin and kilogram, J/(K kg).
# For example, at a temperature of 25 °C (the specific heat capacity can vary with the temperature),
# the heat required to raise the temperature of 1 kg of water by 1 K (equivalent to 1 °C) is 4179.6 joules,
# meaning that the specific heat of water is 4179.6 J·kg−1·K−1.[3]

cp <- 4179.6 # J / kg·K

# How much joules are needed to increase the temperature of 1 m³ of water by 1 °C

rho <- 1000 # kg / m³

degToJoules <- cp * v_stored_water * rho # J / K
joulesToDeg <- 1 / degToJoules # K / J

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

model_stored_temp <- function(df) { return((df$Teh + df$Teb) / 2) }

#
# Modeling stored water energy losses from the heat flowing to the
# From a dataset when nothing happens
#

model_cooling_power <- function(temp_inside, temp_outside, UA) {
  power <- (temp_outside - temp_inside) * UA # W
  return(power)
}

# df <- read_data('2020-04-27.csv')
#df <- read_data('2020-05-02.csv')
df <- read_data('2020-05-07.csv', from_hour=16, to_hour=34)

cooling_dataframes <- list(
  read_data('2020-04-27.csv'),
  read_data('2020-05-02.csv'),
  read_data('2020-05-07.csv', from_hour=16, to_hour=34),
  read_data('2020-04-30.csv', from_hour=17)
);

f <- function(par) {

  error <- 0;
  UA <- par[1];

  for (i in seq_along(cooling_dataframes)) {

    df <- cooling_dataframes[[i]]
    t_ambiant <- par[1+i]

    df$t_stored <- model_stored_temp(df)

    df$e_cooling_expected <- (df$t_stored - df$t_stored[1]) * degToJoules
    df$p_cooling <- model_cooling_power(df$t_stored, t_ambiant, UA) # W
    df$e_cooling <- integrate(df$p_cooling)
    error <- error + mean_squared_error(df$e_cooling_expected, df$e_cooling)
  }
  return(error)
}

r <- optim(c(4, 20, 20, 20, 20), f)
print(r$par)

f(r$par);

plot <- ggplot()

UA <- r$par[1]
# Do not estimate ambiant temperature for now, assume it remains constant
# TODO the current model thinks ambiant temperature is arround 13°, which seems a bit cold…
t_ambiant <- mean(r$par[-1])

for (i in seq_along(cooling_dataframes)) {
    df <- cooling_dataframes[[i]]
    df$t_stored <- model_stored_temp(df)
    df$e_cooling_expected <- (df$t_stored - df$t_stored[1]) * degToJoules
    df$p_cooling <- model_cooling_power(df$t_stored, t_ambiant, UA) # W
    df$e_cooling <- integrate(df$p_cooling)
    # plot <- plot + geom_line(data=df, aes(x=clock, y=e_cooling_expected, color="expected"))
                 # + geom_line(data=df, aes(x=clock, y=e_cooling, color="expected"))
    plot <- plot + geom_line(data=df, aes(x=clock, y=e_cooling_expected, color="expected")) +
                   geom_line(data=df, aes(x=clock, y=e_cooling, color="modeled"))
}

print(plot + scale_x_clock_hours(df$clock))

cooling <- (df$t_stored[length(df$t_stored)] - df$t_stored[1]) / (df$clock[length(df$clock)] - df$clock[1]) # K/s

# Comparing with NF EN 12977-3 (not read for now)
# UA Coefficient de pertes thermiques (ex. 1.667 W/K)
# Us perte thermique du ballon de stockage (< 20 W / m³·K)
# Cr constante de refroidissement par jour (ex. 0,103 Wh/l.K.j)

#UA <- -(cooling * degToJoules) / mean(df$t_stored - t_ambiant) # W/K
Us <- UA / v_stored_water # Us
Cr <- 85400 * Us / (3600 * 1000)

model_cooling_power <- function(temp_inside, temp_outside) {
  power <- (temp_outside - temp_inside) * UA # W
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
df$e_cooling_stored <- integrate(model_cooling_power(df$t_stored, t_ambiant))

ggplot(df) +
  geom_line(aes(clock, Teb, color="Teb")) +
  geom_line(aes(clock, Teh, color="Teh")) +
  geom_line(aes(clock, t_stored, color="t_stored")) +
  geom_line(aes(clock, e_cooling_b * joulesToDeg + Teb0, color="Teb modeled")) +
  geom_line(aes(clock, e_cooling_h * joulesToDeg + Teh0, color="Teh modeled")) +
  geom_line(aes(clock, e_cooling_stored * joulesToDeg + t_stored0, color="t_stored modeled")) +
  ggtitle(sprintf("Cooling model\nUA %.2f W / K\nUs %.2f W / m³·K\nCr %.2f Wh / l·K·j", UA, Us, Cr)) +
  scale_x_clock_hours(df$clock) +
  scale_y_temperature()

#
# Modeling electrical auxiliary heating energy
# from a dataset where the heater can be seen
#

p_aux_heating <- 3000 # W

df <- read_data('2020-05-03.csv')
df <- df[df$clock > 16 * 3600 & df$clock < 34 * 3600, ]

df$t_stored <- model_stored_temp(df)
df$e_cooling <- integrate(model_cooling_power(df$Teb, t_ambiant))

model_aux_power <- function(df) {

  aux_heating_rate <- p_aux_heating * joulesToDeg # K / s

  # suspect heating when
  # 10 min moving average above expected rising rate / factor
  # determined empiracally by comparing expected temperature increase with the recorded one
  # TODO try to compute stored rate by comparing with n-10 value instead of filter
  # TODO we can see on Tef than the heating rate is shorter than computed here

  t_stored_rate <- derivate(df$t_stored) # K / s

  is_aux_heating <- moving_avg(t_stored_rate, 10) > aux_heating_rate / 2.5

  # Heater regulation has not been observed above

  is_aux_heating[df$Teb > 51] <- FALSE

  # Ignore data when water is flowing

  flowEcs <- derivate(df$Vecs / 1000) # m³/s
  flowP <- derivate(df$Vep / 1000) # m³/s
  flowing <- moving_avg(flowP + flowEcs, 10) != 0

  is_aux_heating[flowing] <- FALSE

  p_aux <- rep(0, length(is_aux_heating))
  p_aux[is_aux_heating] <- p_aux_heating
  return(p_aux)
}

df$p_aux <- model_aux_power(df)
df$e_aux <- integrate(df$p_aux)

t_stored0 <- df$t_stored[1]

ggplot(df) +
  geom_line(aes(clock, Teb, color="Teb")) +
  geom_line(aes(clock, Teh, color="Teh")) +
  geom_point(aes(clock, t_stored, color=p_aux>0)) +
  geom_line(aes(clock, (e_cooling + e_aux) * joulesToDeg + t_stored0, color="t_stored modeled")) +
  scale_x_clock_hours(df$clock, break_by=5, minor_break_by=1) +
  scale_y_temperature()

#
# Modeling solar energye
# from 3 days solar heating of the water can be seen
#

df <- read_data('2020-04-22.csv')
df <- df[df$clock > 8 * 3600 & df$clock < 19 * 3600, ]

df$t_stored <- model_stored_temp(df)
df$e_cooling <- integrate(model_cooling_power(df$Teb, t_ambiant))

# P(W) = qv * rho * cp * (Ts - Ti)

# qv : débit volumique, m3/s
# rho : masse volumique eau, 1000 kg/m3
# cp : capacité calorifique de l'eau, 4185 J / kg.°C
# Ts : Température de sortie du ballon, °C
# Ti : Température d'entrée du ballon, °C

model_solar_power <- function(flow, exchanger_in, exchanger_out) {
  return(flow * rho * cp * (exchanger_in - exchanger_out))
}

df$flowP <- derivate(df$Vep / 1000) # m³/s

# Txe > Tep, meaning that it is more likely closer the real temperature going in the water storage exchanger
# Unfortunately, Txs is often > Txe which is not expected, this might come from a measurement error
# Using the temperature of the bottom water seems to be a far better estimation

t_stored0 <- df$t_stored[1]
df$e_solar_expected <- (df$t_stored - t_stored0) * degToJoules - df$e_cooling

# let say Txs can be estimated with
# Txe + a * (Txe - Teb) + b
# TODO check if solar temperature would be a better indication of Txe
model_solar_exchanger_out <- function(t_exchanger_in, t_bottom, par) {
  return (t_exchanger_in + par[1] * (t_exchanger_in - t_bottom) + par[2])
}

f <- function(par) {
  exchanger_out <- model_solar_exchanger_out(df$Txe, df$Teb, par)
  p_solar <- model_solar_power(df$flowP, df$Txe, exchanger_out)
  e_solar <- integrate(p_solar)
  return(mean_squared_error(df$e_solar_expected, e_solar))
}
r <- optim(c(1, 1), f)
model_solar_exchanger_out_params <- r$par

df$t_exchanger_out <- model_solar_exchanger_out(df$Txe, df$Teb, model_solar_exchanger_out_params)

df$p_solar <- model_solar_power(df$flowP, df$Txe, df$t_exchanger_out) # W
df$e_solar <- integrate(df$p_solar) # J (W.s)

ggplot(df) +
  geom_ribbon(aes(clock, ymin=Teb, ymax=Teh), fill="red", alpha = 0.15) +
  geom_line(aes(clock, t_stored, color='stored')) +
  geom_line(aes(clock, Txe, color='exchanger in')) +
  geom_line(aes(clock, t_exchanger_out, color='exchanger out')) +
  scale_color_manual("T°C", breaks=c("stored", "exchanger in", "exchanger out"), values = c("red", "indianred", "dodgerblue3")) +
  scale_x_clock_hours(df$clock, break_by=5, minor_break_by=1) +
  scale_y_temperature()

ggplot(df) +
  geom_line(aes(clock, e_solar_expected, color='expected')) +
  geom_line(aes(clock, e_solar, color='modeled')) +
  scale_x_clock_hours(df$clock, break_by=1, minor_break_by=0.25) +
  scale_y_temperature()

df <- read_data('2020-04-30.csv')

df$t_stored <- model_stored_temp(df) # °C
# TODO E cooling is under evaluated
df$e_cooling <- integrate(model_cooling_power(df$Teb, t_ambiant)) # W
df$t_exchanger_out <- model_solar_exchanger_out(df$Txe, df$Teb, model_solar_exchanger_out_params) # °C

df$flowEcs <- derivate(df$Vecs / 1000) # m³/s
df$flowP <- derivate(df$Vep / 1000) # m³/s

df$p_solar <- model_solar_power(df$flowP, df$Txe, df$t_exchanger_out) # W
df$e_solar <- integrate(df$p_solar) # J (W.s)

t_stored0 <- df$t_stored[1]
df$e_used_expected <- (df$t_stored - t_stored0) * degToJoules - df$e_cooling - df$e_solar

ggplot(df) +
  geom_line(aes(clock, e_cooling, color="cooling")) +
  geom_line(aes(clock, e_solar, color="solar")) +
  geom_line(aes(clock, e_used_expected, color="used")) +
  scale_x_clock_hours(df$clock, break_by=1, minor_break_by=0.25)

# df$powerEcs <- df$flowEcs * rho * cp * (df$Tef - df$Tec) # W
# df$energyEcs <- integrate(df$powerEcs) # J (W.s)

joulesTokWh <- 1 / (1000 * 3600)

# ggplot(df) +
  # geom_line(aes(clock, energyP * joulesToDeg + Te0, color="energyP")) +
  # geom_line(aes(clock, energyEcs * joulesToDeg + Te0, color="energyEcs")) +
  # geom_line(aes(clock, energyAux * joulesToDeg + Te0, color="energyAux")) +
  # geom_line(aes(clock, (energyAux + energyP + energyEcs) * joulesToDeg + lost + Te0, color="Tsim")) +
  # scale_fill_manual(values = c("green", "red"), name = "fill")

# ggplot(df) +
#   geom_line(aes(clock, energyP * joulesTokWh, color="energyP")) +
#   geom_line(aes(clock, energyEcs * joulesTokWh, color="energyEcs")) +
#   geom_line(aes(clock, energyAux * joulesTokWh, color="energyAux"))