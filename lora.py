#!/usr/bin/env python3
"""
Read temperature from a Dragino D20-LB sensor via local ChirpStack (MQTT).

Requirements:
    pip install paho-mqtt --break-system-packages

Flow:
    LPS8N (Gasteway) --> Locsal ChirpStack --> MQTT (localhost:1883) --> this script
"""

import base64
import json
import struct

import paho.mqtt.client as mqtt

# ==================== Settings you need to edit ====================
MQTT_HOST = "localhost"   # same machine ChirpStack is running on
MQTT_PORT = 1883
MQTT_USER = None           # local ChirpStack has no auth by default
MQTT_PASS = None

APPLICATION_ID = "925a5447-f887-4b5e-9bd2-ea9cab4ee0b0"  # from the Application page in ChirpStack (UUID)
DEV_EUI = "a840411358619d85"                              # DevEUI in lowercase

# ChirpStack v4 topic format:
TOPIC = f"application/{APPLICATION_ID}/device/{DEV_EUI}/event/up"
# =====================================================================


def decode_d20lb(payload: bytes):
    """
    Decode Dragino D20-LB payload (FPORT=2)
    Byte0-1: Battery (mV)
    Byte2-3: Temperature (signed, /10)  -> 0x7FFF means probe not connected
    Byte4  : Status byte (alarm bits / probe state)
    """
    if len(payload) < 4:
        return None

    battery_mv = struct.unpack(">H", payload[0:2])[0]

    temp_raw = struct.unpack(">H", payload[2:4])[0]
    if temp_raw == 0x7FFF:
        temperature = None  # probe not connected
    elif temp_raw & 0x8000:
        temperature = (temp_raw - 65536) / 10.0
    else:
        temperature = temp_raw / 10.0

    return {
        "battery_v": battery_mv / 1000.0,
        "temperature_c": temperature,
    }


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Connected to MQTT ({MQTT_HOST}:{MQTT_PORT})")
        client.subscribe(TOPIC)
        print(f"[OK] Listening on: {TOPIC}")
    else:
        print(f"[FAIL] Connection failed, code: {rc}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print("Error parsing JSON:", e)
        return

    # ChirpStack v4 message structure:
    # { "deviceInfo": {...}, "data": "base64...", "fPort": 2, "fCnt": ..., "rxInfo": [...] }
    b64_payload = data.get("data")
    fport = data.get("fPort", 2)

    if not b64_payload:
        return

    raw = base64.b64decode(b64_payload)
    result = decode_d20lb(raw)

    if result is None:
        print("Payload too short or unexpected:", raw.hex())
        return

    if result["temperature_c"] is None:
        print(f"[FPORT {fport}] Probe not connected | Battery: {result['battery_v']:.2f}V")
    else:
        print(
            f"[FPORT {fport}] Temperature: {result['temperature_c']:.1f}°C "
            f"| Battery: {result['battery_v']:.2f}V"
        )


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    print("Waiting for new readings from the sensor... (Ctrl+C to exit)")
    client.loop_forever()


if __name__ == "__main__":
    main()