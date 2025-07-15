// ========== Pines PWM para control de colores (bombas) ==========
const int cPin = 3;    // Cyan    (PWM)
const int mPin = 5;    // Magenta (PWM)
const int yPin = 6;    // Yellow  (PWM)
const int kPin = 9;    // Black   (PWM)
const int wPin = 10;   // White   (PWM)

// ========== Pines analógicos para sensores de nivel ==========
const int cLevelPin = A0;
const int mLevelPin = A1;
const int yLevelPin = A2;
const int kLevelPin = A3;
const int wLevelPin = A4;

// ========== Pines analógicos para sensores de temperatura ==========
const int cTempPin = A5;
const int mTempPin = A6;
const int yTempPin = A7;
const int kTempPin = A8;
const int wTempPin = A9;

// ========== Pines digitales para calentadores ==========
const int cHeaterPin = 2;
const int mHeaterPin = 4;
const int yHeaterPin = 7;
const int kHeaterPin = 8;
const int wHeaterPin = 11;

// ========== Pines digitales para alarmas ==========
const int cAlarmLed = 12;
const int mAlarmLed = 22;
const int yAlarmLed = 23;
const int kAlarmLed = 24;
const int wAlarmLed = 25;
const int buzzerPin = 26;

const int ledPin = 13; // LED integrado

// ========== Pines para el Agitador ==========
const int agitatorPin = 27;       // Pin PWM para el motor del agitador
const int agitatorButtonPin = 28; // Pin para el botón físico (con pull-up interno)
const int AGITATOR_SPEED = 200;   // Velocidad del agitador (0-255)

// ========== Variables generales ==========
int c = 0, m = 0, y = 0, k = 0, w = 0;
double cSetpoint = 30.0, mSetpoint = 30.0, ySetpoint = 30.0, kSetpoint = 30.0, wSetpoint = 30.0;
double Kp = 2.0, Ki = 5.0, Kd = 1.0;

unsigned long cLastTime, mLastTime, yLastTime, kLastTime, wLastTime;
double cLastError, mLastError, yLastError, kLastError, wLastError;
double cCumError, mCumError, yCumError, kCumError, wCumError;

// ========== Constantes para niveles ==========
const int LEVEL_CRITICAL = 10; // Nivel crítico: bloquea bombas
const int LEVEL_WARNING = 20;  // Nivel de advertencia: activa LED y buzzer
const double TEMP_SETPOINT = 30.0; // Temperatura requerida para operar bombas

