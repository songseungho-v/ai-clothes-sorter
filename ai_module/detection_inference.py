# detection_inference.py
import torch
import cv2
from ultralytics import YOLO

yolo_model = None
detection_class_names = []  # ["상의","하의","아우터","치마"]

def load_yolo_model_once():
    global yolo_model, detection_class_names
    if yolo_model is not None:
        return
    # 미리 학습된 YOLOv8 (4개 대분류)
    #model_path = "model_files/yolov8n_clothes.pt"
    model_path = "/Users/songseungho/Desktop/making program/Project_ai_clothes/ai-clothes-sorter/model_files/yolov8n_clothes.pt"
    yolo_model = YOLO(model_path)
    # model.names => dict or list
    detection_class_names = yolo_model.names

def detect_with_yolo(frame_bgr, conf_thres=0.5):
    load_yolo_model_once()
    # predict
    results = yolo_model.predict(source=frame_bgr, conf=conf_thres, verbose=False)
    dets = []
    if len(results) > 0:
        boxes_data = results[0].boxes
        for box in boxes_data:
            xyxy = box.xyxy[0].cpu().numpy()  # [x1,y1,x2,y2]
            cls_idx = int(box.cls[0].item())
            conf    = float(box.conf[0].item())
            x1,y1,x2,y2 = xyxy
            cat = detection_class_names[cls_idx]
            dets.append({
                "box": (x1,y1,x2,y2),
                "category": cat,
                "score": conf
            })
    return dets
