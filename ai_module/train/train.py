# ai_module/train/train.py
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models
from ai_module.data_utils import get_data_loaders, CLASSES

def train_model(train_json, val_json, num_epochs=5, lr=0.001):
    # 1) DataLoader
    train_loader, val_loader = get_data_loaders(train_json, val_json, batch_size=32)

    # 2) Pretrained ResNet18 or EfficientNet
    model = models.resnet18(pretrained=True)
    # 최종 레이어 -> 4개 클래스
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES))

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        for imgs, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(imgs)  # shape [B,4]
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        avg_loss = total_loss / len(train_loader)
        print(f"[TRAIN] Epoch {epoch+1}/{num_epochs} Loss={avg_loss:.4f}")

        # Validation
        model.eval()
        correct, total = 0,0
        with torch.no_grad():
            for vimgs, vlabels in val_loader:
                vouts = model(vimgs)
                _, preds = torch.max(vouts, 1)
                correct += (preds==vlabels).sum().item()
                total += len(vlabels)
        val_acc = correct/total
        print(f"[VAL] Accuracy: {val_acc:.4f}")

    # Save
    torch.save(model.state_dict(), "model_files/model_v1.0.pth")
    print("Model saved -> model_files/model_v1.0.pth")

if __name__=="__main__":
    train_model("dataset/train.json", "dataset/val.json", num_epochs=5)
