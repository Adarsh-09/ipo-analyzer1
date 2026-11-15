import re
from pathlib import Path

t = Path("tests/test_environment.py")
s = t.read_text(encoding="utf-8")
s, n = re.subn(r'^[ \t]*"models",[ \t]*\r?\n', "", s, count=1, flags=re.M)
assert n == 1, "could not find the top-level 'models' entry in test_environment.py"
t.write_text(s, encoding="utf-8")

p = Path("root/train_final_model.py")
s = p.read_text(encoding="utf-8")
old = 'ROOT / "models/ipovision_final.joblib"'
assert s.count(old) == 1, "model path line not found in train_final_model.py"
p.write_text(s.replace(old, 'ROOT / "src/models/artifacts/ipovision_final.joblib"'), encoding="utf-8")
print("patched")