import json
from pathlib import Path
from app.core.settings import load_settings, save_settings, get_default_settings
from app.core.paths import LOG_FILE


def test_default_settings(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    settings = load_settings(settings_file)
    defaults = get_default_settings()

    assert settings["theme"] == defaults["theme"]
    assert settings["container"] == defaults["container"]
    assert settings["auto_update"] == defaults["auto_update"]
    assert settings["shortcut_created"] == defaults["shortcut_created"]
    assert settings["last_tool_check"] == 0
    assert settings["last_app_check"] == 0


def test_save_and_load_settings(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    settings = get_default_settings()
    settings["theme"] = "light"
    settings["container"] = "mp4"

    save_settings(settings, settings_file)
    loaded = load_settings(settings_file)

    assert loaded["theme"] == "light"
    assert loaded["container"] == "mp4"


def test_corrupt_settings_fallback(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("CORRUPT_JSON_GARBAGE!!!", encoding="utf-8")

    settings = load_settings(settings_file)
    defaults = get_default_settings()

    assert settings == defaults
    # Verify that a warning was written to log
    assert LOG_FILE.exists()
    log_content = LOG_FILE.read_text(encoding="utf-8")
    assert "resetting to defaults" in log_content


def test_corrupt_non_dict_fallback(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    settings = load_settings(settings_file)
    defaults = get_default_settings()

    assert settings == defaults
