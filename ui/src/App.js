// ui/src/App.js
import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await axios.post("http://localhost:8000/classify", formData, {
        headers: {"Content-Type": "multipart/form-data"}
      });
      setResult(resp.data);
    } catch(err) {
      console.error(err);
    }
  };

  return (
    <div>
      <h1>Stub-based Classification</h1>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleSubmit}>Classify</button>
      {result &&
        <div>
          <p>Category: {result.category}</p>
          <p>Confidence: {result.confidence}</p>
          <p>Status: {result.status}</p>
          <p>Pressure: {result.pressure}</p>
        </div>
      }
    </div>
  );
}

export default App;
