INSERT INTO enumerations (id, name, position, is_default, type, active, project_id, parent_id, position_name) 
VALUES 
(1, '1 - Немедленно', 1, false, 'IssuePriority', true, NULL, NULL, 'highest'),
(2, '2 - Срочно', 2, false, 'IssuePriority', true, NULL, NULL, 'high2'),
(3, '3 - Высокий', 3, false, 'IssuePriority', true, NULL, NULL, 'high3'),
(4, '4 - Нормальный', 4, false, 'IssuePriority', true, NULL, NULL, 'default'),
(5, '5 - Низкий', 5, false, 'IssuePriority', true, NULL, NULL, 'low2'),
(6, '6 - Очень низкий', 6, false, 'IssuePriority', true, NULL, NULL, 'lowest')
ON CONFLICT (id) DO NOTHING;