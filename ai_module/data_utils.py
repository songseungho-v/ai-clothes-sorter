# ai_module/data_utils.py
import json
import os
from PIL import Image
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T

# 사용자 지정 세부 클래스 (전체 목록)
CLASSES = [
    "가디건",
    "맨투맨",
    "면바지",
    "반바지",
    "반팔셔츠",
    "반팔티",
    "블라우스",
    "셔츠",
    "스웨터",
    "원피스",
    "청바지",
    "후드티"
]

# EfficientNet-B3 보통 300x300
train_transform = T.Compose([
    T.Resize((300,300)),
    T.RandomHorizontalFlip(),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

val_transform = T.Compose([
    T.Resize((300,300)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

class JsonLabelDataset(Dataset):
    """
    JSON 예시:
    [
      { "image_path":"dataset/images/001.jpg", "label":"반팔 티셔츠" },
      { "image_path":"dataset/images/002.jpg", "label":"청치마(Denim Skirt)" },
      ...
    ]
    """
    def __init__(self, json_path, transform=None, classes=None):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.annotations = json.load(f)

        if classes is None:
            raise ValueError("Must provide classes list.")
        self.classes = classes
        self.label2idx = {c: i for i, c in enumerate(self.classes)}

        self.transform = transform

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, idx):
        item = self.annotations[idx]
        img_path = item["image_path"]
        label_str = item["label"]

        if label_str not in self.label2idx:
            raise ValueError(f"Label {label_str} not in classes: {self.classes}")

        label_idx = self.label2idx[label_str]

        img = Image.open(img_path).convert("RGB")
        if self.transform:
            img = self.transform(img)

        return img, label_idx

def get_data_loaders(train_json, val_json, batch_size=32):
    train_ds = JsonLabelDataset(train_json, transform=train_transform, classes=CLASSES)
    val_ds   = JsonLabelDataset(val_json,   transform=val_transform,   classes=CLASSES)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)

    return train_loader, val_loader
