#!/bin/bash
set -exuo pipefail


python data2db.py \
  --csv-file "data/merged.csv" \
  --log-interval 10000 \
  --publication-number "Publication number" \
  --publication-date "Publication date" \
  --patent-office "Patent office" \
  --application-filing-date "Application/filing date" \
  --applicants-bvd-id-numbers "Applicant(s) BvD ID Number(s)" \
  --backward-citations "Backward citations" \
  --forward-citations "Forward citations" \
  --abstract "Abstract"


python data2db.py \
  --csv-file "data/merged_backwards.csv" \
  --log-interval 10000 \
  --publication-number "发布代码" \
  --publication-date "发布日期" \
  --patent-office "专利局" \
  --application-filing-date "申请/提交日期" \
  --applicants-bvd-id-numbers "申请人BvD代码" \
  --backward-citations "引用其他其他专利" \
  --forward-citations "被其他专利引用" \
  --abstract "摘要"
