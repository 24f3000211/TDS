from api.release_gate import ReleaseGateRequest, evaluate


def base():
    return ReleaseGateRequest(
        target="preview",
        event="pull_request",
        ref="refs/heads/feature",
        workflow={
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
        image={"multiStage": True, "runsAsRoot": False, "secretMode": "none", "criticalVulnerabilities": 0, "digestPinned": True},
    )


def test_safe():
    assert evaluate(base()) == {"decision": "promote", "violations": []}


def test_multi_failure():
    r = base()
    r.workflow["permissions"]["issues"] = "write"
    r.workflow.update(trigger="pull_request_target", testsPassed=False, matrixComplete=False, failFast=True)
    r.workflow["actions"][1]["ref"] = "v6"
    r.image.update(multiStage=False, runsAsRoot=True, secretMode="copy", criticalVulnerabilities=1, digestPinned=False)
    result = evaluate(r)
    assert result["decision"] == "block"
    assert set(result["violations"]) == {
        "EXCESS_PERMISSION", "UNSAFE_PR_TRIGGER", "TESTS_INCOMPLETE", "MUTABLE_ACTION",
        "SINGLE_STAGE_IMAGE", "ROOT_RUNTIME", "SECRET_IN_LAYER", "CRITICAL_CVE", "UNPINNED_IMAGE",
    }


def test_production():
    r = base()
    r.target = "production"
    r.event = "push"
    r.ref = "refs/heads/main"
    r.workflow["trigger"] = "push"
    r.workflow["environmentApproval"] = True
    assert evaluate(r) == {"decision": "promote", "violations": []}


def test_production_requires_main_and_approval():
    r = base()
    r.target = "production"
    result = evaluate(r)
    assert result["decision"] == "block"
    assert "INVALID_PRODUCTION_REF" in result["violations"]
    assert "APPROVAL_REQUIRED" in result["violations"]
