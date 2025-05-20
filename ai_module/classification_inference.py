# classification_inference.py
import torch
import torchvision.transforms as T
import torchvision
import torch.nn as nn
from PIL import Image
import os

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

tops_model, bottoms_model, outer_model, skirt_model = None, None, None, None
tops_classes, bottoms_classes, outer_classes, skirt_classes = [],[],[],[]

def load_all_clf_models_once():
    global tops_model, bottoms_model, outer_model, skirt_model
    global tops_classes, bottoms_classes, outer_classes, skirt_classes
    if tops_model is not None:
        return  # already loaded

    def load_model(path):
        checkpoint = torch.load(path, map_location=device)
        classes = checkpoint["classes"]
        net = torchvision.models.efficientnet_b3(weights=None)
        in_features = net.classifier[1].in_features
        net.classifier[1] = nn.Linear(in_features, len(classes))
        net.load_state_dict(checkpoint["model_state"])
        net.eval()
        net.to(device)
        return net, classes

    test_path ="/Users/songseungho/Desktop/making program/Project_ai_clothes/ai-clothes-sorter/model_files/model_effb3.pth"
    # 예) model_files/effb3_tops.pth, effb3_bottoms.pth, effb3_outer.pth, effb3_skirt.pth
    tops_model, tops_classes   = load_model(test_path)
    bottoms_model, bottoms_classes = load_model(test_path)
    outer_model, outer_classes = load_model(test_path)
    skirt_model, skirt_classes = load_model(test_path)
    #skirt_model, skirt_classes = load_model("model_files/effb3_skirt.pth")

def classify_fine(image_pil, big_cat):
    """
    image_pil: PIL Image (crop)
    big_cat: one of ["상의","하의","아우터","치마"]
    return: (fine_label, confidence)
    """
    load_all_clf_models_once()

    if big_cat == "상의":
        model = tops_model
        classes = tops_classes
    elif big_cat == "하의":
        model = bottoms_model
        classes = bottoms_classes
    elif big_cat == "아우터":
        model = outer_model
        classes = outer_classes
    elif big_cat == "치마":
        model = skirt_model
        classes = skirt_classes
    else:
        # default fallback
        return (big_cat, 1.0)

    transform = T.Compose([
        T.Resize((300,300)),
        T.ToTensor(),
        T.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
    ])

    x = transform(image_pil).unsqueeze(0).to(device)
    with torch.no_grad():
        outs = model(x)
        probs = torch.softmax(outs, dim=1)
        top_prob, top_idx = probs.max(dim=1)

    conf = top_prob.item()
    label_idx = top_idx.item()
    fine_label = classes[label_idx]
    return (fine_label, conf)
