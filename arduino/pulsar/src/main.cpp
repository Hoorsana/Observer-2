/* SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
 * 
 * SPDX-License-Identifier: GPL-3.0-or-later */

#include <Arduino.h>

static int mult = 0;
static int last = 0;
static int GRAIN = 1;
static int FREQUENCY = 100;
static int DIGITAL_OUT = 45;

void setup()
{
  Serial.begin(19200);
  pinMode(DIGITAL_OUT, OUTPUT);
  last = millis();
}

void loop()
{
  auto t = millis();
  if (t - last > FREQUENCY)
  {
    analogWrite(DAC1, mult * 255);
    digitalWrite(DIGITAL_OUT, mult ? HIGH : LOW);
    mult = abs(1 - mult);
    last = t;
  }
  delay(GRAIN);
}
