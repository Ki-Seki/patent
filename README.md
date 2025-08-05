## 一些 MySQL 命令

## 一般

```bash
# 安装
sudo apt update
sudo apt install -y mysql-server

# 改密码
mysql -u root -p -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '1234';"

# 创建数据库
mysql -u root -p -e "CREATE DATABASE patent_calculation;"
```

## 迁移 MySQL 数据库的数据盘（不知道跑通与否）

参考：https://shawn-nie.github.io/2019/03/12/MySQL%E6%9B%B4%E6%8D%A2%E6%95%B0%E6%8D%AE%E5%AD%98%E5%82%A8%E8%B7%AF%E5%BE%84%E7%9A%84%E6%96%B9%E6%B3%95/

```bash
# 查看当前数据目录
mysql -u root -p -e "show global variables like '%datadir%';"

# 停止 MySQL 服务
service mysqld stop
sudo pkill mysqld

# 创建新的数据目录
sudo mkdir -p /mnt/public2/code/ssc/.mysql
sudo chown -R mysql:mysql /mnt/public2/code/ssc/.mysql
sudo chmod 755 /mnt/public2/code/ssc/.mysql

# 复制数据到新的目录
sudo cp -R /var/lib/mysql/* /mnt/public2/code/ssc/.mysql/
sudo chown -R mysql:mysql /mnt/public2/code/ssc/.mysql

# 备份原 MySQL 配置文件
sudo cp /etc/mysql/mysql.conf.d/mysqld.cnf /etc/mysql/mysql.conf.d/mysqld.cnf.bak

# 修改 MySQL 配置文件
sudo vi /etc/mysql/mysql.conf.d/mysqld.cnf
# 在 [mysqld] 部分添加或修改以下行
datadir = /mnt/public2/code/ssc/.mysql

# 启动MySQL服务
service mysqld start

```
