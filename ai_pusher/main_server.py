import cv2
import numpy as np
import math
import time
import paho.mqtt.client as mqtt
from shared_state import device_states, device_locks
from mqtt_handler import on_message
import threading
MQTT_BROKER = "172.30.1.21"
MQTT_PORT = 1883
MQTT_TOPIC = "camera/frame/#"

FRAME_W, FRAME_H = 640, 480

def main_loop():
    print("📺 실시간 디바이스 영상 모니터링 시작...")
    while True:
        with threading.Lock():
            if not device_states:
                time.sleep(0.1)
                continue

            cols = math.ceil(math.sqrt(len(device_states)))
            rows = math.ceil(len(device_states) / cols)
            grid = np.zeros((rows * FRAME_H, cols * FRAME_W, 3), dtype=np.uint8)

            for idx, (device_id, info) in enumerate(device_states.items()):
                frame = info["frame"].copy()
                label = f"{device_id} | {info['distance']}cm | {info['current_speed']} | {info['move_state']}"
                cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
                r, c = divmod(idx, cols)
                grid[r*FRAME_H:(r+1)*FRAME_H, c*FRAME_W:(c+1)*FRAME_W] = cv2.resize(frame, (FRAME_W, FRAME_H))

            cv2.imshow("📡 전체 디바이스 실시간 보기", grid)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    client = mqtt.Client(protocol=mqtt.MQTTv5)
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()

    try:
        main_loop()
    finally:
        client.loop_stop()
        client.disconnect()