# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_regression
try:
    from lightgbm import LGBMRegressor
    HAS_LGB = True
except Exception:
    HAS_LGB = False

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FINAL = os.path.join(ROOT, 'data', 'final')
REPORTS = os.path.join(ROOT, 'reports')
os.makedirs(REPORTS, exist_ok=True)


def eval_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    r2 = r2_score(y_true, y_pred)
    mape = (np.abs((y_true - y_pred) / np.maximum(y_true, 1))).mean()
    return mae, rmse, r2, mape


def main():
    df = pd.read_csv(os.path.join(FINAL, 'model_ready_data.csv'), parse_dates=['dt'])
    df = df.sort_values('dt')
    y = df['visitor_count'].values
    X = df.drop(columns=['dt','visitor_count'])

    # 时间切分：前70%训练，后30%测试
    split_idx = int(len(df)*0.7)
    X_train, y_train = X.iloc[:split_idx], y[:split_idx]
    X_test, y_test = X.iloc[split_idx:], y[split_idx:]

    k = min(20, X_train.shape[1])

    models = {
        # 线性族：标准化 + 特征选择 + 模型
        'LinearRegression': Pipeline([
            ('scaler', StandardScaler(with_mean=False)),
            ('select', SelectKBest(score_func=f_regression, k=k)),
            ('model', LinearRegression())
        ]),
        'Ridge': Pipeline([
            ('scaler', StandardScaler(with_mean=False)),
            ('select', SelectKBest(score_func=f_regression, k=k)),
            ('model', Ridge(alpha=1.0))
        ]),
        'Lasso': Pipeline([
            ('scaler', StandardScaler(with_mean=False)),
            ('select', SelectKBest(score_func=f_regression, k=k)),
            ('model', Lasso(alpha=0.001))
        ]),
        # 树模型：可选简单的特征选择
        'RandomForest': Pipeline([
            ('select', SelectKBest(score_func=f_regression, k=k)),
            ('model', RandomForestRegressor(n_estimators=300, max_depth=12, random_state=42))
        ]),
        'GradientBoosting': Pipeline([
            ('select', SelectKBest(score_func=f_regression, k=k)),
            ('model', GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=3, random_state=42))
        ])
    }
    if HAS_LGB:
        models['LightGBM'] = Pipeline([
            ('select', SelectKBest(score_func=f_regression, k=k)),
            ('model', LGBMRegressor(n_estimators=500, learning_rate=0.05, max_depth=-1, random_state=42))
        ])

    rows = []
    preds = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        yhat_tr = model.predict(X_train)
        yhat_te = model.predict(X_test)
        tr = eval_metrics(y_train, yhat_tr)
        te = eval_metrics(y_test, yhat_te)
        rows.append({
            'model': name,
            'train_mae': tr[0], 'test_mae': te[0],
            'train_rmse': tr[1], 'test_rmse': te[1],
            'train_r2': tr[2], 'test_r2': te[2],
            'test_mape': te[3]
        })
        preds[name] = pd.DataFrame({'dt': df['dt'].iloc[split_idx:].values, 'y_true': y_test, f'y_pred_{name}': yhat_te})

    res = pd.DataFrame(rows).sort_values('test_rmse')
    res.to_csv(os.path.join(REPORTS, 'model_comparison.csv'), index=False, encoding='utf-8-sig')

    # 合并预测保存
    out = preds[list(preds.keys())[0]]
    for name in list(preds.keys())[1:]:
        out = out.merge(preds[name], on=['dt','y_true'], how='left')
    out.to_csv(os.path.join(REPORTS, 'test_predictions.csv'), index=False, encoding='utf-8-sig')

    print(res)

if __name__ == '__main__':
    main()
