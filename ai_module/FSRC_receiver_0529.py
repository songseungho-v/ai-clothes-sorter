import cv2, time, json, math, base64, threading
import numpy as np
from queue import Queue
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
import paho.mqtt.client as mqtt

# ------------------ 설정 ------------------
MQTT_BROKER = "172.30.1.88"
MQTT_PORT = 1883
MQTT_TOPIC = "camera/frame/#"
YOLO_MODEL_PATH = "yolov8n.pt"
FRAME_WIDTH, FRAME_HEIGHT = 640, 480
SAVE_INTERVAL = 1.5

device_queues = {}
device_states = {}
last_command_sent = {}
last_saved_time = {}
last_command_time = {}  # device_id별 마지막 명령 전송 시각
COMMAND_COOLDOWN = 0.5  # 최소 0.5초 유지
device_modes = {
    "raspi-01": "detect",
    "raspi-02": "proximity",
    "raspi-03": "detect"
}
device_targets = {
    "raspi-01": "cell phone",
    "raspi-02": "청바지",
    "raspi-03": "치마"
}

SAVE_ROOT = Path("saved_images")
SAVE_ROOT.mkdir(exist_ok=True)
yolo_model = YOLO(YOLO_MODEL_PATH)
lock = threading.Lock()

MODE_DETECT = "detect"
MODE_PROXIMITY = "proximity"

# ------------------ 유틸 함수 ------------------
def analyze_frame(frame):
    results = yolo_model.predict(source=frame, conf=0.5, verbose=False)
    detections = []
    if results:
        for box in results[0].boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            label = yolo_model.names[int(box.cls[0].item())]
            detections.append({
                "label": label,
                "score": float(box.conf[0].item()),
                "box": list(map(int, xyxy))
            })
    return detections

def draw_boxes(frame, detections):
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        color = (0, 255, 0) if det["score"] > 0.8 else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{det['label']} ({det['score']:.2f})", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame

def send_command_to_device(device_id, command):
    control_target_id = {
        "raspi-cam-01": "raspi-01",
        "raspi-cam-02": "raspi-02",
        "raspi-cam-03": "raspi-03"
    }.get(device_id, device_id)

    topic = f"image/command/{control_target_id}"
    client.publish(topic, command)
    print(f"📤 명령 전송 → {topic}: {command}")

def toggle_mode(device_id):
    before = device_modes.get(device_id, MODE_DETECT)
    after = MODE_PROXIMITY if before == MODE_DETECT else MODE_DETECT
    device_modes[device_id] = after
    print(f"🔄 {device_id} 모드 전환: {before} → {after}")

