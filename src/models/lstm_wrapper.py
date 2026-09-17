# -*- coding: utf-8 -*-
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

class LSTMRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, lookback=30, units=64, epochs=30, batch_size=32):
        self.lookback = lookback
        self.units = units
        self.epochs = epochs
        self.batch_size = batch_size
        self.model = None
        self.n_features_ = None

    def _build(self, n_features):
        model = Sequential([
            LSTM(self.units, activation='tanh', input_shape=(self.lookback, n_features), return_sequences=True),
            Dropout(0.2),
            LSTM(self.units//2, activation='tanh'),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def _to_sequences(self, X, y=None):
        # X: (n_samples, n_features) 按时间顺序
        seq_X, seq_y = [], []
        for i in range(self.lookback, len(X)):
            seq_X.append(X[i-self.lookback:i, :])
            if y is not None:
                seq_y.append(y[i])
        return np.array(seq_X), (np.array(seq_y) if y is not None else None)

    def fit(self, X, y):
        X = np.asarray(X, dtype='float32')
        y = np.asarray(y, dtype='float32')
        self.n_features_ = X.shape[1]
        self.model = self._build(self.n_features_)
        Xs, ys = self._to_sequences(X, y)
        es = EarlyStopping(monitor='loss', patience=5, restore_best_weights=True)
        self.model.fit(Xs, ys, epochs=self.epochs, batch_size=self.batch_size, verbose=0, callbacks=[es])
        return self

    def predict(self, X):
        X = np.asarray(X, dtype='float32')
        Xs, _ = self._to_sequences(X)
        # 对于前lookback步无法预测，前置NaN并对齐长度
        preds = self.model.predict(Xs, verbose=0).flatten()
        pad = np.full((self.lookback,), np.nan)
        return np.concatenate([pad, preds])
