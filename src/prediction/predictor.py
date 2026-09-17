# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FINAL = os.path.join(ROOT, 'data', 'final')


def main():
    df = pd.read_csv(os.path.join(FINAL, 'model_ready_data.csv'), parse_dates=['dt'])
    df = df.sort_values('dt')
    y = df['visitor_count'].values
    X = df.drop(columns=['dt','visitor_count'])

    split_idx = int(len(df)*0.9)
    X_train, y_train = X.iloc[:split_idx], y[:split_idx]
    X_test, y_test = X.iloc[split_idx:], y[split_idx:]

    model = GradientBoostingRegressor(n_estimators=400, learning_rate=0.05, max_depth=3, random_state=42)
    model.fit(X_train, y_train)

    # 简单滚动预测：用最近一行特征向量做7/30日短期预测（教学演示）
    last_row = X.iloc[-1:].copy()
    preds_7 = model.predict(np.repeat(last_row.values, 7, axis=0))
    preds_30 = model.predict(np.repeat(last_row.values, 30, axis=0))

    print('Next 7 days (same-day feature approximation):')
    print(np.round(preds_7, 0))

if __name__ == '__main__':
    main()
