read_data <- function(filename, reset_clock=TRUE) {
  df <- read.table(filename, header = TRUE, sep = ",", fill = TRUE)
  if (reset_clock) {
    df$clock <- df$clock - df$clock[1]
  }
  return(df)
}

scale_x_clock_hours <- function(clock_s) {
  hours_from <- clock_s[1] / 3600
  hours_to <- clock_s[length(clock_s)] / 3600
  hours <- seq(hours_from, hours_to, by = 1)
  quarters <- seq(hours_from, hours_to, by = 0.25)
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

moving_avg <- function(x, n){
  return(filter(x, rep(1 / n, n), sides = 2))
}