import os
import shutil
import unicodedata
# ✅ 제품군별 키워드 정의 (파일명 내 포함된 단어 기준)
category_mapping = {
    "무스탕":["무스탕"],
    "수영복": ["수영복", "비키니", "swim", "스윔", "스웜"],
    "여자여름니트":["나시 니트", "나시니트","반팔 니트", "반팔니트", "반팔 가디건", "반팔가디건"],
    "모자": ["비니", "볼캡", "버킷햇"],
    "가방": ["백팩", "에코백", "스몰백", "숄더백"],
    "가죽" : ["가죽", "leather", "레더", "래더"],
    "가디건": ["가디건", "cardigan"],
    "스웨터": ["니트", "스웨터", "sweater", "knit"],
    "청자켓": ["청자켓", "데님자켓", "데님 자켓", "데님 베스트"],
    "블라우스": ["블라우스", "blouse"],
    "파카": ["패딩", "패팅", "puffer", "점퍼", "파카"],
    "기모후드":["기모후드", "기모 후드"],
    "후드": ["후드", "hoodie", "후드티", "후드집업"],
    "맨투맨": ["맨투맨", "sweatshirt", "맨트맨"],
    "크롭셔츠":["크롭셔츠","크롭 셔츠"],
    "크롭티": ["크롭티", "crop", "크롭"],
    "얇은지퍼자켓": ["바람막이", "바라막이", "후리스", "블루종","집업"],
    "자켓": ["자켓", "jacket"],
    "코트": ["코트", "coat"],
    "야상":["야상"],
    "트레이닝복": ["트레이닝", "운동복", "training", "져지"],
    "폴로티셔츠": ["폴로", "polo", "카라티", "카라"],
    "머플러" : ["머플러", "멀플러", "목도리"],
    "스커트": ["스커트", "치마", "skirt"],
    "긴팔티셔츠": ["긴팔티", "롱슬리브", "긴팔", "롱 슬리브"],
    "반팔티셔츠": ["반팔티", "티셔츠", "반팔"],
    "반팔와이셔츠": ["반팔와이셔츠", "반팔 셔츠"],
    "긴팔와이셔츠": ["긴팔와이셔츠", "긴팔 셔츠", "드레스드 셔츠", "셔츠"],
    "드레스": ["드레스", "원피스", "dress"],
    "청바지": ["청바지", "데님", "jeans"],
    "반바지": ["하프 팬츠", "숏팬츠", "숏 팬츠", "반바지", ],
    "긴바지": ["바지", "팬츠", "슬랙스", "jeans", "trousers"],
    "나시" : ["나시", "탱크탑", "탱크 탑"],
    "조끼" : ["조끼"]

}

# ✅ 폴더 경로 설정
input_dir = "data/gujestore"   # 원본 이미지 폴더
output_dir = "images_sorted/"  # 분류된 폴더

# ✅ 분류 폴더 생성
os.makedirs(output_dir, exist_ok=True)

# ✅ 각 카테고리별 폴더 생성
for category in category_mapping.keys():
    os.makedirs(os.path.join(output_dir, category), exist_ok=True)

# "Unknown" 폴더 생성 (미분류 데이터 저장)
unknown_dir = os.path.join(output_dir, "Unknown")
os.makedirs(unknown_dir, exist_ok=True)

# ✅ 파일 순회하며 분류
for filename in os.listdir(input_dir):
    file_path = os.path.join(input_dir, filename)

    # 파일이 아닌 경우 건너뛰기
    if not os.path.isfile(file_path):
        continue

    # 파일명을 소문자로 변환하여 검색 용이성 증가
    filename = unicodedata.normalize('NFC', filename)
    filename_lower = filename.lower()

    # ✅ 파일명에서 카테고리 매칭
    matched_category = None
    for category, keywords in category_mapping.items():
        if any(keyword in filename_lower for keyword in keywords):
            matched_category = category
            break

    # ✅ 해당 폴더로 이동 (없으면 "Unknown")
    target_folder = os.path.join(output_dir, matched_category if matched_category else "Unknown")
    shutil.copy2(file_path, os.path.join(target_folder, filename))

    print(f"[분류] {filename} → {target_folder}")

print("\n✅ 이미지 분류 완료!")
