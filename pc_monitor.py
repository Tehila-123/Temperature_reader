#!/usr/bin/env python3
"""
PC-Side Monitor and MQTT Bridge
Reads temperature from Arduino serial port, displays it in real-time,
and publishes the reading to the MQTT broker at broker.benax.rw.

Dependencies:
    pip install pyserial paho-mqtt
"""

import os
import sys
import time
import json
import serial
import serial.tools.list_ports
import paho.mqtt.client as mqtt

# Ensure stdout supports UTF-8 on Windows to prevent UnicodeEncodeError with emojis/graphics
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# ==========================================
# CONFIGURATION
# ==========================================
BAUD_RATE = 9600
MQTT_BROKER = "broker.benax.rw"
MQTT_PORT = 1883
MQTT_TOPIC = "tehilar/esp8266/dht"  # Subscribed by the dashboard
CANDIDATE_NAME = "Ruzindana Tehila"
DEVICE_ID = "pc_serial_bridge_tehila"

# ANSI Colors for a premium CLI terminal dashboard
CLR_HEADER = "\033[95m"
CLR_OKBLUE = "\033[94m"
CLR_OKCYAN = "\033[96m"
CLR_OKGREEN = "\033[92m"
CLR_WARNING = "\033[93m"
CLR_FAIL = "\033[91m"
CLR_ENDC = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_UNDERLINE = "\033[4m"

# State variables
mqtt_connected = False
msg_count = 0
last_temp = 0.0
last_update_str = "N/A"

# ==========================================
# MQTT CALLBACKS
# ==========================================
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        draw_dashboard()
    else:
        mqtt_connected = False
        print(f"\n{CLR_FAIL}[MQTT] Connection failed with code {rc}{CLR_ENDC}")

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    draw_dashboard()

# ==========================================
# PORT DETECTOR
# ==========================================
def auto_detect_port():
    ports = list(serial.tools.list_ports.comports())
    # Try to find a port with Arduino or USB-Serial chip (CH340, FTDI, CP210x, PL2303) in description
    for p in ports:
        desc = p.description.lower()
        if any(keyword in desc for keyword in ["arduino", "ch340", "usb", "serial", "ftdi", "cp210", "prolific"]):
            return p.device
    # Fallback to the first available port if any
    if ports:
        return ports[0].device
    return None

