import os

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

SERIAL_DEVICE = "/dev/ttyACM0"
SERIAL_BAUDRATE = 9600

# Time to atempt a new connection when the previous failed
SERIAL_RECONNECT_TIMEOUT_S = 5

# How often we expect data readings
# The Arduino will be reset when this timeout expires
FRESH_DATA_TIMEOUT_S = 2

# Where / how often save persistent counters
COUNTERS_FILE_PATH = os.path.join(ROOT_DIR, "counters.json")
COUNTERS_FILE_SAVE_PERIOD_MIN = 10
