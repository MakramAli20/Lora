import base64
import json
import struct
import requests
import paho.mqtt.client as mqtt
from datetime import datetime


# ================= MQTT =================

MQTT_HOST = "192.168.0.110"
MQTT_PORT = 1883

TOPIC = "application/+/device/+/event/up"


# ================= API =================

API_URL = "https://hygienetech.tech/portal/api/sensors/reading"

DEVICE_TOKEN = "4fe8aa6c6f52df60843789ab3446718ba7b309cf90eb33eb1c6f6135a4a4dbf7"


# ================= Decode D20-LB =================

def decode_d20lb(payload: bytes):

    """
    Dragino D20-LB

    Byte 0-1 : Battery mV
    Byte 2-3 : Temperature /10
    """

    if len(payload) < 4:
        return None


    battery_mv = struct.unpack(">H", payload[0:2])[0]

    temp_raw = struct.unpack(">H", payload[2:4])[0]


    if temp_raw == 0x7FFF:

        temperature = None


    elif temp_raw & 0x8000:

        temperature = (temp_raw - 65536) / 10


    else:

        temperature = temp_raw / 10


    return {

        "battery": battery_mv / 1000,

        "temperature": temperature
    }



# ================= Send API =================

def send_temperature(temperature, battery, signal=0):


    if temperature is None:
        return


    payload = {

        "reading_type": "temperature",

        "temperature": round(temperature, 2),

        "temperature_unit": "celsius",

        "humidity": 0,

        "battery_level": round(battery * 100, 0),

        "signal_strength": signal,

        "timestamp":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    }


    headers = {

        "Authorization":
            "Bearer " + DEVICE_TOKEN,

        "Content-Type":
            "application/json"
    }


    try:

        r = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )


        print("API Response:", r.status_code)

        print(r.text)


    except Exception as e:

        print("API Error:", e)



# ================= MQTT =================

def on_connect(client, userdata, flags, rc, properties=None):

    if rc == 0:

        print("[OK] Connected MQTT")

        client.subscribe(TOPIC)

        print("[OK] Listening:", TOPIC)


    else:

        print("MQTT Error:", rc)



def on_message(client, userdata, msg):

    try:

        data = json.loads(
            msg.payload.decode()
        )


    except Exception as e:

        print("JSON Error:", e)

        return



    device_info = data.get(
        "deviceInfo",
        {}
    )


    device_name = device_info.get(
        "deviceName",
        "Unknown"
    )


    dev_eui = device_info.get(
        "devEui",
        "Unknown"
    )


    application_id = device_info.get(
        "applicationId",
        "Unknown"
    )



    encoded = data.get("data")


    if not encoded:

        return



    raw = base64.b64decode(encoded)


    result = decode_d20lb(raw)


    if not result:

        print(
            "Unknown payload:",
            raw.hex()
        )

        return



    temperature = result["temperature"]

    battery = result["battery"]



    print("-----------------------------")

    print("Application :", application_id)

    print("Device Name :", device_name)

    print("DevEUI      :", dev_eui)



    if temperature is None:

        print(
            "Temperature: Probe disconnected"
        )

        return


    else:

        print(
            f"Temperature: {temperature:.1f} °C"
        )


    print(
        f"Battery     : {battery:.2f} V"
    )



    # إرسال للـ API

    send_temperature(
        temperature,
        battery
    )




# ================= MAIN =================


def main():


    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    )


    client.on_connect = on_connect

    client.on_message = on_message



    client.connect(
        MQTT_HOST,
        MQTT_PORT,
        60
    )


    print("Waiting for sensors...")


    client.loop_forever()



if __name__ == "__main__":

    main()