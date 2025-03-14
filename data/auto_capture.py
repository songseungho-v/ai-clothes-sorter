import cv2
import time

# --- 1) 비디오 소스 열기 (웹캠 / CCTV / 동영상 파일 등) ---
cap = cv2.VideoCapture(0)  # 웹캠 예시. 실제 환경에 맞게 교체

# --- 2) MOG2 Background Subtractor 생성 ---
# history: 배경 학습을 위한 프레임 수, detectShadows: 그림자 검출 여부
# (값들은 상황에 맞게 튜닝 필요)
bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=100, detectShadows=True)

print("Adaptive Background Subtraction 시작...")

# 물체 감지 상태 추적용 변수
object_is_detected = False
object_detected_time = None
object_captured = False
capture_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # --- 3) 현재 프레임에서 전경(물체) 마스크 추출 ---
    # apply() 호출 시 내부적으로 배경을 갱신(학습)
    fg_mask = bg_subtractor.apply(frame)

    # 그림자 픽셀(약간 어두운 회색)도 포함될 수 있어, 필요시 추가 후처리
    # 값이 127로 나타나는 경우는 그림자로 간주되기도 함

    # --- 4) 모폴로지 연산으로 노이즈 제거 ---
    # 상황에 따라 커널 크기, 반복 횟수를 조절해야 함
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=2)
    fg_mask = cv2.dilate(fg_mask, None, iterations=2)

    # --- 5) 윤곽(Contour) 검출 ---
    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    current_frame_object_detected = False
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # area 임계값은 실험적으로 조정
        if area > 5000:
            current_frame_object_detected = True
            break

    # --- 6) 연속 감지 로직 ---
    if current_frame_object_detected:
        if not object_is_detected:
            # 이전 프레임까지는 없었는데 이번에 새로 감지됨
            object_is_detected = True
            object_detected_time = time.time()
            object_captured = False
        else:
            # 이미 물체가 감지되고 있는 상태
            if not object_captured:
                elapsed = time.time() - object_detected_time
                if elapsed >= 1.0:
                    # 1초 이상 연속 감지 시 캡처
                    capture_count += 1
                    filename = f"captured_{capture_count}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"→ 물체(옷) 감지 1초 경과! {filename} 저장")
                    object_captured = True
    else:
        # 이번 프레임에서 물체가 감지되지 않으면 상태 리셋
        object_is_detected = False
        object_detected_time = None
        object_captured = False

    # 디버그용: 화면에 표시
    cv2.imshow("Frame", frame)
    cv2.imshow("Foreground Mask", fg_mask)

    key = cv2.waitKey(30)
    if key == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
