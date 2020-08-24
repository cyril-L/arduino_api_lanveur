# Arduino

[Schéma des branchements](./lanveur_schematics/lanveur_schematics.pdf).

## Capteurs

### Sondes de température DS18B20

Les sondes de température ont été repartie sur deux bus OneWire, selon les tests réalisés lors d’un stage.

Les adresses OneWire des capteurs sont pour le moment spécifiées en dur dans le code Arduino. Il sera donc nécessaire de le reprogrammer si une sonde était changée. [Lire les données sur le port série](#lire-les-données-sur-le-port-série) pour lister les adresses des sondes connectées.

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

S’il tourne, arrêter le service récupérant les données de l’Arduino :

```
systemctl --user stop arduino_api
```

Utiliser picocom :

```
sudo apt-get install picocom
picocom -b 9600 /dev/ttyACM0
```

Tapper Ctrl-a suivi de Ctrl-x pour quitter.

Pour lister les adresses des sondes connectées à l’Arduino, taper la touche « Entrée » sur le port série :

```
0 ; 0 ; 0 ; 61.38 ; 48.75 ; 52.31 ; 22.87 ; 31.87 ; 50.44 ; 33.88 ;
Scanning OneWire bus 1
Found 28 8B CA 58 05 00 00 62
Found 28 2B C3 74 05 00 00 AF
Found 28 27 1F 1E 07 00 00 69
Found 28 FF E0 1D A8 15 04 96
End of Scan.
Scanning OneWire bus 2
Found 28 41 C5 88 05 00 00 5C
Found 28 FF 88 C4 64 15 01 FC
Found 28 FF 72 45 90 15 04 9D
End of Scan.
0 ; 0 ; 0 ; 61.38 ; 48.81 ; 52.31 ; 22.87 ; 31.87 ; 50.44 ; …
```

## Sauvegarder et restaurer le programme original

Procédure utilisée pour sauvegarde le programme développé lors du stage (nous n’avions pas les sources).

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