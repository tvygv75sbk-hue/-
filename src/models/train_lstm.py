# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
from lstm_wrapper import LSTMRegressor
from sklearn.metrics import mean_squared_error

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FINAL = os.path.join(ROOT, 'data', 'final')
REPORTS = os.path.join(ROOT, 'reports')
os.makedirs(REPORTS, exist_ok=True)


def main():
    df = pd.read_csv(os.path.join(FINAL, 'model_ready_data.csv'), parse_dates=['dt'])
    df = df.sort_values('dt')
    y = df['visitor_count'].values
    X = df.drop(columns=['dt','visitor_count']).values

    split_idx = int(len(df)*0.7)
    X_train, y_train = X[:split_idx], y[:split_idx]
    X_test, y_test = X[split_idx:], y[split_idx:]

    model = LSTMRegressor(lookback=30, units=64, epochs=20, batch_size=32)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    # 去掉前lookback个NaN
    y_true = y_test[30:]
    y_hat = y_pred[30:]
    rmse = mean_squared_error(y_true, y_hat, squared=False)
    with open(os.path.join(REPORTS, 'lstm_result.txt'), 'w', encoding='utf-8') as f:
        f.write(f'LSTM RMSE: {rmse:.2f}\n')

if __name__ == '__main__':
    main()
