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
from adafruit_mcp3xxx.mcp3008 import MCP3008
from adafruit_mcp3xxx.analog_in import AnalogIn

# GPIO 설정
PUL_PIN = 18
DIR_PIN = 27
STSP_PIN = 17
PULLEY_CIRCUM_MM = 125.66
STEPS_PER_REV = 200
MIN_DELAY = 0.0008

chip = gpiod.Chip("gpiochip4")
pul_line = chip.get_line(PUL_PIN)
dir_line = chip.get_line(DIR_PIN)
stsp_line = chip.get_line(STSP_PIN)
pul_line.request(consumer="gpio_output", type=gpiod.LINE_REQ_DIR_OUT)
dir_line.request(consumer="gpio_output", type=gpiod.LINE_REQ_DIR_OUT)
stsp_line.request(consumer="gpio_output", type=gpiod.LINE_REQ_DIR_OUT)
stsp_line.set_value(1)

# 상태 변수
sensor_thread_running = True
current_speed = 650
user_stop_requested = False
fsr_start_triggered = threading.Event()
fsr_end_triggered = threading.Event()
fsr_start_val = 0
fsr_end_val = 0
move_state = False

# SPI & MCP3008 초기화
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D5)
mcp = MCP3008(spi, cs)
fsr_start = AnalogIn(mcp, 0)
fsr_end = AnalogIn(mcp, 1)

# 터미널 설정
fd = sys.stdin.fileno()
original_term_settings = termios.tcgetattr(fd)
def enable_cbreak_mode(): tty.setcbreak(fd)
def restore_terminal(): termios.tcsetattr(fd, termios.TCSADRAIN, original_term_settings)

# MQTT 설정
cmd = "off"
DEVICE_ID = "raspi-01"
MQTT_BROKER = "172.30.1.88"
MQTT_PORT = 1883
MQTT_TOPIC = f"camera/frame/{DEVICE_ID}"
MQTT_TOPIC_SUBSCRIBE = f"image/command/{DEVICE_ID}"

client = mqtt.Client(protocol=mqtt.MQTTv5)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC_SUBSCRIBE)
client.loop_start()

def on_message(client, userdata, msg):
    global cmd
    if msg.topic.endswith(DEVICE_ID):
        cmd = msg.payload.decode()
        print(f"[MQTT 명령 수신] → {cmd}")

client.on_message = on_message

# 상태 송신 스레드
def state_send():
    try:
        while not user_stop_requested:
            payload = {
                "current_speed": current_speed,
                "move_state": move_state
            }
            client.publish(MQTT_TOPIC, json.dumps(payload))
            time.sleep(0.1)  # 10Hz 송신
    except Exception as e:
        print(f"[❌ 상태 송신 오류] {e}")

# FSR 감지 스레드
def fsr_monitor_loop():
    global fsr_start_val, fsr_end_val
    while sensor_thread_running:
        fsr_start_val = fsr_start.value
        fsr_end_val = fsr_end.value
        fsr_start_triggered.set() if fsr_start_val > 10000 else fsr_start_triggered.clear()
        fsr_end_triggered.set() if fsr_end_val > 10000 else fsr_end_triggered.clear()
        time.sleep(0.002)

# 속도 제어 스레드
def get_key(): return sys.stdin.read(1)
def speed_control_loop():
    global current_speed, sensor_thread_running, user_stop_requested
    print("⬆↑: 속도 증가, ⬇↓: 속도 감소, x: 종료")
    while sensor_thread_running:
        key = get_key()
        if key == 'x':
            user_stop_requested = True
            sensor_thread_running = False
            break
        elif key == '\x1b':
            get_key(); third = get_key()
            if third == 'A': current_speed += 5
            elif third == 'B': current_speed = max(1, current_speed - 5)
            print(f"⚙️ 속도 조절 → {current_speed} mm/s")

# 모터 펄스
def _pulse(delay):
    pul_line.set_value(1)
    time.sleep(delay / 2)
    pul_line.set_value(0)
    time.sleep(delay / 2)

# 인터럽트 기반 모터 이동
def move_distance_mm_interruptible(distance_mm, direction):
    global current_speed
    revs = distance_mm / PULLEY_CIRCUM_MM
    pulses = round(revs * STEPS_PER_REV)
    dir_line.set_value(0 if direction == "backward" else 1)
    print(f"\n▶ {direction.upper()} {distance_mm}mm 이동 시작")

    for _ in range(pulses):
        delay = max(MIN_DELAY, 1.0 / (STEPS_PER_REV / PULLEY_CIRCUM_MM * current_speed))
        if direction == "forward" and fsr_end_triggered.is_set():
            print("🟥 전진 중 FSR_END 감지 → 정지")
            return
        elif direction == "backward" and fsr_start_triggered.is_set():
            print("🟦 후진 중 FSR_START 감지 → 정지")
            return
        _pulse(delay)

# 메인 동작 루프
def repeat_motion_loop():
    global user_stop_requested, cmd, move_state
    print("⏳ 명령 대기 중...")

    while not user_stop_requested:
        print(f" 🔵 FSR_START: {fsr_start_val} | 🔴 FSR_END: {fsr_end_val}", end="\r")

        if cmd == "on":
            move_state = True
            try:
                stsp_line.set_value(1)
                print("\n✅ 명령 'on' 수신 → 후진 시작")
                move_distance_mm_interruptible(750, "backward")
                print("⏳ FSR_START 감지 대기...")
                fsr_start_triggered.wait()

                if user_stop_requested: break

                print("🟦 FSR_START 감지됨 → 전진 시작")
                move_distance_mm_interruptible(750, "forward")
                print("⏳ FSR_END 감지 대기...")
                fsr_end_triggered.wait()

                if user_stop_requested: break
                print("🟥 FSR_END 감지됨 → 루프 반복")
                stsp_line.set_value(0)
            finally:
                move_state = False
        time.sleep(0.05)

# 메인 함수
def main():
    global sensor_thread_running
    try:
        print("▶ 시작하려면 's' 입력:")
        if input().strip().lower() != 's':
            return

        enable_cbreak_mode()

        threads = [
            threading.Thread(target=fsr_monitor_loop, daemon=True),
            threading.Thread(target=speed_control_loop, daemon=True),
            threading.Thread(target=state_send, daemon=True)
        ]
        for t in threads:
            t.start()

        repeat_motion_loop()

    finally:
        sensor_thread_running = False
        restore_terminal()
        time.sleep(0.1)
        stsp_line.set_value(0)
        pul_line.release()
        dir_line.release()
        stsp_line.release()
        print("✅ 프로그램 종료")

if __name__ == "__main__":
    main()
