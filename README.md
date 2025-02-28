# ai-clothes-sorter

# AI Clothes Sorter

## Overview
- Python + FastAPI (backend)
- AI (PyTorch) for classification
- PLC for controlling air gripper, sensors
- UI (React)

## Project Structure

##통합 흐름 테스트(Manual)
백엔드 실행: uvicorn backend.app:app --reload

UI 실행: npm start (React dev server)

브라우저: http://localhost:3000 (UI)

파일 선택 → “Classify” → 백엔드 /classify 호출 → AI Stub & PLC Stub 동작
결과: Category, Confidence, Status, Pressure 표시
Console 확인

백엔드 터미널 로그: “Valve set to: True/False”
UI 콘솔(개발자도구)에서 POST 응답/에러 확인
