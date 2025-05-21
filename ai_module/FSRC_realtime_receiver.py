import cv2
import numpy as np
import paho.mqtt.client as mqtt
import base64
import json
import time
import math
import threading
from queue import Queue

# MQTT 설정
MQTT_BROKER = "172.30.1.21"
MQTT_PORT = 1883
MQTT_TOPIC = "camera/frame/#"

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

device_queues = {}
device_states = {}
lock = threading.Lock()

def send_command_to_device(device_id, command):
    topic = f"image/command/{device_id}"
    client.publish(topic, command)
    print(f"📤 명령 전송 → {topic}: {command}")

# 마지막 명령 상태 저장소
last_command_sent = {}

def device_worker(device_id):
    q = device_queues[device_id]
    while True:
        try:
            data = q.get()
            with lock:
                device_states[device_id] = data

            current_distance = data["distance"]
            current_state = data["move_state"]

            # 결정할 명령
            command = None
            if not current_state and current_distance is not None and int(current_distance) < 30:
                command = "on"
            elif current_state:
                command = "off"

            # 중복 방지 처리
            if command and last_command_sent.get(device_id) != command:
                send_command_to_device(device_id, command)
                last_command_sent[device_id] = command

        except Exception as e:
            print(f"[❌ 워커 에러] {device_id}: {e}")
def on_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) != 3:
        return
    device_id = topic_parts[2]

    try:
        data = json.loads(msg.payload.decode())
        b64_jpeg = data.get("frame")
        distance = data.get("distance")
        current_speed = data.get("current_speed")
        move_state = data.get("move_state")

        if not b64_jpeg:
            return

        jpg_bytes = base64.b64decode(b64_jpeg)
        jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

        if frame is not None:
            payload = {
                "frame": frame,
                "distance": distance,
                "current_speed": current_speed,
                "move_state": move_state
            }

            if device_id not in device_queues:
                device_queues[device_id] = Queue(maxsize=5)
                device_states[device_id] = payload
                threading.Thread(target=device_worker, args=(device_id,), daemon=True).start()

            q = device_queues[device_id]
            if q.full():
                q.get_nowait()
            q.put_nowait(payload)

    except Exception as e:
        print(f"[❌ 메시지 에러] {device_id}: {e}")

# MQTT 설정
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

def main_loop():
    print("📺 디바이스별 실시간 영상 수신 대기 중...")
    try:
        while True:
            with lock:
                num_devices = len(device_states)
                if num_devices == 0:
                    time.sleep(0.1)
                    continue

                cols = math.ceil(math.sqrt(num_devices))
                rows = math.ceil(num_devices / cols)
                grid_image = np.zeros((rows * FRAME_HEIGHT, cols * FRAME_WIDTH, 3), dtype=np.uint8)

                for idx, (device_id, info) in enumerate(device_states.items()):
                    frame = info["frame"]
                    distance = info["distance"]
                    current_speed = info["current_speed"]
                    move_state = info["move_state"]

                    r = idx // cols
                    c = idx % cols

                    label = f"{device_id} | {distance}cm | speed:{current_speed} | state:{move_state}"
                    annotated = cv2.resize(frame.copy(), (FRAME_WIDTH, FRAME_HEIGHT))
                    cv2.putText(annotated, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    y1 = r * FRAME_HEIGHT
                    y2 = y1 + FRAME_HEIGHT
                    x1 = c * FRAME_WIDTH
                    x2 = x1 + FRAME_WIDTH
                    grid_image[y1:y2, x1:x2] = annotated

                cv2.imshow("📺 전체 디바이스 실시간 보기", grid_image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("🛑 종료 요청됨")
    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main_loop()