from ai_module.inference import classify_image

def test_classify_image():
    dummy_bytes = b"fake image data"
    cat, conf, stat = classify_image(dummy_bytes)
    assert cat in ["상의", "하의", "아우터"]  # if random choice used
    assert 0.8 <= conf <= 0.99
    assert stat in ["양호", "보통", "손상"]
