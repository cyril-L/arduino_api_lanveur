#include "OneWire.h"

// Pin assignment

const byte FLOWMETER_1_PIN = 2;
const byte FLOWMETER_2_PIN = 3;

const byte ONEWIRE_BUS_1_PIN = 4;
const byte ONEWIRE_BUS_2_PIN = 5;

// Temperature sensors are distributed on 2 one wire buses

OneWire onewire_bus1(ONEWIRE_BUS_1_PIN);
OneWire onewire_bus2(ONEWIRE_BUS_2_PIN);

typedef struct DS18B20_t {
  const byte address[8];
  OneWire *bus;
} DS18B20_t;

// Sensors found with oneWireScan

const byte temp_sensors_count = 7;

DS18B20_t temp_sensors[temp_sensors_count] {
    {{0x28, 0x8B, 0xCA, 0x58, 0x05, 0x00, 0x00, 0x62}, &onewire_bus1},
    {{0x28, 0x2B, 0xC3, 0x74, 0x05, 0x00, 0x00, 0xAF}, &onewire_bus1},
    {{0x28, 0x27, 0x1F, 0x1E, 0x07, 0x00, 0x00, 0x69}, &onewire_bus1},
    {{0x28, 0xFF, 0xE0, 0x1D, 0xA8, 0x15, 0x04, 0x96}, &onewire_bus1},

    {{0x28, 0x41, 0xC5, 0x88, 0x05, 0x00, 0x00, 0x5C}, &onewire_bus2},
    {{0x28, 0xFF, 0x88, 0xC4, 0x64, 0x15, 0x01, 0xFC}, &onewire_bus2},
    {{0x28, 0xFF, 0x72, 0x45, 0x90, 0x15, 0x04, 0x9D}, &onewire_bus2}
};

// Flow meter pulses interrupt callbacks

volatile unsigned long flowmeter1_pulses = 0;

void flowmeter1_on_rising_edge()  {
  flowmeter1_pulses++;
}

volatile unsigned long flowmeter2_pulses = 0;

void flowmeter2_on_rising_edge()  {
  flowmeter2_pulses++ ;
}

void setup() {
  Serial.begin (9600);
  pinMode(FLOWMETER_1_PIN, INPUT) ;
  attachInterrupt(digitalPinToInterrupt(FLOWMETER_1_PIN), flowmeter1_on_rising_edge, RISING);
  pinMode(FLOWMETER_2_PIN, INPUT) ;
  attachInterrupt(digitalPinToInterrupt(FLOWMETER_2_PIN), flowmeter2_on_rising_edge, RISING);
}

void loop() {
  // TODO legacy data format
  Serial.print(";    ");   
  Serial.print(flowmeter1_pulses);
  Serial.print("    ;    ");
  Serial.print(0);
  Serial.print("    ;    "); 
  Serial.print(flowmeter2_pulses);
  Serial.print("    ;    "); 
  Serial.print(0);

  for (int i = 0; i < temp_sensors_count; ++i) {
    float t = getTempC(&temp_sensors[i]);
    Serial.print("    ;    ");
    Serial.print(t);
  }
  Serial.println("    ;");
}

// TODO legacy code by Tolotra Honoré

float getTempC(DS18B20_t * sensor) {
  const int modeLecture=0xBE;
  const int lancerMesure=0x44;
  byte data[12];
  int tempet=0; // variable pour resultat brute  de la mesure
  float tempetf=0.0; // variable pour resultat à virgule de la mesure
  // XXXXXXXXXXXXXXXXXXXXXX Lancement d'une mesure et lecture du résultat XXXXXXXXXXXXXXXXXXXXXXX
  // Serial.println("**** Acquisition d'une mesure de la temperature **** ");
  // avant chaque nouvelle instruction, il faut :
  //    * initialiser le bus 1-wire
  //    * sélectionner le capteur détecté
  //    * envoyer l'instruction
  //--------- lancer une mesure --------
  sensor->bus->reset(); // initialise le bus 1-wire avant la communication avec un capteur donné
  sensor->bus->select(sensor->address); // sélectionne le capteur ayant l'adresse 64 bits contenue dans le tableau envoyé à la fonction
  sensor->bus->write(lancerMesure,1); // lance la mesure et alimente le capteur par la broche de donnée
  //-------- pause d'une seconde -----
  delay(800);     // au moins 8 s
  // il faudrait mettre une instruction capteur.depower ici, mais le reset va le faire
  //---------- passer en mode LECTURE -------------
  sensor->bus->reset(); // initialise le bus 1-wire avant la communication avec un capteur donné
  sensor->bus->select(sensor->address); // sélectionne le capteur ayant l'adresse 64 bits contenue dans le tableau envoyé à la fonction
  sensor->bus->write(modeLecture,1); // passe en mode lecture de la RAM du capteur
  // ----------- lire les 9 octets de la RAM (appelé Scratchpad) ----
  for ( int i = 0; i < 9; i++) {           // 9 octets de RAM stockés dans 9 octets
    data[i] = sensor->bus->read();             // lecture de l'octet de rang i stocké dans tableau data
  }
  //----- caclul de la température mesurée (enfin!) ---------
  /*data[1]=data[1] & B10000111; // met à 0 les bits de signes inutiles  <- Le bug était caché la
  tempet=data[1]; // bits de poids fort
  tempet=tempet<<8;
  tempet=tempet+data[0]; // bits de poids faible
  */
  tempet=(data[1]<<8)|data[0]; // a l'arrache style !
  // --- en mode 12 bits, la résolution est de 0.0625°C - cf datasheet DS18B20
  tempetf=float(tempet)*6.25;
  tempetf=tempetf/100.0;
  return (tempetf);
}

void oneWireScan(OneWire * bus) {
  byte address[8];

  while (1) {
    if (!bus->search(address)) {
      Serial.println(F("End of Scan."));
      bus->reset_search();
      break;
    }
    
    Serial.print(F("Found "));
    for(byte i = 0; i < 8; ++i) {
      if (address[i] < 0x10) Serial.write('0');
      Serial.print(address[i], HEX);
      Serial.write(' ');
    }
  
    if (OneWire::crc8(address, 7) != address[7]) {
        Serial.print(F("(CRC invalid)"));
    }
  }
  
  Serial.println();
}
