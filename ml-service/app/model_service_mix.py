from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge


def train_ridge_shares(X: np.ndarray, Y: np.ndarray, alpha: float = 1.0) -> Ridge:
    m = Ridge(alpha=alpha)
    m.fit(X, Y)
    return m


def predict_shares(model: Ridge, X: np.ndarray) -> np.ndarray:
    p = model.predict(X)
    p = np.maximum(p, 0.0)
    s = p.sum(axis=1, keepdims=True)
    s[s == 0] = 1.0
    return p / s


def multinomial_log_loss(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-12) -> float:
    yp = np.clip(y_pred, eps, 1.0)
    return float(-np.mean(np.sum(y_true * np.log(yp), axis=1)))
