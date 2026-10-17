import json
from pathlib import Path

from app.main import app
from app.services.registry import F

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"


def test_all_90_features_are_registered_and_real():
    cat = json.loads((ROOT / "data" / "features.json").read_text(encoding="utf-8"))
    assert len(cat) == 90
    assert {c["id"] for c in cat} == set(F), "catalogue and registry differ"
    paths = {f"{m.upper()} {p}" for p, v in app.openapi()["paths"].items() for m in v}
    for fid, (apis, ui, _) in F.items():
        assert apis or ui, f"{fid} has neither API nor UI"
        for a in apis:
            assert a in paths, f"{fid}: endpoint missing {a}"
        for u in filter(None, ui.split(",")):
            assert (SRC / u).exists(), f"{fid}: UI file missing {u}"
