import time
import network
import machine
import ujson as json
from machine import Pin
import dht
from umqtt.simple import MQTTClient

# =========================
# CONFIG
# =========================
WIFI_SSID = "RCA-A"
WIFI_PASS = "RCA@2024"

MQTT_HOST = "157.173.101.159"
MQTT_PORT = 1883

MQTT_USER = None
MQTT_PASS = None

DEVICE_ID = b"esp8266_tehilar"

TOPIC_DATA       = b"tehilar/esp8266/dht"
TOPIC_LED_SET    = b"tehilar/esp8266/led/set"
TOPIC_LED_STATUS = b"tehilar/esp8266/led/status"
TOPIC_STATUS     = b"iot/status/" + DEVICE_ID

PUBLISH_INTERVAL_SEC = 5
KEEPALIVE_SEC = 60
UNIX_OFFSET = 946684800  # MicroPython epoch(2000) → Unix(1970)

# =========================
# HARDWARE
# =========================
sensor = dht.DHT11(Pin(5))   # GPIO5 = D1
led = Pin(4, Pin.OUT)        # GPIO4 = D2
led.value(0)

client = None

def unix_time():
    return int(time.time() + UNIX_OFFSET)

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    try:
        wlan.config(pm=0xa11140)
    except:
        pass

    if not wlan.isconnected():
        print(":signal_strength: Connecting Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        start = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > 30000:
                raise RuntimeError("Wi-Fi timeout")
            time.sleep(0.3)

    print(":white_check_mark: Wi-Fi OK:", wlan.ifconfig()[0])
    return wlan

def publish_led_status():
    state = b"ON" if led.value() else b"OFF"
    client.publish(TOPIC_LED_STATUS, state, retain=True)
    print(":bulb: LED status:", state)

def mqtt_cb(topic, msg):
    if topic == TOPIC_LED_SET:
        cmd = msg.decode().strip().upper()
        print(":envelope_with_arrow: LED cmd:", cmd)
        led.value(1 if cmd in ("ON", "1", "TRUE") else 0)
        publish_led_status()

def mqtt_connect():
    c = MQTTClient(
        client_id=DEVICE_ID,
        server=MQTT_HOST,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASS,
        keepalive=KEEPALIVE_SEC
    )
    c.set_last_will(TOPIC_STATUS, b"offline", retain=True)
    c.set_callback(mqtt_cb)
    c.connect()

    c.publish(TOPIC_STATUS, b"online", retain=True)
    c.subscribe(TOPIC_LED_SET)

    print(":white_check_mark: MQTT connected:", MQTT_HOST)
    return c

# -------- BOOT --------
print("===================================")
print(":rocket: ESP8266 Bonnette starting…")
print("Broker:", MQTT_HOST, MQTT_PORT)
print("===================================")

try:
    wifi_connect()
    try:
        import ntptime
        ntptime.settime()
    except:
        pass

    client = mqtt_connect()
    publish_led_status()
except Exception as e:
    print(":x: Init failed:", e)
    time.sleep(3)
    machine.reset()

last_pub = time.ticks_ms()

# -------- LOOP --------
while True:
    try:
        client.check_msg()

        if time.ticks_diff(time.ticks_ms(), last_pub) >= PUBLISH_INTERVAL_SEC * 1000:
            last_pub = time.ticks_ms()

            sensor.measure()
            payload = {
                "owner": "Bonnette",
                "temperature": sensor.temperature(),
                "humidity": sensor.humidity(),
                "ts": unix_time()
            }

            client.publish(TOPIC_DATA, json.dumps(payload), retain=False)
            print(":white_check_mark: Published:", payload)

        time.sleep_ms(80)

    except Exception as e:
        print(":x: Loop error:", e)
        try:
            client.disconnect()
        except:
            pass

        time.sleep(2)
        try:
            wifi_connect()
            client = mqtt_connect()
            publish_led_status()
        except Exception as e2:
            print(":x: Reconnect failed:", e2)
            time.sleep(3)
            machine.reset()