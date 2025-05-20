import cv2, time, queue, threading, json
import numpy as np
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime

MQTT_BROKER = "172.30.1.21"
TOPIC_FRAME = "camera/frame"
TOPIC_COMMAND_PREFIX = "image/command/"
TOPIC_CAPTURE_PREFIX = "image/request/"
TOPIC_RESULT_PREFIX = "image/result/"
SAVE_DIR = Path("results"); SAVE_DIR.mkdir(exist_ok=True)

frame_queue = queue.Queue(maxsize=1)
capture_flag = False
last_result = None
model = YOLO("/Users/songseungho/Desktop/making program/Project_ai_clothes/ai-clothes-sorter/model_files/yolov8n_clothes.pt")
CLASS_NAMES = model.names

# MQTT 수신 핸들러
def on_message(client, userdata, msg):
    global capture_flag
    topic = msg.topic
    if topic.startswith(TOPIC_FRAME):
        if frame_queue.full(): frame_queue.get_nowait()
        frame_queue.put_nowait(msg.payload)
    elif topic.startswith(TOPIC_COMMAND_PREFIX):
        if msg.payload.decode() == "capture":
            capture_flag = True
            print(f"📥 분석 요청 수신 → {topic}")

client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe(TOPIC_FRAME)
client.subscribe("image/command/#")
client.loop_start()

# 분석 스레드
def analyzer_loop():
    global capture_flag, last_result
    while True:
        if not frame_queue.empty():
            jpg = frame_queue.get()
            frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if frame is None: continue

            if capture_flag:
                capture_flag = False
                print("🔍 YOLO 분석 시작")

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                detections = model.predict(source=frame, conf=0.5, verbose=False)[0].boxes

                best = None
                for box in detections:
                    cls = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                    category = CLASS_NAMES[cls]
                    save_folder = SAVE_DIR / (category if conf > 0.9 else "미분류")
                    save_folder.mkdir(exist_ok=True)
                    fname = f"{category}_{int(conf*100)}_{timestamp}.jpg"
                    cv2.imwrite(str(save_folder / fname), frame)
                    print(f"💾 저장됨: {save_folder / fname}")
                    if best is None or conf > best["score"]:
                        best = {"category": category, "score": conf}

                # 결과 전송
                device_id = msg.topic.split('/')[-1]
                result_topic = f"{TOPIC_RESULT_PREFIX}{device_id}"
                if best:
                    payload = json.dumps(best)
                    client.publish(result_topic, payload)
                    print(f"📤 결과 전송 → {result_topic} : {best}")
                else:
                    print("⚠️ 감지 없음")

        time.sleep(0.05)

threading.Thread(target=analyzer_loop, daemon=True).start()

print("✅ 분석 서버 실행 중...")
try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    client.loop_stop()
    print("🛑 서버 종료됨")