void setup() {
  // Configuración de pines PWM
  pinMode(cPin, OUTPUT);
  pinMode(mPin, OUTPUT);
  pinMode(yPin, OUTPUT);
  pinMode(kPin, OUTPUT);
  pinMode(wPin, OUTPUT);

  // Configuración de calentadores
  pinMode(cHeaterPin, OUTPUT);
  pinMode(mHeaterPin, OUTPUT);
  pinMode(yHeaterPin, OUTPUT);
  pinMode(kHeaterPin, OUTPUT);
  pinMode(wHeaterPin, OUTPUT);

  // Configuración de alarmas
  pinMode(cAlarmLed, OUTPUT);
  pinMode(mAlarmLed, OUTPUT);
  pinMode(yAlarmLed, OUTPUT);
  pinMode(kAlarmLed, OUTPUT);
  pinMode(wAlarmLed, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  // Configuración del agitador
  pinMode(agitatorPin, OUTPUT);
  pinMode(agitatorButtonPin, INPUT_PULLUP); // Botón conectado a GND

  pinMode(ledPin, OUTPUT); // LED onboard

  Serial.begin(9600);
  while (!Serial);

  cLastTime = mLastTime = yLastTime = kLastTime = wLastTime = millis();

  Serial.println("Sistema de control de tanques inicializado.");
  blinkLED(2);
}

void loop() {
  processSerialCommands();
  readSensors();
  controlTemperature();
  checkLevels();
  controlPumps();
  checkAgitatorButton();
  delay(100);
}

// ========== Función para controlar bombas ==========
void controlPumps() {
  double cTemp = analogRead(cTempPin) * 0.48828125;
  double mTemp = analogRead(mTempPin) * 0.48828125;
  double yTemp = analogRead(yTempPin) * 0.48828125;
  double kTemp = analogRead(kTempPin) * 0.48828125;
  double wTemp = analogRead(wTempPin) * 0.48828125;

  int cLevel = getLevel(cLevelPin);
  int mLevel = getLevel(mLevelPin);
  int yLevel = getLevel(yLevelPin);
  int kLevel = getLevel(kLevelPin);
  int wLevel = getLevel(wLevelPin);

  // Control de bombas basado en temperatura y nivel crítico
  if (cTemp >= TEMP_SETPOINT && cLevel >= LEVEL_CRITICAL) {
    analogWrite(cPin, map(c, 0, 100, 255, 0));
  } else {
    analogWrite(cPin, 0); // Apaga la bomba si no se cumplen las condiciones
    if (cTemp < TEMP_SETPOINT) Serial.println("Bomba C detenida: Temperatura menor a 30°C");
    if (cLevel < LEVEL_CRITICAL) Serial.println("Bomba C detenida: Nivel crítico bajo");
  }

  if (mTemp >= TEMP_SETPOINT && mLevel >= LEVEL_CRITICAL) {
    analogWrite(mPin, map(m, 0, 100, 255, 0));
  } else {
    analogWrite(mPin, 0);
    if (mTemp < TEMP_SETPOINT) Serial.println("Bomba M detenida: Temperatura menor a 30°C");
    if (mLevel < LEVEL_CRITICAL) Serial.println("Bomba M detenida: Nivel crítico bajo");
  }

  if (yTemp >= TEMP_SETPOINT && yLevel >= LEVEL_CRITICAL) {
    analogWrite(yPin, map(y, 0, 100, 255, 0));
  } else {
    analogWrite(yPin, 0);
    if (yTemp < TEMP_SETPOINT) Serial.println("Bomba Y detenida: Temperatura menor a 30°C");
    if (yLevel < LEVEL_CRITICAL) Serial.println("Bomba Y detenida: Nivel crítico bajo");
  }

  if (kTemp >= TEMP_SETPOINT && kLevel >= LEVEL_CRITICAL) {
    analogWrite(kPin, map(k, 0, 100, 255, 0));
  } else {
    analogWrite(kPin, 0);
    if (kTemp < TEMP_SETPOINT) Serial.println("Bomba K detenida: Temperatura menor a 30°C");
    if (kLevel < LEVEL_CRITICAL) Serial.println("Bomba K detenida: Nivel crítico bajo");
  }

  if (wTemp >= TEMP_SETPOINT && wLevel >= LEVEL_CRITICAL) {
    analogWrite(wPin, map(w, 0, 100, 0, 255));
  } else {
    analogWrite(wPin, 0);
    if (wTemp < TEMP_SETPOINT) Serial.println("Bomba W detenida: Temperatura menor a 30°C");
    if (wLevel < LEVEL_CRITICAL) Serial.println("Bomba W detenida: Nivel crítico bajo");
  }
}

// ========== Función para el Botón del Agitador ==========
void checkAgitatorButton() {
  if (digitalRead(agitatorButtonPin) == LOW) { // Botón presionado (LOW por pull-up)
    analogWrite(agitatorPin, AGITATOR_SPEED);  // Activa el agitador
    digitalWrite(ledPin, HIGH);                // Feedback visual
    Serial.println("Agitador ACTIVADO (botón presionado)");
  } else {
    analogWrite(agitatorPin, 0);               // Apaga el agitador
    digitalWrite(ledPin, LOW);                 // Apaga el feedback
  }
}

// ========== Funciones Existente (sin cambios) ==========
void processSerialCommands() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (sscanf(input.c_str(), "C:%d M:%d Y:%d K:%d W:%d", &c, &m, &y, &k, &w) == 5) {
      c = constrain(c, 0, 100);
      m = constrain(m, 0, 100);
      y = constrain(y, 0, 100);
      k = constrain(k, 0, 100);
      w = constrain(w, 0, 100);

      Serial.print("CMYKW Recibido: ");
      Serial.print("C:"); Serial.print(c);
      Serial.print(" M:"); Serial.print(m);
      Serial.print(" Y:"); Serial.print(y);
      Serial.print(" K:"); Serial.print(k);
      Serial.print(" W:"); Serial.println(w);

      blinkLED(1);
    } else if (input.startsWith("TEMP ")) {
      char color = input.charAt(5);
      int temp = input.substring(7).toInt();
      switch (color) {
        case 'C': cSetpoint = temp; break;
        case 'M': mSetpoint = temp; break;
        case 'Y': ySetpoint = temp; break;
        case 'K': kSetpoint = temp; break;
        case 'W': wSetpoint = temp; break;
        default: Serial.println("Error: Color no válido");
      }
      Serial.print("Setpoint de "); Serial.print(color);
      Serial.print(" cambiado a: "); Serial.println(temp);
    } else {
      Serial.println("Error: Formato incorrecto");
      blinkLED(3);
    }
  }
}

void readSensors() {
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 5000) {
    lastSend = millis();
    sendSensorData();
  }
}

