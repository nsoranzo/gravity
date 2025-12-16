from io import StringIO

import jsonref

import yaml
from gravity.settings import (
    GunicornSettings,
    Settings,
    TusdSettings,
)


def process_property(key, value, depth=0):
    extra_white_space = "  " * depth
    default = value.get("default", "")
    if isinstance(default, dict):
        # Little hack that prevents listing the default value for tusd in the sample config
        default = {}
    if default != "":
        # make values more yaml-like.
        default = yaml.dump(default)
        if default.endswith("\n...\n"):
            default = default[: -(len("\n...\n"))]
        default = default.strip()
    description = "\n".join(f"{extra_white_space}# {desc}".rstrip() for desc in value["description"].strip().split("\n"))
    combined = value.get("allOf", [])
    if not combined and value.get("anyOf"):
        # we've got a union
        combined = [c for c in value["anyOf"] if c["type"] == "object"]
    if combined and combined[0].get("properties"):
        # we've got a nested map, add key once
        description = f"{description}\n{extra_white_space}{key}:\n"
    has_child = False
    for item in combined:
        if "enum" in item:
            enum_items = [i for i in item["enum"] if not i.startswith("_")]
            description = f'{description}\n{extra_white_space}# Valid options are: {", ".join(enum_items)}'
        if "properties" in item:
            has_child = True
            for _key, _value in item["properties"].items():
                description = f"{description}\n{process_property(_key, _value, depth=depth+1)}"
    if not has_child or key == "handlers":
        comment = "# "
        if key == "gravity":
            # gravity section should not be commented
            comment = ""
        if default == "":
            value_sep = ""
        else:
            value_sep = " "
        description = f"{description}\n{extra_white_space}{comment}{key}:{value_sep}{default}\n"
    return description


def settings_to_sample():
    schema = Settings.model_json_schema()
    # expand schema for easier processing
    data = jsonref.replace_refs(schema, merge_props=True)
    strings = [process_property("gravity", data)]
    for key, value in data["properties"].items():
        strings.append(process_property(key, value, 1))
    concat = "\n".join(strings)
    return concat


def test_json_schema():
    schema = Settings.model_json_schema()
    assert "Configuration for Gravity process manager" in schema["description"]


def test_extra_fields_allowed():
    s = Settings(extra=1)  # type: ignore[call-arg]
    assert not hasattr(s, "extra")


def test_defaults_loaded():
    settings = Settings()
    assert isinstance(settings.gunicorn, GunicornSettings)
    assert settings.gunicorn.bind == "localhost:8080"
    assert isinstance(settings.tusd, TusdSettings)
    assert settings.tusd.tusd_path == "tusd"
    assert settings.tusd.upload_dir == ""


def test_defaults_override_constructor():
    settings = Settings(gunicorn=GunicornSettings(bind="localhost:8081"))
    assert isinstance(settings.gunicorn, GunicornSettings)
    assert settings.gunicorn.bind == "localhost:8081"
    # Try Pydantic's ability to accept dicts for nested models
    settings = Settings(gunicorn={"bind": "localhost:8081"})  # type: ignore[arg-type]
    assert isinstance(settings.gunicorn, GunicornSettings)
    assert settings.gunicorn.bind == "localhost:8081"


def test_defaults_override_env_var(monkeypatch):
    monkeypatch.setenv("GRAVITY_GUNICORN.BIND", "localhost:8081")
    settings = Settings()
    assert isinstance(settings.gunicorn, GunicornSettings)
    assert settings.gunicorn.bind == "localhost:8081"


def test_schema_to_sample():
    sample = settings_to_sample()
    settings = Settings(**yaml.safe_load(StringIO(sample))["gravity"])
    default_settings = Settings()
    assert settings.dict() == default_settings.dict()
