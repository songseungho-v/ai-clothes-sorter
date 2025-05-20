from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import base64
import io
from ai_module.inference import classify_image

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def root():
    return {"msg": "Clothes Classifier (Folder-based, EfficientNet-B3)"}

@app.post("/classify")
async def classify_item(file: UploadFile = File(...)):
    image_bytes = await file.read()
    label, confidence = classify_image(image_bytes)
    return {"label": label, "confidence": round(confidence, 3)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
        except Exception:
            break
        # data는 base64 인코딩된 이미지 문자열 (예: "data:image/jpeg;base64,....")
        if ',' in data:
            header, encoded = data.split(',', 1)
        else:
            encoded = data
        try:
            image_bytes = base64.b64decode(encoded)
        except Exception as e:
            await websocket.send_json({"error": "Invalid image data"})
            continue

        try:
            label, confidence = classify_image(image_bytes)
            result = {"label": label, "confidence": round(confidence, 3)}
        except Exception as e:
            # 예외 발생 시 에러 메시지를 전송하여 프론트엔드에서 확인할 수 있도록 함
            result = {"error": str(e)}
        await websocket.send_json(result)

