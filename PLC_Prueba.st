PROGRAM TankControl
VAR
    // Entradas analógicas para sensores de nivel
    cLevel AT %IW0 : INT; // Nivel Cyan (0-1023)
    mLevel AT %IW1 : INT; // Nivel Magenta
    yLevel AT %IW2 : INT; // Nivel Yellow
    kLevel AT %IW3 : INT; // Nivel Black
    wLevel AT %IW4 : INT; // Nivel White

    // Entradas analógicas para sensores de temperatura
    cTemp AT %IW5 : REAL; // Temperatura Cyan
    mTemp AT %IW6 : REAL; // Temperatura Magenta
    yTemp AT %IW7 : REAL; // Temperatura Yellow
    kTemp AT %IW8 : REAL; // Temperatura Black
    wTemp AT %IW9 : REAL; // Temperatura White

    // Salidas PWM para bombas
    cPump AT %QW0 : INT; // Bomba Cyan (0-255)
    mPump AT %QW1 : INT; // Bomba Magenta
    yPump AT %QW2 : INT; // Bomba Yellow
    kPump AT %QW3 : INT; // Bomba Black
    wPump AT %QW4 : INT; // Bomba White

    // Salidas digitales para calentadores
    cHeater AT %Q0.0 : BOOL; // Calentador Cyan
    mHeater AT %Q0.1 : BOOL; // Calentador Magenta
    yHeater AT %Q0.2 : BOOL; // Calentador Yellow
    kHeater AT %Q0.3 : BOOL; // Calentador Black
    wHeater AT %Q0.4 : BOOL; // Calentador White

    // Salidas digitales para alarmas
    cAlarmLed AT %Q0.5 : BOOL; // LED Alarma Cyan
    mAlarmLed AT %Q0.6 : BOOL; // LED Alarma Magenta
    yAlarmLed AT %Q0.7 : BOOL; // LED Alarma Yellow
    kAlarmLed AT %Q1.0 : BOOL; // LED Alarma Black
    wAlarmLed AT %Q1.1 : BOOL; // LED Alarma White
    buzzer AT %Q1.2 : BOOL;    // Buzzer

    // Salidas para agitador
    agitator AT %QW5 : INT;    // Motor del agitador (0-255)
    agitatorButton AT %I0.0 : BOOL; // Botón del agitador

    // LED integrado
    led AT %Q1.3 : BOOL;

    // Variables de control
    c : INT := 0; m : INT := 0; y : INT := 0; k : INT := 0; w : INT := 0;
    cSetpoint : REAL := 30.0; mSetpoint : REAL := 30.0; ySetpoint : REAL := 30.0;
    kSetpoint : REAL := 30.0; wSetpoint : REAL := 30.0;

    // Variables PID
    Kp : REAL := 2.0; Ki : REAL := 5.0; Kd : REAL := 1.0;
    cLastError : REAL; mLastError : REAL; yLastError : REAL; kLastError : REAL; wLastError : REAL;
    cCumError : REAL; mCumError : REAL; yCumError : REAL; kCumError : REAL; wCumError : REAL;
    cLastTime : TIME; mLastTime : TIME; yLastTime : TIME; kLastTime : TIME; wLastTime : TIME;

    // Constantes
    LEVEL_CRITICAL : INT := 10; // Nivel crítico
    LEVEL_WARNING : INT := 20;  // Nivel de advertencia
    TEMP_SETPOINT : REAL := 30.0; // Temperatura mínima para bombas
    AGITATOR_SPEED : INT := 200;  // Velocidad del agitador
END_VAR

VAR
    lastSend : TIME; // Para enviar datos de sensores
END_VAR

// Función PID
FUNCTION ComputePID : INT
VAR_INPUT
    input : REAL; setpoint : REAL;
    lastTime : TIME; lastError : REAL; cumError : REAL;
END_VAR
VAR_IN_OUT
    lastErrorOut : REAL; cumErrorOut : REAL; lastTimeOut : TIME;
END_VAR
VAR
    currentTime : TIME := T#0ms;
    elapsedTime : REAL;
    error : REAL;
    rateError : REAL;
    output : REAL;
END_VAR
    currentTime := TIME(); // Obtener tiempo actual
    elapsedTime := TIME_TO_REAL(currentTime - lastTime) / 1000.0;
    error := setpoint - input;
    cumErrorOut := cumErrorOut + error * elapsedTime;
    rateError := (error - lastError) / elapsedTime;
    output := Kp * error + Ki * cumErrorOut + Kd * rateError;
    IF output < 0 THEN output := 0; END_IF;
    IF output > 255 THEN output := 255; END_IF;
    lastErrorOut := error;
    lastTimeOut := currentTime;
    ComputePID := REAL_TO_INT(output);
END_FUNCTION

// Función para mapear nivel
FUNCTION GetLevel : INT
VAR_INPUT
    raw : INT; // Valor crudo del sensor (0-1023)
