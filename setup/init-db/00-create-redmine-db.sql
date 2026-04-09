-- Создание базы данных и пользователя для Redmine
CREATE USER redmine_user WITH PASSWORD 'redmine_password';
CREATE DATABASE redmine OWNER redmine_user;
GRANT ALL PRIVILEGES ON DATABASE redmine TO redmine_user;