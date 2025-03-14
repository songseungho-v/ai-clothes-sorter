import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from torchvision import models, datasets, transforms
from tqdm import tqdm

def train_efficientnet_b3_all_logging(
    data_dir="data",
    num_epochs=5,
    lr=0.001,
    batch_size=32
):
    """
    data_dir:
      상위 폴더, 구조는 data/train/<class>/, data/val/<class>/ 로 저장
    """

    # -----------------------
    # 0) 장치 설정
    # -----------------------
    # macOS M1/M2 + PyTorch MPS 지원을 가정한 예시
    # (일반 CUDA 사용 환경이면 "cuda"로 바꿔도 됨)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[INFO] Training on device: {device}")

    # -----------------------
    # 1) Transforms
    # -----------------------
    train_transform = transforms.Compose([
        transforms.Resize((300, 300)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
    ])
    val_transform = transforms.Compose([
        transforms.Resize((300, 300)),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])
    ])

    # -----------------------
    # 2) 데이터셋 / DataLoader
    # -----------------------
    train_dataset = datasets.ImageFolder(f"{data_dir}/train", transform=train_transform)
    val_dataset   = datasets.ImageFolder(f"{data_dir}/val",   transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_dataset,   batch_size=batch_size, shuffle=False,
                              num_workers=4, pin_memory=True)

    classes = train_dataset.classes
    print(f"[INFO] Found classes: {classes}")

    # -----------------------
    # 3) 모델 준비 (EfficientNet-B3)
    # -----------------------
    model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)
    # 마지막 레이어 교체
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(classes))

    model.to(device)

    # -----------------------
    # 4) 손실함수 / 옵티마이저
    # -----------------------
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # (Optional) 학습률 스케줄러 예시
    # scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

    # -----------------------
    # 5) TensorBoard 설정
    # -----------------------
    writer = SummaryWriter(log_dir="runs/exp_all_logging")

    # -- (5a) 모델 그래프 기록 --
    # 그래프를 기록하려면, 예시용으로 실제 이미지 한 배치를 가져와서 forward를 수행해야 함
    sample_imgs, _ = next(iter(train_loader))
    sample_imgs = sample_imgs.to(device)
    writer.add_graph(model, sample_imgs)
    # 그래프 탭에서 모델 구조를 확인할 수 있음

    # -----------------------
    # 6) 학습 루프
    # -----------------------
    global_step = 0
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train   = 0

        # tqdm으로 진행 바 표시
        train_pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}", unit="batch")
        for batch_idx, (imgs, labels) in enumerate(train_pbar):
            imgs, labels = imgs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

            # (Optional) Training Accuracy도 측정
            _, preds = torch.max(outputs, 1)
            correct_train += (preds == labels).sum().item()
            total_train   += labels.size(0)

            # 현재 배치의 학습률 (Adam은 하나의 param_group만 있다고 가정)
            current_lr = optimizer.param_groups[0]['lr']

            # tqdm 진행 바 업데이트
            train_pbar.set_postfix({
                "loss": f"{loss.item():.4f}",
                "lr": f"{current_lr:.6f}"
            })

            # 배치 단위 TensorBoard 기록
            writer.add_scalar("Train/Loss_batch", loss.item(), global_step)
            writer.add_scalar("Train/LR_batch",   current_lr,   global_step)

            global_step += 1

        # 에폭 단위 Training Loss / Accuracy
        avg_loss = running_loss / len(train_loader)
        train_acc = correct_train / total_train

        print(f"[TRAIN] Epoch {epoch+1}, Loss={avg_loss:.4f}, Acc={train_acc:.4f}")
        writer.add_scalar("Train/Loss_epoch", avg_loss,  epoch)
        writer.add_scalar("Train/Acc_epoch",  train_acc, epoch)

        # -- (6a) 에폭 끝나고 파라미터 히스토그램 기록 --
        # 모델의 모든 파라미터(가중치, 편향)에 대해 히스토그램 작성
        for name, param in model.named_parameters():
            #print(name, param.dtype, param.shape)
            # 파라미터를 CPU(float)로 강제 변환
            param_cpu = param.detach().cpu().float()
            writer.add_histogram(f"params/{name}", param_cpu, epoch)

            if param.grad is not None:
                grad_cpu = param.grad.detach().cpu().float()
                writer.add_histogram(f"grads/{name}", grad_cpu, epoch)

        # (Optional) 스케줄러 사용 시 에폭 마다 step
        # scheduler.step()

        # -----------------------
        # 7) 검증 루프
        # -----------------------
        model.eval()
        correct_val = 0
        total_val   = 0
        val_loss    = 0.0
        with torch.no_grad():
            for vimgs, vlabels in val_loader:
                vimgs, vlabels = vimgs.to(device), vlabels.to(device)
                vouts = model(vimgs)
                vloss = criterion(vouts, vlabels)
                val_loss += vloss.item()

                _, preds = torch.max(vouts, 1)
                correct_val += (preds == vlabels).sum().item()
                total_val   += len(vlabels)

        avg_val_loss = val_loss / len(val_loader)
        val_acc      = correct_val / total_val
        print(f"[VAL]   Epoch {epoch+1}, Loss={avg_val_loss:.4f}, Acc={val_acc:.4f}")

        # 검증 결과 TensorBoard 기록 (에폭 단위)
        writer.add_scalar("Val/Loss_epoch", avg_val_loss, epoch)
        writer.add_scalar("Val/Acc_epoch",  val_acc,      epoch)

    # -----------------------
    # 8) 모델 저장 + 마무리
    # -----------------------
    torch.save({
        "model_state": model.state_dict(),
        "classes": classes
    }, "model_files/model_effb3.pth")

    writer.close()
    print("[INFO] Training complete. Model & logs saved.")

if __name__ == "__main__":
    train_efficientnet_b3_all_logging(
        data_dir="data",
        num_epochs=5,
        lr=0.001,
        batch_size=32
    )
