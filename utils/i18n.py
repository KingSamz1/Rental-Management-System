"""
i18n.py — Simple translation layer for LandlordPro.
Uses Claude API to translate UI strings on demand, with session-level caching.
"""
import streamlit as st

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
    """Return the active language code, default English."""
    return st.session_state.get("app_lang", "en")

def set_language(lang_code: str):
    st.session_state["app_lang"] = lang_code
    # Clear translation cache when language changes
    st.session_state.pop("_trans_cache", None)

def language_selector(location="sidebar"):
    """Render the language dropdown. Call from sidebar or settings."""
    lang_code = get_language()
    current_name = next((n for n, c in LANGUAGES.items() if c == lang_code), "English")
    options = list(LANGUAGES.keys())

    if location == "sidebar":
        chosen = st.sidebar.selectbox(
            "🌐 Language",
            options,
            index=options.index(current_name),
            key="_lang_selector",
        )
    else:
        chosen = st.selectbox(
            "🌐 Interface language",
            options,
            index=options.index(current_name),
            key="_lang_selector_inline",
        )

    new_code = LANGUAGES[chosen]
    if new_code != lang_code:
        set_language(new_code)
        st.rerun()

def t(text: str) -> str:
    """
    Translate a string to the active language.
    Returns original text if language is English or translation fails.
    Caches all translations in session state to avoid repeated API calls.
    """
    lang = get_language()
    if lang == "en" or not text or not text.strip():
        return text

    cache = st.session_state.setdefault("_trans_cache", {})
    cache_key = f"{lang}:{text}"
    if cache_key in cache:
        return cache[cache_key]

    try:
        import requests
        lang_name = next((n for n, c in LANGUAGES.items() if c == lang), lang)
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Translate the following UI text to {lang_name}. "
                        f"Return ONLY the translated text, nothing else. "
                        f"Keep any emoji, punctuation, and formatting exactly as-is. "
                        f"Text to translate:\n{text}"
                    )
                }]
            },
            timeout=10,
        )
        result = response.json()["content"][0]["text"].strip()
        cache[cache_key] = result
        return result
    except Exception:
        return text


def t_batch(texts: list[str]) -> list[str]:
    """Translate a list of strings in one API call. More efficient for pages."""
    lang = get_language()
    if lang == "en":
        return texts

    cache = st.session_state.setdefault("_trans_cache", {})
    results = []
    to_translate = []
    indices = []

    for i, text in enumerate(texts):
        key = f"{lang}:{text}"
        if key in cache or not text.strip():
            results.append((i, cache.get(key, text)))
        else:
            to_translate.append(text)
            indices.append(i)
            results.append((i, text))  # placeholder

    if to_translate:
        try:
            import requests
            lang_name = next((n for n, c in LANGUAGES.items() if c == lang), lang)
            numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(to_translate))
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 2000,
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Translate these numbered UI strings to {lang_name}. "
                            f"Return ONLY the translations, one per line, numbered the same way. "
                            f"Keep emoji and formatting exactly as-is.\n\n{numbered}"
                        )
                    }]
                },
                timeout=15,
            )
            lines = response.json()["content"][0]["text"].strip().split("\n")
            translated = []
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and ". " in line:
                    translated.append(line.split(". ", 1)[1])
                elif line:
                    translated.append(line)

            for idx, orig_idx in enumerate(indices):
                if idx < len(translated):
                    tr = translated[idx]
                    cache[f"{lang}:{to_translate[idx]}"] = tr
                    results[orig_idx] = (orig_idx, tr)
        except Exception:
            pass

    return [v for _, v in sorted(results)]
