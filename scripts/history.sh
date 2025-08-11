# ─── 常用命令 ─────────────────────────────────────────────────────────────────────

# 安装mysql并且创建数据库
sudo apt update
sudo apt install -y mysql-server
mysql -u root -p -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '1234';"
mysql -u root -p -e "CREATE DATABASE patent_calculation;"

# 清理数据库二进制日志
mysql -u root -p
SHOW BINARY LOGS;
SHOW VARIABLES LIKE 'log_bin%';
RESET MASTER;  # 清理所有 binlog

# ─── 历史记录 ─────────────────────────────────────────────────────────────────────

# 2025年8月7日，添加最早忽略掉的上市公司字段
python add_listed.py \
    --csv-file "data/merged.csv" \
    --publication-number "Publication number" \
    --commit-interval 100000

# 2025年8月8日，获取上市公司的backward_citations中缺失的
python get_missing.py

# 2025年8月9日，计算所有上市公司的bxfx
python cal_bxfx.py

# 2025年8月10日，计算前三个cd index
python cal_cd.py \
    --index-names cd_t,cd_f_t,cd_f2_t \
    --batch-size 10000

# 2025年8月11日，备份数据库
mysqldump -u root -p patent_calculation > tmp/db_patent_calculation_250811.sql

# 2025年8月11日，部署jina服务
cd /mnt/public2/code/ssc/patent/
HF_ENDPOINT=https://hf-mirror.com uvicorn serve_jina_cos:app --host 0.0.0.0 --port 8000
