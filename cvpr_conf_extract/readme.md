# cvpr_conf_extract

## To-do
从 CVPR 2024 会议官网抓取并整理数据，默认抓取 2024-06-19、2024-06-20、2024-06-21 三个论文列表页。具体而言，需要收集论文标题、作者列表、摘要，以及 PDF 或补充材料的链接等信息。

## Script
- `src/scrape_cvpr2024.py`：抓取 CVPR 2024 论文标题、作者、摘要、PDF 与补充材料链接。
- 支持参数：
  - `--limit`：仅抓取前 N 篇
  - `--format`：`json` 或 `csv`
  - `--output`：输出文件路径（默认 `cvpr_conf_extract/results/cvpr2024_papers.json`）
  - `--listing-url`：自定义论文列表页，可重复传入多个 URL

示例：
```bash
python3 cvpr_conf_extract/src/scrape_cvpr2024.py --limit 5 --format json --output cvpr_conf_extract/results/cvpr2024_first5.json
python3 cvpr_conf_extract/src/scrape_cvpr2024.py --format json --output cvpr_conf_extract/results/cvpr2024_papers.json
python3 cvpr_conf_extract/src/scrape_cvpr2024.py --format csv --output cvpr_conf_extract/results/cvpr2024_all.csv
```
