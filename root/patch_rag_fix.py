from pathlib import Path

p = Path("src/rag/answer.py")
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, f"not found exactly once: {old[:70]!r}"
    s = s.replace(old, new)


rep('    return {"provider": None, "api_key": None, "model": None, "host": None}',
    '    return {"provider": provider, "api_key": None, "model": None, "host": None}   # None, or an unknown name that surfaces as an error')
rep('    if client is None and not is_configured({"provider": provider, "api_key": api_key, "model": model}):',
    '    unknown = provider is not None and provider not in DEFAULT_MODELS            # a typo must surface as an error\n'
    '    if client is None and not unknown and not is_configured({"provider": provider, "api_key": api_key, "model": model}):')
p.write_text(s, encoding="utf-8")
print("answer.py patched")