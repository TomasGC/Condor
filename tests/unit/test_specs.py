import json

import pytest
import validate
from jsonschema import Draft202012Validator

SPEC_FILES = sorted(validate.SPECS_DIR.glob("*.json"))


def test_there_is_at_least_one_spec():
    assert SPEC_FILES


@pytest.mark.parametrize("path", SPEC_FILES, ids=lambda path: path.stem)
class TestEverySpec:
    def spec(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_is_a_valid_json_schema(self, path):
        Draft202012Validator.check_schema(self.spec(path))

    def test_is_named_after_its_file(self, path):
        assert self.spec(path)["title"] == path.stem
        assert validate.MODULE_PATTERN.match(path.stem)

    def test_every_input_states_the_rule_an_error_shows(self, path):
        for name, prop in self.spec(path)["properties"].items():
            assert prop.get("x-rule"), f"{name} has no x-rule"

    def test_every_input_is_required(self, path):
        spec = self.spec(path)
        assert set(spec["required"]) == set(spec["properties"])

    def test_a_json_input_declares_its_content_schema(self, path):
        for name, prop in self.spec(path)["properties"].items():
            if prop.get("contentMediaType") == validate.JSON_MEDIA_TYPE:
                assert prop["type"] == "string", name
                Draft202012Validator.check_schema(prop["contentSchema"])
