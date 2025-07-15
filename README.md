# Advanced Color Mixing System for Industrial Applications

## 🧪 Overview

This project presents a modular and scalable **color mixing system** designed for **industrial environments**, combining **microcontroller-based control**, **computer vision**, and **dual communication protocols (UART and Modbus TCP)**. It is capable of managing CMYKW pigment dosing, real-time temperature regulation with PID control, and fluid level monitoring. The system features a Python-based GUI built with Tkinter and OpenCV for real-time color detection and conversion.

> Developed by Ing. Juan David Sandoval Valencia — ECCI University

---

## 🎯 Key Features

- 🎨 **Color Conversion and Detection**  
  Converts RGB ↔ CMYKW ↔ HSL with high precision. Real-time color detection via camera or image input using OpenCV.

- 🔧 **Microcontroller-Based Control**  
  Controls PWM-driven pumps, PID-regulated heating, and capacitive level sensing using platforms like **Arduino**, **ESP32**, or industrial **PLCs**.

- 🌡️ **Temperature Regulation**  
  PID control loop with tunable gains, ensuring thermal stability around setpoints (default: 30 °C).

- 💬 **Serial Communication Protocol**  
  Universal, lightweight UART-based protocol:  
  `C:xxx M:xxx Y:xxx K:xxx W:xxx\n`

- 🔌 **Modbus TCP Integration**  
  Industrial-grade communication for PLC/SCADA interfacing.

- 💻 **User Interface (GUI)**  
  Built with **Tkinter**, includes:
  - CMYKW/HSL sliders and color preview
  - Color history tracking
  - Predefined color palettes
  - Serial & Modbus configuration
  - Real-time data monitoring

---

## 🖥️ System Architecture

- **Hardware**: Arduino Uno / ESP32 / PLC  
- **Sensors**: LM35 (temperature), analog level sensors  
- **Actuators**: Peristaltic pumps, resistive heaters, buzzer, LED indicators  
- **Communication**: USB Serial (9600 baud), Modbus TCP  
- **Software Stack**:
  - Python 3.x (GUI)
  - OpenCV
  - Tkinter
  - PIL
  - pySerial / pymodbus

---

## 🧠 Control Algorithms

### RGB to CMYKW Conversion

```python
C' = 1 - R/255
M' = 1 - G/255
Y' = 1 - B/255
K  = min(C', M', Y')
```

### PID Control Formula

```
u(t) = Kp * e(t) + Ki ∫ e(t)dt + Kd * de(t)/dt
```

### PWM Mapping

```python
DCMYK = 255 * (1 - P/100)
DW = 255 * (P/100)
```

---

## 🧪 Experimental Validation

| Metric | Value |
|--------|-------|
| Color Conversion Error | 1.5% ± 0.3% |
| Temperature Stability | ±0.4 °C |
| Level Sensor Response Time | 80 ms ± 10 ms |
| Serial Latency | 35 ms ± 5 ms |

---

## 🚀 Getting Started

### Requirements

- Python ≥ 3.8
- Arduino IDE
- Required Python packages:
  ```bash
  pip install opencv-python tkinter pyserial pillow pymodbus
  ```

### Upload Firmware

Use the provided Arduino sketch (e.g., `Pinturas.ino`) to flash your microcontroller.

### Run the GUI

```bash
python chroma.py
```

Connect the hardware via USB serial or configure Modbus TCP.

---

## 📁 Repository Structure

```
📂color-mixing-system/
├── Pinturas.ino              # Arduino firmware
├── chroma.py                 # Python GUI
├── color_app_config.json     # GUI configuration
├── color_history.json        # Color log file
├── README.md                 # This file
└── Articulo_Pinturas.pdf     # Technical paper
```

---

## 🛡️ Safety & Environmental Notes

- Pumps are automatically disabled under low tank levels (<10%)
- Visual/auditory alarms for critical thresholds
- Designed to reduce ink waste by up to 15% compared to manual processes

---

## 🧩 Potential Improvements

- Web-based GUI (Flask, Grafana)
- Adaptive PID control (auto-tuning)
- Integration with CIECAM02 for perceptual color fidelity
- IoT/Cloud logging for industrial traceability

---

## 📜 License

This project is open-source and distributed under the MIT License.

---

## 📫 Contact

**Juan David Sandoval Valencia**  
📧 juandsandoval8@gmail.com  
🏫 ECCI University – Bogotá, Colombia
