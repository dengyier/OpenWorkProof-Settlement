"""A disposable native OWP v0.1 coding delivery; all operator roles are app-owned.

Only the customer public key and detached signature cross the signing boundary.
Execution uses the native Docker driver and a frozen, meaningful test source.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from dataclasses import asdict

import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from openworkproof import acceptance, evidence, repo_tools
from openworkproof.mcp_server import execute_apply_patch, execute_repo_read, execute_run_tests
from openworkproof.models import (WorkOrder, CapabilityGrant, AgentRequest, RepoReadArguments,
    ApplyPatchArguments, RunTestsArguments, TestResultEvidence, CompositionReport,
    ComposeProofArguments, AcceptanceReceipt, AcceptanceRejectionReceipt, request_arguments_digest)
from openworkproof.policy import AuthorizationLedgerPrefix, CommittedEvidence, ProspectiveExecutionFacts, derive_authorization_context
from openworkproof.signing import key_id, sign_payload
from bridge.owp_wallet_signing import prepare_wallet_payload, attach_wallet_signature
from bridge.proposal_evidence import attest_proposal, verify_proposal

FIXED_TEST_SOURCE = b'''import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fixture_app", Path.cwd() / "src" / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

def test_average_multiple_values():
    assert app.average([2, 4, 6]) == 4

def test_average_single_value():
    assert app.average([7]) == 7

def test_average_negative_and_fractional():
    assert app.average([-3, 2]) == -0.5
'''
SOURCE = b"def average(values):\n    return sum(values)\n"
ROLES = ("Maintainer", "Manager", "Developer", "Verifier", "Sidecar", "Acceptor")
TOOLS = sorted(("owp.activate_root_grant", "owp.delegate_grant", "owp.apply_patch", "owp.repo_read", "owp.run_tests", "owp.compose_proof", "owp.request_acceptance",
    "owp.create_pr_proposal", "owp.request_pr_proposal", "owp.revoke_grant", "owp.rollback_patch", "owp.start_retry"))


def _digest(value):
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _time(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _write(path, raw, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(raw)
    os.chmod(path, mode)


def _predicate(name, tools, arguments):
    body = {"name": name, "version": "0.1", "applies_to_tools": sorted(tools), "arguments": arguments}
    return {"predicate_id": _digest({"domain": "openworkproof/predicate-id/v0.1", **body}), **body}


class _RecordedDockerExecutor(repo_tools.DockerRunTestsExecutor):
    """Keep the real native result envelope before native cleanup removes it."""
    observation = None

    def start_and_wait(self, contract):
        outcome = super().start_and_wait(contract)
        if outcome.result is not None:
            self.observation = {"contract": asdict(contract), "result": asdict(outcome.result)}
        return outcome

    def reconcile(self, contract, journal_state, receipt_state):
        outcome = super().reconcile(contract, journal_state, receipt_state)
        if outcome.result is not None:
            self.observation = {"contract": asdict(contract), "result": asdict(outcome.result)}
        return outcome


class DeliverySession:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.ledger_path = self.root / "ledger.sqlite3"
        self.evidence_root = self.root / "evidence"
        self._state_path = self.root / "session.json"
        self._state = json.loads(self._state_path.read_text())
        self.job_id = self._state["job_id"]
        self.customer_public_key = bytes.fromhex(self._state["customer_public_key"])
        self.chain_terms = self._state["chain_terms"]
        self._keys = {}
        for role in ROLES[:-1]:
            path = self.root / "keys" / (role.lower() + ".key")
            if path.stat().st_mode & 0o077:
                raise ValueError("operator key permissions must be 0600")
            self._keys[role] = Ed25519PrivateKey.from_private_bytes(path.read_bytes())
        with evidence.connect_ledger(self.ledger_path) as connection:
            self.work_order = evidence.load_authoritative_work_order(connection)
        if self.work_order.acceptor_key_ids != (key_id(Ed25519PublicKey.from_public_bytes(self.customer_public_key)),):
            raise ValueError("customer public key does not match native WorkOrder")
        for role, private in self._keys.items():
            binding = self.work_order.key_bindings[ROLES.index(role)]
            if key_id(private.public_key()) != binding.key_id:
                raise ValueError("operator key does not match native WorkOrder role")
        self._check_terms()
        self._recover_native_terminal()

    @classmethod
    def load(cls, root):
        return cls(root)

    @classmethod
    def create(cls, root: Path, customer_public_key: bytes, chain_terms: dict):
        if type(customer_public_key) is not bytes or len(customer_public_key) != 32:
            raise ValueError("customer public key must be 32 raw bytes")
        root = Path(root).resolve()
        if root.exists():
            raise ValueError("session root already exists")
        image = os.environ.get("OWP_VERIFIER_IMAGE", "")
        if "@sha256:" not in image:
            raise RuntimeError("OWP_VERIFIER_IMAGE must identify the real frozen-test Docker image")
        image_digest = image.rsplit("@", 1)[-1]
        if "." not in image.split("/")[0] and ":" not in image.split("/")[0] and image.split("/")[0] != "localhost":
            image = "docker.io/" + image
        helper = os.environ.get("OWP_HELPER_IMAGE", "")
        if "@sha256:" not in helper:
            raise RuntimeError("OWP_HELPER_IMAGE must identify a real immutable helper image")
        helper_digest = helper.rsplit("@", 1)[-1]
        inspected = subprocess.run([shutil.which("docker") or "docker", "image", "inspect", image], capture_output=True, check=True)
        observed = json.loads(inspected.stdout)[0]
        if image_digest != observed["Id"] and image not in observed.get("RepoDigests", []):
            raise ValueError("Docker image digest does not match inspected image")
        helper_observed = json.loads(subprocess.run([shutil.which("docker"), "image", "inspect", helper], capture_output=True, check=True).stdout)[0]
        if helper_digest != helper_observed["Id"] and helper not in helper_observed.get("RepoDigests", []):
            raise ValueError("helper image digest does not match inspected image")
        frozen = subprocess.run([shutil.which("docker"), "run", "--rm", "--pull", "never", "--network", "none", "--read-only", "--entrypoint", "/bin/cat", image, "/fixed-tests/verifier_test.py"], capture_output=True, check=True, timeout=15)
        if frozen.stdout != FIXED_TEST_SOURCE:
            raise ValueError("immutable verifier image does not contain exact frozen tests")
        now = _now()
        issued = now - timedelta(seconds=2)
        deadline = now + timedelta(hours=2)
        root.mkdir(parents=True, mode=0o700)
        _write(root / ".gitignore", b"*\n")
        keys = {role: Ed25519PrivateKey.generate() for role in ROLES[:-1]}
        bindings = []
        for role in ROLES:
            pub = customer_public_key if role == "Acceptor" else keys[role].public_key().public_bytes_raw()
            bindings.append({"role": role, "subject_id": role.lower(), "key_id": key_id(Ed25519PublicKey.from_public_bytes(pub)),
                "public_key_b64url": base64.urlsafe_b64encode(pub).decode().rstrip("=")})
            if role != "Acceptor":
                _write(root / "keys" / (role.lower() + ".key"), keys[role].private_bytes_raw())
        source_files = (repo_tools.SourceFile("src/app.py", "100644", SOURCE),)
        tree = repo_tools.git_tree_oid(source_files)
        commit = f"tree {tree}\nauthor Fixture <fixture@openworkproof.invalid> 0 +0000\ncommitter Fixture <fixture@openworkproof.invalid> 0 +0000\n\nDisposable average fixture\n".encode()
        archive = repo_tools.write_source_archive(source_files, commit)
        _write(root / "source" / "base.owpsrc", archive)
        _write(root / "fixed-tests" / "verifier_test.py", FIXED_TEST_SOURCE, 0o444)
        command = repo_tools.FROZEN_VERIFIER_COMMAND
        fixed = {"path": "fixed-tests/verifier_test.py", "media_type": "text/x-python", "sha256": hashlib.sha256(FIXED_TEST_SOURCE).hexdigest(), "size_bytes": len(FIXED_TEST_SOURCE)}
        profile = {"test_mode": "verifier", "command": command, "command_digest": repo_tools.frozen_verifier_command_digest(),
            "expected_exit_code": 0, "container_image_digest": image_digest, "fixed_test_source": fixed, "fixed_test_source_digest": fixed["sha256"]}
        replay = {"schema_version": "openworkproof-replay-profile/0.1", "patch_profile_id": "openworkproof/canonical-text-patch/0.1", "object_format": "sha1",
            "source_artifact_sha256": hashlib.sha256(archive).hexdigest(), "trusted_helper_image_digest": helper_digest,
            "author_name": "OpenWorkProof Sidecar", "author_email": "sidecar@openworkproof.invalid", "commit_message_prefix": "OpenWorkProof patch ",
            "timestamp_rule": "receipt-occurred-at-utc-seconds", "worktree_profile": "linux-posix-case-sensitive-v0.1"}
        artifacts = []
        for purpose, count, media, dimension, suffix in (("patch_input", 1, "text/x-diff", "scope", "diff"), ("patch_result", 1, "application/json", "execution", "json"),
            ("patch_denial_audit", 2, "text/x-diff", "none", "diff"), ("verifier_result", 1, "application/json", "result", "json")):
            for ordinal in range(1, count + 1):
                stem = purpose.replace("_", "-")
                artifacts.append({"name": f"{stem}-{ordinal}", "path": f"{stem}/{ordinal:02d}.{suffix}", "media_type": media,
                    "max_size_bytes": 65536, "evidence_dimension": dimension, "purpose": purpose, "ordinal": ordinal})
        gate = {"tool_name": "owp.create_pr_proposal", "required_role": "Maintainer", "max_validity_seconds": 3600, "scope_schema": "openworkproof/pr-proposal-scope/0.1"}
        template = {"grant_id": secrets.token_hex(32), "parent_grant_id": None, "issuer_key_id": bindings[0]["key_id"], "subject_agent_id": "manager", "subject_key_id": bindings[1]["key_id"],
            "allowed_tools": TOOLS, "allowed_read_roots": ["src"], "allowed_write_roots": ["src"], "usage_mode": "metered", "quota": {"tool_calls": 20, "repair_rounds": 0},
            "valid_from": _time(issued), "expires_at": _time(deadline), "may_delegate": True, "issued_at": _time(issued)}
        job_id = secrets.token_hex(32)
        terms = json.loads(rfc8785.dumps(chain_terms))
        terms_digest = _digest(terms)
        wo_raw = {"work_order_id": job_id, "protocol_version": "0.1", "issuer_id": "maintainer", "acceptor_key_ids": [bindings[-1]["key_id"]],
            "objective": f"Disposable fixture: fix average. Chain terms SHA-256 {terms_digest}", "preconditions": [], "invariants": [], "repository": "fixture/average", "branch": "main",
            "allowed_read_roots": ["src"], "allowed_write_roots": ["src"], "source_commit": repo_tools.git_commit_oid(commit),
            "source_artifact": {"path": "source/base.owpsrc", "media_type": "application/vnd.openworkproof.source+zip", "sha256": replay["source_artifact_sha256"], "size_bytes": len(archive)},
            "patch_profile_id": replay["patch_profile_id"], "replay_profile": replay, "replay_profile_digest": _digest({"domain": "openworkproof/replay-profile/v0.1", "profile": replay}),
            "test_profiles": [profile], "allowed_tools": TOOLS, "quota_ceiling": {"tool_calls": 30, "repair_rounds": 0}, "deadline": _time(deadline), "retention_until": _time(deadline + timedelta(hours=2)),
            "acceptance_criteria": "Frozen average tests pass; customer explicitly signs the native receipt.",
            "postconditions": [_predicate("tests_passed", ["owp.run_tests"], {"test_mode": "verifier", "command_digest": profile["command_digest"], "expected_exit_code": 0, "fixed_test_source_digest": fixed["sha256"]})],
            "approval_gates": [{"gate_id": _digest({"domain": "openworkproof/approval-gate-id/v0.1", **gate}), **gate}],
            "required_evidence_dimensions": ["authority", "scope", "execution", "result"], "independence_policy": "disclose_only",
            "evidence_policy": {"evidence_root": "evidence", "redaction_policy_id": "owp-public-evidence-v0.1", "artifacts": artifacts}, "root_grant_template": template, "key_bindings": bindings, "issued_at": _time(issued)}
        wo = WorkOrder.model_validate(sign_payload("work-order", wo_raw, keys["Maintainer"]))
        evidence.initialize_ledger(root / "ledger.sqlite3", wo)
        parsed = repo_tools.parse_source_archive(archive, wo, trusted_helper_image_digest=helper_digest)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        # Native v0.1 repo-read executor binds its runtime candidate to this ID.
        repo_tools.initialize_candidate_workspace(repo_tools.WorkspaceInitRequest(runtime, "c" * 64, parsed))
        (root / "evidence").mkdir(mode=0o700)
        state = {"job_id": job_id, "customer_public_key": customer_public_key.hex(), "chain_terms": terms, "chain_terms_digest": terms_digest, "image_reference": image,
            "patch": None, "tests": {}, "report": None, "terminal": None, "draft": None, "bundle_digest": None}
        _write(root / "session.json", rfc8785.dumps(state))
        session = cls(root)
        grant = CapabilityGrant.model_validate(sign_payload("capability-grant", {**template, "work_order_digest": wo.digest}, keys["Maintainer"]))
        args = {"operation": "activate_root", "authorizing_grant_id": grant.grant_id, "candidate_grant_digest": grant.digest}
        request = session._request("Manager", grant.grant_id, "owp.activate_root_grant", args, now)
        evidence.activate_root_grant(session.ledger_path, grant, request, sidecar_private_key=keys["Sidecar"], clock=lambda: now)
        for role, tools in (("Developer", ["owp.apply_patch", "owp.repo_read"]),):
            raw = {**template, "grant_id": secrets.token_hex(32), "work_order_digest": wo.digest, "parent_grant_id": grant.grant_id,
                "issuer_key_id": bindings[1]["key_id"], "subject_agent_id": role.lower(), "subject_key_id": bindings[ROLES.index(role)]["key_id"],
                "allowed_tools": tools, "allowed_write_roots": [] if role == "Verifier" else ["src"], "quota": {"tool_calls": 3, "repair_rounds": 0}, "may_delegate": False}
            child = CapabilityGrant.model_validate(sign_payload("capability-grant", raw, keys["Manager"]))
            args = {"operation": "delegate_child", "authorizing_grant_id": grant.grant_id, "candidate_grant_digest": child.digest}
            issuance = evidence.issue_child_grant(session.ledger_path, child, session._request("Manager", grant.grant_id, "owp.delegate_grant", args, now), sidecar_private_key=keys["Sidecar"], clock=lambda: now)
            if issuance.policy_decision != "allow":
                raise ValueError("native developer grant was denied")
        session._state["tests"]["baseline"] = session._run_clean_docker(SOURCE)
        session._save()
        return session

    def _save(self):
        descriptor, temporary = tempfile.mkstemp(prefix=".session-", dir=self.root)
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(rfc8785.dumps(self._state))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self._state_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _recover_native_terminal(self):
        with evidence.connect_ledger(self.ledger_path) as connection:
            terminals = evidence._validated_acceptance_receipts(connection, self.work_order) + evidence._validated_acceptance_rejections(connection, self.work_order)
        if len(terminals) > 1:
            raise ValueError("native terminal decision is ambiguous")
        authoritative = terminals[0].model_dump(mode="json") if terminals else None
        cached = self._state["terminal"]
        if cached is not None and cached != authoritative:
            raise ValueError("terminal cache does not match native ledger")
        if authoritative is None:
            return
        self._state["terminal"] = authoritative
        self._verify_bundle()
        decision_path = self.root / "customer-decision.json"
        decision_bytes = rfc8785.dumps(authoritative)
        if decision_path.exists():
            if decision_path.read_bytes() != decision_bytes:
                raise ValueError("customer terminal artifact does not match native ledger")
        else:
            _write(decision_path, decision_bytes, 0o444)
        if cached is None or self._state["draft"] is not None:
            self._state["draft"] = None
            self._save()

    def _check_terms(self):
        if self.job_id != self.work_order.work_order_id or self._state["job_id"] != self.work_order.work_order_id:
            raise ValueError("session job ID does not match native WorkOrder")
        if _digest(self.chain_terms) != self._state["chain_terms_digest"] or self._state["chain_terms_digest"] not in self.work_order.objective:
            raise ValueError("chain terms changed")

    def _request(self, role, grant_id, tool, args, now):
        return AgentRequest.model_validate(sign_payload("agent-request", {"claim_type": "agent-request", "work_order_digest": self.work_order.digest,
            "grant_id": grant_id, "actor_id": role.lower(), "actor_key_id": key_id(self._keys[role].public_key()), "tool_name": tool,
            "arguments_digest": request_arguments_digest(tool, args), "nonce": secrets.token_hex(32), "requested_at": _time(now), "authentication_method": "agent_signature",
            "model_id": "fixture-operator", "model_version": "1", "prompt_template_digest": _digest("fixture"), "context_source_digest": self.work_order.source_artifact.sha256}, self._keys[role]))

    def _snapshot(self):
        with evidence.connect_ledger(self.ledger_path) as connection:
            wo = evidence.load_authoritative_work_order(connection)
            if wo != self.work_order:
                raise ValueError("native WorkOrder changed")
            receipts = evidence._validated_receipt_prefix(connection, wo)
            grants = evidence._validated_effective_grants(connection, wo, receipts)
            attempts = evidence._validated_grant_attempts(connection, wo, receipts)
        committed = {}
        for receipt in receipts:
            for ref in receipt.evidence_refs:
                raw = (self.evidence_root / ref.path.removeprefix("evidence/")).read_bytes()
                committed[ref.path] = CommittedEvidence(reference=ref, payload=raw)
        prefix = AuthorizationLedgerPrefix(tuple(sorted(grants.values(), key=lambda x: x.grant_id)), tuple(sorted(attempts.values(), key=lambda x: x.digest)), receipts)
        return prefix, tuple(committed[k] for k in sorted(committed))

    def _candidate(self):
        return repo_tools.load_candidate_workspace(self.root / "runtime", "c" * 64)

    def _context(self, now):
        prefix, committed = self._snapshot()
        candidate = self._candidate()
        descriptor = os.open(candidate.worktree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            manifest = repo_tools.scan_workspace_manifest(descriptor, candidate.head_commit)
        finally:
            os.close(descriptor)
        results = tuple(TestResultEvidence.model_validate_json(item.payload) for item in committed if item.reference.path.startswith("evidence/verifier-result/"))
        checkpoint = repo_tools.ReplayCheckpoint((), candidate.head_commit, manifest, repo_tools.workspace_manifest_digest(manifest), results)
        return derive_authorization_context(self.work_order, prefix, committed, checkpoint, now)

    def _grant(self, context, role):
        return next(g for g in context.ledger_prefix.effective_grants if g.subject_key_id == key_id(self._keys[role].public_key()))

    def _run_clean_docker(self, source):
        # A clean Docker rerun with real output, separate from native transaction.
        with tempfile.TemporaryDirectory(prefix="owp-fixture-check-") as directory:
            root = Path(directory)
            _write(root / "src" / "app.py", source)
            os.chmod(root, 0o755)
            os.chmod(root / "src", 0o755)
            os.chmod(root / "src" / "app.py", 0o444)
            argv = [shutil.which("docker"), "run", "--rm", "--pull", "never", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--user", "65532:65532", "--memory", "256m", "--pids-limit", "64", "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m,mode=1777", "--mount", f"type=bind,source={root},target=/workspace,readonly", "--workdir", "/workspace",
                "--entrypoint", "/opt/venv/bin/python", self._state["image_reference"], *repo_tools.FROZEN_VERIFIER_ARGV[1:]]
            result = subprocess.run(argv, capture_output=True, timeout=30)
            return {"exit_code": result.returncode, "stdout": result.stdout.decode(errors="replace"), "stderr": result.stderr.decode(errors="replace"), "argv": argv,
                "environment": "clean Docker rerun; not an independent operator", "image_reference": self._state["image_reference"]}

    def execute(self, patch: str, proposal=None):
        self._check_terms()
        if self._state["patch"] is not None:
            raise ValueError("fixture session executes one patch only")
        raw = patch.encode()
        canonical = repo_tools.parse_patch_phase_a(raw, expected_patch_digest=hashlib.sha256(raw).hexdigest(), expected_patch_size_bytes=len(raw), declared_target_paths=("src/app.py",))
        record = attest_proposal(proposal, patch, self.work_order.digest, self._keys["Developer"]) if proposal is not None else None
        now = _now()
        context = self._context(now)
        facts = ProspectiveExecutionFacts(secrets.token_hex(32), _digest({"root": str(self.root), "operator": "app"}), key_id(self._keys["Sidecar"].public_key()))
        grant = self._grant(context, "Developer")
        args = RepoReadArguments(path="src/app.py")
        execute_repo_read(self.ledger_path, evidence_root=self.evidence_root, context=context, request=self._request("Developer", grant.grant_id, "owp.repo_read", args, now), request_arguments=args,
            execution_facts=facts, sidecar_private_key=self._keys["Sidecar"], candidate_runtime_root=self.root / "runtime", handler=repo_tools.read_candidate_file, clock=lambda: now)
        context = self._context(now)
        args = ApplyPatchArguments(target_paths=canonical.derived_patch_paths, patch_digest=canonical.patch_digest, patch_size_bytes=len(raw))
        receipt = execute_apply_patch(self.ledger_path, evidence_root=self.evidence_root, context=context, request=self._request("Developer", grant.grant_id, "owp.apply_patch", args, now),
            request_arguments=args, execution_facts=facts, sidecar_private_key=self._keys["Sidecar"], patch_bytes=raw, candidate_workspace=self._candidate(), handler=repo_tools.apply_patch_in_candidate_workspace, clock=lambda: now)
        self._state["patch"] = {"text": patch, "digest": canonical.patch_digest, "receipt_id": receipt.receipt_id, "receipt_digest": receipt.digest}
        if record is not None:
            self._state["proposal"] = record
        self._save()
        return self.verify()

    def verify(self):
        self._check_terms()
        if not self._state["patch"] or "verifier" in self._state["tests"] or self._state["report"] or self._state["terminal"]:
            raise ValueError("an unverified applied patch is required")
        now = _now()
        context = self._context(now)
        self._verify_display_data(context)
        patch_receipt = next(r for r in context.ledger_prefix.receipts if r.receipt_id == self._state["patch"]["receipt_id"])
        if patch_receipt.execution_status != "succeeded":
            raise ValueError("an unverified applied patch is required")
        if any(g.subject_key_id == key_id(self._keys["Verifier"].public_key()) for g in context.ledger_prefix.effective_grants):
            raise ValueError("verifier execution already started; inspect before retry")
        candidate = self._candidate()
        manager = self._grant(context, "Manager")
        verifier_raw = manager.model_dump(mode="json")
        verifier_raw.update({"grant_id": secrets.token_hex(32), "parent_grant_id": manager.grant_id,
            "issuer_key_id": key_id(self._keys["Manager"].public_key()), "subject_agent_id": "verifier",
            "subject_key_id": key_id(self._keys["Verifier"].public_key()), "allowed_tools": ["owp.run_tests"],
            "allowed_write_roots": [], "quota": {"tool_calls": 1, "repair_rounds": 0}, "may_delegate": False,
            "issued_at": _time(now), "valid_from": _time(now)})
        verifier_grant = CapabilityGrant.model_validate(sign_payload("capability-grant", verifier_raw, self._keys["Manager"]))
        delegation = {"operation": "delegate_child", "authorizing_grant_id": manager.grant_id, "candidate_grant_digest": verifier_grant.digest}
        issued = evidence.issue_child_grant(self.ledger_path, verifier_grant, self._request("Manager", manager.grant_id, "owp.delegate_grant", delegation, now), sidecar_private_key=self._keys["Sidecar"], clock=lambda: now)
        if issued.policy_decision != "allow":
            raise ValueError("native verifier grant was denied")
        context = self._context(now)
        profile = self.work_order.test_profiles[0]
        args = RunTestsArguments(test_mode="verifier", source_commit=self.work_order.source_commit, candidate_commit=candidate.head_commit, workspace_manifest_digest=candidate.workspace_manifest_digest,
            container_image_digest=profile.container_image_digest, command_digest=profile.command_digest, fixed_test_source_digest=profile.fixed_test_source_digest)
        driver = _RecordedDockerExecutor(docker_binary=Path(shutil.which("docker")), candidate_runtime_root=self.root / "runtime", image_reference=self._state["image_reference"])
        verifier = self._grant(context, "Verifier")
        test_receipt = execute_run_tests(self.ledger_path, evidence_root=self.evidence_root, context=context, request=self._request("Verifier", verifier.grant_id, "owp.run_tests", args, now), request_arguments=args,
            execution_facts=ProspectiveExecutionFacts(secrets.token_hex(32), secrets.token_hex(32), key_id(self._keys["Sidecar"].public_key())),
            candidate_snapshot_request=repo_tools.CandidateExecutionSnapshotRequest(candidate.runtime_root, candidate.workspace_id, candidate.source_artifact_sha256, candidate.head_commit, candidate.workspace_manifest_digest),
            sidecar_private_key=self._keys["Sidecar"], execution_driver=driver, clock=lambda: now)
        clean = self._run_clean_docker((candidate.worktree / "src" / "app.py").read_bytes())
        native_result = None
        if test_receipt.evidence_refs:
            reference = test_receipt.evidence_refs[0]
            native_result = TestResultEvidence.model_validate_json((self.evidence_root / reference.path.removeprefix("evidence/")).read_bytes()).model_dump(mode="json")
        self._state["tests"]["verifier"] = {"receipt_id": test_receipt.receipt_id, "receipt_digest": test_receipt.digest, "native_execution_status": test_receipt.execution_status,
            "native_postconditions_satisfied": test_receipt.state_after == "locally_verified", "native_image": profile.container_image_digest,
            "exit_code": native_result["actual_exit_code"] if native_result else None, "native_result": native_result,
            "native_execution_observation": driver.observation,
            "stdout": None, "stdout_note": "Native driver preserves stdio hashes in result envelope, not stdout text; clean_rerun has separate actual output."}
        self._state["tests"]["clean_rerun"] = clean
        if driver.observation:
            _write(self.root / "native-test-execution.json", rfc8785.dumps(driver.observation), 0o444)
        self._save()
        if test_receipt.state_after == "locally_verified" and clean["exit_code"] == 0:
            context = self._context(now)
            manager = self._grant(context, "Manager")
            args = ComposeProofArguments(expected_state_version=evidence._derive_protocol_transaction_version(action_receipts=context.ledger_prefix.receipts, acceptance_receipts=()), previous_report_digest=None)
            composed = acceptance.compose_proof_transaction(self.ledger_path, evidence_root=self.evidence_root, context=context, request=self._request("Manager", manager.grant_id, "owp.compose_proof", args, now), sidecar_private_key=self._keys["Sidecar"], clock=lambda: now)
            self._state["report"] = composed.report.model_dump(mode="json")
            self._freeze_bundle()
            self._save()
            self._verify_bundle()
        return self.summary()

    def _verify_bundle(self):
        self._verify_frozen_bundle()
        prefix, committed = self._snapshot()
        report = CompositionReport.model_validate(self._state["report"])
        public_keys = self._public_keys()
        kwargs = dict(work_order=self.work_order, report=report, effective_grants=prefix.effective_grants, grant_attempts=prefix.grant_attempts, receipts=prefix.receipts, committed_evidence=committed, public_keys=public_keys)
        terminal = self._state["terminal"]
        if terminal:
            kind = "acceptance_receipt" if terminal["decision"] == "accepted" else "rejection"
            model = AcceptanceReceipt if kind == "acceptance_receipt" else AcceptanceRejectionReceipt
            with evidence.connect_ledger(self.ledger_path) as connection:
                native_terminals = evidence._validated_acceptance_receipts(connection, self.work_order) if kind == "acceptance_receipt" else evidence._validated_acceptance_rejections(connection, self.work_order)
            if len(native_terminals) != 1 or native_terminals[0].model_dump(mode="json") != terminal:
                raise ValueError("terminal metadata does not match current native ledger")
            return acceptance.verify_acceptance_bundle(**kwargs, **{kind: model.model_validate(terminal)})
        kwargs.pop("report")
        return acceptance.verify_composition_bundle(**kwargs, reports=(report,))

    def _freeze_bundle(self):
        prefix, committed = self._snapshot()
        review = self._review_snapshot()
        payload = {"schema_version": "owp-native-composition-snapshot/0.1", "work_order": self.work_order.model_dump(mode="json"), "report": self._state["report"],
            "source_base64": base64.b64encode((self.root / "source" / "base.owpsrc").read_bytes()).decode(), "fixed_tests_base64": base64.b64encode(FIXED_TEST_SOURCE).decode(),
            "review_snapshot": review,
            "review_snapshot_digest": _digest(review),
            "receipts": [r.model_dump(mode="json") for r in prefix.receipts], "effective_grants": [g.model_dump(mode="json") for g in prefix.effective_grants],
            "grant_attempts": [g.model_dump(mode="json") for g in prefix.grant_attempts], "evidence": [{"reference": e.reference.model_dump(mode="json"), "payload_base64": base64.b64encode(e.payload).decode()} for e in committed]}
        raw = rfc8785.dumps(payload)
        _write(self.root / "delivery-bundle.json", raw, 0o444)
        self._state["bundle_digest"] = hashlib.sha256(raw).hexdigest()

    def _verify_frozen_bundle(self):
        if not self._state["bundle_digest"]:
            raise ValueError("delivery bundle is not composed")
        raw = (self.root / "delivery-bundle.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != self._state["bundle_digest"]:
            raise ValueError("frozen delivery bundle changed")
        payload = json.loads(raw)
        if payload["work_order"] != self.work_order.model_dump(mode="json") or payload["report"] != self._state["report"]:
            raise ValueError("frozen delivery authority or report changed")
        review = self._review_snapshot()
        if payload["review_snapshot"] != review or payload["review_snapshot_digest"] != _digest(review):
            raise ValueError("review patch or test metadata changed")
        source = base64.b64decode(payload["source_base64"])
        if source != (self.root / "source" / "base.owpsrc").read_bytes():
            raise ValueError("source artifact changed")
        repo_tools.parse_source_archive(source, self.work_order, trusted_helper_image_digest=self.work_order.replay_profile.trusted_helper_image_digest)
        if base64.b64decode(payload["fixed_tests_base64"]) != FIXED_TEST_SOURCE or (self.root / "fixed-tests" / "verifier_test.py").read_bytes() != FIXED_TEST_SOURCE:
            raise ValueError("frozen tests changed")
        from openworkproof.models import EvidenceRef
        committed = tuple(CommittedEvidence(reference=EvidenceRef.model_validate(item["reference"]), payload=base64.b64decode(item["payload_base64"])) for item in payload["evidence"])
        acceptance.verify_composition_bundle(work_order=self.work_order,
            effective_grants=tuple(CapabilityGrant.model_validate(g) for g in payload["effective_grants"]), grant_attempts=tuple(CapabilityGrant.model_validate(g) for g in payload["grant_attempts"]),
            receipts=tuple(evidence.ACTION_RECEIPT_ADAPTER.validate_python(r) for r in payload["receipts"]), committed_evidence=committed,
            reports=(CompositionReport.model_validate(payload["report"]),), public_keys=self._public_keys())

    def _public_keys(self):
        return {b.key_id: Ed25519PublicKey.from_public_bytes(base64.urlsafe_b64decode(b.public_key_b64url + "=" * (-len(b.public_key_b64url) % 4))) for b in self.work_order.key_bindings}

    def _review_snapshot(self):
        review = {"patch": self._state["patch"], "tests": self._state["tests"]}
        if "proposal" in self._state:
            verify_proposal(self._state["proposal"], self._state["patch"]["text"], self.work_order.digest, self._keys["Developer"].public_key())
            review["proposal"] = self._state["proposal"]
        return review

    def _verify_display_data(self, context):
        patch = self._state["patch"]
        if patch is None:
            return
        self._review_snapshot()
        matches = tuple(r for r in context.ledger_prefix.receipts if r.receipt_id == patch["receipt_id"] and getattr(r, "tool_name", None) == "owp.apply_patch")
        if len(matches) != 1 or matches[0].digest != patch["receipt_digest"]:
            raise ValueError("displayed patch receipt does not match native ledger")
        receipt = matches[0]
        patch_ref = next(ref for ref in receipt.evidence_refs if ref.path.startswith("evidence/patch-input/"))
        patch_bytes = (self.evidence_root / patch_ref.path.removeprefix("evidence/")).read_bytes()
        if patch["text"].encode() != patch_bytes or patch["digest"] != patch_ref.sha256 or receipt.request_arguments.patch_digest != patch["digest"]:
            raise ValueError("displayed patch does not match native evidence")
        displayed = self._state["tests"].get("verifier")
        if displayed is None:
            return
        matches = tuple(r for r in context.ledger_prefix.receipts if r.receipt_id == displayed["receipt_id"] and getattr(r, "tool_name", None) == "owp.run_tests")
        if len(matches) != 1 or matches[0].digest != displayed["receipt_digest"]:
            raise ValueError("displayed verifier receipt does not match native ledger")
        receipt = matches[0]
        actual = None
        if receipt.evidence_refs:
            ref = receipt.evidence_refs[0]
            actual = TestResultEvidence.model_validate_json((self.evidence_root / ref.path.removeprefix("evidence/")).read_bytes()).model_dump(mode="json")
        expected = {"native_result": actual, "exit_code": actual["actual_exit_code"] if actual else None,
            "native_execution_status": receipt.execution_status, "native_postconditions_satisfied": receipt.state_after == "locally_verified", "native_image": self.work_order.test_profiles[0].container_image_digest}
        if any(displayed.get(key) != value for key, value in expected.items()):
            raise ValueError("displayed test verdict does not match native evidence")
        observation = displayed.get("native_execution_observation")
        if observation is not None:
            contract = repo_tools.RunTestsExecutionContract(**observation["contract"])
            result = observation["result"]
            if (contract.request_digest != receipt.nested_claim_digest
                or contract.arguments_digest != receipt.arguments_digest
                or result["execution_contract_digest"] != hashlib.sha256(repo_tools.encode_run_tests_execution_contract(contract)).hexdigest()
                or result["actual_exit_code"] != expected["exit_code"]):
                raise ValueError("native execution observation does not match signed test evidence")

    def prepare_decision(self, decision="ACCEPTED"):
        if decision not in ("ACCEPTED", "REJECTED"):
            raise ValueError("decision must be ACCEPTED or REJECTED")
        self._check_terms()
        if self._state["terminal"] or not self._state["report"]:
            raise ValueError("current native proof is not ready for customer decision")
        self._verify_bundle()
        now = _now()
        context = self._context(now)
        if context.current_state == "proof_ready":
            manager = self._grant(context, "Manager")
            scope = {"work_order_digest": self.work_order.digest, "operation": "submit_final_acceptance", "composition_report_digest": acceptance.composition_report_digest(CompositionReport.model_validate(self._state["report"]))}
            expires_at = min(self.work_order.deadline, now + timedelta(hours=1))
            args = {"request_kind": "final_acceptance", "target_action_digest": _digest({"domain": "openworkproof/final-acceptance-action/v0.1", "requested_scope": scope}),
                "required_role": "Acceptor", "requested_scope": scope, "expires_at": _time(expires_at)}
            acceptance.request_acceptance_transaction(self.ledger_path, evidence_root=self.evidence_root, context=context, request=self._request("Manager", manager.grant_id, "owp.request_acceptance", args, now),
                sidecar_private_key=self._keys["Sidecar"], expires_at=expires_at, clock=lambda: now)
            context = self._context(now)
        native = acceptance.prepare_acceptance(self.ledger_path, evidence_root=self.evidence_root, context=context, clock=lambda: now)
        payload = dict(native.payload)
        domain = native.signing_domain
        if decision == "REJECTED":
            with evidence.connect_ledger(self.ledger_path) as connection:
                request = acceptance._current_acceptance_request(self.ledger_path, self.work_order)
            report = CompositionReport.model_validate(self._state["report"])
            rejection_id = acceptance.rejection_id(work_order_digest=self.work_order.digest, request_receipt_id=request.receipt_id, request_receipt_digest=request.digest,
                report_digest=payload["composition_report_digest"], evidence_snapshot=payload["evidence_snapshot_digest"])
            payload = acceptance._expected_rejection_payload(self.work_order, report, request, payload["evidence_snapshot_digest"], rejection_id, now, context.ledger_prefix.receipts, "BUSINESS_DECISION", "Customer rejected this fixture delivery.")
            domain = "acceptance-rejection-receipt"
        envelope, message = prepare_wallet_payload(domain, payload, self.customer_public_key)
        draft = {"draft_id": secrets.token_hex(32), "decision": decision, "envelope": envelope, "message_base64": base64.b64encode(message).decode(), "prepared_at": _time(now),
            "ledger_tip": context.ledger_prefix.receipts[-1].digest, "chain_terms_digest": self._state["chain_terms_digest"],
            "request_expires_at": _time(acceptance._current_acceptance_request(self.ledger_path, self.work_order).expires_at)}
        self._state["draft"] = draft
        self._save()
        return json.loads(rfc8785.dumps(draft))

    def commit_decision(self, draft_id, signature: bytes):
        self._check_terms()
        draft = self._state["draft"]
        if not draft or draft_id != draft["draft_id"] or self._state["terminal"]:
            raise ValueError("decision draft is stale or already consumed")
        self._verify_bundle()
        now = _now()
        context = self._context(now)
        if context.ledger_prefix.receipts[-1].digest != draft["ledger_tip"] or draft["chain_terms_digest"] != self._state["chain_terms_digest"]:
            raise ValueError("decision draft no longer matches current evidence")
        signed = attach_wallet_signature(draft["envelope"], self.customer_public_key, signature)
        if draft["decision"] == "ACCEPTED":
            terminal = acceptance.commit_acceptance(self.ledger_path, evidence_root=self.evidence_root, context=context, acceptance=AcceptanceReceipt.model_validate(signed), public_keys=None, clock=lambda: now)
        else:
            terminal = acceptance.reject_acceptance_transaction(self.ledger_path, evidence_root=self.evidence_root, context=context, rejection=AcceptanceRejectionReceipt.model_validate(signed), public_keys=None, clock=lambda: now)
        self._state["terminal"] = terminal.model_dump(mode="json")
        self._state["draft"] = None
        _write(self.root / "customer-decision.json", rfc8785.dumps(terminal.model_dump(mode="json")), 0o444)
        self._save()
        self._verify_bundle()
        return self.summary()

    def release_authorization(self):
        self._check_terms()
        terminal = self._state["terminal"]
        if not terminal or terminal["decision"] != "accepted":
            raise ValueError("native customer acceptance is required")
        self._verify_bundle()
        if self._native_status() != "accepted":
            raise ValueError("native current state is not accepted")
        summary = self.summary()
        return {k: summary[k] for k in ("job_id", "work_order_digest", "bundle_digest", "acceptance_digest", "chain_terms_digest")}

    def _native_status(self):
        with evidence.connect_ledger(self.ledger_path) as connection:
            row = connection.execute("SELECT current_state FROM work_order_state WHERE singleton = 1 AND work_order_digest = ?", (self.work_order.digest,)).fetchone()
        if row is None:
            raise ValueError("native current state missing")
        return row[0]

    def summary(self):
        self._check_terms()
        context = self._context(_now())
        self._verify_display_data(context)
        if self._state["report"] is not None:
            self._verify_bundle()
        terminal = self._state["terminal"]
        report = self._state["report"]
        bundle_digest = self._state["bundle_digest"]
        request_expiry = next((_time(r.expires_at) for r in reversed(context.ledger_prefix.receipts) if getattr(r, "request_kind", None) == "final_acceptance"), None)
        return {"job_id": self.job_id, "work_order_digest": self.work_order.digest, "bundle_digest": bundle_digest,
            "acceptance_digest": terminal["digest"] if terminal else None, "status": self._native_status(), "native_status": self._native_status(),
            "verification_decision": "VERIFIED" if report and report["verifier_conclusion"] == "proof_ready" else ("REFUTED" if context.current_state == "needs_rework" else None),
            "acceptance_decision": terminal["decision"].upper() if terminal else None, "source_revision": self.work_order.source_commit,
            "patch": self._state["patch"], "tests": self._state["tests"], "chain_terms": self.chain_terms, "chain_terms_digest": self._state["chain_terms_digest"],
            "proposal": self._state.get("proposal"),
            "bundle_path": str(self.root / "delivery-bundle.json") if bundle_digest else None,
            "acceptance_request_expires_at": request_expiry,
            "verification_kind": "Native v0.1 CompositionReport proof_ready; no v0.5 VerificationDecision or AcceptanceBundle claim",
            "trust_boundary": "All noncustomer roles share the app operator; clean test execution is not independent operator verification.",
            "fixture": True, "autonomous_model": False, "protocol_version": "0.1", "acceptance_bundle_v05": False}
