// Copyright 2020 Cyril Lugan, https://cyril.lugan.fr
// Licensed under the EUPL v1.2, https://eupl.eu/1.2/en/

#include "OneWire.h"

// Pin assignment

const byte FLOW_METER_1_PIN = 2;
const byte FLOW_METER_2_PIN = 3;
const byte AUX_ENERGY_METER_PIN = 6;

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

class DebouncedPluseCounter {
public:

  volatile unsigned long count;

  DebouncedPluseCounter(int digital_pin, int debounce_duration_ms) {
    this->digital_pin = digital_pin;
    this->debounce_duration_ms = debounce_duration_ms;
    count = 0;
  }

  void setup() {
    pinMode(digital_pin, INPUT);
    this->previous_state = digitalRead(digital_pin);
    this->debounced_state = previous_state;
    this->debounce_started_at = 0;
  }

  void update(unsigned long time_ms) {
    int state = digitalRead(digital_pin);
    // If pin state has changed, start a timer
    if (state != previous_state) {
      debounce_started_at = time_ms;
      previous_state = state;
    // Apply the change to debounced_state if the new state is still observed
    // after the debounce duration
    } else if (state != debounced_state && (time_ms > debounce_started_at + debounce_duration_ms)) {
      debounced_state = state;
      if (state) {
        count++;
      }
    }
  }

private:
  unsigned long debounce_started_at;
  int debounce_duration_ms;
  int digital_pin;
  int previous_state;
  int debounced_state;
};

const byte debounce_duration_ms = 5;

const byte pulse_counters_count = 3;

DebouncedPluseCounter pulse_counters[pulse_counters_count] {
  DebouncedPluseCounter(FLOW_METER_1_PIN, debounce_duration_ms),
  DebouncedPluseCounter(FLOW_METER_2_PIN, debounce_duration_ms),
  DebouncedPluseCounter(AUX_ENERGY_METER_PIN, debounce_duration_ms)
};

// Nice resource about timers
// https://learn.adafruit.com/multi-tasking-the-arduino-part-2/timers

// Interrupt is called once a millisecond
// Counter pulse duration is about 90 ms

SIGNAL(TIMER0_COMPA_vect)
{
  unsigned long time_ms = millis();
  for (int i = 0; i < pulse_counters_count; ++i) {
    pulse_counters[i].update(time_ms);
  }
}

void setup() {
  Serial.begin (9600);
  unsigned long time_ms = millis();
  for (int i = 0; i < pulse_counters_count; ++i) {
    pulse_counters[i].setup();
  }

  // Timer0 is already used for millis() - we'll just interrupt somewhere
  // in the middle and call the "Compare A" function above
  OCR0A = 0xAF;
  TIMSK0 |= _BV(OCIE0A);
}

void loop() {

  for (int i = 0; i < pulse_counters_count; ++i) {
    Serial.print(pulse_counters[i].count);
    Serial.print(" ; ");
  }

  for (int i = 0; i < temp_sensors_count; ++i) {
    float t = getTempC(&temp_sensors[i]);
    Serial.print(t);
    Serial.print(" ; ");
  }
  Serial.println();
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
