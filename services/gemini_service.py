"""
ResQNet AI - Gemini AI Service
Wraps Google GenAI SDK with retry logic, mode detection, and JSON parsing.
Automatically falls back to simulation mode if API key is invalid.
Uses the new google-genai SDK (replaces deprecated google-generativeai).
"""

import json
import time
import re
from typing import Any, Dict, Optional, Tuple

from config.settings import (
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_FALLBACK,
    GEMINI_TEMPERATURE, GEMINI_MAX_TOKENS, GEMINI_TIMEOUT
)

# Module-level state
_initialized: bool = False
_client: Optional[Any] = None
_active_model: str = ""
_mode: str = "simulation"
_mode_reason: str = "Not yet initialized"


def initialize_gemini() -> Tuple[str, str]:
    """
    Initialize the Gemini client using google-genai SDK.
    Returns (mode, reason) - mode is 'live' or 'simulation'.
    """
    global _initialized, _client, _active_model, _mode, _mode_reason

    if _initialized:
        return _mode, _mode_reason

    if not GEMINI_API_KEY or GEMINI_API_KEY in ("your_gemini_api_key_here", ""):
        _mode = "simulation"
        _mode_reason = "No Gemini API key configured - using simulation mode"
        _initialized = True
        return _mode, _mode_reason

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        # Test connection with primary model
        models_to_try = [GEMINI_MODEL, GEMINI_MODEL_FALLBACK, "gemini-1.5-flash"]
        connected = False

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents="Reply with exactly the word: OK",
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=10,
                    ),
                )
                if response and response.text:
                    _client = client
                    _active_model = model_name
                    _mode = "live"
                    _mode_reason = f"Connected to {model_name} via Google GenAI SDK"
                    connected = True
                    break
            except Exception as e:
                continue

        if not connected:
            _mode = "simulation"
            _mode_reason = "API key provided but connection failed - using simulation mode"

    except ImportError:
        # Fall back to old SDK if new one not available
        try:
            import google.generativeai as genai_old

            genai_old.configure(api_key=GEMINI_API_KEY)
            model = genai_old.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content("Reply with exactly: OK")
            if response and response.text:
                _client = ("old_sdk", genai_old, GEMINI_MODEL)
                _active_model = GEMINI_MODEL
                _mode = "live"
                _mode_reason = f"Connected to {GEMINI_MODEL} (legacy SDK)"
        except Exception as e2:
            _mode = "simulation"
            _mode_reason = f"SDK error: {str(e2)[:80]}"

    except Exception as e:
        _mode = "simulation"
        _mode_reason = f"Gemini init error: {str(e)[:100]}"

    _initialized = True
    return _mode, _mode_reason


def get_mode() -> str:
    """Return current operating mode: 'live' or 'simulation'."""
    if not _initialized:
        initialize_gemini()
    return _mode


def get_mode_info() -> Dict[str, str]:
    """Return dict with mode and reason."""
    if not _initialized:
        initialize_gemini()
    return {"mode": _mode, "reason": _mode_reason}


def _extract_json(text: str) -> Optional[Dict]:
    """Extract first JSON object or array from LLM response text."""
    if not text:
        return None

    # Direct parse
    try:
        return json.loads(text.strip())
    except Exception:
        pass

    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Find raw JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return None


def call_gemini(prompt: str, max_retries: int = 2) -> Tuple[Optional[Dict], int, str]:
    """
    Call Gemini with a prompt. Returns (parsed_json, execution_ms, raw_text).
    Returns (None, ms, raw_text) if parsing fails or API unavailable.
    """
    if not _initialized:
        initialize_gemini()

    if _mode != "live" or _client is None:
        return None, 0, ""

    start = time.time()

    for attempt in range(max_retries + 1):
        try:
            # New google-genai SDK
            if isinstance(_client, tuple):
                # Old SDK fallback
                _, old_genai, model_name = _client
                model = old_genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                raw_text = response.text if response and response.text else ""
            else:
                # New google-genai SDK
                from google.genai import types
                response = _client.models.generate_content(
                    model=_active_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=GEMINI_TEMPERATURE,
                        max_output_tokens=GEMINI_MAX_TOKENS,
                    ),
                )
                raw_text = response.text if response and response.text else ""

            elapsed_ms = int((time.time() - start) * 1000)
            parsed = _extract_json(raw_text)
            return parsed, elapsed_ms, raw_text

        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                elapsed_ms = int((time.time() - start) * 1000)
                return None, elapsed_ms, f"API error after {max_retries+1} attempts: {str(e)[:100]}"

    return None, 0, ""
