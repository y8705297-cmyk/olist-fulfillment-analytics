# 最终交付验收

## 工程与数据

- 使用现有 Olist Kaggle v2 的九个 CSV，验证指纹后重建分析库。本轮未重新下载数据，核心 SQL 模型和正式分析算法沿用已验证版本。
- `make analysis` 正常退出。原有自动化测试 15 项通过、0 项失败，正式分析审计及断言通过。25 张分析 CSV 和五张原分析图与上轮记录的 SHA-256 一致。
- 从 DuckDB 与分析表逐项核对平台、峰值、地区、阶段、回归、商家和情景结果。三个高峰共 3,158 / 6,138 笔成熟窗口延误，按两位小数报告为 51.45%。

## Dashboard 浏览器验收

在 Apple Silicon Mac 上运行本地 Streamlit，并用 Chrome 检查所有页面。验证了日期、州和主品类筛选，RJ 与床品桌布浴室用品组合筛选返回 1,388 笔订单、1,352 笔可判、202 笔延误。该组合在两个履约页面之间可保留。客户体验模型、商家审查和情景使用各自固定样本。低量月只限制趋势率和中位数的绘制，保留订单计数与分母。

```text
PASS Executive Overview: expected values and 2 chart containers
PASS Delivery Diagnostics: expected values and 4 chart containers
PASS Customer Experience: expected values and 2 chart containers
PASS Seller Prioritization: expected values and 1 chart containers
PASS Improvement Scenarios: expected values and 0 chart containers
PASS scenario slider: zero, 30%, 20%, and remaining orders
PASS state, category and purchase-month filters; scope persists across delivery pages
PASS fixed model sample and unavailable geographic controls
PASS seller selector and matched-peer detail
```

## PDF 与展示文件

- 中文 PDF 共 7 页。使用本机 Chrome 由 Markdown 源文件打印，逐页渲染检查中文、图表、表格、标题和页脚，并用 PDFKit 核对可提取文本和 1–7 页码。
- README 的本地链接、Dashboard 截图和复现步骤已检查。简历文案与报告对齐，明确情景数字及回顾性商家筛选。
- 使用临时 Git 仓库检查忽略规则覆盖虚拟环境、缓存、原始数据、本地 DuckDB 和密钥文件，报告及图表可纳入版本管理。项目未发布至远程仓库。

## 一致性抽查

| 项目 | 验收值 |
| --- | --- |
| 全快照实际下单日期与订单数 | 2016-09-04 至 2018-10-17；99,441 |
| 配送延误 | 6,534 / 96,470，6.77% |
| 高峰 | 2017-11（12.40%）、2018-02（14.13%）、2018-03（18.96%） |
| 低评分关联 | 62.42% 对 9.27%；成熟窗调整 OR 15.44 |
| 商家筛选 | 两期各 ≥50，均为正平滑超额；后期同行覆盖 ≥70%，实际高于同行期望；21 家 |
| 高峰改善情景 | 366 / 1,522；10% 与 20% 相对降幅对应 36.6 与 73.2 笔 |

**解释限制。** 数据缺少细粒度承运事件和明确抽取截止时间。商家群由历史窗口筛选，仍需新的高峰窗口检验。回归与情景结果分别用于衡量关联和规划容量，实际效果需由试点验证。
