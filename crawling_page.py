import os
import re
import time
import uuid
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def download_image(img_url, save_dir):
    """이미지 다운로드 헬퍼 함수"""#26페이지 부터.
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    try:
        r = requests.get(img_url, timeout=5)
        r.raise_for_status()
        # 파일 확장자 결정
        ext = os.path.splitext(img_url)[1]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif"]:
            ext = ".jpg"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(save_dir, filename)
        with open(filepath, "wb") as f:
            f.write(r.content)
        print(f"[다운로드] {img_url} -> {filepath}")
    except Exception as e:
        print(f"[에러] 다운로드 실패: {img_url}, 사유: {e}")

def crawl_site_images_shift_click(base_url="https://www.gujestore.com/",
                                  save_dir="data/gujestore",
                                  max_page=100,
                                  wait_time=3):
    """
    1) 사이트 메인 접속
    2) badgeWrapper 요소를 찾아, Shift+클릭으로 새 창(탭) 열기
    3) 새 창에서 이미지 다운로드
    4) 새 창 닫고 메인 창으로 복귀
    5) 페이지네이션으로 다음 페이지 이동, 반복
    """

    driver = webdriver.Chrome()
    driver.get(base_url)
    time.sleep(wait_time)

    current_page = 1

    while True:
        print(f"=== 현재 페이지: {current_page} ===")

        badge_elements = driver.find_elements(By.CSS_SELECTOR, "div.badgeWrapper")
        if not badge_elements:
            print("더 이상 badgeWrapper를 찾지 못함. 종료합니다.")
            break

        # 메인 창 핸들 기억
        main_window = driver.current_window_handle

        # 배지 래퍼 각각 Shift+클릭 → 새 창 → 이미지 다운로드
        for i, badge_el in enumerate(badge_elements, start=1):
            try:
                # Shift+Click으로 새 창 열기
                ActionChains(driver).key_down(Keys.SHIFT).click(badge_el).key_up(Keys.SHIFT).perform()
                time.sleep(wait_time)

                # 새로운 창(탭)으로 전환
                all_windows = driver.window_handles
                if len(all_windows) < 2:
                    print(f"  [{i}] 새 창이 열리지 않았습니다. 스킵.")
                    continue
                driver.switch_to.window(all_windows[-1])

                # 여기서 이미지 다운로드 진행
                elements = driver.find_elements(By.CSS_SELECTOR, "div.shopProductImgMain.type_slide.shopProductImgRatio")
                print(f"  [{i}] 새 창의 이미지 div: {len(elements)}개")
                # if elements:
                #     # 첫 번째 div만 추출
                #     first_div = elements[0]
                #     style_value = first_div.get_attribute("style")
                #     match = re.search(r'background-image\s*:\s*url\((.*?)\)', style_value)
                #     if match:
                #         raw_url = match.group(1)
                #         img_url = raw_url.strip('"').strip("'")
                #         download_image(img_url, save_dir=save_dir)
                #     else:
                #         print("    첫 div에서 background-image를 찾지 못했습니다.")
                # else:
                #     print("    이미지 div가 없습니다.")
                for j, elem in enumerate(elements, start=1):
                    style_value = elem.get_attribute("style")
                    # 예: background-image:url("https://...");width:100%
                    match = re.search(r'background-image\s*:\s*url\((.*?)\)', style_value)
                    if match:
                        raw_url = match.group(1)
                        img_url = raw_url.strip('"').strip("'")
                        download_image(img_url, save_dir=save_dir)
                    else:
                        print(f"    [{j}] background-image를 찾지 못했습니다.")

                # 새 창 닫기
                driver.close()

                # 다시 메인 창으로 복귀
                driver.switch_to.window(main_window)

                # DOM이 변동될 수 있으므로 다시 badgeElements 가져오기 (안정성 위해)
                badge_elements = driver.find_elements(By.CSS_SELECTOR, "div.badgeWrapper")

            except Exception as e:
                print(f"[에러] 새 창 열기/다운로드 중: {e}")
                # 혹시 새 창이 열렸다면 닫고 복귀
                all_windows = driver.window_handles
                if len(all_windows) > 1:
                    driver.close()
                driver.switch_to.window(main_window)
                time.sleep(1)

        # 페이지네이션 이동
        moved = go_to_next_page(driver, current_page, max_page, wait_time)
        if not moved:
            print("페이지를 더 이상 이동할 수 없습니다. 종료.")
            break

        current_page += 1
        if current_page > max_page:
            print(f"최대 페이지({max_page})에 도달, 종료.")
            break

    driver.quit()

def go_to_next_page(driver, current_page, max_page, wait_time):
    """
    페이지네이션 버튼 (예: .paginationNo-navi-2, .paginationNo-navi.next) 클릭 예시
    """
    try:
        next_sel = f".paginationNo-navi.paginationNo-navi-{current_page + 1}"
        next_btn = driver.find_elements(By.CSS_SELECTOR, next_sel)
        if next_btn:
            next_btn[0].click()
            time.sleep(wait_time)
            return True
        else:
            # next
            next_btn = driver.find_elements(By.CSS_SELECTOR, ".paginationNo-navi.next")
            if next_btn:
                next_btn[0].click()
                time.sleep(wait_time)
                return True
            else:
                return False
    except Exception as e:
        print(f"[에러] 페이지네이션 이동 실패: {e}")
        return False


if __name__ == "__main__":
    crawl_site_images_shift_click(
        base_url="https://www.gujestore.com/",
        save_dir="data/gujeshop",
        max_page=100,
        wait_time=3
    )
