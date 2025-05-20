# train_clf_tops.py
import os
import torch
import torchvision
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms, datasets

def train_clf_tops(data_dir="datasets/fine_tops", epochs=10, lr=0.001, out="model_files/effb3_tops.pth"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_tf = transforms.Compose([
        transforms.Resize((300,300)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
    ])
    val_tf = transforms.Compose([
        transforms.Resize((300,300)),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
    ])
    train_dataset = datasets.ImageFolder(os.path.join(data_dir,"train"), transform=train_tf)
    val_dataset   = datasets.ImageFolder(os.path.join(data_dir,"val"),   transform=val_tf)

    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader   = torch.utils.data.DataLoader(val_dataset,   batch_size=32, shuffle=False)

    classes = train_dataset.classes
    print("Classes:", classes)

    model = torchvision.models.efficientnet_b3(weights=torchvision.models.EfficientNet_B3_Weights.IMAGENET1K_V1)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(classes))
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        model.train()
        total_loss, correct, total = 0, 0, 0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outs = model(imgs)
            loss = criterion(outs, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            _, preds = outs.max(dim=1)
            correct += (preds==labels).sum().item()
            total   += labels.size(0)

        train_acc = correct/total
        avg_loss = total_loss/len(train_loader)
        print(f"[Train] epoch={epoch+1}, loss={avg_loss:.3f}, acc={train_acc:.3f}")

        # validation
        model.eval()
        val_loss, val_correct, val_total = 0, 0, 0
        with torch.no_grad():
            for vimgs, vlabels in val_loader:
                vimgs, vlabels = vimgs.to(device), vlabels.to(device)
                vouts = model(vimgs)
                vloss = criterion(vouts, vlabels)
                val_loss += vloss.item()

                _, vpreds = vouts.max(dim=1)
                val_correct += (vpreds==vlabels).sum().item()
                val_total   += vlabels.size(0)
        val_acc = val_correct/val_total
        val_loss /= len(val_loader)
        print(f"[Val] epoch={epoch+1}, loss={val_loss:.3f}, acc={val_acc:.3f}")

    # save
    savedict = {
        "model_state": model.state_dict(),
        "classes": classes
    }
    torch.save(savedict, out)
    print(f"Saved => {out}")

if __name__=="__main__":
    train_clf_tops()
