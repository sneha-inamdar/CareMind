"""
CareMind 1D Convolutional Neural Network (CNN) Subsystem for ECG Signal Analysis.

Implements a clean 1D CNN baseline model in PyTorch for learning continuous waveform representations
directly from raw 1D ECG time-series segments without requiring manual feature engineering.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from typing import Dict, Any, Tuple, Optional


class ECG1DCNN(nn.Module):
    """
    1D CNN architecture for 1D ECG waveform classification.
    
    Structure:
      Input (B, 1, L)
        ↓ Conv1d(1->16, k=7, s=2) + BatchNorm + ReLU + MaxPool(2)
      Feature Map 1
        ↓ Conv1d(16->32, k=5, s=2) + BatchNorm + ReLU + MaxPool(2)
      Feature Map 2
        ↓ Conv1d(32->64, k=3, s=2) + BatchNorm + ReLU + AdaptiveAvgPool(1)
      Global Representation (64)
        ↓ Linear(64->32) + ReLU + Dropout(0.2)
        ↓ Linear(32->2)
      Class Logits
    """

    def __init__(self, input_channels: int = 1, num_classes: int = 2):
        super(ECG1DCNN, self).__init__()
        
        self.feature_extractor = nn.Sequential(
            nn.Conv1d(input_channels, 16, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.MaxPool1d(2),
            
            nn.Conv1d(16, 32, kernel_size=5, stride=2, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
            
            nn.Conv1d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1)
        )
        
        self.classifier = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input shape expected: (Batch, Channels, Signal_Length)
        if x.dim() == 2:
            x = x.unsqueeze(1)
        feat = self.feature_extractor(x)
        feat = feat.view(feat.size(0), -1)
        logits = self.classifier(feat)
        return logits


class ECGCNNClassifier:
    """
    Scikit-learn compatible wrapper around PyTorch ECG 1D CNN model.
    """

    def __init__(self, epochs: int = 20, batch_size: int = 32, lr: float = 1e-3, random_state: int = 42):
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.random_state = random_state
        self.model: Optional[ECG1DCNN] = None
        self.device = torch.device("cpu")
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray):
        """Train 1D CNN on 1D ECG array X (N, L) and binary labels y (N,)."""
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)
        
        N, L = X.shape
        X_t = torch.tensor(X, dtype=torch.float32).unsqueeze(1) # (N, 1, L)
        y_t = torch.tensor(y, dtype=torch.long)
        
        dataset = TensorDataset(X_t, y_t)
        dataloader = DataLoader(dataset, batch_size=min(self.batch_size, max(1, N)), shuffle=True)
        
        self.model = ECG1DCNN(input_channels=1, num_classes=2).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=1e-4)
        
        self.model.train()
        for epoch in range(self.epochs):
            for batch_x, batch_y in dataloader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return class probabilities array (N, 2)."""
        if not self.is_fitted or self.model is None:
            raise ValueError("Model must be fitted before predict_proba.")
            
        self.model.eval()
        X_t = torch.tensor(X, dtype=torch.float32).unsqueeze(1).to(self.device)
        with torch.no_grad():
            logits = self.model(X_t)
            probs = torch.softmax(logits, dim=1).cpu().numpy()
        return probs

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Return binary class predictions (N,)."""
        probs = self.predict_proba(X)
        return (probs[:, 1] >= threshold).astype(int)
