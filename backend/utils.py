import json
from fastapi.responses import HTMLResponse

def success_response(message, triggers = None):
    headers = {}
    if triggers:
        headers["HX-Trigger"] = json.dumps(triggers)

    return HTMLResponse(
        f'<span class="text-emerald-600 font-medium">✅ {message}</span>',
        headers=headers
    )

def error_response(message, status_code = 500):
    return HTMLResponse(
        f'<span class="text-red-600">❌ {message}</span>',
        status_code=status_code
    )