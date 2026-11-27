import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "vesync"


def test_manifest_and_translations_parity():
    manifest = json.loads((COMP / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "vesync"
    assert manifest["config_flow"] is True

    strings = json.loads((COMP / "strings.json").read_text(encoding="utf-8"))
    en = json.loads((COMP / "translations" / "en.json").read_text(encoding="utf-8"))
    es = json.loads((COMP / "translations" / "es.json").read_text(encoding="utf-8"))

    assert strings == en
    assert set(es["entity"]["sensor"]["program"]["state"]) == set(en["entity"]["sensor"]["program"]["state"])
    assert set(es["entity"]["sensor"]["cook_status"]["state"]) == set(en["entity"]["sensor"]["cook_status"]["state"])


def test_all_python_files_compile():
    for py_file in COMP.glob("*.py"):
        py_compile.compile(str(py_file), doraise=True)
