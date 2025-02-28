import random

def classify_image(image_bytes: bytes) -> (str, float, str):
    categories = ["상의", "하의", "아우터"]
    statuses = ["양호", "보통", "손상"]
    cat = random.choice(categories)
    stat = random.choice(statuses)
    conf = round(random.uniform(0.8, 0.99), 2)
    return (cat, conf, stat)
