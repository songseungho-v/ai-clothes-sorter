import os
import shutil
import random

# ✅ 데이터셋 경로 설정
source_root = "학습용"
train_root = "data/train"
val_root = "data/val"
unused_root = "data/unused"

# ✅ 카테고리별 이미지 개수 설정 (없을 경우 기본값 800)
num = 1000
category_limits = {
    "니트": num,
    "맨투맨": num,
    "바지": num,
    "아우터": num,
    "얇은의류": num,
    "후드티": num,
    # "가디건": 10,
    # "맨투맨": 10,
    # "면바지": 10,
    # "반바지": 10,
    # "반팔셔츠": 10,
    # "반팔티": 10,
    # "블라우스": 10,
    # "셔츠": 10,
    # "스웨터": 10,
    # "원피스": 10,
    # "청바지": 10,
    # "후드티": 10
}

# ✅ Train/Val 비율 설정
train_ratio = 0.7

# ✅ 폴더 생성
os.makedirs(train_root, exist_ok=True)
os.makedirs(val_root, exist_ok=True)
os.makedirs(unused_root, exist_ok=True)

for category in os.listdir(source_root):
    category_path = os.path.join(source_root, category)
    if not os.path.isdir(category_path):
        continue

    images = [f for f in os.listdir(category_path) if f.endswith(('.jpg', '.png', '.jpeg'))]
    total_images = len(images)

    # ✅ 최대 이미지 수 적용
    max_images = category_limits.get(category, num)
    selected_images = images[:max_images]
    unused_images = images[max_images:]  # 나머지 이미지가 unused로 분류됨

    # ✅ Train/Val 분할
    random.shuffle(selected_images)
    train_count = int(len(selected_images) * train_ratio)
    train_images = selected_images[:train_count]
    val_images = selected_images[train_count:]

    # ✅ 카테고리별 폴더 생성
    train_category_path = os.path.join(train_root, category)
    val_category_path = os.path.join(val_root, category)
    unused_category_path = os.path.join(unused_root, category)
    os.makedirs(train_category_path, exist_ok=True)
    os.makedirs(val_category_path, exist_ok=True)
    os.makedirs(unused_category_path, exist_ok=True)

    # ✅ 이미지 이동
    for img in train_images:
        shutil.copy2(os.path.join(category_path, img), os.path.join(train_category_path, img))

    for img in val_images:
        shutil.copy2(os.path.join(category_path, img), os.path.join(val_category_path, img))

    for img in unused_images:
        shutil.copy2(os.path.join(category_path, img), os.path.join(unused_category_path, img))

    print(f"✅ {category}: Train({len(train_images)}개) / Val({len(val_images)}개) / Unused({len(unused_images)}개) 분할 완료!")

print("\n🚀 모든 데이터셋이 지정한 개수에 맞춰 Train/Val/Unused로 분할되었습니다!")
