# Temperature Display and MQTT Monitoring System

This project is a complete Embedded Systems software integration that reads temperature from a physical digital sensor (DHT11) using an Arduino Uno, displays it alongside the candidate's name on a 16x2 Liquid Crystal Display (LCD) via an I2C adapter module, transmits the data via Serial to a PC-side bridge, and publishes the telemetry to an MQTT broker.

The dashboard can then subscribe to the MQTT topic to plot the temperature in real time.

---

## 📋 Table of Contents
1. [System Flow & Architecture](#-system-flow--architecture)
2. [Hardware Connections](#-hardware-connections)
3. [Communication Specifications](#-communication-specifications)
4. [Arduino Uno Setup](#-arduino-uno-setup)
5. [PC Bridge Setup & Execution](#-pc-bridge-setup--execution)
6. [Dashboard Setup](#-dashboard-setup)

---

## 🏗️ System Flow & Architecture

```
[DHT11 Temp Sensor] 
       │
       ▼ (Digital DATA Pin 7)
 [Arduino Uno] ──► [16x2 I2C LCD Display] (Displays Name & Temp)
       │
       ▼ (USB Serial @ 9600 Baud)
  [PC Bridge] (Python Script)
       │
       ▼ (MQTT over TCP Port 1883)
[broker.benax.rw] (MQTT Broker)
       │
       ▼ (MQTT over WebSockets Port 9001/443)
 [Web Dashboard] (Real-time HTML & Charts)
```

```mermaid
graph TD
    subgraph Hardware ["Microcontroller System"]
        Sensor["Temperature Sensor (DHT11)"] -->|Digital DATA Pin 7| Arduino["Arduino Uno"]
        Arduino -->|I2C Interface A4/A5| LCD["16x2 I2C LCD Display"]
    end

    subgraph PC ["PC-Side Client"]
        Arduino -->|USB Serial (COM / 9600 baud)| PythonBridge["PC Program (Python Bridge)"]
    end

    subgraph Infrastructure ["Broker & Dashboard"]
        PythonBridge -->|MQTT TCP (Port 1883)| Broker["Mosquitto MQTT Broker (broker.benax.rw)"]
        Broker -->|MQTT WebSockets| Dashboard["HTML Dashboard (Paho JS)"]
    end

    style Arduino fill:#00979C,stroke:#333,stroke-width:2px,color:#fff
    style PythonBridge fill:#3776AB,stroke:#333,stroke-width:2px,color:#fff
    style Broker fill:#3C5280,stroke:#333,stroke-width:2px,color:#fff
    style Dashboard fill:#FF6F00,stroke:#333,stroke-width:2px,color:#fff
```

---

## 🔌 Hardware Connections

### 1. DHT11 Sensor to Arduino Uno
| DHT11 Module Pin | Description | Arduino Pin |
|---|---|---|
| **VCC** | Power Input (+5V or +3.3V) | `5V` |
| **GND** | Ground Reference | `GND` |
| **DATA** | Digital Data Output | `Digital Pin 7` |

### 2. 16x2 LCD Display with I2C Module to Arduino Uno
| I2C Module Pin | Description | Arduino Pin |
|---|---|---|
| **GND** | Ground Reference | `GND` |
| **VCC** | Power Input (+5V) | `5V` |
| **SDA** | I2C Serial Data | `A4` |
| **SCL** | I2C Serial Clock | `A5` |

*(Note: On newer Arduino Uno boards, you can also use the dedicated SCL and SDA pins located next to the AREF pin).*

---

## 📡 Communication Specifications

### 1. Serial Connection
* **Interface**: USB Serial (virtual COM port)
* **Baud Rate**: `9600`
* **Configuration**: 8 data bits, no parity, 1 stop bit (8N1)
* **Data Format**: Plain float value with one decimal place followed by a newline (e.g. `24.5\n`) transmitted every 2 seconds.

### 2. MQTT Topic & Broker
* **Broker Host**: `broker.benax.rw`
* **TCP Port (PC Bridge)**: `1883`
* **WebSockets Port (Web Dashboard)**: `9001` or `8083` or `443` (depending on network policies)
* **Publish Topic**: `tehilar/esp8266/dht` (maps to client dashboard)
* **Message Payload**: JSON formatted string:
  ```json
  {
    "owner": "Ruzindana Tehila",
    "temperature": 24.5,
    "humidity": 50.0,
    "ts": 1781682342
  }
  ```

---

## 💻 Arduino Uno Setup

1. **Open** `temperature_reader.ino` in the Arduino IDE.
2. Install the **DHT Sensor Library** by Adafruit:
   - Go to **Sketch > Include Library > Manage Libraries...**
   - Search for **DHT sensor library** (by Adafruit) and click **Install**. 
   - *Select "Install all" if it asks to install dependencies like Adafruit Unified Sensor.*
3. Install the **LiquidCrystal_I2C** library:
   - Search for **LiquidCrystal_I2C** (by Frank de Brabander) and click **Install**.
4. Connect your Arduino Uno to your PC using the USB-A to USB-B cable.
5. Select the board: **Tools > Board > Arduino Uno**.
6. Select the port: **Tools > Port > (Select the COM port of your board)**.
7. Click **Upload** (Ctrl + U).
8. Once uploaded, open the **Serial Monitor** (Ctrl + Shift + M) set to `9600 baud` to verify temperature data is printed every 2 seconds.

> [!NOTE]
> *Candidate Name Display*: The name on the LCD is configured as `"Ruzindana Tehila"`. Since it is exactly 16 characters, it will display statically on Row 1. If you change `CANDIDATE_NAME` in the sketch to a name longer than 16 characters, the board will automatically start scrolling it horizontally.
> *I2C Address*: The code defaults to the standard address `0x27`. If the LCD backlight turns on but no text appears, your module might use address `0x3F` instead. You can update `LCD_I2C_ADDRESS` in the sketch config accordingly.

---

## 🐍 PC Bridge Setup & Execution

The PC-side program reads temperature values from the serial port and publishes them to the MQTT broker.

### Prerequisites
Make sure Python 3.x is installed on your PC. You will need to install the dependencies:

```bash
pip install pyserial paho-mqtt
```

### Running the Monitor
To start the monitoring program, open a terminal (PowerShell or Command Prompt) and run:

```bash
python pc_monitor.py
```

The script features **automatic port detection** and will attempt to find your Arduino. If you have multiple devices connected, you can specify the COM port manually:

```bash
python pc_monitor.py COM3
```

### Real-Time Terminal Dashboard
Upon connection, the terminal opens a premium, interactive CLI dashboard displaying:
- **Broker and Port** details
- **MQTT Connectivity status** (with automatic reconnection handling)
- **Serial Port details**
- **Real-time temperature card** with an **ASCII progress bar** and temperature-sensitive coloring (Cold is blue, Normal is green, Hot is red)
- **Cumulative packet count** and **last updated timestamp**

---

## 📊 Dashboard Setup

To visualize the temperature readings in real time:

1. Open the file `Dashboard/dashboard.html` in your web browser.
2. Edit the MQTT parameters in the `<script>` tag of `dashboard.html` if they point to the old IP broker. Make sure they point to your broker:
   ```javascript
   const WS_HOST = "broker.benax.rw";
   const WS_PORT = 9001; // Change to your WebSockets port if different
   const TOPIC_DATA = "tehilar/esp8266/dht";
   ```
3. The dashboard will automatically connect, subscribe to the topic, display the current temperature/humidity values, and plot them in a real-time line chart.
