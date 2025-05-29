import gpiod
import time
import cv2
import numpy as np
import serial
import threading
import sys
import termios
import tty
import busio
import digitalio
import board
import paho.mqtt.client as mqtt
import json
import base64
from picamera2 import Picamera2

ExTime = 3000
AnGain = 7

# SPI & MCP3008 초기화
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D5)

def on_message(client, userdata, msg):
    global cmd
    if msg.topic.endswith(DEVICE_ID):
        cmd = msg.payload.decode()

#MQTT 설정
DEVICE_ID = "raspi-01"
MQTT_BROKER = "172.30.1.21"  # 서버의 IP 주소로 변경하세요
MQTT_PORT = 1883
MQTT_TOPIC = f"camera/frame/{DEVICE_ID}"
MQTT_TOPIC_SUBSCRIBE = f"image/command/{DEVICE_ID}"

# MQTT 연결
client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC_SUBSCRIBE)
client.loop_start()

# 카메라 초기화
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}))
picam2.controls.ExposureTime = ExTime
picam2.controls.AnalogueGain = AnGain
picam2.start()
time.sleep(2)

print("📡 실시간 영상 전송 시작...")

#실시간 영상 전송 스레드
def camera_realtime():
        try:
            while True:
                # 프레임 캡처
                frame = picam2.capture_array()
                ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                if not ret:
                        continue

                # JPEG 바이트 -> Base64 인코딩
                b64_jpeg = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                # JSON 메세지 구성
                payload = {
                        "distance": latest_distance,
                        "current_speed":current_speed,
                        "move_state":move_state,
                        "frame" : b64_jpeg
                }

                client.publish(MQTT_TOPIC, json.dumps(payload))
                time.sleep(0.01)  # 약 20 FPS

        except KeyboardInterrupt:
            print("\n🛑 종료됨")

        finally:
            picam2.stop()
            client.loop_stop()
            client.disconnect()

# 라이다 센서 스레드
def sensor_loop():
    global latest_distance, sensor_thread_running
    ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=1)
    while sensor_thread_running:
        try:
            if ser.in_waiting >= 9:
                bytes_read = ser.read(9)
                if bytes_read[0] == 0x59 and bytes_read[1] == 0x59:
                    latest_distance = bytes_read[2] + bytes_read[3] * 256
        except: pass
        time.sleep(0.001)
    ser.close()

# 메인 함수
def main():
    global sensor_thread_running
    try:
        print("▶ 시작하려면 's' 입력:")
        if input().strip().lower() != 's':
            return
        enable_cbreak_mode()
        threads = [
            threading.Thread(target=sensor_loop, daemon=True),
            threading.Thread(target=camera_realtime, daemon=True)
        ]
        for t in threads: t.start()
        repeat_motion_loop()
    finally:
        sensor_thread_running = False
        time.sleep(0.1)
        restore_terminal()
        stsp_line.set_value(0)
        pul_line.release()
        dir_line.release()
        stsp_line.release()
        print("✅ 프로그램 종료")

if __name__ == "__main__":
    main()
