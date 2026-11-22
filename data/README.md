# 数据目录

[原始数据由 Olist 在 Kaggle 发布](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)。

- `raw/` 存放九张公开 CSV。下载脚本将原始 ZIP 与各 CSV 的 SHA-256 指纹记录在 `raw/manifest.json`。ZIP 解压完成后可移除。
- `processed/olist.duckdb` 由构建脚本生成，含源表、分析表与 KPI 视图。
- [数据质量报告](../reports/data_quality_report.md)记录实测逐列审计和逐 CSV 指纹，供复现时对照。
- 原始 CSV、下载信息、数据库文件及依赖环境只留在本地，由忽略规则管理。
- Kaggle 公开接口下载失败时，可从上述发布页获取 ZIP，随后从项目根目录运行 `.venv/bin/python -m src.fetch_data --archive /path/to/brazilian-ecommerce.zip`。已有九个文件时优先复用本地副本。

## 本次验证的快照

Kaggle 公开目录返回版本 2，更新时间为 2021-10-01 UTC，归档版本 ID 为 2669146。下载时以同一个官方归档的字节区间完成传输，拼合后的 44,717,580 字节与官方响应的 MD5 一致。构建入口会按 [snapshot.json](snapshot.json) 校验九个 CSV 的 SHA-256。不同压缩方式打包的副本可以使用，前提是解压出的九个 CSV 指纹相同。 [Kaggle v2 发布页](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/versions/2)
