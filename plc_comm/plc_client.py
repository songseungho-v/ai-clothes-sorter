# plc_comm/plc_client.py

def set_valve(on: bool):
    """
    Dummy function to simulate PLC valve control
    """
    print(f"[PLC] Valve set to: {on}")

def read_sensor() -> float:
    """
    Simulate reading a sensor value
    """
    return 4.5  # e.g. 4.5 bar
