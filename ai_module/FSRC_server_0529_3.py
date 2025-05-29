import cv2
import time
import json
import math
import base64
import threading
import numpy as np
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
import paho.mqtt.client as mqtt
from queue import Queue

# ------------------ 설정 ------------------
MQTT_BROKER = "172.30.1.88"
MQTT_PORT = 1883
MQTT_TOPIC = "camera/frame/#"
YOLO_MODEL_PATH = "yolov8n.pt"
FRAME_WIDTH, FRAME_HEIGHT = 640, 480
SAVE_INTERVAL = 1.5

MODE_DETECT = "detect"
MODE_PROXIMITY = "proximity"

device_modes = {
    "raspi-01": MODE_DETECT,
    "raspi-02": MODE_PROXIMITY,
    "raspi-03": MODE_DETECT
}
device_targets = {
    "raspi-01": "cell phone",
    "raspi-02": "청바지",
    "raspi-03": "치마"
}

yolo_model = YOLO(YOLO_MODEL_PATH)
SAVE_ROOT = Path("saved_images")
SAVE_ROOT.mkdir(exist_ok=True)
lock = threading.Lock()

# ------------------ 디바이스 핸들러 클래스 ------------------
class DeviceHandler:
    def __init__(self, device_id, is_cam_device):
        self.device_id = device_id
        self.queue = Queue(maxsize=1)
        self.state = {}
        self.last_command = None
        self.last_saved_time = 0
        self.target = device_targets.get(device_id.replace("cam-", ""), None)
        self.is_cam = is_cam_device
        self.mode = device_modes.get(device_id.replace("cam-", ""), MODE_DETECT)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def update_data(self, data):
        if not self.queue.empty():
            self.queue.get_nowait()
        self.queue.put_nowait(data)

    def send_command(self, command):
        control_target_id = {
            "raspi-cam-01": "raspi-01",
            "raspi-cam-02": "raspi-02",
            "raspi-cam-03": "raspi-03"
        }.get(self.device_id, self.device_id)
        if command != self.last_command:
            topic = f"image/command/{control_target_id}"
            client.publish(topic, command)
            print(f"[📤 명령 전송] → {topic}: {command}")
            self.last_command = command

    def run(self):
        while True:
            try:
                data = self.queue.get()
                now = time.time()
                frame = data.get("frame")
                distance = data.get("distance")
                move_state = data.get("move_state")

                if self.is_cam:
                    if frame is None or distance is None:
                        continue

                    if self.mode == MODE_PROXIMITY:
                        command = "on" if int(distance) < 30 else "off"
                        if command == "on" and now - self.last_saved_time >= SAVE_INTERVAL:
                            path = SAVE_ROOT / "proximity"
                            path.mkdir(parents=True, exist_ok=True)
                            filename = f"{self.device_id}_{datetime.now():%Y%m%d_%H%M%S}.jpg"
                            cv2.imwrite(str(path / filename), frame)
                            print(f"[📷 저장됨] {filename}")
                            self.last_saved_time = now
                        self.send_command(command)
                        self.state = {**data, "detections": []}
                        continue

                    # detect 모드
                    if int(distance) >= 30 or move_state:
                        if move_state:
                            self.send_command("off")
                        self.state = {**data, "detections": []}
                        continue

                    detections = analyze_frame(frame)
                    command = "off"
                    for det in detections:
                        if det["label"] == self.target and det["score"] > 0.8:
                            command = "on"
                            if now - self.last_saved_time >= SAVE_INTERVAL:
                                path = SAVE_ROOT / det["label"]
                                path.mkdir(parents=True, exist_ok=True)
                                filename = f"{self.device_id}_{datetime.now():%Y%m%d_%H%M%S}_{int(det['score']*100)}.jpg"
                                cv2.imwrite(str(path / filename), frame)
                                print(f"[💾 저장됨] {filename}")
                                self.last_saved_time = now
                            break

                    self.state = {**data, "detections": detections}
                    self.send_command(command)

                else:
                    self.state = data  # 모터/센서 전용

            except Exception as e:
                print(f"[❌ 워커 에러] {self.device_id}: {e}")

# ------------------ YOLO 분석 ------------------
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

# ------------------ MQTT 핸들러 ------------------
handlers = {}
def draw_boxes(frame, detections):
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        color = (0, 255, 0) if det["score"] > 0.8 else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{det['label']} ({det['score']:.2f})", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame
def on_message(client, _, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) != 3:
        return
    device_id = topic_parts[2]
    is_cam = "cam" in device_id

    try:
        payload = json.loads(msg.payload.decode())
        data = {}

        if is_cam:
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

        if device_id not in handlers:
            handlers[device_id] = DeviceHandler(device_id, is_cam)

        handlers[device_id].update_data(data)

    except Exception as e:
        print(f"[❌ MQTT 메시지 에러] {device_id}: {e}")

# ------------------ MQTT 초기화 ------------------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

# ------------------ UI 메인 루프 ------------------
def main_loop():
    print("📺 실시간 모니터링 시작")
    try:
        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            cam_handlers = {k: h for k, h in handlers.items() if h.is_cam and "frame" in h.state}

            if not cam_handlers:
                time.sleep(0.1)
                continue

            cols = math.ceil(math.sqrt(len(cam_handlers)))
            rows = math.ceil(len(cam_handlers) / cols)
            canvas = np.zeros((rows * FRAME_HEIGHT, cols * FRAME_WIDTH, 3), dtype=np.uint8)

            for idx, (device_id, handler) in enumerate(cam_handlers.items()):
                info = handler.state
                frame = info["frame"].copy()
                detections = info.get("detections", [])
                frame = draw_boxes(frame, detections)
                label = f"{device_id} | {info.get('distance')}cm | state:{info.get('move_state')} | mode:{handler.mode}"
                cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

                r, c = divmod(idx, cols)
                canvas[r*FRAME_HEIGHT:(r+1)*FRAME_HEIGHT, c*FRAME_WIDTH:(c+1)*FRAME_WIDTH] = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            cv2.imshow("📡 디바이스 모니터링", canvas)

    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()

# ------------------ 실행 ------------------
if __name__ == "__main__":
    main_loop()