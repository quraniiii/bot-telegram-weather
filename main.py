from flask import Flask, request
import telegram
import paho.mqtt.client as mqtt
import json
import threading
import time

app = Flask(__name__)

# Konfigurasi bot Telegram
TOKEN = "8003547224:AAF1EuUByjS1egXcYIOsBM-AgHSTLK_7jr0"
bot = telegram.Bot(token=TOKEN)

# Simpan chat_id dan flag sinkronisasi
latest_chat_id = None
latest_response = None
response_event = threading.Event()

# Konfigurasi MQTT
MQTT_BROKER = "industrial.api.ubidots.com"
MQTT_PORT = 1883
MQTT_TOPIC_REQUEST = "sensor/request"
MQTT_TOPIC_RESPONSE = "sensor/response"

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with result code " + str(rc))
    client.subscribe(MQTT_TOPIC_RESPONSE)

def on_message(client, userdata, msg):
    global latest_response
    try:
        payload = json.loads(msg.payload.decode())
        print("Dapat data dari sensor:", payload)
        latest_response = payload
        response_event.set()
    except Exception as e:
        print("Error parsing MQTT message:", e)

client.username_pw_set("BBUS-gjzkGarULmV4ovISufhQZRVsFDtcOt", "")
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Jalankan MQTT client di thread terpisah
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.start()

@app.route("/", methods=["POST"])
def webhook():
    global latest_chat_id
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    message = update.message

    if message and message.text:
        latest_chat_id = message.chat_id
        text = message.text.lower()

        if text == "/start":
            bot.send_message(chat_id=latest_chat_id, text="👋 Selamat datang! Ketik /cek_cuaca untuk mengetahui kondisi cuaca saat ini.")
        elif text == "/cek_cuaca":
            bot.send_message(chat_id=latest_chat_id, text="⏳ Mengambil data cuaca...")
            response_event.clear()
            client.publish(MQTT_TOPIC_REQUEST, "cek")

            if response_event.wait(timeout=10):  # Tunggu max 10 detik
                temp = latest_response.get("temperature", "N/A")
                hum = latest_response.get("humidity", "N/A")
                bot.send_message(
                    chat_id=latest_chat_id,
                    text=f"⛅ Cuaca Saat Ini:\n🌡 Suhu: {temp}°C\n💦 Kelembaban: {hum}%"
                )
            else:
                bot.send_message(chat_id=latest_chat_id, text="❌ Gagal mengambil data dari sensor.")
    return "OK"

if __name__ == "__main__":
    import keep_alive
    keep_alive.run()
    app.run(host="0.0.0.0", port=5000)
