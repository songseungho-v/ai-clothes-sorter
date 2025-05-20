import cv2
import time
import os
from ai_module.detection_inference import detect_objects_opencv

def run_realtime_detection():
    cap = cv2.VideoCapture(0)  # 웹캠 (index=0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    os.makedirs("result_detections", exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1) detect
        detections = detect_objects_opencv(frame, score_threshold=0.5)

        # 2) draw bounding boxes
        h, w, _ = frame.shape
        center_screen_x = w / 2

        for det in detections:
            (x1, y1, x2, y2) = det["box"]
            label = det["label"]
            score = det["score"]

            # draw rectangle
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,255,0), 2)
            text = f"{label} {score:.2f}"
            cv2.putText(frame, text, (int(x1), int(y1)-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            # 3) check if bounding box is horizontally at center
            #    e.g. bounding box center within +/- 20px of screen center
            box_center_x = (x1 + x2) / 2
            if abs(box_center_x - center_screen_x) < 20:
                # => we consider that "centered"
                # 4) capture & save with detection result
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{label}_conf{score:.2f}.jpg"
                save_path = os.path.join("result_detections", filename)
                cv2.imwrite(save_path, frame)
                print(f"[CAPTURE] saved {save_path}")

        # show frame
        cv2.imshow("Detections", frame)

        # press ESC to quit
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_realtime_detection()
