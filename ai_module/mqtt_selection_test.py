# 디버깅 강화 버전: 이미지 수신 + YOLO 분석 + 저장 + 로깅 전체 포함
import cv2
import numpy as np
import queue
import json
import base64
from pathlib import Path
from datetime import datetime
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from verify_decode import verify_and_decode_image
# -------- YOLO 모델 로딩 --------
yolo_model = YOLO("/Users/songseungho/Desktop/making program/Project_ai_clothes/ai-clothes-sorter/model_files/yolov8n_clothes.pt")
detection_class_names = yolo_model.names

# -------- MQTT 설정 --------
MQTT_BROKER = "172.30.1.21"
MQTT_TOPIC_FRAME = "image/#"
MQTT_TOPIC_RESULT = "camera/result"
EXPECTED_CATEGORY = "상의"

frame_queue = queue.Queue(maxsize=1)

def on_message(client, userdata, msg):
    print(f"[MQTT 수신됨] 토픽: {msg.topic} | 크기: {len(msg.payload)} bytes")
    if frame_queue.full():
        frame_queue.get_nowait()
    frame_queue.put_nowait(msg.payload)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe(MQTT_TOPIC_FRAME)
client.loop_start()

def detect_with_yolo(frame_bgr, conf_thres=0.5):
    results = yolo_model.predict(source=frame_bgr, conf=conf_thres, verbose=False)
    dets = []
    if len(results) > 0:
        boxes_data = results[0].boxes
        for box in boxes_data:
            xyxy = box.xyxy[0].cpu().numpy()
            cls_idx = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = xyxy
            cat = detection_class_names[cls_idx]
            dets.append({
                "box": (x1, y1, x2, y2),
                "category": cat,
                "score": conf
            })
    return dets

# -------- 디렉토리 설정 --------
SAVE_DIR = Path.cwd() / "results"
FAIL_DIR = SAVE_DIR / "_unmatched"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
FAIL_DIR.mkdir(parents=True, exist_ok=True)

try:
    while True:
        if not frame_queue.empty():
            jpg_bytes = frame_queue.get()
            print(f"🖼️ 수신된 이미지 크기: {len(jpg_bytes)} bytes")
            verify_and_decode_image(jpg_bytes)
            # 디코딩 시도
            jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame_rgb = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

            if frame_rgb is None:
                print("❌ 이미지 디코딩 실패: frame_rgb is None")
                continue

            print(f"✅ 이미지 디코딩 성공: shape={frame_rgb.shape}")

            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            # YOLO 감지
            detections = detect_with_yolo(frame_bgr)
            print(f"📦 YOLO 결과 개수: {len(detections)}")

            matched = False
            category = "unknown"
            for i, det in enumerate(detections):
                print(f"🔍 [{i}] 분류: {det['category']} ({det['score']:.2f})")
                if det["category"] == EXPECTED_CATEGORY:
                    matched = True
                category = det["category"]

            # 저장 파일 이름 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{category}_{timestamp}.jpg"

            # 감지 결과에 따라 저장 위치 분기
            if matched:
                save_path = SAVE_DIR / category
                save_path.mkdir(exist_ok=True)
                filepath = save_path / filename
                cv2.imwrite(str(filepath), frame_bgr)
                print(f"💾 [매치됨] 저장됨: {filepath}")
                client.publish(MQTT_TOPIC_RESULT, "OK")
                print("✅ '상의' 감지됨 → OK 전송")
            else:
                failpath = FAIL_DIR / filename
                cv2.imwrite(str(failpath), frame_bgr)
                print(f"⚠️ [매치 실패] 저장됨: {failpath}")

except KeyboardInterrupt:
    print("🛑 중단됨 (Ctrl+C)")
finally:
    client.loop_stop()
    client.disconnect()
    cv2.destroyAllWindows()
