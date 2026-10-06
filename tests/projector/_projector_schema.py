"""A small stdlib JSON-Schema (draft 2020-12 subset) validator for the console contract schema, Python 3.9.

Covers exactly the keywords contracts.schema.json uses: $ref (#/$defs/..), type (string or list), enum, const,
properties, required, items, pattern, minimum, maxLength, anyOf. Cross-checked against the `jsonschema` package on the
pinned 3.12 stack (see test_projector_schema_selfcheck). Test helper only; prooflab/ code never imports it.
"""
import json
import os
import re

SCHEMA_PATH = os.path.join("handoffs", "ifabric-handoff-3", "evidence-console-plan", "schemas", "contracts.schema.json")


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def load_schema():
    with open(os.path.join(repo_root(), SCHEMA_PATH), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _is_type(value, name):
    if name == "string":
        return isinstance(value, str)
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    raise ValueError("unknown type " + name)


def validate(instance, schema, root=None, path="$"):
    """Every error as a string; [] = valid."""
    root = root or schema
    errors = []
    if "$ref" in schema:
        ref = schema["$ref"]
        assert ref.startswith("#/"), ref
        node = root
        for part in ref[2:].split("/"):
            node = node[part]
        return validate(instance, node, root, path)
    if "anyOf" in schema:
        if not any(not validate(instance, s, root, path) for s in schema["anyOf"]):
            errors.append("%s: matches none of anyOf" % path)
    t = schema.get("type")
    if t is not None:
        names = t if isinstance(t, list) else [t]
        if not any(_is_type(instance, n) for n in names):
            return errors + ["%s: type %r, wanted %s" % (path, type(instance).__name__, names)]
    if "const" in schema and instance != schema["const"]:
        errors.append("%s: %r != const %r" % (path, instance, schema["const"]))
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r not in enum %s" % (path, instance, schema["enum"]))
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: %r does not match %s" % (path, instance, schema["pattern"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: longer than %d" % (path, schema["maxLength"]))
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: below minimum" % path)
    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append("%s: required %r missing" % (path, name))
        for name, sub in (schema.get("properties") or {}).items():
            if name in instance:
                errors += validate(instance[name], sub, root, "%s.%s" % (path, name))
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors += validate(item, schema["items"], root, "%s[%d]" % (path, i))
    return errors


def validate_def(instance, def_name, schema=None):
    schema = schema or load_schema()
    return validate(instance, {"$ref": "#/$defs/" + def_name}, schema)
