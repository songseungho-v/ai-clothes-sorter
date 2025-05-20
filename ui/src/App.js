import React, { useState, useEffect, useRef } from "react";

function App() {
  const videoRef = useRef(null);
  const captureCanvasRef = useRef(null);    // 서버 전송용 (hidden)
  const processedCanvasRef = useRef(null);    // 분석된 영상 표시용 (visible)
  const wsRef = useRef(null);

  // 사용 가능한 카메라와 선택된 장치 상태 관리
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState("");

  // 분류 결과 (카테고리와 신뢰도)
  const [classification, setClassification] = useState({ label: "", confidence: 0 });

  // 프레임 처리 상태를 추적하기 위한 ref
  const processingRef = useRef(false);

  // 1. 사용 가능한 카메라 목록 가져오기
  useEffect(() => {
    async function getVideoDevices() {
      try {
        const allDevices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = allDevices.filter((device) => device.kind === "videoinput");
        setDevices(videoDevices);
        if (videoDevices.length > 0) {
          setSelectedDevice(videoDevices[0].deviceId);
        }
      } catch (err) {
        console.error("카메라 디바이스 가져오기 에러:", err);
      }
    }
    getVideoDevices();
  }, []);

  // 2. 선택한 카메라로 스트림 시작하기
  useEffect(() => {
    async function startStream() {
      if (selectedDevice) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { exact: selectedDevice } }
          });
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
          }
        } catch (err) {
          console.error("스트림 시작 에러:", err);
        }
      }
    }
    startStream();
  }, [selectedDevice]);

  // 3. WebSocket 연결하여 실시간 분류 결과 수신
  useEffect(() => {
    wsRef.current = new WebSocket("ws://localhost:8000/ws");
    wsRef.current.onopen = () => console.log("WebSocket 연결됨");
    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // 분류 결과를 받으면, 처리 상태를 false로 변경하여 다음 프레임 전송 허용
        setClassification(data);
      } catch (err) {
        console.error("WebSocket 메시지 파싱 에러:", err);
      } finally {
        processingRef.current = false;
      }
    };
    wsRef.current.onerror = (error) => {
      console.error("WebSocket 에러:", error);
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // 4. 주기적으로 영상 프레임 캡처 후 WebSocket 전송 (처리 중이 아닐 때만 전송)
  useEffect(() => {
    const interval = setInterval(() => {
      // 새로운 프레임을 전송하기 전, 이전 프레임 처리가 완료되었는지 확인
      if (
        videoRef.current &&
        captureCanvasRef.current &&
        wsRef.current &&
        wsRef.current.readyState === WebSocket.OPEN &&
        !processingRef.current &&
        videoRef.current.videoWidth > 0 // 영상 크기가 유효한 경우
      ) {
        processingRef.current = true;  // 현재 프레임 처리 시작 표시
        const video = videoRef.current;
        const captureCanvas = captureCanvasRef.current;
        captureCanvas.width = video.videoWidth;
        captureCanvas.height = video.videoHeight;
        const capCtx = captureCanvas.getContext("2d");
        capCtx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
        const imageData = captureCanvas.toDataURL("image/jpeg");
        wsRef.current.send(imageData);
      }
    }, 50);  // 500ms 간격
    return () => clearInterval(interval);
  }, []);

  // 5. 주기적으로 분석된 영상(오버레이 결과) 업데이트
  useEffect(() => {
    const interval = setInterval(() => {
      if (videoRef.current && processedCanvasRef.current) {
        const video = videoRef.current;
        const procCanvas = processedCanvasRef.current;
        procCanvas.width = video.videoWidth;
        procCanvas.height = video.videoHeight;
        const procCtx = procCanvas.getContext("2d");
        procCtx.drawImage(video, 0, 0, procCanvas.width, procCanvas.height);
        procCtx.font = "30px Arial";
        procCtx.fillStyle = "red";
        if (classification.label) {
          procCtx.fillText(
            `${classification.label} (${(classification.confidence * 100).toFixed(1)}%)`,
            10,
            40
          );
        }
      }
    }, 50);
    return () => clearInterval(interval);
  }, [classification]);

  // 6. 카메라 선택 핸들러
  const handleDeviceChange = (e) => {
    setSelectedDevice(e.target.value);
  };

  return (
    <div style={{ textAlign: "center" }}>
      <h1>실시간 옷 분류</h1>
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="deviceSelect">카메라 선택: </label>
        <select id="deviceSelect" onChange={handleDeviceChange} value={selectedDevice}>
          {devices.map((device, idx) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label || `Camera ${idx + 1}`}
            </option>
          ))}
        </select>
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: "1rem" }}>
        <div>
          <h3>실시간 영상 (원본)</h3>
          <video
            ref={videoRef}
            style={{ width: "640px", height: "480px", border: "1px solid #ccc" }}
            autoPlay
            muted
          />
        </div>
        <div>
          <h3>분석된 영상</h3>
          <canvas
            ref={processedCanvasRef}
            style={{ width: "640px", height: "480px", border: "1px solid #ccc" }}
          />
        </div>
      </div>
      {/* 서버 전송용 캔버스는 숨김 */}
      <canvas ref={captureCanvasRef} style={{ display: "none" }} />
      <div style={{ marginTop: "1rem" }}>
        <h2>분류 결과</h2>
        <p>카테고리: {classification.label}</p>
        <p>신뢰도: {classification.confidence}</p>
      </div>
    </div>
  );
}

export default App;
