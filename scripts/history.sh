# 2025年8月7日，添加最早忽略掉的上市公司字段
python add_listed.py \
    --csv-file "data/merged.csv" \
    --publication-number "Publication number" \
    --commit-interval 100000

# 2025年8月8日，获取上市公司的backward_citations中缺失的
python get_missing.py
