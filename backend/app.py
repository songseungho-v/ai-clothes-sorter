# backend/app.py
from fastapi import FastAPI, UploadFile, File
from inference import classify_image

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "Clothes Classifier (Folder-based, EfficientNet-B3)"}

@app.post("/classify")
async def classify_item(file: UploadFile = File(...)):
    image_bytes = await file.read()
    label, confidence = classify_image(image_bytes)
    return {"label": label, "confidence": round(confidence,3)}
