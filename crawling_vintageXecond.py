import os
import re
import time
import requests
import uuid
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def sanitize_filename(name):
    return re.sub(r'[\/:*?"<>|]', '-', name).strip()


def download_image(img_url, filename, save_dir="images"):
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 "
            "Safari/537.36"
        ),
        "Referer": "https://www.xecond.co.kr/"
    }

    try:
        resp = requests.get(img_url, headers=headers, timeout=7)
        resp.raise_for_status()

        ext = os.path.splitext(img_url)[1]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif"]:
            ext = ".jpg"

        os.makedirs(save_dir, exist_ok=True)
        safe_name = sanitize_filename(filename)
        unique_id = str(uuid.uuid4())[:8]
        full_path = os.path.join(save_dir, f"{safe_name}_{unique_id}{ext}")

        with open(full_path, "wb") as f:
            f.write(resp.content)

        print(f"[다운로드] {img_url} -> {full_path}")
    except Exception as e:
        print(f"[에러] 다운로드 실패: {img_url}, 사유: {e}")


def crawl_site():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')  # 새 headless 모드
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--blink-settings=imagesEnabled=false')  # 이미지 로딩 비활성화

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 7)

    category_links = [
        "https://www.xecond.co.kr/product/list.html?cate_no=25",
        "https://www.xecond.co.kr/product/list.html?cate_no=26",
        "https://www.xecond.co.kr/product/list.html?cate_no=71",
        "https://www.xecond.co.kr/product/list.html?cate_no=27"
    ]

    for cat_idx, category_link in enumerate(category_links, start=1):
        print(f"\n=== 카테고리 {cat_idx} 이동: {category_link} ===")
        driver.get(category_link)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.pc_list_main ul.prdList.column4 li.item.xans-record-")))

        while True:
            current_url = driver.current_url
            download_images_in_current_page(driver)

            try:
                next_page = driver.find_element(By.CSS_SELECTOR, 'div.ec-base-paginate.typeList a.btnNext')
                if next_page and next_page.get_attribute('href'):
                    driver.get(next_page.get_attribute('href'))
                    wait.until(EC.staleness_of(next_page))  # 새 페이지 로딩 대기
                else:
                    print("다음 페이지가 없습니다. 다음 카테고리로 이동.")
                    break

                if driver.current_url == current_url:
                    print("페이지가 이동하지 않았습니다. 다음 카테고리로 이동.")
                    break
            except Exception:
                print("다음 페이지 버튼 없음 또는 오류 발생.")
                break

    print("\n모든 카테고리 크롤링 완료.")
    driver.quit()


def download_images_in_current_page(driver):
    wait = WebDriverWait(driver, 7)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.pc_list_main ul.prdList.column4 li.item.xans-record-")))
        boxes = driver.find_elements(By.CSS_SELECTOR, "div.pc_list_main ul.prdList.column4 li.item.xans-record-")
        print(f"박스(box) 개수: {len(boxes)}")

        threads = []
        for i, box in enumerate(boxes, start=1):
            try:
                img_tag = box.find_element(By.CSS_SELECTOR, "img.thumb")
                name_tag = box.find_element(By.CSS_SELECTOR, "p.name span a")

                brand_element = name_tag.find_elements(By.TAG_NAME, "b")
                brand = brand_element[0].text.strip() if brand_element else "NoBrand"
                product = name_tag.text.replace(brand, '').strip() if brand else name_tag.text.strip()
                final_name = f"{brand} {product}".strip()

                img_src = img_tag.get_attribute("src")
                filename = f"{final_name}_{i}"

                # 비동기 다운로드 (스레드)
                t = threading.Thread(target=download_image, args=(img_src, filename, "raw_data/vintageXecond"))
                t.start()
                threads.append(t)

            except Exception as e:
                print(f"[에러] box 처리 중: {e}")

        for t in threads:
            t.join()

    except Exception as e:
        print(f"[에러] 페이지 로드 중 문제 발생: {e}")


if __name__ == "__main__":
    crawl_site()
