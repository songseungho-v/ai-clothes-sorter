# 이미지 디코딩 검증 예제: 수신된 jpg_bytes를 파일로 저장하고 OpenCV로 확인
import cv2
import numpy as np
import pathlib

# 예시: MQTT 수신 콜백 내부에서 받은 이미지 바이트가 있다고 가정
def verify_and_decode_image(jpg_bytes):
    debug_dir = pathlib.Path("debug_recv")
    debug_dir.mkdir(exist_ok=True)

    # 1. 파일로 저장
    debug_file_path = debug_dir / "received.jpg"
    with open(debug_file_path, "wb") as f:
        f.write(jpg_bytes)
    print(f"💾 수신된 이미지 저장: {debug_file_path}")

    # 2. OpenCV로 디코딩 테스트
    jpg_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
    decoded = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)

    if decoded is None:
        print("❌ OpenCV 디코딩 실패: 이미지가 손상되었거나 잘못된 형식입니다.")
    else:
        print(f"✅ 디코딩 성공: shape = {decoded.shape}")
        cv2.imshow("Decoded Image", decoded)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return decoded

# 수동 테스트용 (jpg_bytes를 테스트용으로 불러올 수도 있음)
if __name__ == "__main__":
    try:
        with open("debug_recv/received.jpg", "rb") as f:
            raw_bytes = f.read()
        verify_and_decode_image(raw_bytes)
    except FileNotFoundError:
        print("⚠️ 테스트용 이미지 파일이 없습니다. 먼저 MQTT로 수신 후 저장하세요.")