# ==========================================
# DASHBOARD DRAWING
# ==========================================
def draw_dashboard(status_msg=None, is_error=False):
    # Clear screen (works on Windows & Unix terminals that support ANSI)
    os.system("cls" if os.name == "nt" else "clear")
    
    # Header Card
    print(f"{CLR_HEADER}=================================================================={CLR_ENDC}")
    print(f"{CLR_BOLD}  🌡️  TEMPERATURE DISPLAY & MQTT MONITORING SYSTEM  {CLR_ENDC}")
    print(f"{CLR_HEADER}=================================================================={CLR_ENDC}")
    
    # Metadata & Settings
    print(f"  {CLR_BOLD}Candidate Name:{CLR_ENDC}  {CLR_OKBLUE}{CANDIDATE_NAME}{CLR_ENDC}")
    print(f"  {CLR_BOLD}MQTT Broker:   {CLR_ENDC}  {CLR_OKCYAN}{MQTT_BROKER}:{MQTT_PORT}{CLR_ENDC}")
    print(f"  {CLR_BOLD}MQTT Topic:    {CLR_ENDC}  {CLR_OKCYAN}{MQTT_TOPIC}{CLR_ENDC}")
    
    # Status Badges
    mqtt_status = f"{CLR_OKGREEN}Connected{CLR_ENDC}" if mqtt_connected else f"{CLR_FAIL}Disconnected (Retrying...){CLR_ENDC}"
    print(f"  {CLR_BOLD}MQTT Status:   {CLR_ENDC}  {mqtt_status}")
    print(f"  {CLR_BOLD}Serial Port:   {CLR_ENDC}  {CLR_OKGREEN}{port_name} @ {BAUD_RATE} baud{CLR_ENDC}")
    print(f"{CLR_HEADER}------------------------------------------------------------------{CLR_ENDC}")
    
    # Telemetry Value Card
    print(f"  {CLR_BOLD}CURRENT TEMPERATURE READING:{CLR_ENDC}")
    print("")
    
    # Render temperature large
    if last_temp > 0.0:
        # Determine color code based on temperature threshold
        if last_temp < 18.0:
            temp_color = CLR_OKBLUE  # Cold
        elif last_temp < 28.0:
            temp_color = CLR_OKGREEN  # Room/Pleasant
        else:
            temp_color = CLR_FAIL  # Hot
            
        print(f"     {temp_color}{CLR_BOLD}[ {last_temp:.1f} °C ]{CLR_ENDC}")
        
        # Simple ASCII Bar Graph (e.g. 0 to 50 scale)
        bars = int(min(max(last_temp, 0), 50) / 2)
        bar_graph = "█" * bars + "░" * (25 - bars)
        print(f"     Progress: |{temp_color}{bar_graph}{CLR_ENDC}|")
    else:
        print(f"     {CLR_WARNING}[ Waiting for Serial data... ]{CLR_ENDC}")
        print("     Progress: |░░░░░░░░░░░░░░░░░░░░░░░░░|")
        
    print("")
    print(f"  {CLR_BOLD}Total Published:{CLR_ENDC}  {CLR_OKGREEN}{msg_count} packets{CLR_ENDC}")
    print(f"  {CLR_BOLD}Last Updated:   {CLR_ENDC}  {last_update_str}")
    print(f"{CLR_HEADER}=================================================================={CLR_ENDC}")
    
    # Footer Status Message
    if status_msg:
        color = CLR_FAIL if is_error else CLR_OKBLUE
        print(f"  {CLR_BOLD}Status:{CLR_ENDC} {color}{status_msg}{CLR_ENDC}")
    else:
        print(f"  {CLR_BOLD}Status:{CLR_ENDC} Running. Press Ctrl+C to exit.")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    # 1. Resolve Serial Port
    if len(sys.argv) > 1:
        port_name = sys.argv[1]
    else:
        port_name = auto_detect_port()
        
    if not port_name:
        print(f"{CLR_FAIL}{CLR_BOLD}Error: No serial ports detected!{CLR_ENDC}")
        print("Please connect the Arduino Uno and try again, or pass the port manually:")
        print("  python pc_monitor.py COM3")
        sys.exit(1)
        
    # 2. Setup MQTT Client
    client = mqtt.Client(client_id=DEVICE_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    print(f"[MQTT] Connecting to broker {MQTT_BROKER}...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()  # Run MQTT client in background thread
    except Exception as e:
        print(f"{CLR_WARNING}[MQTT] Initial connection failed: {e}. Will attempt auto-reconnect.{CLR_ENDC}")
        
    # 3. Setup Serial Connection
    print(f"[Serial] Opening port {port_name}...")
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=3)
        # Flush buffers
        ser.reset_input_buffer()
    except Exception as e:
        print(f"{CLR_FAIL}{CLR_BOLD}Error opening serial port {port_name}: {e}{CLR_ENDC}")
        client.loop_stop()
        sys.exit(1)
        
    # Draw initial blank dashboard
    draw_dashboard("System initialized. Awaiting first read...")
    
    # 4. Main Bridge Loop
    try:
        while True:
            # Read line from Arduino
            if ser.in_waiting > 0 or True: # True handles blocking read timeout
                try:
                    line = ser.readline()
                    if not line:
                        continue # Timeout with no data
                        
                    # Decode and parse
                    decoded = line.decode("utf-8").strip()
                    if not decoded:
                        continue
                        
                    # Attempt to parse float temperature
                    try:
                        temp_val = float(decoded)
                        
                        # Validate range to allow high diagnostic readings
                        if -100.0 <= temp_val <= 1000.0:
                            last_temp = temp_val
                            msg_count += 1
                            last_update_str = time.strftime("%H:%M:%S")
                            
                            # Compile standard JSON payload matching the dashboard requirements
                            payload = {
                                "owner": "Ruzindana Tehila",
                                "temperature": last_temp,
                                "humidity": 50.0, # default placeholder humidity as sensor is LM35
                                "ts": int(time.time())
                            }
                            
                            # Publish to MQTT (non-blocking)
                            if mqtt_connected:
                                client.publish(MQTT_TOPIC, json.dumps(payload), qos=0)
                                draw_dashboard(f"Received {last_temp}°C and published successfully.")
                            else:
                                draw_dashboard(f"Received {last_temp}°C (MQTT disconnected - dropped packet).", is_error=True)
                        else:
                            draw_dashboard(f"Ignored out-of-range value: {decoded}", is_error=True)
                            
                    except ValueError:
                        # Non-float messages (like boot debug prints from Arduino)
                        draw_dashboard(f"Arduino Print: {decoded}")
                        
                except serial.SerialException as se:
                    draw_dashboard(f"Serial connection lost: {se}", is_error=True)
                    time.sleep(2)
                    # Attempt to re-open serial port
                    try:
                        ser.close()
                        ser = serial.Serial(port_name, BAUD_RATE, timeout=3)
                        ser.reset_input_buffer()
                    except:
                        pass
                except Exception as ex:
                    draw_dashboard(f"Loop error: {ex}", is_error=True)
                    
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print(f"\n{CLR_OKBLUE}Terminating PC Monitor Bridge...{CLR_ENDC}")
    finally:
        # Cleanup
        try:
            ser.close()
        except:
            pass
        client.loop_stop()
        client.disconnect()
        print(f"{CLR_OKGREEN}Graceful exit completed.{CLR_ENDC}")
