const int tempPin = A0;     // Analog temperature sensor
const int lightPin = A1;    // OSEPP LIGHT-02 sensor
const int joyXPin = A2;     // Joystick X-axis
const int joyYPin = A3;     // Joystick Y-axis

void setup() {
  Serial.begin(9600);
}

void loop() {
  int tempVal = analogRead(tempPin);
  int lightVal = analogRead(lightPin);
  int xVal = analogRead(joyXPin);
  int yVal = analogRead(joyYPin);

  // One line per reading, comma separated, for the laptop bridge
  Serial.print("Light:");
  Serial.print(lightVal);
  Serial.print(",Temperature:");
  Serial.print(tempVal);
  Serial.print(",X:");
  Serial.print(xVal);
  Serial.print(",Y:");
  Serial.println(yVal);

  // Grove joystick click: pressing down spikes X to about 1023
  if (xVal > 1000) {
    Serial.println("CAPTURE");
    delay(1500);
  }

  delay(500);
}
