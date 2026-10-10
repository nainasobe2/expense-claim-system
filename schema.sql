-- Smart Expense Claim Approval System (PS-068)
-- Team: The Semicolons
-- Database Schema & Seed Data

CREATE DATABASE IF NOT EXISTS expense_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE expense_db;

-- 1. Users Table
-- Roles: 'EMPLOYEE', 'MANAGER', 'FINANCE_ADMIN'
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('EMPLOYEE', 'MANAGER', 'FINANCE_ADMIN') NOT NULL,
    department VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Policies Table
-- Dynamic policy rules per category
CREATE TABLE IF NOT EXISTS policies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL UNIQUE,
    max_amount DECIMAL(10, 2) NOT NULL,
    max_days_old INT NOT NULL DEFAULT 30,
    receipt_required_above DECIMAL(10, 2) NOT NULL DEFAULT 25.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Claims Table
-- Statuses: 'SUBMITTED', 'PENDING_MANAGER', 'PENDING_FINANCE', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED'
CREATE TABLE IF NOT EXISTS claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    expense_date DATE NOT NULL,
    description TEXT NOT NULL,
    receipt_path VARCHAR(255) NULL,
    receipt_hash VARCHAR(64) NULL,
    status ENUM('SUBMITTED', 'PENDING_MANAGER', 'PENDING_FINANCE', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED') NOT NULL DEFAULT 'SUBMITTED',
    flags JSON NULL,
    assigned_approver_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_approver_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_expense_date (expense_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Claim History Table (Audit Trail)
CREATE TABLE IF NOT EXISTS claim_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    claim_id INT NOT NULL,
    action VARCHAR(50) NOT NULL,
    actor_id INT NOT NULL,
    comment TEXT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_claim_id (claim_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Seed Data
-- Default password for all seed users: "password123"
-- pbkdf2:sha256 hash: pbkdf2:sha256:1000000$TJWVoFuU9oiYgjOr$9112801b4ec5314b4bd2b06bfff46d9a0b7bdabb65801e5ddae458af648a7f1a
-- ============================================================================

INSERT INTO users (id, name, email, password_hash, role, department)
VALUES
    (1, 'Alice Employee', 'employee@example.com', 'pbkdf2:sha256:1000000$TJWVoFuU9oiYgjOr$9112801b4ec5314b4bd2b06bfff46d9a0b7bdabb65801e5ddae458af648a7f1a', 'EMPLOYEE', 'Engineering'),
    (2, 'Bob Manager', 'manager@example.com', 'pbkdf2:sha256:1000000$TJWVoFuU9oiYgjOr$9112801b4ec5314b4bd2b06bfff46d9a0b7bdabb65801e5ddae458af648a7f1a', 'MANAGER', 'Engineering'),
    (3, 'Carol Finance', 'finance@example.com', 'pbkdf2:sha256:1000000$TJWVoFuU9oiYgjOr$9112801b4ec5314b4bd2b06bfff46d9a0b7bdabb65801e5ddae458af648a7f1a', 'FINANCE_ADMIN', 'Finance')
ON DUPLICATE KEY UPDATE name=VALUES(name), department=VALUES(department);

INSERT INTO policies (category, max_amount, max_days_old, receipt_required_above)
VALUES
    ('TRAVEL', 1000.00, 30, 50.00),
    ('MEALS', 75.00, 15, 20.00),
    ('EQUIPMENT', 500.00, 45, 100.00),
    ('OTHER', 150.00, 30, 25.00)
ON DUPLICATE KEY UPDATE 
    max_amount=VALUES(max_amount), 
    max_days_old=VALUES(max_days_old), 
    receipt_required_above=VALUES(receipt_required_above);

