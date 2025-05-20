import paho.mqtt.client as mqtt
import cv2
import numpy as np
import queue

MQTT_BROKER = "172.30.1.21"  # 라즈베리파이 IP로 변경
MQTT_TOPIC_FRAME = "camera/frame"

frame_queue = queue.Queue(maxsize=1)

# MQTT v5로 업데이트 (DeprecationWarning 제거)
def on_message(client, userdata, msg):
    if frame_queue.full():
        frame_queue.get_nowait()
    frame_queue.put_nowait(msg.payload)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe(MQTT_TOPIC_FRAME)
client.loop_start()

try:
    while True:
        if not frame_queue.empty():
            jpg_bytes = frame_queue.get()
            jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
            frame_rgb = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

            if frame_rgb is not None:
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                cv2.imshow('Raspberry Pi Camera', frame_rgb)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except KeyboardInterrupt:
    pass

finally:
    client.loop_stop()
    client.disconnect()
    cv2.destroyAllWindows()
