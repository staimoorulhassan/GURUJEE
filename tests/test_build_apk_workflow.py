"""Tests for .github/workflows/build-apk.yml — covers the changes in this PR.

PR change: artifact upload path corrected from `bin/*.apk` to `gurujee/*.apk`
in the "Also upload APK as artifact" step.

The "Upload APK to GitHub Release" step (softprops/action-gh-release) was NOT
changed and still uses `bin/*.apk`; tests assert both paths to guard against
accidental cross-modification.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "build-apk.yml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_workflow() -> dict:
    """Parse and return the workflow YAML as a dict."""
    return yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))


def _get_steps(workflow: dict) -> list[dict]:
    """Return the flat list of steps from the single job."""
    job = next(iter(workflow["jobs"].values()))
    return job.get("steps", [])


def _find_step(steps: list[dict], name_substring: str) -> dict | None:
    """Return the first step whose name contains name_substring (case-insensitive)."""
    for step in steps:
        step_name = step.get("name", "")
        if name_substring.lower() in step_name.lower():
            return step
    return None


# ---------------------------------------------------------------------------
# Tests: YAML validity
# ---------------------------------------------------------------------------

class TestWorkflowYamlValidity:
    """Verify the workflow file is valid YAML and has the expected top-level keys."""

    def test_workflow_file_exists(self):
        assert WORKFLOW_FILE.exists(), f"Workflow file not found: {WORKFLOW_FILE}"

    def test_workflow_parses_as_valid_yaml(self):
        workflow = _load_workflow()
        assert isinstance(workflow, dict), "Workflow YAML must parse to a dict"

    def test_workflow_has_jobs(self):
        workflow = _load_workflow()
        assert "jobs" in workflow, "Workflow must have a 'jobs' key"

    def test_workflow_has_on_trigger(self):
        workflow = _load_workflow()
        # PyYAML (YAML 1.1) parses the bare `on:` key as Python boolean True.
        # Accept either form so the test is robust to YAML loader behaviour.
        assert ("on" in workflow or True in workflow), (
            "Workflow must have an 'on' trigger key"
        )

    def test_workflow_has_name(self):
        workflow = _load_workflow()
        assert "name" in workflow, "Workflow must have a 'name' key"


# ---------------------------------------------------------------------------
# Tests: artifact upload path (the PR change)
# ---------------------------------------------------------------------------

class TestArtifactUploadPath:
    """Verifies the artifact upload path was updated from bin/ to gurujee/."""

    def _artifact_upload_step(self) -> dict:
        steps = _get_steps(_load_workflow())
        step = _find_step(steps, "Also upload APK as artifact")
        assert step is not None, (
            "Could not find step 'Also upload APK as artifact' in workflow"
        )
        return step

    def test_artifact_upload_step_exists(self):
        """The 'Also upload APK as artifact' step must exist."""
        self._artifact_upload_step()  # raises if not found

    def test_artifact_upload_uses_gurujee_path(self):
        """Artifact upload path must point to gurujee/*.apk (not bin/*.apk)."""
        step = self._artifact_upload_step()
        upload_path = step.get("with", {}).get("path", "")
        assert upload_path == "gurujee/*.apk", (
            f"Expected artifact path 'gurujee/*.apk', got '{upload_path}'"
        )

    def test_artifact_upload_does_not_use_bin_path(self):
        """Artifact upload path must NOT be bin/*.apk (the old incorrect path)."""
        step = self._artifact_upload_step()
        upload_path = step.get("with", {}).get("path", "")
        assert "bin/" not in upload_path, (
            f"Artifact upload path still references bin/: '{upload_path}'"
        )

    def test_artifact_upload_name_is_gurujee_apk(self):
        """Artifact must be named 'gurujee-apk'."""
        step = self._artifact_upload_step()
        artifact_name = step.get("with", {}).get("name", "")
        assert artifact_name == "gurujee-apk", (
            f"Expected artifact name 'gurujee-apk', got '{artifact_name}'"
        )

    def test_artifact_upload_uses_upload_artifact_action(self):
        """Step must use actions/upload-artifact@v4."""
        step = self._artifact_upload_step()
        action = step.get("uses", "")
        assert action == "actions/upload-artifact@v4", (
            f"Expected 'actions/upload-artifact@v4', got '{action}'"
        )

    def test_artifact_upload_if_no_files_found_is_warn(self):
        """if-no-files-found must remain 'warn' (not 'error' or 'ignore')."""
        step = self._artifact_upload_step()
        policy = step.get("with", {}).get("if-no-files-found", "")
        assert policy == "warn", (
            f"Expected if-no-files-found='warn', got '{policy}'"
        )

    def test_artifact_upload_path_uses_glob_pattern(self):
        """Path must be a glob pattern ending with *.apk."""
        step = self._artifact_upload_step()
        path = step.get("with", {}).get("path", "")
        assert path.endswith("*.apk"), (
            f"Artifact path must end with *.apk; got '{path}'"
        )


# ---------------------------------------------------------------------------
# Tests: release upload step NOT changed (regression guard)
# ---------------------------------------------------------------------------

class TestReleaseUploadStepUnchanged:
    """Ensures the GitHub Release upload step was not accidentally modified."""

    def _release_step(self) -> dict:
        steps = _get_steps(_load_workflow())
        step = _find_step(steps, "Upload APK to GitHub Release")
        assert step is not None, (
            "Could not find step 'Upload APK to GitHub Release' in workflow"
        )
        return step

    def test_release_step_exists(self):
        """The 'Upload APK to GitHub Release' step must still exist."""
        self._release_step()

    def test_release_step_files_path_unchanged(self):
        """Release step files path must still be bin/*.apk (was not changed in PR)."""
        step = self._release_step()
        files_path = step.get("with", {}).get("files", "")
        assert files_path == "bin/*.apk", (
            f"Release step files path should still be 'bin/*.apk'; got '{files_path}'"
        )

    def test_release_step_uses_softprops_action(self):
        """Release step must use softprops/action-gh-release@v2."""
        step = self._release_step()
        action = step.get("uses", "")
        assert "softprops/action-gh-release" in action, (
            f"Expected softprops/action-gh-release action; got '{action}'"
        )


# ---------------------------------------------------------------------------
# Tests: both upload steps are distinct and independent
# ---------------------------------------------------------------------------

class TestTwoUploadStepsAreDistinct:
    """Ensures the two upload steps have different paths (one bin/, one gurujee/)."""

    def test_two_upload_artifact_steps_use_different_paths(self):
        """The upload-artifact step for APKs must use gurujee/*.apk, not bin/*.apk."""
        steps = _get_steps(_load_workflow())
        apk_upload_paths = [
            step["with"]["path"]
            for step in steps
            if step.get("uses", "").startswith("actions/upload-artifact")
            and str(step.get("with", {}).get("path", "")).endswith(".apk")
        ]
        assert len(apk_upload_paths) == 1, (
            f"Expected exactly 1 upload-artifact step with an *.apk path; found: {apk_upload_paths}"
        )
        assert apk_upload_paths[0] == "gurujee/*.apk", (
            f"APK upload-artifact path must be 'gurujee/*.apk'; got '{apk_upload_paths[0]}'"
        )

    def test_gurujee_path_not_duplicated_in_workflow(self):
        """gurujee/*.apk must appear exactly once in the workflow."""
        text = WORKFLOW_FILE.read_text(encoding="utf-8")
        count = text.count("gurujee/*.apk")
        assert count == 1, (
            f"'gurujee/*.apk' should appear exactly once in the workflow; found {count} times"
        )

    def test_bin_path_in_workflow_only_for_release_step(self):
        """bin/*.apk must appear only in the release step, not in artifact upload."""
        steps = _get_steps(_load_workflow())
        artifact_step = _find_step(steps, "Also upload APK as artifact")
        assert artifact_step is not None
        artifact_path = artifact_step.get("with", {}).get("path", "")
        assert "bin/" not in artifact_path, (
            f"bin/ path leaked into artifact upload step: '{artifact_path}'"
        )


# ---------------------------------------------------------------------------
# Tests: boundary / negative cases
# ---------------------------------------------------------------------------

class TestBoundaryAndNegative:
    """Boundary and negative tests for additional confidence."""

    def test_workflow_file_is_non_empty(self):
        content = WORKFLOW_FILE.read_text(encoding="utf-8").strip()
        assert len(content) > 0, "Workflow file is empty"

    def test_artifact_path_is_string_not_list(self):
        """Artifact path must be a plain string (not a YAML list)."""
        steps = _get_steps(_load_workflow())
        step = _find_step(steps, "Also upload APK as artifact")
        assert step is not None
        path_value = step.get("with", {}).get("path")
        assert isinstance(path_value, str), (
            f"Artifact path must be a string; got {type(path_value).__name__}: {path_value!r}"
        )

    def test_artifact_path_does_not_contain_spaces(self):
        """Artifact path must not contain unquoted spaces."""
        steps = _get_steps(_load_workflow())
        step = _find_step(steps, "Also upload APK as artifact")
        assert step is not None
        path = step.get("with", {}).get("path", "")
        assert " " not in path, f"Artifact path contains spaces: '{path}'"

    def test_workflow_yaml_has_no_duplicate_keys(self):
        """Workflow YAML must load without silent duplicate-key shadowing."""
        # PyYAML silently drops duplicate keys; we do a raw text check for the
        # most critical key in the changed section.
        text = WORKFLOW_FILE.read_text(encoding="utf-8")
        # Count occurrences of 'gurujee-apk' (artifact name) — should be exactly 1
        assert text.count("gurujee-apk") == 1, (
            "Artifact name 'gurujee-apk' appears more than once — possible duplicate step"
        )