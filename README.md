## 一些 MySQL 命令

```bash
# 安装
sudo apt update
sudo apt install -y mysql-server

# 改密码
mysql -u root -p -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '1234';"

# 创建数据库
mysql -u root -p -e "CREATE DATABASE patent_calculation;"
```

# TODO

- cd value calculation
- embedding calculation
