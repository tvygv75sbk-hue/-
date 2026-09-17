# 大理古城景区游客流量预测（免费数据）

步骤：
1. 创建虚拟环境并安装依赖：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
2. 采集数据（全免费API）：
   - Open-Meteo 历史天气
   - Wikimedia Pageviews（“大理古城”中文维基页面日访问量）
   - Google Trends（pytrends，对“"大理古城"”的关注度）
   - China holidays（python-holidays）
3. 运行脚本：
   - `python src/data_collection/fetch_open_meteo.py`
   - `python src/data_collection/fetch_wikimedia.py`
   - `python src/data_collection/fetch_trends.py`
   - `python src/data_collection/build_target_from_signals.py`
   - `python src/preprocessing/cleaning.py`
   - `python src/feature_engineering/feature_builder.py`
   - `python src/models/train_baselines.py`
   - （可选）`python src/evaluation/explain.py` 生成SHAP解释与典型案例
   - （可选）`python src/models/train_lstm.py` 训练LSTM演示（需安装TensorFlow）
   - （可选）`python src/data_collection/selenium_log_demo.py` 生成模拟浏览日志
4. 报告查看：`reports/01_数据采集处理报告.md`、`reports/02_数据分析报告.md`、`reports/00_综合实验报告_大理古城游客流量预测.md`

MySQL 入库（可选）：
- 先在 MySQL 客户端执行：`SOURCE database/create_tables.sql;`（如需触发器/存储过程，再执行 `SOURCE database/dynamic.sql;`）
- 设置环境变量连接串（示例，替换 {{MYSQL_PASSWORD}}）：
  - PowerShell：`$env:MYSQL_URL = "mysql+pymysql://root:{{MYSQL_PASSWORD}}@localhost:3306/dali_tourism_forecast?charset=utf8mb4"`
- 运行入库：`python src/database/load_to_mysql.py`

说明：本项目不抓取携程/马蜂窝受限数据，全部使用免费且开放的API与公共数据；若后续接入真实景区门禁数据，可替换`build_target_from_signals.py`中的目标构建逻辑。
