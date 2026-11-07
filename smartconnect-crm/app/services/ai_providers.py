"""Multi-provider AI layer.

Every AI call in the app goes through generate_text(). It picks the provider,
model and API key from the signed-in user's AI settings, falls back to the
server's default Gemini key when the user has not set their own, calls the
provider over HTTPS, and records tokens and an estimated cost in ai_usage.
"""
import base64
import hashlib
import os

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from flask_login import current_user

from app import db

# (input price, output price) in US dollars per 1 million tokens.
# These are approximate and only used for the "estimated cost" column.
# Update them from each provider's pricing page when needed.
PROVIDERS = {
    "gemini": {
        "label": "Google Gemini",
        "default": "gemini-flash-latest",
        "models": {
            "gemini-flash-latest": (0.30, 2.50),
            "gemini-flash-lite-latest": (0.10, 0.40),
            "gemini-pro-latest": (1.25, 10.00),
        },
    },
    "openai": {
        "label": "OpenAI",
        "default": "gpt-4o-mini",
        "models": {
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4o": (2.50, 10.00),
        },
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "default": "claude-haiku-4-5-20251001",
        "models": {
            "claude-haiku-4-5-20251001": (1.00, 5.00),
            "claude-sonnet-5-5": (3.00, 15.00),
        },
    },
    "deepseek": {
        "label": "DeepSeek",
        "default": "deepseek-chat",
        "models": {
            "deepseek-chat": (0.27, 1.10),
            "deepseek-reasoner": (0.55, 2.19),
        },
    },
}

SERVER_DEFAULT = ("gemini", "gemini-flash-latest")


class AIError(Exception):
    """kind is one of: rate_limit, auth, timeout, config, other."""

    def __init__(self, message, kind="other"):
        super().__init__(message)
        self.kind = kind


# ---------- key encryption ----------
def _fernet():
    secret = (
        os.environ.get("AI_KEYS_SECRET")
        or current_app.config.get("AI_KEYS_SECRET")
        or current_app.config.get("SECRET_KEY")
        or ""
    )
    if not secret:
        raise AIError("No secret key is configured to encrypt API keys.", "config")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_key(plain):
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_key(token):
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise AIError("The saved API key could not be decrypted. Please save it again.", "config")


def mask_key(token):
    """Last four characters of the saved key, for display only."""
    try:
        plain = decrypt_key(token)
    except AIError:
        return "(unreadable)"
    return "•" * 8 + plain[-4:]


# ---------- cost ----------
def estimate_cost(provider, model, input_tokens, output_tokens):
    prices = PROVIDERS.get(provider, {}).get("models", {}).get(model)
    if not prices:
        return 0.0
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000


# ---------- settings ----------
def get_user_setting(user_id):
    from app.models import AISetting
    return AISetting.query.filter_by(user_id=user_id).first()


def resolve(task):
    """Return (provider, model, api_key, key_source) for this task and user."""
    setting = None
    if current_user and current_user.is_authenticated:
        setting = get_user_setting(current_user.id)
    if setting and setting.api_key_enc:
        info = PROVIDERS.get(setting.provider, PROVIDERS["gemini"])
        model = setting.email_model if task == "email" else setting.action_model
        if model not in info["models"]:
            model = info["default"]
        return setting.provider, model, decrypt_key(setting.api_key_enc), "user"

    key = current_app.config.get("GEMINI_API_KEY")
    if not key:
        raise AIError("No AI key is available. Add your own key under AI Settings.", "config")
    return SERVER_DEFAULT[0], SERVER_DEFAULT[1], key, "server"


# ---------- provider calls ----------
def _post(url, headers, payload, timeout):
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.Timeout:
        raise AIError("timeout: the AI provider did not answer in time.", "timeout")
    except requests.RequestException as exc:
        raise AIError(f"Could not reach the AI provider: {exc}", "other")
    if resp.status_code == 429:
        raise AIError("429 quota exceeded: the AI provider is rate-limiting requests.", "rate_limit")
    if resp.status_code in (401, 403):
        raise AIError(f"{resp.status_code} The API key was rejected by the provider.", "auth")
    if resp.status_code in (500, 502, 503, 504):
        raise AIError("The AI provider is busy right now (high demand). Please try again in a minute.", "other")
    if resp.status_code >= 400:
        raise AIError(f"The AI provider returned an error ({resp.status_code}).", "other")
    try:
        return resp.json()
    except ValueError:
        raise AIError("The AI provider returned an unreadable response.", "other")


def _call_gemini(model, key, prompt, timeout):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    data = _post(url, {"x-goog-api-key": key}, {"contents": [{"parts": [{"text": prompt}]}]}, timeout)
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise AIError("The AI provider returned no text.", "other")
    usage = data.get("usageMetadata", {})
    return text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)


def _call_openai_style(url, model, key, prompt, timeout):
    data = _post(url, {"Authorization": f"Bearer {key}"},
                 {"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout)
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise AIError("The AI provider returned no text.", "other")
    usage = data.get("usage", {})
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def _call_anthropic(model, key, prompt, timeout):
    data = _post("https://api.anthropic.com/v1/messages",
                 {"x-api-key": key, "anthropic-version": "2023-06-01"},
                 {"model": model, "max_tokens": 600, "messages": [{"role": "user", "content": prompt}]}, timeout)
    try:
        text = data["content"][0]["text"]
    except (KeyError, IndexError):
        raise AIError("The AI provider returned no text.", "other")
    usage = data.get("usage", {})
    return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


def _call(provider, model, key, prompt, timeout):
    if provider == "gemini":
        return _call_gemini(model, key, prompt, timeout)
    if provider == "openai":
        return _call_openai_style("https://api.openai.com/v1/chat/completions", model, key, prompt, timeout)
    if provider == "deepseek":
        return _call_openai_style("https://api.deepseek.com/chat/completions", model, key, prompt, timeout)
    if provider == "anthropic":
        return _call_anthropic(model, key, prompt, timeout)
    raise AIError("Unknown AI provider.", "config")


# ---------- usage log ----------
def _log(task, provider, model, source, tin, tout, status, error=None):
    """Never let logging break the request."""
    try:
        from app.models import AIUsage
        row = AIUsage(
            user_id=current_user.id if current_user and current_user.is_authenticated else None,
            task=task, provider=provider, model=model, key_source=source,
            input_tokens=tin, output_tokens=tout,
            est_cost=estimate_cost(provider, model, tin, tout),
            status=status, error_message=(error or "")[:200] or None,
        )
        db.session.add(row)
        db.session.commit()
    except Exception:
        db.session.rollback()


def generate_text(task, prompt, timeout=15):
    """task is 'email' or 'action'. Returns the model's text or raises AIError."""
    provider, model, key, source = resolve(task)
    try:
        text, tin, tout = _call(provider, model, key, prompt, timeout)
    except AIError as exc:
        _log(task, provider, model, source, 0, 0, exc.kind, str(exc))
        raise
    _log(task, provider, model, source, tin, tout, "ok")
    return text.strip()