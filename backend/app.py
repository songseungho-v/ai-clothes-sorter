# backend/app.py

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from backend skeleton"}

# 실행(개발용): uvicorn backend.app:app --reload
