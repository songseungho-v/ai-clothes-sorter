import cv2
import numpy as np
import paho.mqtt.client as mqtt
import base64
import json
import time
import math
import threading
from queue import Queue
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime
# ------------------ 설정 ------------------
MQTT_BROKER = "172.30.1.21"
MQTT_PORT = 1883
MQTT_TOPIC = "camera/frame/#"
#YOLO_MODEL_PATH = "/Users/songseungho/Desktop/making program/Project_ai_clothes/ai-clothes-sorter/model_files/yolov8n_clothes.pt"
YOLO_MODEL_PATH = "yolov8n.pt"
FRAME_WIDTH, FRAME_HEIGHT = 640, 480
SAVE_ROOT = Path("saved_images")
SAVE_ROOT.mkdir(exist_ok=True)
device_queues = {}         # device_id: Queue
device_states = {}         # device_id: latest info
last_command_sent = {}     # device_id: last sent command
device_targets = {         # 감지 대상 클래스
    "raspi-01": "cell phone",
    "raspi-02": "청바지",
    "raspi-03": "치마"
}
# 마지막 감지 시간 저장
last_detection_time = {}
DETECTION_INTERVAL = 3  # 초 단위
yolo_model = YOLO(YOLO_MODEL_PATH)
lock = threading.Lock()

# ------------------ 유틸 함수 ------------------
def analyze_frame(frame):
    results = yolo_model.predict(source=frame, conf=0.5, verbose=False)
    detections = []
    if results:
        for box in results[0].boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            cls_idx = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            label = yolo_model.names[cls_idx]
            detections.append({
                "label": label,
                "score": conf,
                "box": list(map(int, xyxy))
            })
    return detections

def draw_boxes(frame, detections):
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        label = f"{det['label']} ({det['score']:.2f})"
        color = (0, 255, 0) if det["score"] > 0.8 else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame

def send_command_to_device(device_id, command):
    topic = f"image/command/{device_id}"
    client.publish(topic, command)
    print(f"📤 명령 전송 → {topic}: {command}")

# ------------------ 워커 스레드 ------------------
def device_worker(device_id):
    q = device_queues[device_id]
    target_item = device_targets.get(device_id, None)

    while True:
        try:
            data = q.get()
            frame = data["frame"]
            distance = data["distance"]
            move_state = data["move_state"]

            detections = analyze_frame(frame)
            with lock:
                data["detections"] = detections
                device_states[device_id] = data

            command = "off"
            saved = False

            if distance is not None and int(distance) < 30:
                for det in detections:
                    if not move_state and det["label"] == target_item and det["score"] > 0.8:
                        print(f"[✅ 감지] {device_id}: {det['label']} {det['score']:.2f}")
                        command = "on"
                        saved = True
                        label_dir = SAVE_ROOT / det["label"]
                        label_dir.mkdir(parents=True, exist_ok=True)

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{device_id}_{timestamp}_{int(det['score']*100)}.jpg"
                        filepath = label_dir / filename
                        cv2.imwrite(str(filepath), frame)
                        print(f"💾 저장됨: {filepath}")
                        break

            if command != last_command_sent.get(device_id):
                send_command_to_device(device_id, command)
                last_command_sent[device_id] = command

        except Exception as e:
            print(f"[❌ 워커 에러] {device_id}: {e}")

# ------------------ MQTT 콜백 ------------------
def on_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) != 3:
        return
    device_id = topic_parts[2]

    try:
        payload = json.loads(msg.payload.decode())
        b64_jpeg = payload.get("frame")
        if not b64_jpeg:
            return

        frame = cv2.imdecode(np.frombuffer(base64.b64decode(b64_jpeg), dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return

        data = {
            "frame": frame,
            "distance": payload.get("distance"),
            "current_speed": payload.get("current_speed"),
            "move_state": payload.get("move_state"),
            "detections": []
        }

        if device_id not in device_queues:
            device_queues[device_id] = Queue(maxsize=5)
            threading.Thread(target=device_worker, args=(device_id,), daemon=True).start()

        q = device_queues[device_id]
        if q.full():
            q.get_nowait()
        q.put_nowait(data)

    except Exception as e:
        print(f"[❌ 메시지 에러] {device_id}: {e}")

# ------------------ MQTT 연결 ------------------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

# ------------------ 메인 디스플레이 루프 ------------------
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
                    frame = info["frame"].copy()
                    detections = info.get("detections", [])
                    frame = draw_boxes(frame, detections)

                    label = f"{device_id} | {info['distance']}cm | speed:{info['current_speed']} | state:{info['move_state']}"
                    cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    r, c = divmod(idx, cols)
                    resized = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
                    y1, y2 = r * FRAME_HEIGHT, (r + 1) * FRAME_HEIGHT
                    x1, x2 = c * FRAME_WIDTH, (c + 1) * FRAME_WIDTH
                    grid_image[y1:y2, x1:x2] = resized

                cv2.imshow("📡 전체 디바이스 실시간 모니터링", grid_image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()

# ------------------ 실행 ------------------
if __name__ == "__main__":
    main_loop()