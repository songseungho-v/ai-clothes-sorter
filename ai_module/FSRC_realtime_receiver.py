import cv2
import numpy as np
import paho.mqtt.client as mqtt
import base64
import json
import time
import math
from datetime import datetime
import threading
# 설정
MQTT_BROKER = "172.30.1.21"
MQTT_PORT = 1883
MQTT_TOPIC = "camera/frame/#"
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
# 디바이스별 프레임 저장소
latest_frames = {}  # device_id: (frame, distance)

#YOLOv8 모델 결과 저장 변수
resultDivide = "test1"
# MQTT 수신 콜백
def on_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) != 3:
        return
    device_id = topic_parts[2]

    try:
        data = json.loads(msg.payload.decode())
        b64_jpeg = data.get("frame")
        distance = data.get("distance")
        current_speed = data.get("current_speed")
        move_state = data.get("move_state")

        if not b64_jpeg:
            return

        jpg_bytes = base64.b64decode(b64_jpeg)
        jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

        if frame is not None:
            latest_frames[device_id] = {
                "frame": frame,
                "distance": distance,
                "current_speed": current_speed,
                "move_state": move_state
            }
        #명령 발신동작은?
    except Exception as e:
        print(f"[❌ 에러] 메시지 처리 중 오류: {e}")
# MQTT 명령 송신 함수 정의
def send_command_to_device(device_id, command):
    topic = f"image/command/{device_id}"
    client.publish(topic, command)
    print(f"📤 명령 전송됨 → {topic}: {command}")

# MQTT 초기화
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

def main():
    print("📺 디바이스별 실시간 영상 수신 대기 중...")
    try:
        while True:

            num_devices = len(latest_frames)
            if num_devices == 0:
                time.sleep(0.1)
                continue

            cols = math.ceil(math.sqrt(num_devices))
            rows = math.ceil(num_devices / cols)
            grid_image = np.zeros((rows * FRAME_HEIGHT, cols * FRAME_WIDTH, 3), dtype=np.uint8)

            for idx, (device_id, info) in enumerate(latest_frames.items()):
                frame = info["frame"]
                distance = info["distance"]
                current_speed = info["current_speed"]
                move_state = info["move_state"]
                r = idx // cols
                c = idx % cols

                label = f"{device_id} | {distance}cm | speed:{current_speed} | state:{move_state}"
                annotated = cv2.resize(frame.copy(), (FRAME_WIDTH, FRAME_HEIGHT))
                cv2.putText(annotated, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                y1 = r * FRAME_HEIGHT
                y2 = y1 + FRAME_HEIGHT
                x1 = c * FRAME_WIDTH
                x2 = x1 + FRAME_WIDTH
                grid_image[y1:y2, x1:x2] = annotated
                if not move_state and distance is not None and int(distance) < 30:
                    # active 명령전달
                    send_command_to_device(device_id, "on")

                elif move_state:
                    send_command_to_device(device_id, "off")
            cv2.imshow("📺 전체 디바이스 실시간 보기", grid_image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


    # threads = [
    #     threading.Thread(target=send_command_to_device_interface, args=(device_id), daemon = True)
    #     #threading.Thread(target=yoloDivideCapture, args=(device_id, frame) daemon = True),
    #     #threading.Thread(target=capture_image, args=(device_id, frame) daemon=True)
    # ]
    # for t in threads: t.start()
    except KeyboardInterrupt:
        print("🛑 종료 요청됨")

    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
# try:
#     while True:
#         for device_id, (frame, distance, current_speed, move_state) in latest_frames.items():
#             try:
#                 frame_copy = frame.copy()
#                 label = f"{device_id} | {distance}cm | speed:{current_speed} | state:{move_state}"
#                 cv2.putText(frame_copy, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
#                 cv2.imshow(device_id, frame_copy)
#             except Exception as e:
#                 print(f"[❌ 표시 오류] {device_id}: {e}")
#
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#         time.sleep(0.01)
#
# except KeyboardInterrupt:
#     print("\n🛑 프로그램 종료됨")
#
# finally:
#     client.loop_stop()
#     client.disconnect()
#     cv2.destroyAllWindows()