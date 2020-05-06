#!/usr/bin/env Rscript

library(ggplot2)

df <- read.table(commandArgs(trailingOnly=TRUE), header = TRUE, sep = ",", fill = TRUE)

ggplot(df) +
  geom_line(aes(clock, Teh, color="Teh")) +
  geom_line(aes(clock, Teb, color="Teb")) +
  geom_line(aes(clock, Tef, color="Tef")) +
  geom_line(aes(clock, Tec, color="Tec"))

ggplot(df) +
  geom_line(aes(clock, Tep, color="Tep")) +
  geom_line(aes(clock, Txe, color="Txe")) +
  geom_line(aes(clock, Txs, color="Txs"))

ggplot(df) +
  geom_line(aes(clock, Vecs, color="Vecs")) +
  geom_line(aes(clock, Vep, color="Vep"))