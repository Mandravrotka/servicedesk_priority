import json
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("uvicorn.error")

class LLMWebManager:
    def __init__(self, project_root: Path):
        self.setup_dir = project_root / "setup"
        self.templates_dir = self.setup_dir  / "templates"

        # Настройка Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True, lstrip_blocks=True,
            variable_start_string='[[[', variable_end_string=']]]'
        )
        self.jinja_env.globals['providers'] = json.loads((self.setup_dir / "llm-providers.json").read_text())

    def render_and_save(self, template_dir, output_dir, env_vars):
        for template_file in template_dir.glob("*.template"):
            logger.info(f"{str(output_dir)}/{template_file}")
            (output_dir / template_file.name.replace(".template", "")).write_text(
                self.jinja_env.from_string(template_file.read_text()).render(env_vars))

    def apply_from_env(self, env_vars):
        """Генерирует workflows и credentials на основе переменных окружения."""
        logger.info(
            f"Генерация workflows и credentials с: LLM={env_vars.get('LLM_PROVIDER')}, EMB={env_vars.get('EMBEDDING_PROVIDER')}")
        try:
            self.render_and_save(self.templates_dir / "workflows", self.setup_dir / "workflow", env_vars)
            self.render_and_save(self.templates_dir / "credentials", self.setup_dir / "credentials", env_vars)

            return {"success": True, "message": "Воркфлоу и credentials успешно сгенерированы"}
        except Exception as thrown:
            logger.error(f"Ошибка в apply_from_env: {thrown}")
            return {"success": False, "error": str(thrown)}