# import cv2
# import time
# import os
#
# cap = cv2.VideoCapture(1)
# bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=100, detectShadows=True)
#
# capture_count = 0
#
# while True:
#     ret, frame = cap.read()
#     if not ret:
#         break
#
#     fg_mask = bg_subtractor.apply(frame)
#     kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
#     fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=2)
#     fg_mask = cv2.dilate(fg_mask, None, iterations=2)
#
#     contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#
#     # 여러 컨투어 각각 판단
#     for cnt in contours:
#         area = cv2.contourArea(cnt)
#         if area > 50000:
#             # bounding box
#             x, y, w, h = cv2.boundingRect(cnt)
#             # 객체 부분만 잘라서 저장 (원한다면)
#             obj_roi = frame[y:y+h, x:x+w]
#
#             capture_count += 1
#             filename = f"captured_{capture_count}.jpg"
#             cv2.imwrite(filename, frame)  # 또는 obj_roi
#             print(f"→ 객체 감지 area={area}, {filename} 저장")
#
#     cv2.imshow("Frame", frame)
#     cv2.imshow("Foreground Mask", fg_mask)
#
#     key = cv2.waitKey(30)
#     if key == 27:  # ESC
#         break
#
# cap.release()
# cv2.destroyAllWindows()

import cv2
import time

# --- 1) 비디오 소스 열기 (웹캠 / CCTV / 동영상 파일 등) ---
cap = cv2.VideoCapture(1)  # 웹캠 예시. 실제 환경에 맞게 교체

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
# import cv2
# import time
# import os
# import numpy as np
# from detection_inference import detect_with_yolo
# from classification_inference import classify_fine
# from PIL import Image, ImageDraw, ImageFont
# import unicodedata
#
# # 폰트 경로: 한글을 지원하는 TTF 파일을 프로젝트에 두고, 해당 경로로 지정
# fontPath = os.path.join(os.path.dirname(__file__), "NanumGothic.ttf")
#
# def put_text_with_pil(cv2_img, text, position, font_path=fontPath, font_size=20, color=(0,255,0)):
#     # OpenCV BGR -> PIL RGB 변환
#     cv2_img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
#     pil_img = Image.fromarray(cv2_img_rgb)
#     draw = ImageDraw.Draw(pil_img)
#     text_nfc = unicodedata.normalize('NFC', text)
#     try:
#         font = ImageFont.truetype(font_path, font_size)
#     except Exception as e:
#         print("Font load error:", e)
#         font = ImageFont.load_default()
#     draw.text(position, text_nfc, font=font, fill=(color[2], color[1], color[0]))
#     return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
#
# # 임계값: 세분류 confidence가 이 값 미만이면 박스를 무시
# CONF_THRESHOLD = 0.6
#
# def run_pipeline_camera():
#     cap = cv2.VideoCapture(2)  # 사용 중인 카메라 인덱스에 맞게 조정
#     if not cap.isOpened():
#         print("Cannot open camera.")
#         return
#
#     os.makedirs("result_pipeline", exist_ok=True)
#
#     # --- Background Subtraction 설정 ---
#     # MOG2를 사용하여 배경 모델을 학습하고, 지속적인 움직임을 감지
#     bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=100, detectShadows=True)
#     kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
#
#     # 객체 연속 감지를 위한 상태 변수
#     object_is_detected = False
#     object_detected_time = None
#     object_captured = False
#     capture_threshold = 2.0  # 객체가 연속 감지되어야 하는 최소 시간 (초)
#
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#
#         current_time = time.time()
#         img_h, img_w, _ = frame.shape
#         img_area = img_w * img_h
#
#         # --- 배경 차분을 이용한 전경 마스크 ---
#         fg_mask = bg_subtractor.apply(frame)
#         fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=2)
#         fg_mask = cv2.dilate(fg_mask, None, iterations=2)
#         contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#
#         current_frame_object_detected = False
#         for cnt in contours:
#             area = cv2.contourArea(cnt)
#             if area > 5000:  # 이 값은 실험적으로 조절 (너무 작은 객체는 무시)
#                 current_frame_object_detected = True
#                 break
#
#         # --- 연속 감지 로직 ---
#         if current_frame_object_detected:
#             if not object_is_detected:
#                 object_is_detected = True
#                 object_detected_time = current_time
#                 object_captured = False
#             # 이미 감지 중인 경우, 추가로 별도 처리 없이 시간 측정
#         else:
#             # 객체가 감지되지 않으면 상태 리셋
#             object_is_detected = False
#             object_detected_time = None
#             object_captured = False
#
#         # --- YOLO를 이용한 Detection 및 세분류 ---
#         detections = detect_with_yolo(frame, conf_thres=0.5)
#         for det in detections:
#             (x1, y1, x2, y2) = det["box"]
#             big_cat = det["category"]  # "상의", "하의", "아우터", "치마"
#             score_d = det["score"]
#
#             # 박스 면적이 너무 큰 경우(화면 전체 95% 이상)나 confidence 낮으면 무시
#             box_area = (x2 - x1) * (y2 - y1)
#             if box_area / img_area > 0.95 or score_d < 0.6:
#                 continue
#
#             # YOLO 검출 결과 표시: 박스와 대분류 텍스트(PIL)
#             temp_frame = frame.copy()
#             cv2.rectangle(temp_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,255,0), 2)
#             temp_frame = put_text_with_pil(temp_frame, f"{big_cat}({score_d:.2f})", (int(x1), int(y1)-5),
#                                            font_path=fontPath, font_size=20, color=(0,255,0))
#
#             # 해당 영역 크롭 및 세분류 수행
#             crop_bgr = frame[int(y1):int(y2), int(x1):int(x2)]
#             if crop_bgr.size <= 0:
#                 continue
#             crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
#             pil_crop = Image.fromarray(crop_rgb)
#             fine_label, fine_conf = classify_fine(pil_crop, big_cat)
#
#             if fine_conf < CONF_THRESHOLD:
#                 continue
#
#             temp_frame = put_text_with_pil(temp_frame, f"{fine_label}({fine_conf:.2f})", (int(x1), int(y1)+20),
#                                            font_path=fontPath, font_size=20, color=(0,255,255))
#             frame = temp_frame
#
#             # --- 캡처 조건: 박스 중앙이 화면 중앙에 위치하고,
#             # 객체가 연속 감지되어 일정 시간 이상 유지된 경우에만 캡처 ---
#             w = frame.shape[1]
#             center_box_x = (x1 + x2) / 2
#             if abs(center_box_x - w/2) < 20:
#                 if object_is_detected and (current_time - object_detected_time) >= capture_threshold and not object_captured:
#                     timestamp = time.strftime("%Y%m%d_%H%M%S")
#                     filename = f"{timestamp}_{big_cat}_{fine_label}_{fine_conf:.2f}.jpg"
#                     cv2.imwrite(os.path.join("result_pipeline", filename), frame)
#                     print(f"[CAPTURE] saved => {filename}")
#                     object_captured = True
#
#         cv2.imshow("2-stage pipeline", frame)
#         if cv2.waitKey(1) & 0xFF == 27:  # ESC 키 종료
#             break
#
#     cap.release()
#     cv2.destroyAllWindows()
#
# if __name__ == "__main__":
#     run_pipeline_camera()
