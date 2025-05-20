import cv2
import numpy as np
import paho.mqtt.client as mqtt
import queue
import base64
import json

# 설정
DEVICE_ID = "raspi-01"
MQTT_BROKER = "172.30.1.21"
MQTT_PORT = 1883
MQTT_TOPIC = f"camera/frame/{DEVICE_ID}"
# 프레임 수신 큐
frame_queue = queue.Queue(maxsize=1)


# MQTT 메시지 수신 콜백
def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())

    #거리값
    distance = data.get("distance")
    print(f"거리 수신 : {distance}cm")
    #base64 -> jpeg -> queue
    b64_jpeg = data.get("frame")
    if frame_queue.full():
        frame_queue.get_nowait()
    frame_queue.put_nowait(base64.b64decode(b64_jpeg))


# MQTT 초기화
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

print("📺 수신 대기 중...")

try:
    while True:
        if not frame_queue.empty():
            jpg_bytes = frame_queue.get()
            jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

            if frame is not None:
                cv2.imshow("Raspberry Pi Live Feed", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except KeyboardInterrupt:
    print("\n🛑 종료됨")

finally:
    client.loop_stop()
    client.disconnect()
    cv2.destroyAllWindows()