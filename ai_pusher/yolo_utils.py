from ultralytics import YOLO

model = YOLO("yolov8n.pt")

def analyze_frame(frame):
    results = model.predict(source=frame, conf=0.5, verbose=False)
    detections = []
    if results:
        for box in results[0].boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
            label = model.names[cls]
            detections.append({"label": label, "score": conf, "box": xyxy})
    return detections