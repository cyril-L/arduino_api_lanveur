#!/usr/bin/env Rscript

library(ggplot2)

source("utils.R")

df <- read_data(commandArgs(trailingOnly=TRUE))

ggplot(df) +
  geom_line(aes(clock, Teh, color="Teh")) +
  geom_line(aes(clock, Teb, color="Teb")) +
  geom_line(aes(clock, Tef, color="Tef")) +
  geom_line(aes(clock, Tec, color="Tec")) +
  scale_x_clock_hours(df$clock, break_by=5, minor_break_by=1) +
  scale_y_temperature()

ggplot(df) +
  geom_line(aes(clock, Tep, color="Tep")) +
  geom_line(aes(clock, Txe, color="Txe")) +
  geom_line(aes(clock, Txs, color="Txs")) +
  scale_x_clock_hours(df$clock, break_by=5, minor_break_by=1) +
  scale_y_temperature()

ggplot(df) +
  geom_line(aes(clock, Vecs, color="Vecs")) +
  geom_line(aes(clock, Vep, color="Vep")) +
  scale_x_clock_hours(df$clock, break_by=5, minor_break_by=1)