import json

import pytest

from r3e_coach import store


def test_entry_key_and_layout_fallback():
    assert store.entry_key("Sachsenring", "Sachsenring", "Audi R8") == "Sachsenring|Sachsenring|Audi R8"
    # fehlt das Layout, wird der Streckenname eingesetzt
    assert store.entry_key("Sachsenring", None, "Audi R8") == "Sachsenring|Sachsenring|Audi R8"
    assert store.entry_key("Nordschleife", "GP-Strecke", "Audi R8") == "Nordschleife|GP-Strecke|Audi R8"


def test_entry_key_requires_track_and_vehicle():
    with pytest.raises(ValueError):
        store.entry_key("", None, "Audi R8")
    with pytest.raises(ValueError):
        store.entry_key("Sachsenring", None, "")


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "setups.json"
    data = store.empty_data()
    store.add_analysis(data, "Sachsenring|Sachsenring|Audi R8", {
        "csv_source": "x.csv", "samples": 10, "findings": [],
    })
    store.save(data, path)
    assert not (tmp_path / "setups.json.tmp").exists()  # atomar: keine .tmp-Reste
    loaded = store.load(path)
    assert loaded["schema_version"] == 1
    assert "Sachsenring|Sachsenring|Audi R8" in loaded["setups"]


def test_load_missing_and_corrupt_tolerated(tmp_path):
    assert store.load(tmp_path / "fehlt.json")["setups"] == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{kein json", encoding="utf-8")
    assert store.load(bad)["setups"] == {}


def test_load_ignores_unknown_fields_keeps_entries(tmp_path):
    path = tmp_path / "setups.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "future_field": 42,
        "setups": {"A|A|B": {"notes": "n", "neues_feld": "x"}},
    }), encoding="utf-8")
    data = store.load(path)
    assert "A|A|B" in data["setups"]
    assert data["setups"]["A|A|B"]["neues_feld"] == "x"


def test_ensure_entry_structure():
    data = store.empty_data()
    entry = store.ensure_entry(data, "A|A|B")
    assert entry["chassis"]["arb_front"] is None
    assert entry["tires"]["pressure_rear"] is None
    assert entry["analyses"] == []
    assert entry["history"] == []
    # bestehende Felder bleiben, fehlende werden ergänzt
    data["setups"]["A|A|B"] = {"notes": "alt"}
    entry = store.ensure_entry(data, "A|A|B")
    assert entry["notes"] == "alt"
    assert entry["chassis"]["toe_rear"] is None


def test_add_analysis_newest_first_and_applied_default():
    data = store.empty_data()
    store.add_analysis(data, "A|A|B", {"csv_source": "alt.csv", "findings": []})
    store.add_analysis(data, "A|A|B", {"csv_source": "neu.csv", "findings": []})
    entry = store.get_entry(data, "A|A|B")
    assert [a["csv_source"] for a in entry["analyses"]] == ["neu.csv", "alt.csv"]
    assert all(a["applied"] is None for a in entry["analyses"])
    assert entry["updated_at"]


def test_upsert_values_and_history():
    data = store.empty_data()
    key = "A|A|B"
    store.upsert_values(data, key, chassis={"arb_front": 6},
                        tires={"pressure_rear": 1.8},
                        target_lap_ms=96500, notes="Testlauf")
    entry = store.get_entry(data, key)
    assert entry["chassis"]["arb_front"] == 6
    assert entry["chassis"]["arb_rear"] is None  # nicht angefasst
    assert entry["tires"]["pressure_rear"] == 1.8
    assert entry["target_lap_ms"] == 96500
    assert entry["notes"] == "Testlauf"
    store.add_history(data, key, "Druck hinten 1,9 → 1,8 bar", "stabiler")
    assert store.get_entry(data, key)["history"][0]["change"].startswith("Druck")
    assert store.get_entry(data, key)["history"][0]["observed"] == "stabiler"


def test_none_values_are_ignored_in_upsert():
    data = store.empty_data()
    store.upsert_values(data, "A|A|B", target_lap_ms=96000, notes=None)
    entry = store.get_entry(data, "A|A|B")
    assert entry["target_lap_ms"] == 96000
    assert entry["notes"] == ""  # None ändert nichts am vorhandenen Wert


def test_list_keys_sorted():
    data = store.empty_data()
    for key in ("Z|Z|C", "A|A|B"):
        store.ensure_entry(data, key)
    assert store.list_keys(data) == ["A|A|B", "Z|Z|C"]


def test_default_store_path_in_app_dir():
    assert store.default_store_path().endswith("setups.json")


def test_schema_version_written(tmp_path):
    path = tmp_path / "setups.json"
    store.save(store.empty_data(), path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