# ------------------ 디바이스 워커 ------------------
def device_worker(device_id):
    q = device_queues[device_id]
    target_item = device_targets.get(device_id.replace("cam-", ""), None)

    while True:
        try:
            data = q.get()
            frame = data.get("frame")
            distance = data.get("distance")
            move_state = data.get("move_state")
            now = time.time()

            with lock:
                mode = device_modes.get(device_id.replace("cam-", ""), MODE_DETECT)

            # cam이 포함된 디바이스는 분석 및 제어 수행
            if "cam" in device_id:
                if frame is None or distance is None:
                    continue

                if mode == MODE_PROXIMITY:
                    command = "on" if int(distance) < 30 else "off"

                    if command == "on" and now - last_saved_time.get(device_id, 0) >= SAVE_INTERVAL:
                        save_dir = SAVE_ROOT / "proximity"
                        save_dir.mkdir(parents=True, exist_ok=True)
                        filename = f"{device_id}_{datetime.now():%Y%m%d_%H%M%S}.jpg"
                        cv2.imwrite(str(save_dir / filename), frame)
                        print(f"📷 [PROXIMITY] 저장됨: {filename}")
                        last_saved_time[device_id] = now

                    with lock:
                        device_states[device_id] = {**data, "detections": []}

                    if command != last_command_sent.get(device_id):
                        send_command_to_device(device_id, command)
                        last_command_sent[device_id] = command
                    continue

                # DETECT 모드
                if mode == MODE_DETECT:
                    if move_state:
                        # 모터가 동작 중이면 명령 X
                        with lock:
                            device_states[device_id] = {**data, "detections": []}
                        continue
                if distance is None or int(distance) >= 30 or move_state:
                    with lock:
                        device_states[device_id] = {**data, "detections": []}
                    if move_state and last_command_sent.get(device_id) != "off":
                        send_command_to_device(device_id, "off")
                        last_command_sent[device_id] = "off"
                    continue
                detections = analyze_frame(frame)
                command = "off"
                for det in detections:
                    if det["label"] == target_item and det["score"] > 0.8:
                        command = "on"
                        if now - last_saved_time.get(device_id, 0) >= SAVE_INTERVAL:
                            label_dir = SAVE_ROOT / det["label"]
                            label_dir.mkdir(parents=True, exist_ok=True)
                            filename = f"{device_id}_{datetime.now():%Y%m%d_%H%M%S}_{int(det['score']*100)}.jpg"
                            cv2.imwrite(str(label_dir / filename), frame)
                            print(f"💾 저장됨: {filename}")
                            last_saved_time[device_id] = now
                        break

                with lock:
                    data["detections"] = detections
                    device_states[device_id] = data

                now = time.time()
                if now - last_command_time.get(device_id, 0) >= COMMAND_COOLDOWN and command != last_command_sent.get(
                        device_id):
                    send_command_to_device(device_id, command)
                    last_command_sent[device_id] = command
                    last_command_time[device_id] = now

            else:
                # cam이 없는 디바이스는 모터/센서 정보만 표시용
                with lock:
                    device_states[device_id] = data

        except Exception as e:
            print(f"[❌ 워커 에러] {device_id}: {e}")

# ------------------ MQTT 핸들러 ------------------
def on_message(client, _, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) != 3:
        return
    device_id = topic_parts[2]

    try:
        payload = json.loads(msg.payload.decode())
        data = {}

        if "cam" in device_id:
            b64 = payload.get("frame")
            if not b64:
                return
            frame = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                return
            data["frame"] = frame
            data["distance"] = payload.get("distance")
        else:
            data["move_state"] = payload.get("move_state")
            data["current_speed"] = payload.get("current_speed")

        data["detections"] = []

        if device_id not in device_queues:
            device_queues[device_id] = Queue(maxsize=5)
            threading.Thread(target=device_worker, args=(device_id,), daemon=True).start()

        q = device_queues[device_id]
        if q.full():
            q.get_nowait()
        q.put_nowait(data)

    except Exception as e:
        print(f"[❌ MQTT 메시지 에러] {device_id}: {e}")

# ------------------ MQTT 초기화 ------------------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

# ------------------ UI / 메인 루프 ------------------
def main_loop():
    print("📺 디바이스별 실시간 영상 수신 대기 중...")
    try:
        while True:
            key = cv2.waitKey(1) & 0xFF

            if key == ord('1'):
                toggle_mode("raspi-01")
            elif key == ord('2'):
                toggle_mode("raspi-02")
            elif key == ord('3'):
                toggle_mode("raspi-03")
            elif key == ord('q'):
                break

            with lock:
                cam_devices = {k: v for k, v in device_states.items() if "cam" in k}
                num = len(cam_devices)
                if num == 0:
                    time.sleep(0.1)
                    continue

                cols, rows = math.ceil(math.sqrt(num)), math.ceil(num / math.sqrt(num))
                canvas = np.zeros((rows * FRAME_HEIGHT, cols * FRAME_WIDTH, 3), dtype=np.uint8)

                for idx, (device_id, info) in enumerate(cam_devices.items()):
                    frame = draw_boxes(info["frame"].copy(), info.get("detections", []))
                    label = f"{device_id} | {info['distance']}cm | speed:{info.get('current_speed')} | state:{info.get('move_state')} | mode:{device_modes.get(device_id)}"
                    cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

                    r, c = divmod(idx, cols)
                    canvas[r*FRAME_HEIGHT:(r+1)*FRAME_HEIGHT, c*FRAME_WIDTH:(c+1)*FRAME_WIDTH] = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

                cv2.imshow("📡 cam 디바이스 모니터링", canvas)

    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()

# ------------------ 실행 ------------------
if __name__ == "__main__":
    main_loop()