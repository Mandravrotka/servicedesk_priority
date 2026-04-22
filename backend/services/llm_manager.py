import json
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import List, Dict


class LLMWebManager:
    ALLOWED_EMBEDDING_PROVIDERS = {"ollama", "openai", "gemini"}

    EMBEDDING_CONFIGS = {
        "ollama": {
            "node_type": "@n8n/n8n-nodes-langchain.embeddingsOllama",
            "cred_type": "ollamaApi", "cred_name": "priority - embedding LLM", "cred_id": "p18TeZI2HN7zR8zo",
            "model_param": "model", "base_url_param": "baseUrl", "api_key_param": "apiKey",
            "default_url": "http://host.docker.internal:11434",
            "node_name": "Embeddings Ollama "
        },
        "openai": {
            "node_type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi",
            "cred_type": "openAiApi", "cred_name": "OpenAi account", "cred_id": "Ama2q0G633PuAKTd",
            "model_param": "model", "base_url_param": "url", "api_key_param": "apiKey",
            "default_url": "https://api.openai.com/v1",
            "node_name": "Embeddings OpenAI "
        },
        "gemini": {
            "node_type": "@n8n/n8n-nodes-langchain.embeddingsGoogleGemini",
            "cred_type": "googlePalmApi", "cred_name": "Google Gemini(PaLM) Api account", "cred_id": "xfqxcJ7ZbnYUAChL",
            "model_param": "modelName", "base_url_param": None, "api_key_param": "apiKey",
            "default_url": None,
            "node_name": "Embeddings Google Gemini "
        }
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.providers_file = project_root / "setup" / "llm-providers.json"
        self.templates_dir = project_root / "setup" / "templates"
        self.output_dir = project_root / "setup" / "workflow"
        self.providers = self._load_providers()
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True, lstrip_blocks=True,
            variable_start_string='[[[', variable_end_string=']]]',
            block_start_string='[%', block_end_string='%]',
            comment_start_string='[#', comment_end_string='#]',
        )

    def _load_providers(self) -> dict:
        try:
            raw = json.loads(self.providers_file.read_text(encoding="utf-8"))
            return {k.strip(): v for k, v in raw.items()}
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить llm-providers.json: {e}")

    def get_llm_providers_list(self) -> List[Dict[str, str]]:
        return [{"id": key, "name": f"{key} ({cfg.get('cred_name', '')})"} for key, cfg in self.providers.items()]

    def get_embedding_providers_list(self) -> List[Dict[str, str]]:
        return [{"id": p, "name": p.upper()} for p in self.ALLOWED_EMBEDDING_PROVIDERS]

    def _sanitize_json(self, text: str) -> str:
        text = re.sub(r',\s*([}\]])', r'\1', text)
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)

    def apply_from_env(self, env_vars: dict) -> dict:
        # 1. LLM Конфиг
        llm_provider = env_vars.get("LLM_PROVIDER", "ollama").strip().lower()
        if llm_provider not in self.providers:
            return {"success": False, "error": f"Неподдерживаемый LLM провайдер: {llm_provider}"}

        llm_cfg = self.providers[llm_provider]
        llm_ctx = {
            "llm_node_type": llm_cfg["node_type"], "llm_cred_type": llm_cfg["cred_type"],
            "llm_cred_name": llm_cfg["cred_name"], "llm_cred_id": llm_cfg["cred_id"],
            "llm_model_param": llm_cfg["model_param"], "llm_base_url_param": llm_cfg.get("base_url_param"),
            "llm_api_key_param": llm_cfg.get("api_key_param"),
            "llm_model": env_vars.get("LLM_MODEL", llm_cfg.get("default_model", "")),
            "llm_url": env_vars.get("LLM_URL", llm_cfg.get("default_url", "")),
            "llm_api_key": env_vars.get("LLM_API_KEY", ""),
            "llm_node_name": "Main LLM "
        }

        # 2. Embedding Конфиг
        emb_provider = env_vars.get("EMBEDDING_PROVIDER", "ollama").strip().lower()
        if emb_provider not in self.ALLOWED_EMBEDDING_PROVIDERS:
            return {"success": False, "error": f"Неподдерживаемый провайдер эмбеддингов: {emb_provider}"}

        emb_cfg = self.EMBEDDING_CONFIGS[emb_provider]
        emb_ctx = {
            "emb_node_type": emb_cfg["node_type"], "emb_cred_type": emb_cfg["cred_type"],
            "emb_cred_name": emb_cfg["cred_name"], "emb_cred_id": emb_cfg["cred_id"],
            "emb_model_param": emb_cfg["model_param"], "emb_base_url_param": emb_cfg.get("base_url_param"),
            "emb_api_key_param": emb_cfg.get("api_key_param"),
            "emb_model": env_vars.get("EMBEDDING_MODEL", ""),
            "emb_url": env_vars.get("EMBEDDING_URL", emb_cfg.get("default_url", "")),
            "emb_api_key": env_vars.get("EMBEDDING_API_KEY", ""),
            "emb_node_name": emb_cfg["node_name"]  # <-- ИМЯ ИЗ КОНФИГА (с пробелом)
        }

        context = {**llm_ctx, **emb_ctx}

        # 3. Рендеринг
        for template_file in self.templates_dir.glob("*.template"):
            try:
                template = self.jinja_env.get_template(template_file.name)
                rendered = template.render(context)
                cleaned = self._sanitize_json(rendered)

                out_name = template_file.name.replace("workflow-", "").replace(".json.template", ".json")
                out_path = self.output_dir / out_name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(cleaned, encoding="utf-8")
            except Exception as e:
                return {"success": False, "error": f"Ошибка генерации {template_file.name}: {str(e)}"}

        return {"success": True, "message": "Воркфлоу сгенерирован"}