END_VAR
    GetLevel := (raw * 100) / 1023; // Mapear a 0-100%
END_FUNCTION

// Programa principal
METHOD Main : VOID
VAR
    cLevelVal : INT; mLevelVal : INT; yLevelVal : INT; kLevelVal : INT; wLevelVal : INT;
    alarmActive : BOOL := FALSE;
END_VAR
    // Convertir entradas analógicas de temperatura (suponiendo 0-1023 a °C)
    cTemp := INT_TO_REAL(cTemp) * 0.48828125;
    mTemp := INT_TO_REAL(mTemp) * 0.48828125;
    yTemp := INT_TO_REAL(yTemp) * 0.48828125;
    kTemp := INT_TO_REAL(kTemp) * 0.48828125;
    wTemp := INT_TO_REAL(wTemp) * 0.48828125;

    // Obtener niveles
    cLevelVal := GetLevel(cLevel);
    mLevelVal := GetLevel(mLevel);
    yLevelVal := GetLevel(yLevel);
    kLevelVal := GetLevel(kLevel);
    wLevelVal := GetLevel(wLevel);

    // Control de bombas
    IF cTemp >= TEMP_SETPOINT AND cLevelVal >= LEVEL_CRITICAL THEN
        cPump := (c * 255) / 100; // Mapear 0-100 a 0-255
    ELSE
        cPump := 0;
    END_IF;

    IF mTemp >= TEMP_SETPOINT AND mLevelVal >= LEVEL_CRITICAL THEN
        mPump := (m * 255) / 100;
    ELSE
        mPump := 0;
    END_IF;

    IF yTemp >= TEMP_SETPOINT AND yLevelVal >= LEVEL_CRITICAL THEN
        yPump := (y * 255) / 100;
    ELSE
        yPump := 0;
    END_IF;

    IF kTemp >= TEMP_SETPOINT AND kLevelVal >= LEVEL_CRITICAL THEN
        kPump := (k * 255) / 100;
    ELSE
        kPump := 0;
    END_IF;

    IF wTemp >= TEMP_SETPOINT AND wLevelVal >= LEVEL_CRITICAL THEN
        wPump := (w * 255) / 100;
    ELSE
        wPump := 0;
    END_IF;

    // Control de temperatura (PID)
    cHeater := ComputePID(cTemp, cSetpoint, cLastTime, cLastError, cCumError, cLastError, cCumError, cLastTime) > 0;
    mHeater := ComputePID(mTemp, mSetpoint, mLastTime, mLastError, mCumError, mLastError, mCumError, mLastTime) > 0;
    yHeater := ComputePID(yTemp, ySetpoint, yLastTime, yLastError, yCumError, yLastError, yCumError, yLastTime) > 0;
    kHeater := ComputePID(kTemp, kSetpoint, kLastTime, kLastError, kCumError, kLastError, kCumError, kLastTime) > 0;
    wHeater := ComputePID(wTemp, wSetpoint, wLastTime, wLastError, wCumError, wLastError, wCumError, wLastTime) > 0;

    // Comprobar niveles para alarmas
    alarmActive := FALSE;
    IF cLevelVal < LEVEL_CRITICAL THEN
        cAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSIF cLevelVal < LEVEL_WARNING THEN
        cAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSE
        cAlarmLed := FALSE;
    END_IF;

    IF mLevelVal < LEVEL_CRITICAL THEN
        mAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSIF mLevelVal < LEVEL_WARNING THEN
        mAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSE
        mAlarmLed := FALSE;
    END_IF;

    IF yLevelVal < LEVEL_CRITICAL THEN
        yAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSIF yLevelVal < LEVEL_WARNING THEN
        yAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSE
        yAlarmLed := FALSE;
    END_IF;

    IF kLevelVal < LEVEL_CRITICAL THEN
        kAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSIF kLevelVal < LEVEL_WARNING THEN
        kAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSE
        kAlarmLed := FALSE;
    END_IF;

    IF wLevelVal < LEVEL_CRITICAL THEN
        wAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSIF wLevelVal < LEVEL_WARNING THEN
        wAlarmLed := TRUE;
        alarmActive := TRUE;
    ELSE
        wAlarmLed := FALSE;
    END_IF;

    // Activar buzzer si hay alarma
    IF alarmActive THEN
        buzzer := TRUE;
    ELSE
        buzzer := FALSE;
    END_IF;

    // Control del agitador
    IF NOT agitatorButton THEN // Botón presionado (LOW por pull-up)
        agitator := AGITATOR_SPEED;
        led := TRUE;
    ELSE
        agitator := 0;
        led := FALSE;
    END_IF;

    // Enviar datos de sensores cada 5 segundos
    IF TIME_TO_REAL(TIME() - lastSend) > 5000.0 THEN
        lastSend := TIME();
        // Aquí se implementaría la lógica para enviar datos por puerto serial
        // Por ejemplo, escribir en un buffer serial (depende del PLC)
    END_IF;
END_METHOD
END_PROGRAM
