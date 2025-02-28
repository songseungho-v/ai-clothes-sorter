# plc_comm/plc_client.py

def set_valve(on: bool):
    """
    Stub function to simulate PLC valve control
    """
    print(f"[PLC STUB] Valve set to: {on}")

def read_pressure() -> float:
    """
    Stub to simulate reading pressure sensor
    """
    # Pretend we have 4.2 bar
    return 4.2

def move_conveyor(speed: float):
    """
    Stub to simulate conveyor motor
    """
    print(f"[PLC STUB] Conveyor speed set to {speed} m/s")
