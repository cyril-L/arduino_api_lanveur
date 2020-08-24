# Arduino

## TODOs

- Changement de capteur de température
- Schematics

## Flasher le code Arduino depuis le Raspberry Pi

```
cd $HOME/arduino_api_lanveur/arduino
wget https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_ARMv7.tar.gz
tar xvzf arduino-cli_latest_Linux_ARMv7.tar.gz
```

```
$ ./arduino-cli core update-index
$ ./arduino-cli board list
Port         Type              Board Name  FQBN            Core
/dev/ttyACM0 Serial Port (USB) Arduino Uno arduino:avr:uno arduino:avr
/dev/ttyAMA0 Serial Port       Unknown
$ ./arduino-cli core install arduino:avr
```

```
./arduino-cli compile --fqbn arduino:avr:uno data_acquisition
```

```
./arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno data_acquisition
```

## Lire les données sur le port série

```
sudo apt-get install picocom
picocom -b 9600 /dev/ttyACM0
```

## Sauvegarder et restaurer le programme original

Procédure utilisée pour sauvegarde le programme original tournant sur l’Arduino (nous n’avions pas les sources).

```
sudo apt-get install avrdude
```

Pour sauvegarder le binaire tournant sur l’Arduino :

```
avrdude -p atmega328p  -carduino -P /dev/ttyACM0 -b 115200 -U flash:r:flash_backup_file.hex
```

Pour restaurer ce binaire :

```
avrdude -p atmega328p -carduino -P /dev/ttyACM0 -b 115200 -e -U flash:w:flash_backup_file.hex
```