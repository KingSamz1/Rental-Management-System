"""
i18n.py — Translation layer for LandlordPro.
Translates all strings in one batch API call per language switch.
Results cached in session state — zero API calls on subsequent renders.
"""
import streamlit as st
import requests

LANGUAGES = {
    "English":    "en",
    "Français":   "fr",
    "Español":    "es",
    "Português":  "pt",
    "Kiswahili":  "sw",
    "العربية":    "ar",
    "हिन्दी":     "hi",
    "中文":       "zh",
    "日本語":     "ja",
    "Deutsch":    "de",
    "Русский":    "ru",
}


def get_language() -> str:
    return st.session_state.get("app_lang", "en")


def set_language(lang_code: str):
    if lang_code != st.session_state.get("app_lang", "en"):
        st.session_state["app_lang"] = lang_code
        st.session_state.pop("_trans_cache", None)
        st.session_state.pop("_trans_lang", None)


def language_selector(location="sidebar"):
    lang_code    = get_language()
    current_name = next((n for n, c in LANGUAGES.items() if c == lang_code), "English")
    options      = list(LANGUAGES.keys())

    if location == "sidebar":
        chosen = st.sidebar.selectbox(
            "🌐 Language", options,
            index=options.index(current_name),
            key="_lang_selector_sb",
        )
    else:
        chosen = st.selectbox(
            "🌐 Language", options,
            index=options.index(current_name),
            key="_lang_selector_inline",
        )

    new_code = LANGUAGES[chosen]
    if new_code != lang_code:
        set_language(new_code)
        st.rerun()


def _translate_batch(texts: list[str], lang_code: str) -> dict[str, str]:
    unique   = list(dict.fromkeys(t for t in texts if t and t.strip()))
    if not unique:
        return {}
    lang_name = next((n for n, c in LANGUAGES.items() if c == lang_code), lang_code)
    numbered  = "\n".join(f"{i+1}|||{s}" for i, s in enumerate(unique))
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 4096,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Translate these UI strings to {lang_name}. "
                        f"Return ONLY the translations in the exact same format: "
                        f"number|||translated text, one per line. "
                        f"Keep emoji exactly as-is. Do not add any other text.\n\n"
                        f"{numbered}"
                    )
                }]
            },
            timeout=30,
        )
        resp.raise_for_status()
        result  = resp.json()["content"][0]["text"].strip()
        mapping = {}
        for line in result.split("\n"):
            line = line.strip()
            if "|||" in line:
                parts = line.split("|||", 1)
                try:
                    idx = int(parts[0].strip()) - 1
                    if 0 <= idx < len(unique):
                        mapping[unique[idx]] = parts[1].strip()
                except ValueError:
                    pass
        return mapping
    except Exception:
        return {}


def _ensure_cache(strings: list[str]):
    lang = get_language()
    if lang == "en":
        return
    cache      = st.session_state.setdefault("_trans_cache", {})
    cache_lang = st.session_state.get("_trans_lang", "en")
    if cache_lang != lang:
        cache.clear()
        st.session_state["_trans_lang"] = lang
    missing = [s for s in strings if s and s.strip() and f"{lang}:{s}" not in cache]
    if not missing:
        return
    mapping = _translate_batch(missing, lang)
    for orig, translated in mapping.items():
        cache[f"{lang}:{orig}"] = translated


def t(text: str) -> str:
    lang = get_language()
    if lang == "en" or not text or not text.strip():
        return text
    cache = st.session_state.get("_trans_cache", {})
    key   = f"{lang}:{text}"
    if key in cache:
        return cache[key]
    mapping = _translate_batch([text], lang)
    result  = mapping.get(text, text)
    cache[key] = result
    st.session_state["_trans_cache"] = cache
    return result


def preload_translations(*strings: str):
    """Call at top of each page to batch-translate all strings in one API call."""
    _ensure_cache(list(strings))
