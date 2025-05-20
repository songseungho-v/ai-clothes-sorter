import os
import shutil
import random
import hashlib
from multiprocessing import Pool, cpu_count
import cv2
import imagehash
from PIL import Image

# ✅ 경로 설정
BASE_FOLDER = "raw_data/중복제거Image/"
DUPLICATE_FOLDER = os.path.join(BASE_FOLDER, "중복된이미지")
TRAIN_FOLDER = "data/train"
VAL_FOLDER = "data/val"

# ✅ 카테고리 폴더 리스트
def get_categories(base_folder):
    return [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f)) and f != "중복된이미지"]

# ✅ 카테고리 수에 따른 샘플 개수 설정
def get_sample_count(category_count):
    if category_count <= 5:
        return 300
    elif category_count <= 10:
        return 500
    elif category_count <= 20:
        return 700
    else:
        return 1000

# ✅ 폴더 준비
def prepare_dirs(categories):
    os.makedirs(DUPLICATE_FOLDER, exist_ok=True)
    for split_dir in [TRAIN_FOLDER, VAL_FOLDER]:
        os.makedirs(split_dir, exist_ok=True)
        for category in categories:
            os.makedirs(os.path.join(split_dir, category), exist_ok=True)

# ✅ 해시 기반 중복 제거 함수 (MD5 + pHash)
def remove_duplicates(category):
    folder_path = os.path.join(BASE_FOLDER, category)
    duplicate_path = os.path.join(DUPLICATE_FOLDER, category)
    os.makedirs(duplicate_path, exist_ok=True)

    hash_dict = {}
    phash_dict = {}
    images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    for img in images:
        img_path = os.path.join(folder_path, img)

        # MD5 해시 체크
        with open(img_path, 'rb') as f:
            img_hash = hashlib.md5(f.read()).hexdigest()

        # 완전 동일한 이미지 제거
        if img_hash in hash_dict:
            print(f"🛑 [MD5 중복 제거] {img} ↔ {hash_dict[img_hash]}")
            shutil.move(img_path, os.path.join(duplicate_path, img))
            continue

        # Perceptual Hash (pHash) 체크
        img_phash = imagehash.phash(Image.open(img_path))
        found_duplicate = False

        for other_img, other_phash in phash_dict.items():
            if img_phash - other_phash <= 3:  # 허용 오차 (5 이하로 설정)
                print(f"🛑 [pHash 중복 제거] {img} ↔ {other_img}")
                shutil.move(img_path, os.path.join(duplicate_path, img))
                found_duplicate = True
                break

        if not found_duplicate:
            hash_dict[img_hash] = img
            phash_dict[img] = img_phash

    print(f"✅ [{category}] 폴더에서 중복 제거 완료! 남은 이미지: {len(phash_dict)}개")

# ✅ train/val 분할 및 복사
def split_data(categories):
    sample_per_category = get_sample_count(len(categories))
    train_per_category = int(sample_per_category * 0.7)
    val_per_category = sample_per_category - train_per_category

    for category in categories:
        src_dir = os.path.join(BASE_FOLDER, category)
        images = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.shuffle(images)

        selected_images = images[:sample_per_category] if len(images) >= sample_per_category else images
        train_images = selected_images[:train_per_category]
        val_images = selected_images[train_per_category:]

        for img in train_images:
            shutil.copy2(os.path.join(src_dir, img), os.path.join(TRAIN_FOLDER, category, img))
        for img in val_images:
            shutil.copy2(os.path.join(src_dir, img), os.path.join(VAL_FOLDER, category, img))

        print(f"✅ {category}: Train({len(train_images)}개) / Val({len(val_images)}개) 분할 완료!")

if __name__ == '__main__':
    categories = get_categories(BASE_FOLDER)
    prepare_dirs(categories)

    # ✅ 멀티프로세싱으로 카테고리별 중복 제거
    with Pool(processes=cpu_count()) as pool:
        pool.map(remove_duplicates, categories)

    # ✅ 분할 작업
    split_data(categories)
    print("\n🚀 중복 제거 및 Train/Val 분할 완료!")