void sendSensorData() {
  double cTemp = analogRead(cTempPin) * 0.48828125;
  double mTemp = analogRead(mTempPin) * 0.48828125;
  double yTemp = analogRead(yTempPin) * 0.48828125;
  double kTemp = analogRead(kTempPin) * 0.48828125;
  double wTemp = analogRead(wTempPin) * 0.48828125;

  Serial.print("Temperaturas - C:"); Serial.print(cTemp);
  Serial.print("°C M:"); Serial.print(mTemp);
  Serial.print("°C Y:"); Serial.print(yTemp);
  Serial.print("°C K:"); Serial.print(kTemp);
  Serial.print("°C W:"); Serial.print(wTemp); Serial.println("°C");

  Serial.print("Niveles - C:"); Serial.print(getLevel(cLevelPin));
  Serial.print("% M:"); Serial.print(getLevel(mLevelPin));
  Serial.print("% Y:"); Serial.print(getLevel(yLevelPin));
  Serial.print("% K:"); Serial.print(getLevel(kLevelPin));
  Serial.print("% W:"); Serial.print(getLevel(wLevelPin)); Serial.println("%");
}

int getLevel(int pin) {
  int raw = analogRead(pin);
  return map(raw, 0, 1023, 0, 100);
}

void controlTemperature() {
  analogWrite(cHeaterPin, computePID(analogRead(cTempPin) * 0.48828125, cSetpoint, &cLastTime, &cLastError, &cCumError));
  analogWrite(mHeaterPin, computePID(analogRead(mTempPin) * 0.48828125, mSetpoint, &mLastTime, &mLastError, &mCumError));
  analogWrite(yHeaterPin, computePID(analogRead(yTempPin) * 0.48828125, ySetpoint, &yLastTime, &yLastError, &yCumError));
  analogWrite(kHeaterPin, computePID(analogRead(kTempPin) * 0.48828125, kSetpoint, &kLastTime, &kLastError, &kCumError));
  analogWrite(wHeaterPin, computePID(analogRead(wTempPin) * 0.48828125, wSetpoint, &wLastTime, &wLastError, &wCumError));
}

int computePID(double input, double setpoint, unsigned long *lastTime, double *lastError, double *cumError) {
  unsigned long currentTime = millis();
  double elapsedTime = (double)(currentTime - *lastTime) / 1000.0;
  double error = setpoint - input;
  *cumError += error * elapsedTime;
  double rateError = (error - *lastError) / elapsedTime;
  double output = Kp * error + Ki * (*cumError) + Kd * rateError;
  output = constrain(output, 0, 255);
  *lastError = error;
  *lastTime = currentTime;
  return (int)output;
}

void checkLevels() {
  bool alarmActive = false;

  // Comprobar niveles para cada tanque
  if (getLevel(cLevelPin) < LEVEL_CRITICAL) {
    digitalWrite(cAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Alarma C: Nivel crítico bajo");
  } else if (getLevel(cLevelPin) < LEVEL_WARNING) {
    digitalWrite(cAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Advertencia C: Nivel bajo");
  } else {
    digitalWrite(cAlarmLed, LOW);
  }

  if (getLevel(mLevelPin) < LEVEL_CRITICAL) {
    digitalWrite(mAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Alarma M: Nivel crítico bajo");
  } else if (getLevel(mLevelPin) < LEVEL_WARNING) {
    digitalWrite(mAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Advertencia M: Nivel bajo");
  } else {
    digitalWrite(mAlarmLed, LOW);
  }

  if (getLevel(yLevelPin) < LEVEL_CRITICAL) {
    digitalWrite(yAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Alarma Y: Nivel crítico bajo");
  } else if (getLevel(yLevelPin) < LEVEL_WARNING) {
    digitalWrite(yAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Advertencia Y: Nivel bajo");
  } else {
    digitalWrite(yAlarmLed, LOW);
  }

  if (getLevel(kLevelPin) < LEVEL_CRITICAL) {
    digitalWrite(kAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Alarma K: Nivel crítico bajo");
  } else if (getLevel(kLevelPin) < LEVEL_WARNING) {
    digitalWrite(kAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Advertencia K: Nivel bajo");
  } else {
    digitalWrite(kAlarmLed, LOW);
  }

  if (getLevel(wLevelPin) < LEVEL_CRITICAL) {
    digitalWrite(wAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Alarma W: Nivel crítico bajo");
  } else if (getLevel(wLevelPin) < LEVEL_WARNING) {
    digitalWrite(wAlarmLed, HIGH);
    alarmActive = true;
    Serial.println("Advertencia W: Nivel bajo");
  } else {
    digitalWrite(wAlarmLed, LOW);
  }

  // Activar buzzer si alguna alarma está activa
  if (alarmActive) {
    tone(buzzerPin, 1000, 200);
    delay(300);
    noTone(buzzerPin);
  }
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(ledPin, HIGH);
    delay(150);
    digitalWrite(ledPin, LOW);
    delay(150);
  }
}