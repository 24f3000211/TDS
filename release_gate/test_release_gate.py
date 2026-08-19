from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def payload():
    return {
        "target": "preview",
        "event": "pull_request",
        "ref": "refs/heads/feature",
        "workflow": {
            "trigger": "pull_request",
            "permissions": {"contents": "read", "packages": "write", "id-token": "none"},
            "testsPassed": True,
            "matrixComplete": True,
            "failFast": False,
            "actions": [
                {"owner": "actions", "name": "checkout", "ref": "v4"},
                {"owner": "docker", "name": "build-push-action", "ref": "0123456789abcdef0123456789abcdef01234567"},
            ],
        },
        "image": {
            "multiStage": True,
            "runsAsRoot": False,
            "secretMode": "none",
            "criticalVulnerabilities": 0,
            "digestPinned": True,
        },
    }


def test_safe_preview():
    r = client.post("/release-gate", json=payload())
    assert r.json() == {"decision": "promote", "violations": []}


def test_multi_failure():
    p = payload()
    p["workflow"]["permissions"]["issues"] = "write"
    p["workflow"]["trigger"] = "pull_request_target"
    p["workflow"]["testsPassed"] = False
    p["workflow"]["matrixComplete"] = False
    p["workflow"]["failFast"] = True
    p["workflow"]["actions"][1]["ref"] = "v6"
    p["image"].update({"multiStage": False, "runsAsRoot": True, "secretMode": "copy", "criticalVulnerabilities": 1, "digestPinned": False})
    result = client.post("/release-gate", json=p).json()
    assert result["decision"] == "block"
    assert set(result["violations"]) == {
        "EXCESS_PERMISSION", "UNSAFE_PR_TRIGGER", "TESTS_INCOMPLETE", "MUTABLE_ACTION",
        "SINGLE_STAGE_IMAGE", "ROOT_RUNTIME", "SECRET_IN_LAYER", "CRITICAL_CVE", "UNPINNED_IMAGE"
    }


def test_valid_production():
    p = payload()
    p["target"] = "production"
    p["event"] = "push"
    p["ref"] = "refs/heads/main"
    p["workflow"]["trigger"] = "push"
    p["workflow"]["environmentApproval"] = True
    assert client.post("/release-gate", json=p).json() == {"decision": "promote", "violations": []}
