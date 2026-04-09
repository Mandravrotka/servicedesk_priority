#!/usr/bin/env python3
"""
Консольный скрипт для переключения LLM-провайдера в PriorityDesk
Чистый, структурированный и поддерживаемый код без смайликов и ведущих подчёркиваний
"""

import json
import re
import sys
from pathlib import Path


class LLMSwitcher:
    def __init__(self):
        self.setup_dir = Path(__file__).parent.resolve()
        self.project_root = self.setup_dir.parent
        self.env_file = self.project_root / ".env"
        self.providers_file = self.setup_dir / "llm-providers.json"
        self.template_file = self.setup_dir / "templates" / "workflow-main-llm.json.template"

    def run(self):
        """Основной поток выполнения"""
        print("Переключение LLM-провайдера\n")

        # 1. Загрузка данных
        providers = self.load_providers()
        current_env = self.load_env()

        # 2. Сбор новых настроек
        config = self.collect_config(providers, current_env)
        if not config:
            return

        # 3. Подтверждение
        if not self.confirm_changes(config):
            print("Отменено.")
            return

        # 4. Сохранение
        self.update_env_file(config["env"])
        self.generate_workflow(config["provider"], config["model"])

        # 5. Финал
        self.print_completion_message()

    def load_env(self) -> dict:
        """Загружает переменные из .env"""
        env = {}
        if not self.env_file.exists():
            return env
        for line in self.env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"\'')
        return env

    def load_providers(self) -> dict:
        """Загружает список провайдеров"""
        try:
            return json.loads(self.providers_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"[ERROR] Не найден: {self.providers_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Ошибка JSON: {e}")
            sys.exit(1)

    def select_provider(self, providers: dict, current: str) -> str:
        """Показывает меню выбора провайдера"""
        keys = list(providers.keys())
        print("Доступные LLM-провайдеры:")
        for i, key in enumerate(keys, 1):
            name = providers[key].get("cred_name", "Без имени")
            mark = " ← текущий" if key == current else ""
            print(f"  {i}. {key} ({name}){mark}")

        while True:
            try:
                choice = input(f"\nВыберите (1-{len(keys)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(keys):
                    return keys[idx]
            except (ValueError, KeyboardInterrupt, EOFError):
                pass
            print("Неверный ввод. Введите число от 1 до", len(keys))

    def input_with_default(self, prompt: str, default: str = "") -> str:
        """Ввод с поддержкой значения по умолчанию"""
        try:
            if default:
                value = input(f"{prompt} ({default}): ").strip()
                return value if value else default
            return input(f"{prompt}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nОтменено.")
            sys.exit(0)

    def collect_config(self, providers: dict, current_env: dict) -> dict | None:
        """Собирает все необходимые данные от пользователя"""
        current_provider = current_env.get("LLM_PROVIDER", "ollama")
        selected_key = self.select_provider(providers, current_provider)
        provider = providers[selected_key]

        # Модель
        default_model = current_env.get("LLM_MODEL") or provider.get("default_model", "")
        model = self.input_with_default("Введите название модели", default_model)

        # Base URL
        base_url = ""
        if provider.get("base_url_param"):
            default_url = current_env.get("LLM_URL") or provider.get("default_url", "")
            base_url = self.input_with_default("Введите базовый URL API", default_url)

        # API-ключ
        api_key = ""
        if provider.get("api_key_param"):
            api_key = self.input_with_default("Введите API-ключ", "")

        return {
            "provider": provider,
            "model": model,
            "env": {
                "LLM_PROVIDER": selected_key,
                "LLM_MODEL": model,
                "LLM_URL": base_url,
                "LLM_API_KEY": api_key,
            },
        }

    def ask(self, prompt: str, default: bool = True) -> bool:
        """Задаёт yes/no вопрос"""
        default_str = "Y/n" if default else "y/N"
        try:
            answer = input(f"{prompt} [{default_str}]: ").strip().lower()
            if not answer:
                return default
            return answer in ("y", "yes")
        except (KeyboardInterrupt, EOFError):
            return False

    def confirm_changes(self, config: dict) -> bool:
        """Показывает сводку и запрашивает подтверждение"""
        print("\nНовые настройки:")
        print(f"   Провайдер: {config['env']['LLM_PROVIDER']}")
        print(f"   Модель: {config['model']}")
        if config["env"]["LLM_URL"]:
            print(f"   Base URL: {config['env']['LLM_URL']}")
        if config["env"]["LLM_API_KEY"]:
            print(f"   API Key: {'*' * 8}")

        return self.ask("\nПрименить изменения?", True)

    def update_env_file(self, new_values: dict):
        """Обновляет .env, размещая LLM-настройки в секции # LLM Settings"""
        lines = []
        section_found = False

        if self.env_file.exists():
            content = self.env_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                stripped = line.strip()

                if stripped == "# LLM Settings":
                    section_found = True
                    lines.append(line)
                    for key in ["LLM_PROVIDER", "LLM_MODEL", "LLM_URL", "LLM_API_KEY"]:
                        lines.append(f"{key}={new_values.get(key, '')}")
                    continue

                # Пропускаем старые значения
                if "=" in line:
                    key = line.split("=", 1)[0].strip()
                    if key in new_values:
                        continue

                lines.append(line)

        self.env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Файл .env обновлён")

    def generate_workflow(self, provider: dict, model: str):
        """Генерирует main_llm.json из шаблона"""
        try:
            template = self.template_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"[ERROR] Шаблон не найден: {self.template_file}")
            sys.exit(1)

        # Подстановка значений
        replacements = {
            "{{node_type}}": provider["node_type"],
            "{{cred_type}}": provider["cred_type"],
            "{{cred_name}}": provider["cred_name"],
            "{{cred_id}}": provider["cred_id"],
            "{{model_param}}": provider["model_param"],
            "{{base_url_param}}": provider.get("base_url_param", ""),
            "{{api_key_param}}": provider.get("api_key_param", ""),
            "=qwen3-vl:235b-instruct": f"={model}",
        }
        for k, v in replacements.items():
            template = template.replace(k, v)

        # Удаление пустых блоков {{#if}}...{{/if}}
        template = re.sub(r'\s*{{#if\s+\w+}}.*?{{/if}}\s*', '', template, flags=re.DOTALL)
        template = re.sub(r',\s*\}', '}', template)
        template = re.sub(r'\{\{,\s*\}\}', '{}', template)

        # Сохранение
        output_path = self.project_root / "workflow" / "main_llm.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template, encoding="utf-8")
        print(f"Сгенерирован воркфлоу: {output_path}")

    def print_completion_message(self):
        """Вывод финальных инструкций"""
        print("\nГотово!")
        print("Следующие шаги:")
        print("   1. Импортируйте в n8n:")
        print("      docker cp workflow/main_llm.json n8n:/tmp/workflow.json")
        print("      docker exec n8n n8n import:workflow --input /tmp/workflow.json")
        print("   2. Перезапустите воркфлоу в n8n")
        print("   3. Проверьте работу системы")


if __name__ == "__main__":
    LLMSwitcher().run()