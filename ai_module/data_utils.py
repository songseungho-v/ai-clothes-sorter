# ai_module/data_utils.py
import json
import os
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from PIL import Image

CLASSES = ["상의", "하의", "치마", "아우터"]  # 4개

# 전처리
train_transform = T.Compose([
    T.Resize((224,224)),
    T.RandomHorizontalFlip(),
    T.ToTensor(),
    T.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
])

val_transform = T.Compose([
    T.Resize((224,224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
])

class JsonLabelDataset(Dataset):
    def __init__(self, json_path, transform=None, classes=None):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.annotations = json.load(f)  # [ { image_path, label }, ... ]

        if classes is None:
            raise ValueError("Must provide classes list.")
        self.classes = classes
        self.label2idx = {c: i for i, c in enumerate(self.classes)}

        self.transform = transform

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, idx):
        item = self.annotations[idx]
        img_path = item["image_path"]  # e.g. "dataset/images/001.jpg"
        label_str = item["label"]      # e.g. "상의"

        if label_str not in self.label2idx:
            raise ValueError(f"Label {label_str} not in {self.classes}")

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

#"반팔티","치마","원피스","청바지","카고바지","면바지","트레이닝바지","트레이닝상의","긴팔티","셔츠","후드티","반바지","자켓","패딩","코트","맨투맨"