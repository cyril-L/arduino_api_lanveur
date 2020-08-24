# Arduino

[Schéma des branchements](./lanveur_schematics/lanveur_schematics.pdf).

## Capteurs

### Sondes de température DS18B20

TODO Changement de capteur de température

### Compteur électrique triphasé Orno WE-520

Un compteur est utilisé pour mesurer l’énergie consommée par le chauffage d’appoint, une résistance de 3 kW en triphasé.

La notice du compteur spécifie la sortie impulsion suivante :

- Tension : 12~17V
- Courant : 27 mA
- Longueur de câble maximale : 20 m
- Durée d’impulsion : 80 ms
- Fréquence : 800 impulsions par kWh

Bien qu’une sortie 5 V semble hors spécification, elle fonctionne. Nous avons choisi cette solution pour simplifier le montage. L’alternative 12 V est également proposée sur le [schéma](./lanveur_schematics/lanveur_schematics.pdf).

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