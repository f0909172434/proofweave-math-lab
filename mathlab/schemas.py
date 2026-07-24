from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .errors import ValidationError
from .io import find_project_root


TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def load_schema(name: str, root: Path | None = None) -> dict[str, Any]:
    base = root or find_project_root()
    path = base / "schemas" / (name if name.endswith(".json") else f"{name}.schema.json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"Schema not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid schema JSON {path}: {exc}") from exc


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    names = [expected] if isinstance(expected, str) else expected
    for name in names:
        py_type = TYPE_MAP.get(name)
        if py_type is None:
            continue
        if name in {"integer", "number"} and isinstance(value, bool):
            continue
        if isinstance(value, py_type):
            return True
    return False


def validate_instance(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate the deterministic subset of JSON Schema used by this project.

    The schema files remain standards-compliant draft 2020-12 artifacts.  This
    dependency-free validator enforces every keyword used by the bundled
    schemas: type, required, enum, const, numeric/string/array bounds,
    uniqueItems, date-time/URI formats, properties and additionalProperties.
    Install a full validator when remote `$ref` or other advanced keywords are
    added.
    """

    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None and not _matches_type(value, expected):
        return [f"{path}: expected {expected}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string is longer than maxLength")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError("timezone is required")
            except ValueError:
                errors.append(f"{path}: expected an RFC 3339 date-time with timezone")
        elif schema.get("format") == "uri":
            parsed_uri = urlparse(value)
            if not parsed_uri.scheme or (
                parsed_uri.scheme in {"http", "https"} and not parsed_uri.netloc
            ):
                errors.append(f"{path}: expected an absolute URI")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: number is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: number is above maximum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: array is shorter than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: array is longer than maxItems")
        if schema.get("uniqueItems"):
            canonical = [
                json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for item in value
            ]
            if len(canonical) != len(set(canonical)):
                errors.append(f"{path}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_instance(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required property {required!r}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors.extend(validate_instance(item, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property {key!r}")
    return errors


def require_valid(value: Any, schema_name: str, root: Path | None = None) -> None:
    errors = validate_instance(value, load_schema(schema_name, root))
    if errors:
        raise ValidationError("; ".join(errors))


def validate_all_schemas(root: Path | None = None) -> list[str]:
    base = root or find_project_root()
    errors: list[str] = []
    for path in sorted((base / "schemas").glob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                errors.append(f"{path}: not declared as draft 2020-12")
            if schema.get("type") != "object":
                errors.append(f"{path}: root type must be object")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")
    return errors
