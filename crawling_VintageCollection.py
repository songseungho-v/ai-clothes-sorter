import os
import re
import time
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By

def sanitize_filename(name):
    """파일 이름에 쓸 수 없는 문자 제거."""
    return re.sub(r'[\\/:*?"<>|]', '-', name).strip()

def download_image(img_url, filename, save_dir="images"):
    """이미지 다운로드 함수."""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    # 프로토콜 보완 (// -> https://)
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    # User-Agent/Referer 설정(403 방지)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 "
            "Safari/537.36"
        ),
        "Referer": "https://www.vintage-collection.co.kr/"
    }

    try:
        resp = requests.get(img_url, headers=headers, timeout=10)
        resp.raise_for_status()

        # 확장자 추출
        ext = os.path.splitext(img_url)[1]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif"]:
            ext = ".jpg"

        safe_name = sanitize_filename(filename)
        full_path = os.path.join(save_dir, safe_name + ext)
        with open(full_path, "wb") as f:
            f.write(resp.content)

        print(f"[다운로드] {img_url} -> {full_path}")
    except Exception as e:
        print(f"[에러] 다운로드 실패: {img_url}, 사유: {e}")

def crawl_site():
    driver = webdriver.Chrome()
    driver.get("https://www.vintage-collection.co.kr/")  # 실제 시작 페이지

    time.sleep(2)  # 페이지 로딩 대기

    # 1) li.xans-record- 목록에서 a 태그 href만 추출하여 문자열 리스트로 보관
    category_list = driver.find_elements(By.CSS_SELECTOR, "li.xans-record-")
    print(f"발견된 카테고리 개수: {len(category_list)}")

    category_links = []
    for idx, cat_li in enumerate(category_list, start=1):
        try:
            a_tag = cat_li.find_element(By.TAG_NAME, "a")
            href = a_tag.get_attribute("href")
            if href:
                category_links.append(href)
        except Exception as e:
            print(f"[에러] 카테고리 링크 추출 중 문제: {e}")
            # 계속 진행

    # 2) 수집한 카테고리 링크를 순회하며 크롤링
    for cat_idx, category_link in enumerate(category_links, start=1):
        try:
            print(f"\n=== 카테고리 {cat_idx} 이동: {category_link} ===")
            driver.get(category_link)
            time.sleep(2)

            # 페이지 반복 탐색
            while True:
                # (a) 현재 페이지에서 이미지 다운로드
                download_images_in_current_page(driver)

                old_url = driver.current_url
                next_buttons = driver.find_elements(
                    By.CSS_SELECTOR,
                    'img[src="/web/upload/gl_b_img/btn_comment_next.png"]'
                )
                if next_buttons:
                    next_buttons[0].click()
                    time.sleep(2)  # 페이지 로딩 대기

                    new_url = driver.current_url
                    if new_url == old_url:
                        # URL이 안 바뀜 -> 더 이상 넘어갈 수 없음
                        print("더 이상 넘어갈 수 없음. 다음 카테고리로 이동.")
                        break
                else:
                    print("다음 페이지 버튼이 없음. 다음 카테고리로 이동.")
                    break

        except Exception as e:
            print(f"[에러] 카테고리 이동 중 문제 발생: {e}")

    print("\n모든 카테고리 크롤링 완료.")
    driver.quit()

def download_images_in_current_page(driver):
    """
    현재 페이지에서
    (1) class="thumb" 이미지의 src를 찾음
    (2) 이 이미지가 속한 부모 구조(div.box 내 p 태그)를 합쳐 파일명 생성
    (3) 이미지 다운로드
    """
    time.sleep(2)  # 페이지 안정화 대기

    boxes = driver.find_elements(By.CSS_SELECTOR, "div.box")
    print(f"박스(box) 개수: {len(boxes)}")

    for i, box in enumerate(boxes, start=1):
        try:
            thumbs = box.find_elements(By.CSS_SELECTOR, "img.thumb")
            if not thumbs:
                continue

            # p 태그 목록
            p_tags = box.find_elements(By.TAG_NAME, "p")
            # p_tags[2] 대신 안전하게 길이 체크
            if len(p_tags) > 2:
                item_name = p_tags[2].text.strip()
            else:
                item_name = "NoName"

            for j, thumb_img in enumerate(thumbs, start=1):
                img_src = thumb_img.get_attribute("src")
                filename = f"{item_name}_{j}"
                download_image(img_src, filename, save_dir="data/vintageCollection")

        except Exception as e:
            print(f"[에러] box 처리 중: {e}")


if __name__ == "__main__":
    crawl_site()
