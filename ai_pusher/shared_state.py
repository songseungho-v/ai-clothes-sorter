from pathlib import Path
import threading

# 디바이스 상태 저장소
device_queues = {}           # device_id: Queue
device_states = {}           # device_id: 최신 프레임 + 상태 정보
device_locks = {}            # device_id: threading.Lock()
last_command_sent = {}       # device_id: 마지막 명령
device_targets = {
    "raspi-01": "cell phone",
    "raspi-02": "청바지",
    "raspi-03": "치마",
}

SAVE_ROOT = Path("saved_images")
SAVE_ROOT.mkdir(exist_ok=True)

# MQTT 전송 함수
client = None  # mqtt_handler에서 set_client()로 설정

def set_client(mqtt_client):
    global client
    client = mqtt_client

def send_command_to_device(device_id, command):
    if client is None:
        raise RuntimeError("MQTT client not set in shared_state.")
    topic = f"image/command/{device_id}"
    client.publish(topic, command)
    print(f"📤 명령 전송 → {topic}: {command}")