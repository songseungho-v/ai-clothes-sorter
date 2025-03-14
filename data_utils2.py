import os
import shutil
import random

# ✅ 데이터셋 경로 설정
source_root = "data"
train_root = "data/train"
val_root = "data/val"

# ✅ 카테고리별 이미지 개수 설정 (없을 경우 기본값 500)
category_limits = {
    "가디건": 10,
    "맨투맨": 10,
    "면바지": 10,
    "반바지": 10,
    "반팔셔츠": 10,
    "반팔티": 10,
    "블라우스": 10,
    "셔츠": 10,
    "스웨터": 10,
    "원피스": 10,
    "청바지": 10,
    "후드티": 10
}  # 필요하면 추가 가능

# ✅ Train/Val 비율 설정
train_ratio = 0.7

# ✅ Train/Val 폴더 생성
os.makedirs(train_root, exist_ok=True)
os.makedirs(val_root, exist_ok=True)

# ✅ 카테고리별 처리
for category in os.listdir(source_root):
    category_path = os.path.join(source_root, category)
    if not os.path.isdir(category_path):
        continue  # 폴더가 아닐 경우 스킵

    images = [f for f in os.listdir(category_path) if f.endswith(('.jpg', '.png', '.jpeg'))]
    total_images = len(images)

    # ✅ 설정된 개수 제한 적용
    max_images = category_limits.get(category, 10)  # 기본값 500
    images = images[:max_images]  # 최대 개수 제한 적용

    # ✅ Train/Val 분할
    random.shuffle(images)
    train_count = int(len(images) * train_ratio)

    train_images = images[:train_count]
    val_images = images[train_count:]

    # ✅ 카테고리별 폴더 생성
    train_category_path = os.path.join(train_root, category)
    val_category_path = os.path.join(val_root, category)
    os.makedirs(train_category_path, exist_ok=True)
    os.makedirs(val_category_path, exist_ok=True)

    # ✅ 이미지 이동
    for img in train_images:
        shutil.copy2(os.path.join(category_path, img), os.path.join(train_category_path, img))

    for img in val_images:
        shutil.copy2(os.path.join(category_path, img), os.path.join(val_category_path, img))

    print(f"✅ {category}: Train({len(train_images)}개) / Val({len(val_images)}개) 분할 완료!")

print("\n🚀 모든 데이터셋이 지정한 개수에 맞춰 Train/Val로 분할되었습니다!")
