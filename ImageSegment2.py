import os
import cv2
import shutil
from multiprocessing import Pool, cpu_count

input_dir = './input_images'
output_dirs = {
    "one": './output/one',
    "two": './output/two'
}
for path in output_dirs.values():
    os.makedirs(path, exist_ok=True)

def count_symmetry(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)

    # 이미지 전체 중심 기준으로 나누기 (객체 중심 대신)
    h, w = mask.shape
    if w % 2 != 0:
        mask = mask[:, :w - 1]
        img = img[:, :w - 1]
        w -= 1

    mid_x = w // 2
    left = mask[:, :mid_x]
    right = mask[:, mid_x:]
    right_flipped = cv2.flip(right, 1)

    # SSIM 계산
    from skimage.metrics import structural_similarity as ssim
    score = ssim(left, right_flipped)
    return score

def process_image(filename):
    try:
        print(f"🔍 Processing {filename}")
        img_path = os.path.join(input_dir, filename)
        image = cv2.imread(img_path)
        if image is None:
            raise ValueError(f"이미지를 받을 수 없습니다: {img_path}")

        symmetry_score = count_symmetry(image)

        # 임계값 기준으로 분류
        if symmetry_score > 0.5:
            shutil.copy(img_path, os.path.join(output_dirs["one"], filename))
            result = "one"
        else:
            shutil.copy(img_path, os.path.join(output_dirs["two"], filename))
            result = "two"

        print(f"✅ {filename} 처리 완료 | Symmetry Score: {symmetry_score:.2f} | Result: {result}")

    except Exception as e:
        print(f"❌ Error for {filename}: {e}")

if __name__ == '__main__':
    image_list = [f for f in os.listdir(input_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
    num_workers = min(cpu_count(), 6)

    with Pool(num_workers) as pool:
        pool.map(process_image, image_list)

    print("🚀 좌우 대치보단 one/two 폴더 분류 완료")
