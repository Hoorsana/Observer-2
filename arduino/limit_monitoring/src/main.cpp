/* SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
 * 
 * SPDX-License-Identifier: GPL-3.0-or-later */

#include <Arduino.h>

const float voltage = 3.3;
const float dac_lo = 0.55;  // See https://www.arduino.cc/en/pmwiki.php?n=Main/arduinoBoardDue
const float dac_hi = 2.75;
const float lo = 1023 / (voltage/dac_lo);
const float hi = 1023 / (voltage/dac_hi);

int analog_read(uint8_t pin)
{
  return map(analogRead(pin), lo, hi, 0, 255);
}

void setup()
{
  Serial.begin(19200);
}

void loop()
{
  auto temperature = analog_read(A1);
  if (temperature > 229.5)
  {
    digitalWrite(40, HIGH);
  }
  else
  {
    digitalWrite(40, LOW);
  }
}
