# -*- coding: utf-8 -*-
import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

# 中文字体自动选择（Windows常见：Microsoft YaHei；备选：SimHei/SimSun/Noto Sans CJK SC）
try:
    from matplotlib import font_manager as fm
    candidates = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Noto Sans CJK SC', 'Arial Unicode MS']
    available = set(f.name for f in fm.fontManager.ttflist)
    chosen = None
    for name in candidates:
        if name in available:
            chosen = name
            break
    if chosen:
        matplotlib.rcParams['font.sans-serif'] = [chosen]
        matplotlib.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROC = os.path.join(ROOT, 'data', 'processed')
FINAL = os.path.join(ROOT, 'data', 'final')
FIGS = os.path.join(ROOT, 'reports', 'figures')
os.makedirs(FIGS, exist_ok=True)


def main():
    merged = pd.read_csv(os.path.join(PROC, 'merged_signals.csv'), parse_dates=['dt'])
    model = pd.read_csv(os.path.join(FINAL, 'model_ready_data.csv'), parse_dates=['dt'])

    # 1. 游客量时间序列
    plt.figure(figsize=(12,4))
    plt.plot(merged['dt'], merged['visitor_count'], label='visitor_count')
    plt.title('游客量时间序列（代理目标）')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGS, 'visitor_series.png'), dpi=150)

    # 2. 天气 vs 游客量（散点）
    plt.figure(figsize=(5,4))
    plt.scatter(merged['temp_mean'], merged['visitor_count'], s=8, alpha=0.5)
    plt.xlabel('temp_mean'); plt.ylabel('visitor_count'); plt.title('温度 vs 游客量')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGS, 'temp_vs_visitors.png'), dpi=150)

    # 3. 降水 vs 游客量
    plt.figure(figsize=(5,4))
    plt.scatter(merged['precipitation'], merged['visitor_count'], s=8, alpha=0.5)
    plt.xlabel('precipitation'); plt.ylabel('visitor_count'); plt.title('降水 vs 游客量')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGS, 'rain_vs_visitors.png'), dpi=150)

if __name__ == '__main__':
    main()
