# pipeline.py
import cv2
import time
import os
import numpy as np
from detection_inference import detect_with_yolo
from classification_inference import classify_fine
from PIL import Image, ImageDraw, ImageFont
import unicodedata
# 한글 텍스트를 위한 helper 함수 (PIL 사용)
fontPath="NanumGothic.ttf"

def put_text_with_pil(cv2_img, text, position, font_path=fontPath, font_size=20, color=(0,255,0)):
    cv2_img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(cv2_img_rgb)
    draw = ImageDraw.Draw(pil_img)
    text_nfc = unicodedata.normalize('NFC', text)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print("Font load error:", e)
        font = ImageFont.load_default()
    draw.text(position, text_nfc, font=font, fill=(color[2], color[1], color[0]))
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# 임계값 (세분류 confidence가 이 값 미만이면 박스를 그리지 않음)
CONF_THRESHOLD = 0.6

def run_pipeline_camera():
    cap = cv2.VideoCapture(2)
    if not cap.isOpened():
        print("Cannot open camera.")
        return

    os.makedirs("result_pipeline", exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        img_h, img_w, _ = frame.shape
        img_area = img_w * img_h

        # 1) YOLO detect => [ {box, category, score}, ... ]
        detections = detect_with_yolo(frame, conf_thres=0.5)

        # 2) 각 검출 영역에 대해 세분류 수행
        for det in detections:
            (x1, y1, x2, y2) = det["box"]
            big_cat = det["category"]  # 예: "상의", "하의", "아우터", "치마"
            score_d = det["score"]

            # 계산: 박스 면적
            box_area = (x2 - x1) * (y2 - y1)
            # 만약 박스 면적이 전체 이미지 면적의 80% 이상이면 건너뛰기
            if box_area / img_area > 0.95:
                continue

            # 박스 그리기 및 대분류 텍스트 표시
            temp_frame = frame.copy()
            cv2.rectangle(temp_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,255,0), 2)
            temp_frame = put_text_with_pil(temp_frame, f"{big_cat}({score_d:.2f})", (int(x1), int(y1)-5),
                                           font_path=fontPath, font_size=20, color=(0,255,0))

            # 크롭
            crop_bgr = frame[int(y1):int(y2), int(x1):int(x2)]
            if crop_bgr.size <= 0:
                continue
            crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            pil_crop = Image.fromarray(crop_rgb)

            # 3) 세분류 수행
            fine_label, fine_conf = classify_fine(pil_crop, big_cat)

            # 세분류 confidence가 낮으면 무시
            if fine_conf < CONF_THRESHOLD:
                continue

            # 세분류 텍스트 추가
            temp_frame = put_text_with_pil(temp_frame, f"{fine_label}({fine_conf:.2f})", (int(x1), int(y1)+20),
                                           font_path=fontPath, font_size=20, color=(0,255,255))
            frame = temp_frame

            # 중앙에 도달 시 캡처
            w = frame.shape[1]
            center_box_x = (x1 + x2) / 2
            if abs(center_box_x - w/2) < 20:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{big_cat}_{score_d}_{fine_label}_{fine_conf}.jpg"
                cv2.imwrite(os.path.join("result_pipeline", filename), frame)
                print(f"[CAPTURE] saved => {filename}")

        cv2.imshow("2-stage pipeline", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_pipeline_camera()
