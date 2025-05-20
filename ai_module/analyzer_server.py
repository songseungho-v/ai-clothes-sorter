import cv2
import numpy as np
import queue
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime
import json
import threading
import time
# ------------------- 설정 -------------------
MQTT_BROKER = "172.30.1.21"
TOPIC_PREFIX_FRAME = "image/request/"
TOPIC_PREFIX_COMMAND = "image/command/"
TOPIC_PREFIX_RESULT = "image/result/"
TOPIC_PREFIX_ACTION = "image/action/"

SAVE_DIR = Path("results")
UNCLASSIFIED_DIR = SAVE_DIR / "미분류"
SAVE_DIR.mkdir(exist_ok=True)
UNCLASSIFIED_DIR.mkdir(exist_ok=True)

# ------------------- 상태 -------------------
frame_queues = {}       # device_id: Queue
capture_flags = {}      # device_id: True/False
model = YOLO("/Users/songseungho/Desktop/making program/Project_ai_clothes/ai-clothes-sorter/model_files/yolov8n_clothes.pt")
CLASS_NAMES = model.names

# ------------------- MQTT 핸들러 -------------------
def on_message(client, userdata, msg):
    print(f"[MQTT 수신됨] 토픽: {msg.topic} | 크기: {len(msg.payload)} bytes")
    parts = msg.topic.split('/')
    if len(parts) != 3:
        return
    _, msg_type, device_id = parts

    if msg_type == "request":
        frame_queues.setdefault(device_id, queue.Queue(maxsize=1))
        q = frame_queues[device_id]
        if q.full():
            q.get_nowait()
        q.put_nowait(msg.payload)

    elif msg_type == "command":
        capture_flags[device_id] = True

client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe("image/request/#")
client.subscribe("image/command/#")
client.loop_start()

# ------------------- 분석 함수 -------------------
def detect(frame_bgr):
    results = model.predict(source=frame_bgr, conf=0.5, verbose=False)
    detections = []
    if results:
        for box in results[0].boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            cls_idx = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            category = CLASS_NAMES[cls_idx]
            x1, y1, x2, y2 = map(int, xyxy)
            detections.append({
                "category": category,
                "score": conf,
                "box": [x1, y1, x2, y2]
            })
    return detections

# ------------------- 처리 루프 -------------------
def processing_loop():
    while True:
        for device_id, q in frame_queues.items():
            if capture_flags.get(device_id, False) and not q.empty():
                capture_flags[device_id] = False
                jpg_bytes = q.get()
                jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
                frame_bgr = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)
                if frame_bgr is None:
                    continue

                detections = detect(frame_bgr)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                best = None
                for det in detections:
                    cat = det["category"]
                    score = det["score"]
                    folder = SAVE_DIR / (cat if score > 0.9 else "미분류")
                    folder.mkdir(exist_ok=True)
                    fname = f"{cat}_{int(score*100)}_{timestamp}.jpg"
                    cv2.imwrite(str(folder / fname), frame_bgr)
                    print(f"💾 저장됨: {folder / fname}")
                    if best is None or score > best["score"]:
                        best = det

                # 결과 전송
                if best:
                    result_topic = f"{TOPIC_PREFIX_RESULT}{device_id}"
                    client.publish(result_topic, json.dumps(best))
                    print(f"📤 결과 전송 → {result_topic}: {best['category']} ({best['score']:.2f})")

                    # 조건 만족 시 동작 명령
                    if best["category"] == "상의":
                        action_topic = f"{TOPIC_PREFIX_ACTION}{device_id}"
                        client.publish(action_topic, "start")
                        print(f"✅ '상의' 감지됨 → 동작 트리거 전송: {action_topic}")

threading.Thread(target=processing_loop, daemon=True).start()

print("✅ 분석 서버 실행 중... MQTT 수신 대기")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    client.loop_stop()
    print("🛑 종료됨")