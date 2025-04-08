from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
import paho.mqtt.client as mqtt
import json
import os
import threading

TOKEN = "ISI_DENGAN_TOKEN_BOT_MU"
MQTT_BROKER = "industrial.api.ubidots.com"
MQTT_PORT = 1883
MQTT_TOPIC_REQUEST = "sensor/request"
MQTT_TOPIC_RESPONSE = "sensor/response"
UBIDOTS_TOKEN = "ISI_DENGAN_TOKEN_UBIDOTS_MU"

app = Flask(__name__)
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

latest_data = {}

# MQTT Callback
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with result code "+str(rc))
    client.subscribe(MQTT_TOPIC_RESPONSE)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        latest_data['temperature'] = payload.get("temperature")
        latest_data['humidity'] = payload.get("humidity")
        print("Received:", latest_data)
    except Exception as e:
        print("MQTT Error:", e)

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(UBIDOTS_TOKEN, "")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

def mqtt_loop():
    mqtt_client.loop_forever()

threading.Thread(target=mqtt_loop).start()

# Telegram Command Handlers
def start(update, context):
    update.message.reply_text(
        "👋 Selamat datang!\n"
        "Ketik /cek_cuaca untuk mengetahui cuaca saat ini ☁️"
    )

def cek_cuaca(update, context):
    chat_id = update.message.chat_id
    latest_data.clear()
    mqtt_client.publish(MQTT_TOPIC_REQUEST, "request")

    def wait_for_data():
        for _ in range(10):  # Tunggu max 10 detik
            if 'temperature' in latest_data:
                temp = latest_data['temperature']
                hum = latest_data['humidity']
                bot.send_message(chat_id=chat_id, text=(
                    "⛅ Cuaca Saat Ini:\n"
                    f"🌡 Suhu: {temp}°C\n"
                    f"💦 Kelembaban: {hum}%"
                ))
                return
            time.sleep(1)
        bot.send_message(chat_id=chat_id, text="⚠️ Gagal mengambil data cuaca.")

    threading.Thread(target=wait_for_data).start()

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("cek_cuaca", cek_cuaca))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"
