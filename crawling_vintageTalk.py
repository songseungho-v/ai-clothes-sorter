import os
import re
import time
import requests
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def sanitize_filename(name):
    """파일 이름에 쓸 수 없는 문자 제거."""
    return re.sub(r'[\\/:*?"<>|]', '-', name).strip()


def download_image(img_url, filename, save_dir="images"):
    """이미지 다운로드 함수 (UUID 추가하여 중복 방지)"""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    if img_url.startswith("//"):
        img_url = "https:" + img_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 "
            "Safari/537.36"
        ),
        "Referer": "https://vintagetalk.co.kr/"
    }

    try:
        resp = requests.get(img_url, headers=headers, timeout=10)
        resp.raise_for_status()

        ext = os.path.splitext(img_url)[1]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif"]:
            ext = ".jpg"

        safe_name = sanitize_filename(filename)
        unique_id = str(uuid.uuid4())[:8]  # 8자리 랜덤 UUID 추가
        full_path = os.path.join(save_dir, f"{safe_name}_{unique_id}{ext}")

        with open(full_path, "wb") as f:
            f.write(resp.content)

        print(f"[다운로드] {img_url} -> {full_path}")
    except Exception as e:
        print(f"[에러] 다운로드 실패: {img_url}, 사유: {e}")


def crawl_site():
    driver = webdriver.Chrome()
    driver.get("https://vintagetalk.co.kr/")
    wait = WebDriverWait(driver, 10)

    time.sleep(2)

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

    category_links = category_links[1:9]

    for cat_idx, category_link in enumerate(category_links, start=1):
        try:
            print(f"\n=== 카테고리 {cat_idx} 이동: {category_link} ===")
            driver.get(category_link)

            # (1) 페이지가 로드될 때까지 대기
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.PrdItem")))

            while True:
                download_images_in_current_page(driver)

                old_url = driver.current_url

                # '다음 페이지' 버튼 찾기
                next_buttons = driver.find_elements(By.CSS_SELECTOR, 'img[alt="다음 페이지"]')

                if next_buttons:
                    print("다음 페이지 버튼 클릭 시도...")

                    # JavaScript를 사용하여 클릭 (강제 클릭)
                    driver.execute_script("arguments[0].click();", next_buttons[0])

                    # 페이지가 완전히 변경될 때까지 기다림
                    try:
                        WebDriverWait(driver, 5).until(EC.staleness_of(next_buttons[0]))
                        print("페이지 변경 감지됨. 다음 페이지로 이동 중...")
                    except:
                        print("페이지가 변경되지 않음. 다음 카테고리로 이동.")
                        break

                    time.sleep(2)  # 페이지가 완전히 로드될 시간 대기
                    new_url = driver.current_url

                    if new_url == old_url:
                        print("페이지 변경이 감지되지 않음. 다음 카테고리로 이동.")
                        break
                else:
                    print("다음 페이지 버튼이 없음. 다음 카테고리로 이동.")
                    break

        except Exception as e:
            print(f"[에러] 카테고리 이동 중 문제 발생: {e}")

    print("\n모든 카테고리 크롤링 완료.")
    driver.quit()


def download_images_in_current_page(driver):
    """상품 이미지 다운로드"""
    wait = WebDriverWait(driver, 10)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.PrdItem")))

        boxes = driver.find_elements(By.CSS_SELECTOR, "div.PrdItem")
        print(f"박스(box) 개수: {len(boxes)}")

        for i, box in enumerate(boxes, start=1):
            try:
                thumbs = box.find_elements(By.CSS_SELECTOR, "img.prdthumb")
                if not thumbs:
                    continue

                p_tags = box.find_elements(By.CSS_SELECTOR, 'span[style*="font-size:14px;color:#222222;"]')

                if len(p_tags) > 1:
                    item_name = p_tags[1].text.strip()
                elif len(p_tags) == 1:
                    item_name = p_tags[0].text.strip()
                else:
                    item_name = "NoName"

                for j, thumb_img in enumerate(thumbs, start=1):
                    img_src = thumb_img.get_attribute("src")
                    filename = f"{item_name}_{j}"
                    download_image(img_src, filename, save_dir="data/vintageTalk")

            except Exception as e:
                print(f"[에러] box 처리 중: {e}")

    except Exception as e:
        print(f"[에러] 페이지 로드 중 문제 발생: {e}")


if __name__ == "__main__":
    crawl_site()
