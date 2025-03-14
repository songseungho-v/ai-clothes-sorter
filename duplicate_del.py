import os
import shutil
import numpy as np
import cv2
import open_clip
import torch
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from skimage.metrics import structural_similarity as ssim
import time

# ✅ CLIP 모델 로드 (ViT-B/32)
device = torch.device("mps")
model, preprocess, tokenizer = open_clip.create_model_and_transforms("ViT-B/32", pretrained="openai", device=device)

print("✅ CLIP 모델 로드 성공!")

# ✅ 폴더 경로 설정
root_folder = "images_sorted/Unknown"  # 원본 이미지 폴더
clean_dataset_folder = "clean_dataset/"  # 중복 제거 후 학습 데이터 저장
duplicate_folder = "duplicates/"  # 중복된 제품 저장
os.makedirs(clean_dataset_folder, exist_ok=True)
os.makedirs(duplicate_folder, exist_ok=True)


# ✅ CLIP 기반 특징 벡터 추출 함수
def extract_clip_features(img_path):
    """CLIP을 사용하여 이미지 특징 벡터를 추출"""
    try:
        image = preprocess(Image.open(img_path)).unsqueeze(0).to(device)
        with torch.no_grad():
            features = model.encode_image(image).cpu().numpy().flatten()
        return features / np.linalg.norm(features)  # 정규화 적용
    except Exception as e:
        print(f"[❌ 오류] CLIP 벡터 추출 실패: {img_path} ({e})")
        return None


# ✅ SSIM(구조적 유사도) 계산 함수 (크기 차이 고려)
def calculate_ssim(img1, img2):
    """두 이미지 간 SSIM(구조적 유사도) 계산 (크기 조정 포함)"""
    try:
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # 크기 맞추기
        min_height = min(img1.shape[0], img2.shape[0])
        min_width = min(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (min_width, min_height))
        img2 = cv2.resize(img2, (min_width, min_height))

        score, _ = ssim(img1, img2, full=True)
        return score
    except Exception as e:
        print(f"[❌ 오류] SSIM 계산 실패: {e}")
        return 0


# ✅ ORB(특징점 기반 유사도) 계산 함수 (크기 보정 추가)
def calculate_orb_similarity(img1, img2):
    """ORB 알고리즘을 이용한 특징점 매칭 기반 유사도 계산 (크기 조정 포함)"""
    try:
        orb = cv2.ORB_create(nfeatures=500)  # 특징점 개수 제한 (과대 비교 방지)
        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)

        if des1 is None or des2 is None:
            return 0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        similar_regions = [m for m in matches if m.distance < 70]
        return len(similar_regions) / max(len(matches), 1)  # 유사도 정규화
    except Exception as e:
        print(f"[❌ 오류] ORB 유사도 계산 실패: {e}")
        return 0


# ✅ 모든 이미지 리스트 가져오기
image_files = [f for f in os.listdir(root_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]
total_images = len(image_files)

# ✅ CLIP 벡터 저장
image_vectors = {}
image_cache = {}  # SSIM & ORB 비교 속도 개선

start_time = time.time()

for idx, img_file in enumerate(image_files, start=1):
    img_path = os.path.join(root_folder, img_file)
    clip_features = extract_clip_features(img_path)

    if clip_features is not None:
        image_vectors[img_file] = clip_features
        image_cache[img_file] = cv2.imread(img_path)  # 이미지 미리 로드

    elapsed_time = time.time() - start_time
    print(f"[{idx}/{total_images}] 벡터 및 SSIM용 이미지 로드 완료: {img_file} | 총 소요시간: {elapsed_time:.2f}초")

print("\n✅ 모든 이미지 특징 벡터 및 SSIM 준비 완료!")

# ✅ 중복 제거 기준 설정
clip_threshold = 0.90  # CLIP 코사인 유사도 임계값
ssim_threshold = 0.75  # SSIM 유사도 임계값 (완화)
orb_threshold = 0.83  # ORB 매칭 비율 임계값 #77

# ✅ 중복된 이미지 관리
checked_images = set()

for img1 in image_files:
    if img1 in checked_images:
        continue

    img1_vector = image_vectors.get(img1)
    img1_data = image_cache.get(img1)

    if img1_vector is None or img1_data is None:
        continue

    for img2 in image_files:
        if img1 == img2 or img2 in checked_images:
            continue

        img2_vector = image_vectors.get(img2)
        img2_data = image_cache.get(img2)

        if img2_vector is None or img2_data is None:
            continue

        # ✅ CLIP 유사도 계산
        clip_similarity = cosine_similarity([img1_vector], [img2_vector])[0][0]

        # ✅ SSIM 계산 (크기 차이 고려)
        ssim_score = calculate_ssim(img1_data, img2_data)

        # ✅ ORB 계산 (크기 차이 고려)
        orb_score = calculate_orb_similarity(img1_data, img2_data)

        # ✅ 비교 결과 실시간 출력
        print(f"[비교 중] {img1} ↔ {img2} | CLIP: {clip_similarity:.4f}, SSIM: {ssim_score:.4f}, ORB: {orb_score:.4f}")

        # ✅ 중복 제품 판별 (CLIP + SSIM + ORB 기준 충족)
        if clip_similarity >= clip_threshold and (ssim_score >= ssim_threshold or orb_score >= orb_threshold):
            print(
                f"🛑 [중복 제거] {img1} ↔ {img2} (CLIP: {clip_similarity:.4f}, SSIM: {ssim_score:.4f}, ORB: {orb_score:.4f})")
            shutil.move(os.path.join(root_folder, img2), os.path.join(duplicate_folder, img2))
            checked_images.add(img2)

print("\n✅ 중복 제품 제거 완료!")
