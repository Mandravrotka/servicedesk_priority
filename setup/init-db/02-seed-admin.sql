INSERT INTO users (username, password_hash)
VALUES (
    'admin',
    '$2b$12$2gDbkK2/X/gi/Q/MiZVFgeWUa0I4CEJvUBquSz8aBomCZZzCU/6.a'
) ON CONFLICT (username) DO NOTHING;