# Datalogging solaire thermique

Ce programme s’intègre dans le système de datalogging de bâtiments de la ville de Lorient. Zabbix est utilisé pour afficher les données et alerter en cas d’anomalie détectée sur les mesures.

L’objectif est ici de faire remonter vers ce système les données mesurées sur une installation de production d’eau chaude sanitaire solaire, avec un appoint électrique.

![Schema installation eau chaude solaire](./docs/schema_installation_lanveur.svg)

L’installation pour le datalogging est composée des éléments suivants :

- Un Arduino connecté à des sondes de température et des compteurs à impulsions (eau et électricité).
- Un Raspberry Pi, connecté en USB à l’Arduino récupère ces données et les expose
- Une clé 3G pour faire remonter les données.

## Installation

Ces instructions permettent d’installer le programme sur un Raspberry Pi fraîchement réinstallé. Voir ici pour [repgrogrammer l’Arduino](./arduino/README.md).

**TODO zabbix agent**

Récupération du code à la racine du répertoire personnel :

```
sudo apt install git
cd $HOME
git clone https://github.com/cyril-L/arduino_api_lanveur.git
```

Installation des dépendances Python :

```
sudo apt-get install python3-serial python3-flask
```

Execution des tests unitaires :

```
$ cd $HOME/arduino_api_lanveur/
$ python3 data_processing.py
........
----------------------------------------------------------------------
Ran 8 tests in 0.006s

OK
$ python3 serial_reader.py --unit-test
.........
----------------------------------------------------------------------
Ran 9 tests in 0.007s

OK
```

Lancement manuel du programme :

```
python3 main.py
```

Lancement automatique du programme avec un Service systemd :

```
mkdir -p $HOME/.config/systemd/user/
```

Éditer le fichier $HOME/.config/systemd/user/arduino_api.service

```
[Unit]
Description=Serial interface with the Arduino, used by the zabbix-agent

[Service]
ExecStart=/usr/bin/python3 /home/pi/arduino_api_lanveur/main.py

[Install]
WantedBy=default.target
```

systemd devrait maintenant connaître le service :

```
$ systemctl --user list-unit-files | grep arduino_api
arduino_api.service          static
```

Lancer le service manuellement :

```
$ systemctl --user daemon-reload
$ systemctl --user start arduino_api
$ systemctl --user status arduino_api
● arduino_api.service - Serial interface with the Arduino, used by the zabbix-agent
   Loaded: loaded (/home/pi/.config/systemd/user/arduino_api.service; static; vendor preset: enabled)
   Active: active (running) since Wed 2020-08-19 18:28:47 CEST; 50s ago
 Main PID: 1122 (python3)
   CGroup: /user.slice/user-1000.slice/user@1000.service/arduino_api.service
           └─1122 /usr/bin/python3 /home/pi/arduino_api_lanveur/main.py

août 19 18:28:47 sepi-lanveur systemd[22340]: Started Serial interface with the Arduino, used by the zabbix-agent.
…
```

Activer le service pour démarrer automatiquement :

```
$ systemctl --user enable arduino_api
Created symlink /home/pi/.config/systemd/user/default.target.wants/arduino_api.service → /home/pi/.config/systemd/user/arduino_api.service.
$ sudo loginctl enable-linger $USER
```