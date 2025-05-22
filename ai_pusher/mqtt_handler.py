import json
import base64
import cv2
from queue import Queue
import threading
from shared_state import device_queues, device_states, device_locks
from device_worker import device_worker
import numpy as np
def on_message(client, userdata, msg):
    from shared_state import set_client  # 순환 방지용 지연 import
    set_client(client)

    parts = msg.topic.split("/")
    if len(parts) != 3: return
    device_id = parts[2]

    try:
        payload = json.loads(msg.payload.decode())
        b64_jpeg = payload.get("frame")
        if not b64_jpeg: return

        jpg = base64.b64decode(b64_jpeg)
        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None: return

        data = {
            "frame": frame,
            "distance": payload.get("distance"),
            "current_speed": payload.get("current_speed"),
            "move_state": payload.get("move_state"),
        }

        if device_id not in device_queues:
            q = Queue(maxsize=5)
            device_queues[device_id] = q
            device_states[device_id] = data
            device_locks[device_id] = threading.Lock()
            threading.Thread(target=device_worker, args=(device_id, q), daemon=True).start()
        q = device_queues[device_id]
        if q.full(): q.get_nowait()
        q.put_nowait(data)

    except Exception as e:
        print(f"[❌ MQTT Error] {device_id}: {e}")