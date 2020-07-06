read_data <- function(filename, reset_clock=TRUE, from_hour=NULL, to_hour=NULL) {
  df <- read.table(filename, header = TRUE, sep = ",", fill = TRUE)
  if (reset_clock) {
    df$clock <- df$clock - df$clock[1]
  }

  if (!is.null(from_hour)) {
    df <- df[df$clock >= from_hour * 3600, ]
  }

  if (!is.null(to_hour)) {
    df <- df[df$clock < to_hour * 3600, ]
  }

  if (reset_clock & (!is.null(from_hour) | !is.null(to_hour))) {
    df$clock <- df$clock - df$clock[1]
  }

  if (max(df$Tep) < max(df$Txs)) {
    # Swap Txs and Tep
    df$tmp <- df$Tep
    df$Tep <- df$Txs
    df$Txs <- df$tmp
  }

  # Swap Txs and Txe
  # df$tmp <- df$Txe
  # df$Txe <- df$Txs
  # df$Txs <- df$tmp

  return(df)
}

scale_x_clock_hours <- function(clock_s, break_by=1, minor_break_by=0.25) {
  hours_from <- floor(clock_s[1] / 3600)
  hours_to <- clock_s[length(clock_s)] / 3600
  hours <- seq(hours_from, hours_to, by=break_by)
  quarters <- seq(hours_from, hours_to, by=minor_break_by)
  return(scale_x_continuous(name="Time (h)", breaks=hours * 3600, minor_breaks=quarters * 3600, labels=hours))
}

scale_y_temperature <- function() {
  return(scale_y_continuous(name="Temperature (°C)", breaks=seq(0, 100, 5), minor_breaks=seq(0, 100, 1)))
}

sample_period <- 60 # s

derivate <- function(v) {
  return(c(0, diff(v) / sample_period))
}

integrate <- function(v) {
  return(diffinv(v)[-1] * sample_period)
}

moving_avg <- function(x, n) {
  return(filter(x, rep(1 / n, n), sides = 2))
}

mean_squared_error <- function(expected, predicted) {
  return(mean((expected - predicted)^2))
}