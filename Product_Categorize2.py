import os
import shutil
import re

# ✅ 원본 폴더 및 저장할 폴더 경로 설정
source_folder = "data/v1"
target_root_folder = "categorized_images"
uncategorized_folder = os.path.join(target_root_folder, "미분류")

# ✅ 폴더 생성
os.makedirs(target_root_folder, exist_ok=True)
os.makedirs(uncategorized_folder, exist_ok=True)

# ✅ 정규식 패턴 정의
year_pattern = re.compile(r"\b\d{2,4}'?s\b")  # 연도 제거 (예: "90's", "2000's" 등)
number_pattern = re.compile(r'\(\d+\)$')  # (1), (2) 같은 패턴 제거
underscore_code_pattern = re.compile(r'_\d+(_[a-fA-F0-9]+)?$')  # "_1" 또는 "_1_f85cd683" 같은 랜덤 코드 제거
bracket_pattern = re.compile(r'\([^)]*\)')  # 소괄호() 안의 모든 내용 제거 (예: "(흑청)")
size_pattern = re.compile(r'\b\d*(cm|mm|M|L|XL|S|XS|XXL|FREE|OneSize|Small|Medium|Large|0~3M|1T|2T|3T|4T|5T|6T|7T|8T|9T|10T|11T|12T|13T|19T|20T)\b', re.IGNORECASE)  # 사이즈 제거
number_before_underscore_pattern = re.compile(r'\b\d+_1')  # "_1" 앞의 숫자 제거 (예: "37_1" → "_1")
# ✅ 성별 관련 단어 리스트 (완전 제거)
gender_words = ["공용","공용","남자", "남자", "여자", "여자"]

# ✅ 파일 목록 가져오기
image_files = [f for f in os.listdir(source_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]

for file in image_files:
    # 🔥 파일명에서 확장자 제거
    filename_without_ext = os.path.splitext(file)[0]

    # 🔥 불필요한 정보 제거 (연도, (1), 랜덤코드, 소괄호)
    filename_cleaned = year_pattern.sub('', filename_without_ext)  # 연도 제거
    filename_cleaned = number_pattern.sub('', filename_cleaned)  # "(1)" 제거
    filename_cleaned = number_before_underscore_pattern.sub('_1', filename_cleaned)  # "_1" 앞의 숫자 제거
    filename_cleaned = underscore_code_pattern.sub('', filename_cleaned)  # "_1" 및 랜덤 코드 제거
    filename_cleaned = bracket_pattern.sub('', filename_cleaned)  # "(흑청)" 제거
    filename_cleaned = filename_cleaned.strip()  # 앞뒤 공백 제거

    # 🔥 단어들을 리스트로 변환
    words = filename_cleaned.split()
#    print(f"📌 원본 단어: {words}")

    # 🔥 1단계: 성별 단어 제거
    words_filtered = [word for word in words if word not in gender_words]
#    print(f"🚀 성별 제거 후: {words_filtered}")

    # 🔥 2단계: 사이즈 단어 제거
    words_final = [word for word in words_filtered if not size_pattern.match(word)]
    print(f"✅ 사이즈 제거 후: {words_final}")

    # 🔥 3단계: 공용 단어가 남아있다면 마지막 단어로 선택하지 않도록 처리
    last_word = None
    for word in reversed(words_final):
        if word not in gender_words:  # "공용"이 마지막으로 남지 않도록 보장
            last_word = word
            break

    print(f"📂 최종 카테고리: {last_word}")

    # 🔥 카테고리 폴더 설정
    category_folder = os.path.join(target_root_folder, last_word) if last_word else uncategorized_folder
    os.makedirs(category_folder, exist_ok=True)

    # 🔥 파일 복사
    src_path = os.path.join(source_folder, file)
    dest_path = os.path.join(category_folder, file)
    shutil.copy(src_path, dest_path)

    print(f"✅ 파일 분류 완료: {file} → {category_folder}")

print("\n🚀 모든 파일이 카테고리별로 정리되었습니다!")
