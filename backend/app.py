# backend/app.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_module.inference import classify_image
from plc_comm.plc_client import set_valve, read_pressure

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 혹은 ["*"]로 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
@app.get("/")
def root():
    return {"message": "Hello from Stub-based backend"}

@app.post("/classify")
async def classify_item(file: UploadFile = File(...)):
    """
    Accept an image file, call AI stub
    Then do PLC stub logic
    """
    image_bytes = await file.read()
    category, confidence, status = classify_image(image_bytes)

    # Let's pretend we open the valve if status is "양호"
    if status == "양호":
        set_valve(on=True)
    else:
        set_valve(on=False)

    # read pressure just for demonstration
    pressure_value = read_pressure()

    return {
        "category": category,
        "confidence": confidence,
        "status": status,
        "pressure": pressure_value
    }

