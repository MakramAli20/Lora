import base64
import json
import struct
import paho.mqtt.client as mqtt


MQTT_HOST = "192.168.0.110"
MQTT_PORT = 1883

# يستقبل كل الأجهزة داخل كل التطبيقات
TOPIC = "application/+/device/+/event/up"


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



def on_connect(client, userdata, flags, rc, properties=None):

    if rc == 0:
        print("[OK] Connected MQTT")

        client.subscribe(TOPIC)

        print("[OK] Listening:", TOPIC)

    else:
        print("MQTT Error:", rc)



def on_message(client, userdata, msg):

    try:
        data = json.loads(msg.payload.decode())

    except Exception as e:
        print("JSON Error:", e)
        return


    # معلومات الجهاز
    device_info = data.get("deviceInfo", {})

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


    # البيانات
    encoded = data.get("data")

    if not encoded:
        return


    raw = base64.b64decode(encoded)


    result = decode_d20lb(raw)

    if not result:
        print("Unknown payload:", raw.hex())
        return



    print("-----------------------------")

    print("Application :", application_id)

    print("Device Name :", device_name)

    print("DevEUI      :", dev_eui)


    if result["temperature"] is None:

        print(
            "Temperature: Probe disconnected"
        )

    else:

        print(
            f"Temperature: {result['temperature']:.1f} °C"
        )


    print(
        f"Battery     : {result['battery']:.2f} V"
    )



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