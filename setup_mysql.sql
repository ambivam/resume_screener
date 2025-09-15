-- MySQL Setup Script for Resume Screener Application
-- Run this script in MySQL Workbench or command line

-- Create database
CREATE DATABASE IF NOT EXISTS resume_screener;

-- Use the database
USE resume_screener;

-- Create user (optional - you can use root)
-- CREATE USER 'resume_user'@'localhost' IDENTIFIED BY 'your_password';
-- GRANT ALL PRIVILEGES ON resume_screener.* TO 'resume_user'@'localhost';
-- FLUSH PRIVILEGES;

-- Verify database exists
SHOW DATABASES LIKE 'resume_screener';

-- Show current user
SELECT USER();

-- Test connection
SELECT 'MySQL connection successful!' as status;
