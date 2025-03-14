import os
import time
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import socket
socket.setdefaulttimeout(5)
def crawl_images(keyword, save_root='data', max_count=500, train_ratio=0.7):
    """
    구글 이미지에서 'keyword'로 검색해 최대 max_count장 다운로드.
    train_ratio 비율(0~1)만큼은 train/<keyword> 폴더에, 나머지는 val/<keyword> 폴더에 저장.
    """
    # 1) ChromeDriver 설정
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    # 2) 구글 이미지 검색
    driver.get("https://www.google.com/imghp?hl=en")
    time.sleep(1)

    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(keyword)
    search_box.send_keys(Keys.RETURN)
    time.sleep(1)

    # 3) 스크롤 내려서 썸네일 로드
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # '결과 더보기' 버튼 클릭 시도
            try:
                more_button = driver.find_element(By.CSS_SELECTOR, ".mye4qd")
                more_button.click()
                time.sleep(1)
            except:
                break
        last_height = new_height

        containers = driver.find_elements(By.CSS_SELECTOR, "div.H8Rx8c")
        if len(containers) >= max_count:
            break

    # 4) 저장 폴더 준비: train / val
    # keyword 폴더명 정리(슬래시 등 제거)
    folder_name = keyword.replace('/', '_').replace('\\', '_')
    train_dir = os.path.join(save_root, "train", folder_name)
    val_dir   = os.path.join(save_root, "val",   folder_name)

    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)

    # 앞부분 train, 뒷부분 val 개수 결정
    train_count = int(max_count * train_ratio)

    # 5) 큰 이미지 다운로드
    count = 0
    containers = driver.find_elements(By.CSS_SELECTOR, "div.H8Rx8c")

    for index, container in enumerate(containers):
        if count >= max_count:
            break

        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", container)
            time.sleep(1)

            container.click()

            # 큰 이미지 대기
            big_image = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "img.sFlh5c.FyHeAf.iPVvYb:not([src^='data'])"))
            )

            src = big_image.get_attribute("src")
            if src.startswith("http"):
                # 어느 폴더에 저장할지 결정
                if count < train_count:
                    sub_dir = train_dir
                else:
                    sub_dir = val_dir

                file_name = f"{keyword}_{count}.jpg"
                file_path = os.path.join(sub_dir, file_name)

                urllib.request.urlretrieve(src, file_path)
                print(f"[{keyword}] Downloaded {file_name} to {sub_dir}")
                count += 1
            else:
                print(f"[{keyword}] Skipped data URL or invalid src")
        except socket.timeout:
            print("Download timed out, skipping this image.")
            continue
        except Exception as e:
            print(f"Error at container {index}: {e}")
            continue

    driver.quit()


def main():
    # 예시: 클래스(=키워드) 목록
    test_keywords = [
        #"긴팔티셔츠",
        "반팔티셔츠",
        "폴로티셔츠",
        "블라우스",
        "스웨터",
        "후드",
        "맨투맨",
        "니트",
        #"크롭티",
        #"반팔와이셔츠",
        #"긴팔와이셔츠",
        "긴바지",
        "반바지",
        #"스키니진",
        #"와이드팬츠",
        #"핫팬츠",
        "미니스커트",
        "롱스커트",
        "청치마",
        #"드레스",
        "원피스",
        #"점프수트",
        #"코트",
        #"자켓",
        #"파카",
        #"가디건",
        #"트렌치코트",
        #"패딩",
        #"후리스",
        #"정장마이",
        #"야상잠바",
        #"브래지어",
        #"삼각팬티",
        #"사각팬티",
        #"러닝셔츠",
        #"양말",
        #"장갑",
        #"스카프",
        #"넥타이",
        #"벨트",
        #"모자",
        #"파자마",
        #"실크잠옷",
        #"망사잠옷",
        #"트레이닝복",
        #"수영복",
        #"농구유니폼",
        #"요가복"
    ]

    for kw in test_keywords:
        print(f"\n=== Crawling: {kw} ===")
        crawl_images(kw, save_root="data", max_count=500, train_ratio=0.7)
        time.sleep(1.5)

    print("\nAll crawling tasks completed.")


if __name__ == "__main__":
    main()
