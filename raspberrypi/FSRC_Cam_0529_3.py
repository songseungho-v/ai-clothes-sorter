import sys, select, tty, termios, time
import cv2
from picamera2 import Picamera2
import paho.mqtt.client as mqtt
import numpy as np
import base64
import serial
import json
import threading

# MQTT 설정
MQTT_BROKER = "172.30.1.88"  # ⚠️ Pi Zero에서는 서버의 IP로 변경 필요
MQTT_TOPIC_FRAME = "camera/frame/raspi-cam-01"

# 카메라 및 거리 초기값
ExTime = 3000
AnGain = 7
latest_distance = 0
user_stop_requested = False

# MQTT 초기화
client = mqtt.Client(protocol=mqtt.MQTTv5)
client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

# 카메라 초기화
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}))
picam2.controls.ExposureTime = ExTime
picam2.controls.AnalogueGain = AnGain
picam2.start()
print("📸 카메라 시작됨")

# 카메라 프레임 송신 스레드
def camera_realtime():
    while not user_stop_requested:
        frame = picam2.capture_array()
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue
        b64_jpeg = base64.b64encode(jpeg.tobytes()).decode('utf-8')

        payload = {
            "distance": latest_distance,
            "current_speed": "0",
            "move_state": False,
            "frame": b64_jpeg
        }
        client.publish(MQTT_TOPIC_FRAME, json.dumps(payload))
        time.sleep(0.01)  # 약 100 FPS

# 거리 센서 스레드
def sensor_loop():
    global latest_distance
    try:
        ser = serial.Serial("/dev/ttyS0", 115200, timeout=1)
        while not user_stop_requested:
            if ser.in_waiting >= 9:
                bytes_read = ser.read(9)
                if bytes_read[0] == 0x59 and bytes_read[1] == 0x59:
                    latest_distance = bytes_read[2] + bytes_read[3] * 256
            time.sleep(0.001)
        ser.close()
    except Exception as e:
        print(f"[❌ 센서 오류] {e}")

# 키보드 비동기 입력
def get_key_nonblocking():
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    if dr:
        return sys.stdin.read(1)
    return None

# 터미널 모드 설정
def enable_cbreak_mode():
    tty.setcbreak(sys.stdin.fileno())

def restore_terminal_mode():
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original_term_settings)

# 거리 표시 및 노출/게인 제어 루프
def state_loop():
    global user_stop_requested, ExTime, AnGain
    print("⬆ a/s: 노출시간 조절 | d/f: Gain 조절 | x: 종료")
    prev_display = ""

    try:
        enable_cbreak_mode()
        while not user_stop_requested:
            distance_display = f"{latest_distance} cm" if latest_distance is not None else "---"
            if distance_display != prev_display:
                print(f"\r📏 거리: {distance_display}🔧 Ex:{ExTime} | Gain:{AnGain}", end="")
                prev_display = distance_display

            key = get_key_nonblocking()
            if key:
                if key == 'x':
                    user_stop_requested = True
                elif key == 'a':
                    ExTime += 100
                elif key == 's':
                    ExTime = max(100, ExTime - 100)
                elif key == 'd':
                    AnGain += 1
                elif key == 'f':
                    AnGain = max(1, AnGain - 1)
                picam2.set_controls({"ExposureTime": ExTime, "AnalogueGain": AnGain})

            time.sleep(0.1)
    finally:
        restore_terminal_mode()

# 메인 실행
def main():
    global original_term_settings
    original_term_settings = termios.tcgetattr(sys.stdin.fileno())

    try:
        print("▶ 시작하려면 's' 입력:")
        if input().strip().lower() != 's':
            print("⛔️ 's' 입력 안됨 → 종료")
            return

        print("✅ 시작됨. 스레드 가동 중...")

        threads = [
            threading.Thread(target=sensor_loop, daemon=True),
            threading.Thread(target=camera_realtime, daemon=True)
        ]
        for t in threads:
            t.start()

        state_loop()

    except KeyboardInterrupt:
        print("\n🛑 사용자 종료")

    finally:
        picam2.stop()
        client.loop_stop()
        client.disconnect()
        print("\n✅ 프로그램 종료")

if __name__ == "__main__":
    main()
