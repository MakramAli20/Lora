const mqtt = require("mqtt");
const express = require("express");
const cors = require("cors");


const app = express();

app.use(cors());
app.use(express.json());


// MQTT ChirpStack
const MQTT_HOST = "mqtt://192.168.0.110:1883";

const TOPIC = "application/+/device/+/event/up";


// آخر بيانات وصلت
let devices = {};


// اتصال MQTT
const client = mqtt.connect(MQTT_HOST);


client.on("connect", () => {

    console.log("MQTT Connected");

    client.subscribe(TOPIC);

    console.log("Listening:", TOPIC);

});



client.on("message", (topic, message)=>{


    try {

        const data = JSON.parse(message.toString());


        const device = data.deviceInfo;


        const payload = Buffer.from(
            data.data,
            "base64"
        );


        // D20-LB decode
        const battery =
            payload.readUInt16BE(0) / 1000;


        const temp =
            payload.readUInt16BE(2) / 10;



        const result = {

            deviceName: device.deviceName,

            devEui: device.devEui,

            temperature: temp,

            battery: battery,

            time: new Date()

        };


        devices[device.devEui] = result;


        console.log(result);


    }

    catch(err){

        console.log(err);

    }


});



// API
app.get("/devices",(req,res)=>{

    res.json(devices);

});



// تشغيل السيرفر
app.listen(4000,()=>{

    console.log(
        "LoRa Server running on port 4000"
    );

});