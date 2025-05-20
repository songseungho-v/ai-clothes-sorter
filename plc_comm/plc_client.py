# plc_comm/plc_client.py
import time

# 카테고리별 모터 작동까지 대기 시간 (예시)
PLC_DELAY = {
    "상의": 2.0,
    "하의": 2.0,
    "치마": 2.0,
    "아우터": 2.0,
    # 필요시 다른 카테고리를 추가/수정 가능
}


def connect_plc():
    """
    실제 PLC 연결 로직(예: Modbus, TCP/IP 등)을 구성해야 합니다.
    여기서는 스텁(가짜) 함수로 대체.
    """
    print("[PLC_STUB] PLC에 연결 완료 (Stub).")


def motor_on_for_1sec():
    """
    실제 모터 ON 신호를 PLC에 전송하고 1초간 대기 후 OFF 신호를 보내는 스텁.
    """
    print("[PLC_STUB] 모터 ON (1초).")
    time.sleep(1.0)
    print("[PLC_STUB] 모터 OFF.")


def control_plc_motor(category):
    """
    1) category별로 PLC_DELAY 시간을 대기
    2) motor_on_for_1sec()를 호출해 모터를 1초 작동
    """
    delay_time = PLC_DELAY.get(category, 2.0)
    print(f"→ [PLC_STUB] '{category}' 감지됨, {delay_time}초 후 모터 1초 동작 예정")
    time.sleep(delay_time)
    motor_on_for_1sec()
