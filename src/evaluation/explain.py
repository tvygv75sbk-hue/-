# -*- coding: utf-8 -*-
import os
import json
import numpy as np
import pandas as pd
try:
    import shap
except Exception as _e:
    shap = None
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FINAL = os.path.join(ROOT, 'data', 'final')
REPORTS = os.path.join(ROOT, 'reports')
FIGS = os.path.join(REPORTS, 'figures')
os.makedirs(FIGS, exist_ok=True)


def load_best_model_name():
    cmp = pd.read_csv(os.path.join(REPORTS, 'model_comparison.csv'))
    return cmp.sort_values('test_rmse').iloc[0]['model']


def build_model(name, k, input_dim):
    if name == 'GradientBoosting':
        return GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=3, random_state=42)
    if name == 'RandomForest':
        return RandomForestRegressor(n_estimators=300, max_depth=12, random_state=42)
    if name == 'LightGBM':
        return LGBMRegressor(n_estimators=500, learning_rate=0.05, max_depth=-1, random_state=42)
    if name == 'LinearRegression':
        return Pipeline([
            ('scaler', StandardScaler(with_mean=False)),
            ('select', SelectKBest(score_func=f_regression, k=min(k, input_dim))),
            ('model', LinearRegression())
        ])
    if name == 'Ridge':
        return Pipeline([
            ('scaler', StandardScaler(with_mean=False)),
            ('select', SelectKBest(score_func=f_regression, k=min(k, input_dim))),
            ('model', Ridge(alpha=1.0))
        ])
    if name == 'Lasso':
        return Pipeline([
            ('scaler', StandardScaler(with_mean=False)),
            ('select', SelectKBest(score_func=f_regression, k=min(k, input_dim))),
            ('model', Lasso(alpha=0.001))
        ])
    return GradientBoostingRegressor()


def pick_case(df):
    # 优先选择节假日；否则选择95分位的高峰
    if 'is_holiday' in df.columns and df['is_holiday'].sum() > 0:
        return df[df['is_holiday'] == 1].iloc[-1]
    q95 = df['visitor_count'].quantile(0.95)
    return df[df['visitor_count'] >= q95].iloc[-1]


def main():
    df = pd.read_csv(os.path.join(FINAL, 'model_ready_data.csv'), parse_dates=['dt'])
    df = df.sort_values('dt').reset_index(drop=True)
    y = df['visitor_count'].values
    X = df.drop(columns=['dt','visitor_count'])
    feature_names = list(X.columns)

    split_idx = int(len(df)*0.7)
    X_train, y_train = X.iloc[:split_idx], y[:split_idx]
    X_test, y_test = X.iloc[split_idx:], y[split_idx:]

    best = load_best_model_name()
    model = build_model(best, k=min(20, X_train.shape[1]), input_dim=X_train.shape[1])
    model.fit(X_train, y_train)

    # 仅对树模型计算SHAP（TreeExplainer），线性模型用KernelExplainer成本较高，这里略过
    base_model = model
    if isinstance(model, Pipeline):
        try:
            base_model = model.named_steps['model']
        except Exception:
            pass

    try:
        if shap is None:
            raise RuntimeError('shap 未安装（requirements.txt 中为可选项）')
        explainer = shap.TreeExplainer(base_model)
        shap_values = explainer.shap_values(X_test)
        shap.summary_plot(shap_values, X_test, feature_names=feature_names, show=False)
        # 保存静态PNG摘要（可选）
        try:
            import matplotlib.pyplot as plt
            plt.savefig(os.path.join(FIGS, 'shap_summary.png'), dpi=150, bbox_inches='tight')
        except Exception:
            pass
        # 典型案例解释
        case_row = pick_case(df.iloc[split_idx:].assign(idx=range(len(X_test))))
        idx = int(case_row['idx']) if 'idx' in case_row else -1
        contrib = pd.Series(shap_values[idx], index=feature_names).sort_values(key=lambda s: s.abs(), ascending=False)
        top5 = contrib.head(5)
        out_md = [
            '# 典型案例决策解释',
            f'- 模型: {best}',
            f'- 日期: {df.iloc[split_idx:]["dt"].iloc[idx].date()}',
            f'- 实际: {y_test[idx]:.0f}',
            f'- 预测: {model.predict(X_test.iloc[[idx]])[0]:.0f}',
            '## Top5 特征贡献（按绝对值）'
        ]
        for k, v in top5.items():
            out_md.append(f'- {k}: {v:+.1f}')
        with open(os.path.join(REPORTS, 'case_explanation.md'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_md))
    except Exception as e:
        with open(os.path.join(REPORTS, 'case_explanation.md'), 'w', encoding='utf-8') as f:
            f.write(f"暂未生成SHAP解释，原因: {e}")

if __name__ == '__main__':
    main()
