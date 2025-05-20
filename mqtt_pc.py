import paho.mqtt.client as mqtt
import time

MQTT_BROKER = "192.168.0.25"  # 라즈베리파이 IP 주소로 변경
MQTT_TOPIC_PUB = "from/pc"
MQTT_TOPIC_SUB = "from/pi"

# 메시지 수신 시 호출되는 함수
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"[라즈베리파이로부터 수신한 메시지]: {message}")

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)

client.subscribe(MQTT_TOPIC_SUB)
client.loop_start()

try:
    count = 0
    while True:
        message = f"안녕하세요 {count}"
        client.publish(MQTT_TOPIC_PUB, message)
        print(f"[라즈베리파이로 전송한 메시지]: {message}")
        count += 1
        time.sleep(5)

except KeyboardInterrupt:
    client.loop_stop()
    print("MQTT 통신 종료")
