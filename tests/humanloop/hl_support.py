"""Shared helpers: fixtures, the fake ServiceNow client, an injected environment."""
import copy
import json
import os

from prooflab.servicenow.client import ServiceNowClient
from prooflab.tests.fake_servicenow import CLIENT_ID, CLIENT_SECRET, INTEGRATION_USER, OWNER_USER, FakeServiceNow

HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT = {"value": 10000, "operator": "<=", "unit": "tokens"}   # a test input, not code policy


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as handle:
        return copy.deepcopy(json.load(handle))


def assessment(**over):
    data = fixture("assessment-breached.json")
    data.pop("_note")
    data.update(over)
    return data


def make_client(fake):
    return ServiceNowClient(base_url=fake.base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)


def env_for(log, approval_log=None, owner=OWNER_USER):
    env = {"SNOW_OWNER_USER": owner, "PROOFLAB_DELIVERY_LOG": str(log), "SNOW_INTEGRATION_USER": INTEGRATION_USER}
    if approval_log:
        env["PROOFLAB_APPROVAL_DELIVERY_LOG"] = str(approval_log)
    return env


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)
