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
    domain_name VARCHAR(100) NOT NULL,
    issue_id INTEGER NOT NULL,
    input_text TEXT NOT NULL,
    prompt_used TEXT NOT NULL,
    priority_determined INTEGER NOT NULL,
    explanation TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    confidence INTEGER,
    confidence_reason TEXT
);

-- Таблица логов интеграции с Redmine
CREATE TABLE IF NOT EXISTS redmine_logs (
    id SERIAL PRIMARY KEY,
    domain_name VARCHAR(100) NOT NULL,
    issue_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);