# backend/app.py
from fastapi import FastAPI, UploadFile, File
from ai_module.inference import classify_image

app = FastAPI()

@app.get("/")
def root():
    return {"message":"Welcome to clothes classifier (4 classes)"}

@app.post("/classify")
async def classify_item(file: UploadFile = File(...)):
    image_bytes = await file.read()
    label, confidence = classify_image(image_bytes)
    return {"label": label, "confidence": round(confidence,3)}
