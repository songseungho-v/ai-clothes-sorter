import os
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from torchvision import models, transforms, datasets
from tqdm import tqdm


def train_efficientnet_b3_all_logging(
        data_dir="data",
        num_epochs=5,
        lr=0.001,
        batch_size=32,
        log_dir="runs/exp_all_logging2",
        model_out="model_files/model_effb3.pth"
):
    """
    EfficientNet-B3 모델로 학습 + TensorBoard 로그를 기록하는 함수.

    Args:
        data_dir (str): 데이터 상위 폴더. 내부 구조: data/train/<class>/, data/val/<class>/.
        num_epochs (int): 학습 epoch 수.
        lr (float): 학습률(learning rate).
        batch_size (int): 배치 크기.
        log_dir (str): TensorBoard 로그를 저장할 경로.
        model_out (str): 학습 완료 후 모델 state를 저장할 경로.

    Returns:
        None
    """

    # -----------------------
    # 0) 장치(디바이스) 설정
    # -----------------------
    # macOS M1/M2 + PyTorch MPS, 일반 CUDA 환경이면 "cuda"
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[INFO] Training on device: {device}")

    # -----------------------
    # 1) Transforms
    # -----------------------
    # EfficientNet-B3는 300×300 권장.
    # 필요 시 224×224로도 가능하지만 정확도에 약간 차이 발생할 수 있음.
    train_transform = transforms.Compose([
        transforms.Resize((300, 300)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    val_transform = transforms.Compose([
        transforms.Resize((300, 300)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # -----------------------
    # 2) 데이터셋 / DataLoader
    # -----------------------
    train_dir = os.path.join(data_dir, "train")
    val_dir = os.path.join(data_dir, "val")

    # ImageFolder: train/<class>/..., val/<class>/... 폴더 구조
    # 해당 폴더 내에 클래스별로 이미지가 저장되어 있어야 함.
    train_dataset = datasets.ImageFolder(train_dir, transform=train_transform)
    val_dataset = datasets.ImageFolder(val_dir, transform=val_transform)

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=4, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=4, pin_memory=True
    )

    # classes 리스트(예: ["니트", "맨투맨", "바지", "아우터", "얇은의류", "후드티"] 등)
    classes = train_dataset.classes
    print(f"[INFO] Found classes: {classes}")

    # -----------------------
    # 3) 모델 준비 (EfficientNet-B3)
    # -----------------------
    # 사전학습된 EfficientNet-B3 불러옴 (torchvision>=0.13)
    model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)

    # 마지막 레이어 교체 -> len(classes)개
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(classes))

    model.to(device)

    # -----------------------
    # 4) 손실함수 / 옵티마이저
    # -----------------------
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # (Optional) 학습률 스케줄러
    # scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

    # -----------------------
    # 5) TensorBoard 설정
    # -----------------------
    writer = SummaryWriter(log_dir=log_dir)

    # 샘플 이미지를 한 배치 가져와서 모델 그래프 기록
    sample_imgs, _ = next(iter(train_loader))
    sample_imgs = sample_imgs.to(device)
    writer.add_graph(model, sample_imgs)

    # -----------------------
    # 6) 학습 루프
    # -----------------------
    global_step = 0
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0

        train_pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{num_epochs}", unit="batch")
        for batch_idx, (imgs, labels) in enumerate(train_pbar):
            imgs, labels = imgs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

            # training accuracy
            _, preds = torch.max(outputs, 1)
            correct_train += (preds == labels).sum().item()
            total_train += labels.size(0)

            # 현재 학습률
            current_lr = optimizer.param_groups[0]['lr']
            train_pbar.set_postfix({
                "loss": f"{loss.item():.4f}",
                "lr": f"{current_lr:.6f}"
            })

            # 배치 단위 로그
            writer.add_scalar("Train/Loss_batch", loss.item(), global_step)
            writer.add_scalar("Train/LR_batch", current_lr, global_step)

            global_step += 1

        # 에폭 단위 Loss/Acc
        avg_loss = running_loss / len(train_loader)
        train_acc = correct_train / total_train

        print(f"[TRAIN] Epoch {epoch + 1}, Loss={avg_loss:.4f}, Acc={train_acc:.4f}")
        writer.add_scalar("Train/Loss_epoch", avg_loss, epoch)
        writer.add_scalar("Train/Acc_epoch", train_acc, epoch)

        # (에폭 끝) 모델 파라미터 / 그라디언트 히스토그램
        for name, param in model.named_parameters():
            param_cpu = param.detach().cpu().float()
            writer.add_histogram(f"params/{name}", param_cpu, epoch)
            if param.grad is not None:
                grad_cpu = param.grad.detach().cpu().float()
                writer.add_histogram(f"grads/{name}", grad_cpu, epoch)

        # (Optional) 스케줄러
        # scheduler.step()

        # -----------------------
        # 7) 검증 루프
        # -----------------------
        model.eval()
        correct_val = 0
        total_val = 0
        val_loss = 0.0

        with torch.no_grad():
            for vimgs, vlabels in val_loader:
                vimgs, vlabels = vimgs.to(device), vlabels.to(device)
                vouts = model(vimgs)
                vloss = criterion(vouts, vlabels)
                val_loss += vloss.item()

                _, preds = torch.max(vouts, 1)
                correct_val += (preds == vlabels).sum().item()
                total_val += len(vlabels)

        avg_val_loss = val_loss / len(val_loader)
        val_acc = correct_val / total_val
        print(f"[VAL]   Epoch {epoch + 1}, Loss={avg_val_loss:.4f}, Acc={val_acc:.4f}")

        writer.add_scalar("Val/Loss_epoch", avg_val_loss, epoch)
        writer.add_scalar("Val/Acc_epoch", val_acc, epoch)

    # -----------------------
    # 8) 모델 저장 + 마무리
    # -----------------------
    torch.save({
        "model_state": model.state_dict(),
        "classes": classes
    }, model_out)

    writer.close()
    print(f"[INFO] Training complete. Model saved to {model_out}")
    print(f"[INFO] TensorBoard logs saved in {log_dir}")


if __name__ == "__main__":
    # 사용 예시
    train_efficientnet_b3_all_logging(
        data_dir="data",
        num_epochs=5,
        lr=0.001,
        batch_size=32,
        log_dir="runs/exp_all_logging0318",
        model_out="model_files/model_effb3.pth"
    )
