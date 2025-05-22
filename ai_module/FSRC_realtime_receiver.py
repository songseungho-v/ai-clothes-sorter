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
device_modes = {
    "raspi-01": "detect",
    "raspi-02": "proximity",
    "raspi-03": "detect"
}
# 마지막 감지 시간 저장
last_detection_time = {}
DETECTION_INTERVAL = 3  # 초 단위
yolo_model = YOLO(YOLO_MODEL_PATH)
lock = threading.Lock()

last_saved_time = {}
DETECTION_SAVE_INTERVAL = 1.5  # 초 단위
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

def toggle_mode(device_id):
    current = device_modes.get(device_id, "detect")
    device_modes[device_id] = "proximity" if current == "detect" else "detect"
    print(f"🔄 {device_id} 모드 전환: {current} → {device_modes[device_id]}")

# ------------------ 워커 스레드 ------------------
def device_worker(device_id):
    q = device_queues[device_id]
    target_item = device_targets.get(device_id, None)
    mode = device_modes.get(device_id, "detect")
    while True:
        try:
            data = q.get()
            frame = data["frame"]
            distance = data["distance"]
            move_state = data["move_state"]
            now = time.time()

            if mode == "proximity":
                if distance is not None and int(distance) < 30:
                    # 저장 간격 제한
                    if now - last_saved_time.get(device_id, 0) >= DETECTION_INTERVAL:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        save_dir = SAVE_ROOT / "proximity"
                        save_dir.mkdir(parents=True, exist_ok=True)
                        filename = f"{device_id}_{timestamp}.jpg"
                        filepath = save_dir / filename
                        cv2.imwrite(str(filepath), frame)
                        print(f"📷 [PROXIMITY] 저장됨: {filepath}")
                        last_saved_time[device_id] = now

                with lock:
                    device_states[device_id] = {**data, "detections": []}
                continue  # 다음 루프로 이동

            # 30cm 이상일 경우 YOLO 추론 생략
            if distance is None or int(distance) >= 30 or move_state:
                with lock:
                    device_states[device_id] = {**data, "detections": []}
                # ✅ 현재 모터가 동작 중이면 무조건 "off" 명령 전송 고려
                if move_state and last_command_sent.get(device_id) != "off":
                    send_command_to_device(device_id, "off")
                    last_command_sent[device_id] = "off"
                continue
            # YOLO 분석
            detections = analyze_frame(frame)
            with lock:
                data["detections"] = detections
                device_states[device_id] = data

                # 감지 및 저장 여부 판단
                command = "off"
                for det in detections:
                    if not move_state and det["label"] == target_item and det["score"] > 0.8:
                        #print(f"[✅ 감지] {device_id}: {det['label']} {det['score']:.2f}")
                        command = "on"

                        # 이미지 저장

                        last_time = last_saved_time.get(device_id, 0)

                        if now - last_time >= DETECTION_SAVE_INTERVAL:
                            label_dir = SAVE_ROOT / det["label"]
                            label_dir.mkdir(parents=True, exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{device_id}_{timestamp}_{int(det['score'] * 100)}.jpg"
                            filepath = label_dir / filename
                            cv2.imwrite(str(filepath), frame)
                            print(f"💾 저장됨: {filepath}")
                            last_saved_time[device_id] = now
                        # else:
                        #     print(f"⏸️ 저장 생략: {device_id} - 감지 간격 {now - last_time:.2f}s")
                        break

                # 중복 명령 방지 후 송신
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

        # 거리 확인 (YOLO 수행 전에 조건 확인)
        distance = payload.get("distance")
        move_state = payload.get("move_state")
        current_speed = payload.get("current_speed")

        # 프레임 디코딩 (거리 조건을 확인한 후 진행)
        jpg_bytes = base64.b64decode(b64_jpeg)
        jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)
        if frame is None:
            return

        data = {
            "frame": frame,
            "distance": distance,
            "current_speed": current_speed,
            "move_state": move_state,
            "detections": []  # YOLO 결과는 device_worker에서 채움
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
                    distance = info.get("distance")
                    speed = info.get("current_speed")
                    state = info.get("move_state")

                    # 라벨 및 박스 추가
                    frame = draw_boxes(frame, detections)
                    mode = device_modes.get(device_id, "detect")
                    label = f"{device_id} | {distance}cm | speed:{speed} | state:{state} | mode:{mode}"
                    cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    r, c = divmod(idx, cols)
                    resized = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
                    y1, y2 = r * FRAME_HEIGHT, (r + 1) * FRAME_HEIGHT
                    x1, x2 = c * FRAME_WIDTH, (c + 1) * FRAME_WIDTH
                    grid_image[y1:y2, x1:x2] = resized

                cv2.imshow("📡 전체 디바이스 실시간 모니터링", grid_image)

            if cv2.waitKey(1) & 0xFF == ord('1'):
                toggle_mode("raspi-01")
            elif cv2.waitKey(1) & 0xFF == ord('2'):
                toggle_mode("raspi-02")
            elif cv2.waitKey(1) & 0xFF == ord('3'):
                toggle_mode("raspi-03")
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()

# ------------------ 실행 ------------------
if __name__ == "__main__":
    main_loop()