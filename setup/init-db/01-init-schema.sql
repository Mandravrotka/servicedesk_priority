-- Таблица конфигураций доменов
CREATE TABLE IF NOT EXISTS domain_configs (
    id SERIAL PRIMARY KEY,
    domain_name VARCHAR(100) UNIQUE NOT NULL,
    project_id INTEGER NOT NULL,
    main_prompt TEXT NOT NULL
);

-- Таблица логов ИИ
CREATE TABLE IF NOT EXISTS llm_logs (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL,
    input_text TEXT NOT NULL,
    prompt_used TEXT NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    task_type VARCHAR(100),
    model_used VARCHAR(100),
    result_data JSONB
);

-- Таблица логов интеграции с Redmine
CREATE TABLE IF NOT EXISTS redmine_logs (
    id SERIAL PRIMARY KEY,
    domain_name VARCHAR(100) NOT NULL,
    issue_id INTEGER NOT NULL,
    task_created_at TIMESTAMP WITH TIME ZONE,
    priority_determined INTEGER,
    priority_explanation TEXT,
    confidence INTEGER,
    confidence_explanation TEXT,
    logged_at TIMESTAMP WITH TIME ZONE
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'admin',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);