# ai_module/inference.py
import torch
import io
from PIL import Image
from torchvision import models
import torch.nn as nn
import torchvision.transforms as T
from ai_module.data_utils import CLASSES

model = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

infer_transform = T.Compose([
    T.Resize((224,224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
])

def load_model_once():
    global model
    if model is None:
        print("[INFO] Loading model_v1.0.pth ...")
        net = models.resnet18()
        net.fc = nn.Linear(net.fc.in_features, len(CLASSES))
        net.load_state_dict(torch.load("model_files/model_v1.0.pth", map_location=device))
        net.eval()
        net.to(device)
        model = net

def classify_image(image_bytes: bytes):
    load_model_once()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = infer_transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.softmax(outputs, dim=1)
        top_prob, top_idx = probs.max(dim=1)

    label = CLASSES[top_idx.item()]
    confidence = top_prob.item()
    return label, confidence
