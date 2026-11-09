"""
Deep Metric Learning (Triplet Network) Fine-Tuning Script.
Trains a feature embedder (MobileNetV3 / ResNet) with Triplet Margin Loss
to project staff tag visual crops into a compact metric embedding space.
"""

import os
import random
import argparse
from pathlib import Path
from PIL import Image

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import torchvision.models as models

class TripletTagDataset(Dataset):
    """
    Dataset loader generating (Anchor, Positive, Negative) triplets:
    - Anchor: Staff tag crop
    - Positive: Same staff tag under different frame / rotation / lighting
    - Negative: Distractor (shirt pattern, desk, shadow, other employee)
    """
    def __init__(self, data_root: str, transform=None, samples_per_epoch: int = 1000):
        self.root = Path(data_root)
        self.transform = transform
        self.samples_per_epoch = samples_per_epoch

        self.pos_dir = self.root / "triplet_crops" / "positive"
        self.neg_dir = self.root / "triplet_crops" / "negative"

        self.pos_files = list(self.pos_dir.glob("*.jpg")) if self.pos_dir.exists() else []
        self.neg_files = list(self.neg_dir.glob("*.jpg")) if self.neg_dir.exists() else []

        print(f"Loaded {len(self.pos_files)} positive crops, {len(self.neg_files)} negative crops.")

    def __len__(self):
        return self.samples_per_epoch

    def __getitem__(self, idx):
        if not self.pos_files or not self.neg_files:
            # Fallback dummy tensors if dataset directory is empty
            dummy = torch.zeros(3, 128, 128)
            return dummy, dummy, dummy

        # Randomly choose anchor
        anchor_path = random.choice(self.pos_files)
        # Positive: choose another positive or perturbed version of anchor
        pos_path = random.choice(self.pos_files)
        # Negative: choose distractor
        neg_path = random.choice(self.neg_files)

        anchor_img = Image.open(anchor_path).convert("RGB")
        pos_img = Image.open(pos_path).convert("RGB")
        neg_img = Image.open(neg_path).convert("RGB")

        if self.transform:
            anchor_img = self.transform(anchor_img)
            pos_img = self.transform(pos_img)
            neg_img = self.transform(neg_img)

        return anchor_img, pos_img, neg_img

class TagEmbedder(nn.Module):
    """
    Compact Visual Embedding Network (128-dim L2-normalized representation).
    """
    def __init__(self, embedding_dim: int = 128):
        super().__init__()
        backbone = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
        self.features = backbone.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.head = nn.Sequential(
            nn.Linear(576, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Linear(256, embedding_dim)
        )

    def forward(self, x):
        feat = self.features(x)
        feat = self.pool(feat).flatten(1)
        emb = self.head(feat)
        # L2 normalize embeddings so Euclidean distance equals Cosine similarity
        emb = nn.functional.normalize(emb, p=2, dim=1)
        return emb

def train_embedder(
    data_dir: str,
    epochs: int = 20,
    batch_size: int = 32,
    lr: float = 1e-4,
    margin: float = 0.3,
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
):
    print(f"--- Starting Deep Metric Learning Embedder Training ---")
    print(f"Device: {device}, Batch size: {batch_size}, Epochs: {epochs}, Triplet Margin: {margin}")

    # Top-down fisheye augmentations
    transform_train = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.RandomRotation(30),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    dataset = TripletTagDataset(data_dir, transform=transform_train, samples_per_epoch=1200)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)

    model = TagEmbedder(embedding_dim=128).to(device)
    criterion = nn.TripletMarginLoss(margin=margin, p=2)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_loss = float("inf")
    output_dir = Path("../models")
    output_dir.mkdir(parents=True, exist_ok=True)
    best_weights_path = output_dir / "tag_embedder_best.pth"

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for batch_i, (anchor, pos, neg) in enumerate(loader):
            anchor = anchor.to(device)
            pos = pos.to(device)
            neg = neg.to(device)

            optimizer.zero_grad()
            emb_a = model(anchor)
            emb_p = model(pos)
            emb_n = model(neg)

            loss = criterion(emb_a, emb_p, emb_n)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / max(1, len(loader))
        scheduler.step()
        print(f"Epoch [{epoch:02d}/{epochs:02d}] - Triplet Loss: {avg_loss:.4f}")

        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(model.state_dict(), best_weights_path)
            print(f"   => New best model saved (loss: {best_loss:.4f}) to {best_weights_path}")

    print("--- Embedder Training Completed Successfully! ---")
    return model

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Metric Learning Tag Embedder")
    parser.add_argument("--data", type=str, default="./dataset", help="Dataset directory")
    parser.add_argument("--epochs", type=int, default=15, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--margin", type=float, default=0.3, help="Triplet margin")
    args = parser.parse_args()

    train_embedder(args.data, args.epochs, args.batch_size, args.lr, args.margin)

