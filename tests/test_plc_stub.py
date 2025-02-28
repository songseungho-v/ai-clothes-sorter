from plc_comm.plc_client import set_valve, read_pressure

def test_set_valve(capfd):
    set_valve(on=True)
    out, _ = capfd.readouterr()
    assert "[PLC STUB] Valve set to: True" in out

def test_read_pressure():
    p = read_pressure()
    assert p > 0.0
