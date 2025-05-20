# inference.py

import torch
import io
from PIL import Image
from torchvision import models
import torch.nn as nn
import torchvision.transforms as T
import time

model = None
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"[INFO] Training on device: {device}")
loaded_classes = None

infer_transform = T.Compose([
    T.Resize((300,300)),
    T.ToTensor(),
    T.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
])

def load_model_once():
    global model, loaded_classes
    if model is None:
        checkpoint = torch.load("model_files/model_effb3.pth", map_location=device)
        classes = checkpoint["classes"]  # list of folder-based classes
        loaded_classes = classes

        net = models.efficientnet_b3(weights=None)  # We'll load state dict
        in_features = net.classifier[1].in_features
        net.classifier[1] = nn.Linear(in_features, len(classes))
        net.load_state_dict(checkpoint["model_state"])
        net.eval()
        net.to(device)
        model = net


def classify_image(image_bytes: bytes):
    load_model_once()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = infer_transform(img).unsqueeze(0).to(device)

    start = time.time()  # 측정 시작
    with torch.no_grad():
        outputs = model(tensor)
    inference_time = (time.time() - start) * 1000  # ms 단위

    probs = torch.softmax(outputs, dim=1)
    top_prob, top_idx = probs.max(dim=1)

    print(f"Inference time: {inference_time:.2f} ms")

    label_idx = top_idx.item()
    label_str = loaded_classes[label_idx]
    confidence = top_prob.item()
    return label_str, confidence
