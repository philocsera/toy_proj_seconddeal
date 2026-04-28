-- EC2에서 MySQL 초기 세팅
-- 실행: sudo mysql < mysql_setup.sql

CREATE DATABASE IF NOT EXISTS seconddeal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'seconddeal_user'@'localhost' IDENTIFIED BY 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON seconddeal.* TO 'seconddeal_user'@'localhost';
FLUSH PRIVILEGES;

SHOW DATABASES;
SELECT user, host FROM mysql.user;
