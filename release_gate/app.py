import re
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
EXPECTED_PERMISSIONS = {"contents": "read", "packages": "write", "id-token": "none"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")

class ReleaseGateRequest(BaseModel):
    target: str
    event: str
    ref: str
    workflow: dict
    image: dict


def evaluate(req: ReleaseGateRequest):
    violations = []
    workflow, image = req.workflow, req.image

    if workflow.get("permissions", {}) != EXPECTED_PERMISSIONS:
        violations.append("EXCESS_PERMISSION")

    if req.event == "pull_request":
        if workflow.get("trigger") != "pull_request":
            violations.append("UNSAFE_PR_TRIGGER")
        if workflow.get("testsPassed") is not True or workflow.get("matrixComplete") is not True or workflow.get("failFast") is not False:
            violations.append("TESTS_INCOMPLETE")

    for action in workflow.get("actions", []):
        if action.get("owner") != "actions" and not SHA40.fullmatch(action.get("ref", "")):
            violations.append("MUTABLE_ACTION")
            break

    if image.get("multiStage") is not True:
        violations.append("SINGLE_STAGE_IMAGE")
    if image.get("runsAsRoot") is not False:
        violations.append("ROOT_RUNTIME")
    if image.get("secretMode") not in ("none", "buildkit"):
        violations.append("SECRET_IN_LAYER")
    if image.get("criticalVulnerabilities") != 0:
        violations.append("CRITICAL_CVE")
    if image.get("digestPinned") is not True:
        violations.append("UNPINNED_IMAGE")

    if req.target == "production":
        if req.event != "push" or req.ref != "refs/heads/main":
            violations.append("INVALID_PRODUCTION_REF")
        if workflow.get("environmentApproval") is not True:
            violations.append("APPROVAL_REQUIRED")

    return {"decision": "promote" if not violations else "block", "violations": violations}

@app.post("/release-gate")
def release_gate(req: ReleaseGateRequest):
    return evaluate(req)
