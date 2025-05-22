from datetime import datetime
import cv2
from shared_state import device_states, device_locks, last_command_sent, device_targets, send_command_to_device, SAVE_ROOT
from yolo_utils import analyze_frame
import time

DETECTION_INTERVAL = 3  # 초
last_detection_time = {}

# device_worker.py (최적화 개선 버전)

def device_worker(device_id):
    q = device_queues[device_id]
    target_label = device_targets.get(device_id)
    last_detection_time[device_id] = 0

    while True:
        try:
            data = q.get()
            frame = data["frame"]
            distance = data["distance"]
            move_state = data["move_state"]

            # 🔄 frame은 항상 저장 (실시간 표시용)
            with device_locks[device_id]:
                device_states[device_id] = data

            # 🔍 조건 충족 시에만 분석 수행
            if distance is None or int(distance) >= 30 or move_state:
                continue

            now = time.time()
            if now - last_detection_time[device_id] < DETECTION_INTERVAL:
                continue

            # 🔍 YOLO 분석 수행
            detections = analyze_frame(frame)
            data["detections"] = detections
            with device_locks[device_id]:
                device_states[device_id]["detections"] = detections

            command = "off"
            for det in detections:
                if det["label"] == target_label and det["score"] > 0.8:
                    command = "on"
                    _save_detection(frame, det, device_id)
                    last_detection_time[device_id] = now
                    break

            if command != last_command_sent.get(device_id):
                send_command_to_device(device_id, command)
                last_command_sent[device_id] = command

        except Exception as e:
            print(f"[❌ Worker Error] {device_id}: {e}")

def _save_detection(frame, det, device_id):
    label_dir = SAVE_ROOT / det["label"]
    label_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{device_id}_{timestamp}_{int(det['score'] * 100)}.jpg"
    path = label_dir / filename
    cv2.imwrite(str(path), frame)
    print(f"💾 저장됨: {path}")