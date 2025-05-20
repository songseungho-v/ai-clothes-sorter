# 분석 서버용 코드: 실시간 프레임 수신 + "capture" 명령 수신 시 YOLO 분석 수행
import cv2
import numpy as np
import queue
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime

# -------- 설정 --------
MQTT_BROKER = "172.30.1.21"
TOPIC_FRAME = "camera/frame"
TOPIC_COMMAND = "camera/command/raspi-01"
TOPIC_RESULT = "camera/result/raspi-01"
EXPECTED_CATEGORY = "상의"

frame_queue = queue.Queue(maxsize=1)
capture_flag = False

# -------- YOLO 모델 --------
model = YOLO("/Users/songseungho/Desktop/making program/Project_ai_clothes/ai-clothes-sorter/model_files/yolov8n_clothes.pt")
CLASS_NAMES = model.names

SAVE_DIR = Path("results")
FAIL_DIR = SAVE_DIR / "_unmatched"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
FAIL_DIR.mkdir(parents=True, exist_ok=True)

# -------- MQTT 핸들러 --------
def on_message(client, userdata, msg):
    global capture_flag

    if msg.topic == TOPIC_FRAME:
        if frame_queue.full():
            frame_queue.get_nowait()
        frame_queue.put_nowait(msg.payload)

    elif msg.topic == TOPIC_COMMAND:
        command = msg.payload.decode()
        print(f"📩 명령 수신: {command}")
        if command == "capture":
            capture_flag = True

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe(TOPIC_FRAME)
client.subscribe(TOPIC_COMMAND)
client.loop_start()

# -------- YOLO 분석 --------
def detect(frame_bgr):
    results = model.predict(source=frame_bgr, conf=0.5, verbose=False)
    detections = []
    if len(results) > 0:
        for box in results[0].boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            cls_idx = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = xyxy
            category = CLASS_NAMES[cls_idx]
            detections.append({
                "category": category,
                "score": conf,
                "box": (x1, y1, x2, y2)
            })
    return detections

# -------- 메인 루프 --------
try:
    while True:
        if not frame_queue.empty():
            jpg_bytes = frame_queue.get()
            jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame_rgb = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

            if frame_rgb is None:
                print("❌ JPEG 디코딩 실패")
                continue

            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            cv2.imshow("Live Stream", frame_rgb)

            if capture_flag:
                print("📸 캡처 명령 감지됨 → YOLO 분석 시작")
                capture_flag = False

                detections = detect(frame_bgr)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if detections:
                    match = any(d["category"] == EXPECTED_CATEGORY for d in detections)
                    category = detections[0]["category"]
                    save_path = SAVE_DIR / category
                    save_path.mkdir(exist_ok=True)
                    filename = f"{category}_{timestamp}.jpg"
                    cv2.imwrite(str(save_path / filename), frame_bgr)
                    print(f"💾 저장됨: {save_path/filename}")
                    if match:
                        client.publish(TOPIC_RESULT, "OK")
                        print("✅ 상의 감지됨 → OK 전송")
                else:
                    filename = f"unmatched_{timestamp}.jpg"
                    cv2.imwrite(str(FAIL_DIR / filename), frame_bgr)
                    print(f"⚠️ 감지 실패 → 저장됨: {FAIL_DIR/filename}")

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except KeyboardInterrupt:
    print("🛑 종료됨")
finally:
    client.loop_stop()
    client.disconnect()
    cv2.destroyAllWindows()
