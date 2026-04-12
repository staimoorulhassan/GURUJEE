"""Tests for .specify/extensions/git/scripts/bash/*.sh scripts.

These tests exercise the new git extension bash scripts added in the PR:
  - git-common.sh   : has_git(), check_feature_branch()
  - create-new-feature.sh : branch name generation, flags, JSON output
  - auto-commit.sh  : config-driven commit behaviour
  - initialize-repo.sh : git init flow, custom commit message
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
BASH_SCRIPTS = REPO_ROOT / ".specify" / "extensions" / "git" / "scripts" / "bash"
GIT_COMMON_SH = BASH_SCRIPTS / "git-common.sh"
CREATE_FEATURE_SH = BASH_SCRIPTS / "create-new-feature.sh"
AUTO_COMMIT_SH = BASH_SCRIPTS / "auto-commit.sh"
INITIALIZE_REPO_SH = BASH_SCRIPTS / "initialize-repo.sh"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a command, capturing stdout+stderr, with merged env."""
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=merged_env,
    )


def _bash(script: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run an inline bash script."""
    return _run(["bash", "-c", script], cwd=cwd, env=env)


def _git(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a git command in a directory."""
    git_env = {
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        **(env or {}),
    }
    return _run(["git"] + args, cwd=cwd, env=git_env)


def _make_git_repo(tmp_path: Path) -> Path:
    """Initialise a fresh git repo with a single empty commit."""
    _git(["init", "-q", str(tmp_path)], cwd=tmp_path)
    _git(["config", "user.email", "test@example.com"], cwd=tmp_path)
    _git(["config", "user.name", "Test User"], cwd=tmp_path)
    _git(["commit", "--allow-empty", "-m", "initial"], cwd=tmp_path)
    return tmp_path


def _make_specify_config(tmp_path: Path, auto_commit_overrides: str = "") -> Path:
    """Write a minimal .specify/extensions/git/git-config.yml into tmp_path."""
    config_dir = tmp_path / ".specify" / "extensions" / "git"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_content = (
        "branch_numbering: sequential\n"
        "init_commit_message: \"[Spec Kit] Initial commit\"\n"
        "auto_commit:\n"
        "  default: false\n"
        + auto_commit_overrides
    )
    config_file = config_dir / "git-config.yml"
    config_file.write_text(config_content, encoding="utf-8")
    return config_file


# ===========================================================================
# Tests for git-common.sh: check_feature_branch()
# ===========================================================================

class TestCheckFeatureBranch:
    """Tests for the check_feature_branch() function in git-common.sh."""

    def _check(self, branch: str, has_git: str = "true") -> subprocess.CompletedProcess:
        script = (
            f"source '{GIT_COMMON_SH}' && "
            f"check_feature_branch '{branch}' '{has_git}'"
        )
        return _bash(script)

    # --- valid sequential branches ---

    def test_sequential_three_digits(self):
        result = self._check("001-feature-name")
        assert result.returncode == 0

    def test_sequential_four_digits(self):
        result = self._check("0042-some-feature")
        assert result.returncode == 0

    def test_sequential_large_number(self):
        result = self._check("1000-big-feature")
        assert result.returncode == 0

    def test_sequential_minimum_three_digits(self):
        result = self._check("100-my-feature")
        assert result.returncode == 0

    # --- valid timestamp branches ---

    def test_timestamp_format(self):
        result = self._check("20260319-143022-feature-name")
        assert result.returncode == 0

    def test_timestamp_format_short_slug(self):
        result = self._check("20260319-143022-fix")
        assert result.returncode == 0

    # --- invalid branches ---

    def test_plain_name_rejected(self):
        result = self._check("main")
        assert result.returncode != 0
        assert "Not on a feature branch" in result.stderr

    def test_feature_slash_rejected(self):
        result = self._check("feature/my-feature")
        assert result.returncode != 0

    def test_short_numeric_prefix_rejected(self):
        # Only 2 digits — less than required 3
        result = self._check("12-short-name")
        assert result.returncode != 0

    def test_no_prefix_rejected(self):
        result = self._check("add-user-auth")
        assert result.returncode != 0

    # --- malformed timestamp branches ---

    def test_seven_digit_date_rejected(self):
        # 7-digit date is invalid
        result = self._check("2026031-143022-feature")
        assert result.returncode != 0
        assert "Not on a feature branch" in result.stderr

    def test_timestamp_without_slug_rejected(self):
        # No trailing slug after YYYYMMDD-HHMMSS
        result = self._check("20260319-143022")
        assert result.returncode != 0
        assert "Not on a feature branch" in result.stderr

    # --- no-git-repo graceful degradation ---

    def test_no_git_repo_returns_zero(self):
        # When has_git_repo is not "true", validation is skipped
        result = self._check("main", has_git="false")
        assert result.returncode == 0
        assert "skipped branch validation" in result.stderr

    def test_no_git_repo_always_passes(self):
        result = self._check("invalid-branch-name", has_git="false")
        assert result.returncode == 0


# ===========================================================================
# Tests for git-common.sh: has_git()
# ===========================================================================

class TestHasGit:
    """Tests for the has_git() function in git-common.sh."""

    def test_has_git_in_real_repo(self):
        # REPO_ROOT is a real git repo
        script = f"source '{GIT_COMMON_SH}' && has_git '{REPO_ROOT}' && echo YES"
        result = _bash(script)
        assert result.returncode == 0
        assert "YES" in result.stdout

    def test_no_git_in_empty_dir(self, tmp_path: Path):
        # A fresh temp dir is not a git repo
        script = f"source '{GIT_COMMON_SH}' && has_git '{tmp_path}' && echo YES || echo NO"
        result = _bash(script)
        assert "NO" in result.stdout

    def test_has_git_after_init(self, tmp_path: Path):
        _make_git_repo(tmp_path)
        script = f"source '{GIT_COMMON_SH}' && has_git '{tmp_path}' && echo YES || echo NO"
        result = _bash(script)
        assert "YES" in result.stdout


# ===========================================================================
# Tests for create-new-feature.sh
# ===========================================================================

class TestCreateNewFeature:
    """Tests for create-new-feature.sh."""

    def _run_script(
        self,
        args: list[str],
        env: dict | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess:
        return _run(
            ["bash", str(CREATE_FEATURE_SH)] + args,
            cwd=cwd or REPO_ROOT,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
                **(env or {}),
            },
        )

    # --- error cases ---

    def test_no_description_exits_nonzero(self):
        result = self._run_script(["--dry-run"])
        assert result.returncode != 0
        assert "Usage" in result.stderr or "Usage" in result.stdout

    def test_whitespace_only_description_exits_nonzero(self):
        result = self._run_script(["--dry-run", "   "])
        assert result.returncode != 0

    def test_short_name_missing_value_exits_nonzero(self):
        result = self._run_script(["--dry-run", "--short-name", "Add feature"])
        # When --short-name value starts with no-flag text it's used as the value;
        # but when --short-name is last, it's an error
        result2 = self._run_script(["--dry-run", "--short-name"])
        assert result2.returncode != 0
        assert "--short-name requires a value" in result2.stderr

    def test_number_missing_value_exits_nonzero(self):
        result = self._run_script(["--dry-run", "--number"])
        assert result.returncode != 0
        assert "--number requires a value" in result.stderr

    def test_number_non_integer_exits_nonzero(self):
        result = self._run_script(["--dry-run", "--number", "abc", "Feature"])
        assert result.returncode != 0
        assert "--number must be a non-negative integer" in result.stderr

    # --- sequential mode with explicit --number ---

    def test_sequential_branch_with_number(self):
        result = self._run_script(
            ["--dry-run", "--number", "7", "--short-name", "user-auth", "Add user auth"]
        )
        assert result.returncode == 0
        assert "BRANCH_NAME: 007-user-auth" in result.stdout
        assert "FEATURE_NUM: 007" in result.stdout

    def test_sequential_branch_pads_to_three_digits(self):
        result = self._run_script(
            ["--dry-run", "--number", "1", "--short-name", "fix-bug", "Fix a bug"]
        )
        assert result.returncode == 0
        assert "BRANCH_NAME: 001-fix-bug" in result.stdout
        assert "FEATURE_NUM: 001" in result.stdout

    def test_sequential_branch_large_number(self):
        result = self._run_script(
            ["--dry-run", "--number", "1000", "--short-name", "big-feature", "Big feature"]
        )
        assert result.returncode == 0
        assert "BRANCH_NAME: 1000-big-feature" in result.stdout

    # --- JSON output mode ---

    def test_json_output_contains_branch_name_and_feature_num(self):
        result = self._run_script(
            ["--dry-run", "--number", "5", "--short-name", "api-client", "--json", "Add API client"]
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["BRANCH_NAME"] == "005-api-client"
        assert data["FEATURE_NUM"] == "005"

    def test_json_dry_run_flag_present(self):
        result = self._run_script(
            ["--dry-run", "--number", "2", "--short-name", "test-feature", "--json", "Test feature"]
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("DRY_RUN") is True

    def test_json_output_is_valid_json(self):
        result = self._run_script(
            ["--dry-run", "--number", "9", "--json", "Some feature description"]
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)  # must not raise
        assert "BRANCH_NAME" in data
        assert "FEATURE_NUM" in data

    # --- timestamp mode ---

    def test_timestamp_mode_prefix_format(self):
        result = self._run_script(
            ["--dry-run", "--timestamp", "--short-name", "new-feature", "--json", "New feature"]
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        feature_num = data["FEATURE_NUM"]
        # Must match YYYYMMDD-HHMMSS pattern
        assert len(feature_num) == 15  # 8 + 1 + 6
        assert feature_num[8] == "-"
        assert feature_num[:8].isdigit()
        assert feature_num[9:].isdigit()

    def test_timestamp_branch_name_starts_with_feature_num(self):
        result = self._run_script(
            ["--dry-run", "--timestamp", "--short-name", "ts-feature", "--json", "Timestamp feature"]
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["BRANCH_NAME"].startswith(data["FEATURE_NUM"] + "-")

    def test_timestamp_ignores_number_flag_with_warning(self):
        result = self._run_script(
            ["--dry-run", "--timestamp", "--number", "5", "--short-name", "ts-feature", "--json", "Feature"]
        )
        assert result.returncode == 0
        assert "--number is ignored when --timestamp is used" in result.stderr
        data = json.loads(result.stdout)
        # Must still be a timestamp branch, not 005-...
        assert "-" in data["FEATURE_NUM"]  # timestamp has hyphen separator

    # --- GIT_BRANCH_NAME env override ---

    def test_git_branch_name_override_exact(self):
        result = self._run_script(
            ["--dry-run", "--json", "Some feature"],
            env={"GIT_BRANCH_NAME": "my-exact-branch"},
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["BRANCH_NAME"] == "my-exact-branch"

    def test_git_branch_name_override_extracts_sequential_prefix(self):
        result = self._run_script(
            ["--dry-run", "--json", "Some feature"],
            env={"GIT_BRANCH_NAME": "042-my-feature"},
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["BRANCH_NAME"] == "042-my-feature"
        assert data["FEATURE_NUM"] == "042"

    def test_git_branch_name_override_extracts_timestamp_prefix(self):
        result = self._run_script(
            ["--dry-run", "--json", "Some feature"],
            env={"GIT_BRANCH_NAME": "20260319-143022-my-feature"},
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["BRANCH_NAME"] == "20260319-143022-my-feature"
        assert data["FEATURE_NUM"] == "20260319-143022"

    def test_git_branch_name_override_too_long_exits_nonzero(self):
        # 245+ byte name should fail when GIT_BRANCH_NAME is used
        long_name = "a" * 245
        result = self._run_script(
            ["--dry-run", "--json", "Feature"],
            env={"GIT_BRANCH_NAME": long_name},
        )
        assert result.returncode != 0
        assert "244 bytes" in result.stderr

    # --- short-name cleaning ---

    def test_short_name_uppercased_is_lowercased(self):
        result = self._run_script(
            ["--dry-run", "--number", "1", "--short-name", "User-Auth", "Add auth"]
        )
        assert result.returncode == 0
        assert "001-user-auth" in result.stdout

    def test_short_name_with_spaces_converted_to_dashes(self):
        result = self._run_script(
            ["--dry-run", "--number", "3", "--short-name", "user auth flow", "Add flow"]
        )
        assert result.returncode == 0
        assert "003-user-auth-flow" in result.stdout

    # --- branch name generation from description ---

    def test_description_generates_branch_suffix(self):
        result = self._run_script(
            ["--dry-run", "--number", "2", "Implement OAuth2 login flow"]
        )
        assert result.returncode == 0
        # The branch should contain meaningful words from the description
        assert "002-" in result.stdout

    def test_description_stop_words_filtered(self):
        result = self._run_script(
            ["--dry-run", "--number", "10", "Add the user authentication system"]
        )
        assert result.returncode == 0
        branch_line = [l for l in result.stdout.splitlines() if l.startswith("BRANCH_NAME:")][0]
        branch_name = branch_line.split(": ", 1)[1]
        # Stop words like "the", "add" should be filtered out; meaningful words should remain
        assert "010-" in branch_name
        # "user", "authentication", "system" are non-stop-words
        assert len(branch_name) > len("010-")

    # --- branch length truncation ---

    def test_long_branch_name_truncated_to_244(self):
        long_short_name = "x" * 250
        result = self._run_script(
            ["--dry-run", "--number", "1", "--short-name", long_short_name, "Feature"]
        )
        assert result.returncode == 0
        branch_line = [l for l in result.stdout.splitlines() if l.startswith("BRANCH_NAME:")][0]
        branch_name = branch_line.split(": ", 1)[1]
        assert len(branch_name.encode("utf-8")) <= 244
        assert "244-byte limit" in result.stderr

    # --- specs dir highest number detection ---

    def test_highest_from_specs_dir(self, tmp_path: Path):
        """Script detects existing spec dirs and increments the highest number."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "001-first-feature").mkdir()
        (specs_dir / "003-third-feature").mkdir()

        # Create a minimal git repo here so the script is happy
        _make_git_repo(tmp_path)

        # Copy scripts to the tmp_path structure so _find_project_root resolves correctly
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(CREATE_FEATURE_SH), str(scripts_dir / "create-new-feature.sh"))
        shutil.copy(str(GIT_COMMON_SH), str(scripts_dir / "git-common.sh"))

        result = _run(
            ["bash", str(scripts_dir / "create-new-feature.sh"),
             "--dry-run", "--short-name", "next-feature", "--json", "Next feature"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # Next number after 003 should be 004
        assert data["FEATURE_NUM"] == "004"

    def test_timestamp_dirs_not_counted_in_sequential(self, tmp_path: Path):
        """Timestamp-format spec dirs must not be counted as sequential numbers."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "002-existing").mkdir()
        (specs_dir / "20260319-143022-timestamp-spec").mkdir()

        _make_git_repo(tmp_path)

        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(CREATE_FEATURE_SH), str(scripts_dir / "create-new-feature.sh"))
        shutil.copy(str(GIT_COMMON_SH), str(scripts_dir / "git-common.sh"))

        result = _run(
            ["bash", str(scripts_dir / "create-new-feature.sh"),
             "--dry-run", "--short-name", "new-feat", "--json", "New feature"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # Timestamp dir should not count; next is 003
        assert data["FEATURE_NUM"] == "003"

    # --- no git repo (graceful degradation) ---

    def test_no_git_repo_still_outputs_branch_name(self, tmp_path: Path):
        """When not in a git repo, scripts warns and still outputs branch name."""
        # Set up scripts in a non-git tmp directory
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(CREATE_FEATURE_SH), str(scripts_dir / "create-new-feature.sh"))
        shutil.copy(str(GIT_COMMON_SH), str(scripts_dir / "git-common.sh"))

        result = _run(
            ["bash", str(scripts_dir / "create-new-feature.sh"),
             "--dry-run", "--number", "1", "--short-name", "no-git", "--json", "No git repo"],
            cwd=tmp_path,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["BRANCH_NAME"] == "001-no-git"


# ===========================================================================
# Tests for auto-commit.sh
# ===========================================================================

class TestAutoCommit:
    """Tests for auto-commit.sh."""

    def _run_script(
        self,
        args: list[str],
        cwd: Path | None = None,
        env: dict | None = None,
    ) -> subprocess.CompletedProcess:
        base_env = {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
        return _run(
            ["bash", str(AUTO_COMMIT_SH)] + args,
            cwd=cwd or REPO_ROOT,
            env={**base_env, **(env or {})},
        )

    def test_no_event_name_exits_nonzero(self):
        result = self._run_script([])
        assert result.returncode != 0
        assert "Usage" in result.stderr

    def test_event_disabled_in_config_exits_zero(self):
        # The real config has all events disabled by default
        result = self._run_script(["after_specify"])
        assert result.returncode == 0

    def test_event_before_plan_disabled_exits_zero(self):
        result = self._run_script(["before_plan"])
        assert result.returncode == 0

    def test_no_config_file_exits_zero(self, tmp_path: Path):
        """When no git-config.yml exists, auto-commit is disabled by default."""
        _make_git_repo(tmp_path)
        # No .specify directory — no config file
        # Copy script to a location where _find_project_root finds tmp_path
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(AUTO_COMMIT_SH), str(scripts_dir / "auto-commit.sh"))

        result = _run(
            ["bash", str(scripts_dir / "auto-commit.sh"), "after_specify"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0

    def test_event_enabled_commits_changes(self, tmp_path: Path):
        """When an event is enabled, changed files are committed."""
        _make_git_repo(tmp_path)

        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(AUTO_COMMIT_SH), str(scripts_dir / "auto-commit.sh"))

        # Write config with after_specify enabled
        _make_specify_config(
            tmp_path,
            auto_commit_overrides=(
                "  after_specify:\n"
                "    enabled: true\n"
                "    message: \"[Spec Kit] Add specification\"\n"
            ),
        )

        # Create a new file to commit
        (tmp_path / "new-file.txt").write_text("hello", encoding="utf-8")

        result = _run(
            ["bash", str(scripts_dir / "auto-commit.sh"), "after_specify"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        assert "committed" in result.stderr

        # Verify the commit was made
        log_result = _git(["log", "--oneline", "-1"], cwd=tmp_path)
        assert "[Spec Kit] Add specification" in log_result.stdout

    def test_event_enabled_no_changes_skips_commit(self, tmp_path: Path):
        """When enabled but no changes exist, script skips the commit."""
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(AUTO_COMMIT_SH), str(scripts_dir / "auto-commit.sh"))

        _make_specify_config(
            tmp_path,
            auto_commit_overrides=(
                "  after_specify:\n"
                "    enabled: true\n"
                "    message: \"[Spec Kit] Add specification\"\n"
            ),
        )

        _make_git_repo(tmp_path)
        # Stage and commit all setup files so the working tree is clean
        _git(["add", "."], cwd=tmp_path)
        _git(["commit", "-m", "add setup files"], cwd=tmp_path)

        result = _run(
            ["bash", str(scripts_dir / "auto-commit.sh"), "after_specify"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        assert "No changes to commit" in result.stderr

    def test_default_true_enables_unlisted_event(self, tmp_path: Path):
        """When auto_commit.default is true and no event override exists, commit runs."""
        _make_git_repo(tmp_path)

        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(AUTO_COMMIT_SH), str(scripts_dir / "auto-commit.sh"))

        # Config with default: true, no specific event overrides
        config_dir = tmp_path / ".specify" / "extensions" / "git"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "git-config.yml").write_text(
            "branch_numbering: sequential\n"
            "auto_commit:\n"
            "  default: true\n",
            encoding="utf-8",
        )

        (tmp_path / "change.txt").write_text("changed", encoding="utf-8")

        result = _run(
            ["bash", str(scripts_dir / "auto-commit.sh"), "after_implement"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        assert "committed" in result.stderr

    def test_default_true_explicit_false_disables_event(self, tmp_path: Path):
        """When default is true but the event is explicitly disabled, no commit."""
        _make_git_repo(tmp_path)

        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(AUTO_COMMIT_SH), str(scripts_dir / "auto-commit.sh"))

        config_dir = tmp_path / ".specify" / "extensions" / "git"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "git-config.yml").write_text(
            "branch_numbering: sequential\n"
            "auto_commit:\n"
            "  default: true\n"
            "  after_specify:\n"
            "    enabled: false\n"
            "    message: \"[Spec Kit] Spec\"\n",
            encoding="utf-8",
        )

        (tmp_path / "file.txt").write_text("content", encoding="utf-8")

        result = _run(
            ["bash", str(scripts_dir / "auto-commit.sh"), "after_specify"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        # Should NOT have committed — file remains untracked
        status = _git(["status", "--short"], cwd=tmp_path)
        assert "file.txt" in status.stdout

    def test_default_commit_message_used_when_none_configured(self, tmp_path: Path):
        """When no custom message, uses auto-generated default message."""
        _make_git_repo(tmp_path)

        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(AUTO_COMMIT_SH), str(scripts_dir / "auto-commit.sh"))

        config_dir = tmp_path / ".specify" / "extensions" / "git"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "git-config.yml").write_text(
            "auto_commit:\n"
            "  default: false\n"
            "  after_plan:\n"
            "    enabled: true\n",
            encoding="utf-8",
        )

        (tmp_path / "plan.txt").write_text("plan content", encoding="utf-8")

        result = _run(
            ["bash", str(scripts_dir / "auto-commit.sh"), "after_plan"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        log_result = _git(["log", "--oneline", "-1"], cwd=tmp_path)
        # Default message should be "[Spec Kit] Auto-commit after plan"
        assert "Auto-commit" in log_result.stdout
        assert "plan" in log_result.stdout

    def test_before_event_uses_before_phase_in_message(self, tmp_path: Path):
        """Events like before_clarify use 'before' in the auto-generated message."""
        _make_git_repo(tmp_path)

        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(AUTO_COMMIT_SH), str(scripts_dir / "auto-commit.sh"))

        config_dir = tmp_path / ".specify" / "extensions" / "git"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "git-config.yml").write_text(
            "auto_commit:\n"
            "  default: false\n"
            "  before_clarify:\n"
            "    enabled: true\n",
            encoding="utf-8",
        )

        (tmp_path / "draft.txt").write_text("draft", encoding="utf-8")

        result = _run(
            ["bash", str(scripts_dir / "auto-commit.sh"), "before_clarify"],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        assert "before" in result.stderr


# ===========================================================================
# Tests for initialize-repo.sh
# ===========================================================================

class TestInitializeRepo:
    """Tests for initialize-repo.sh."""

    def test_already_initialized_skips_with_message(self):
        """Running in an existing git repo skips initialization."""
        result = _run(
            ["bash", str(INITIALIZE_REPO_SH)],
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "already initialized" in result.stderr

    def test_fresh_directory_creates_git_repo(self, tmp_path: Path):
        """Running in a non-git directory initializes the repo."""
        # Set up scripts in a fresh temp directory
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(INITIALIZE_REPO_SH), str(scripts_dir / "initialize-repo.sh"))

        result = _run(
            ["bash", str(scripts_dir / "initialize-repo.sh")],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        assert result.returncode == 0
        assert "✓ Git repository initialized" in result.stderr
        assert (tmp_path / ".git").exists()

    def test_fresh_directory_uses_default_commit_message(self, tmp_path: Path):
        """Initial commit uses default '[Spec Kit] Initial commit' message."""
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(INITIALIZE_REPO_SH), str(scripts_dir / "initialize-repo.sh"))

        _run(
            ["bash", str(scripts_dir / "initialize-repo.sh")],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )

        # Verify the commit message
        log = _git(["log", "--oneline", "-1"], cwd=tmp_path)
        assert "[Spec Kit] Initial commit" in log.stdout

    def test_custom_commit_message_from_config(self, tmp_path: Path):
        """Custom init_commit_message from git-config.yml is used."""
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(INITIALIZE_REPO_SH), str(scripts_dir / "initialize-repo.sh"))

        config_dir = tmp_path / ".specify" / "extensions" / "git"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "git-config.yml").write_text(
            "init_commit_message: \"Custom project init\"\n",
            encoding="utf-8",
        )

        _run(
            ["bash", str(scripts_dir / "initialize-repo.sh")],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )

        log = _git(["log", "--oneline", "-1"], cwd=tmp_path)
        assert "Custom project init" in log.stdout

    def test_second_run_skips_already_initialized(self, tmp_path: Path):
        """Running initialize-repo.sh twice: second run skips silently."""
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(INITIALIZE_REPO_SH), str(scripts_dir / "initialize-repo.sh"))

        env = {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
        script_path = str(scripts_dir / "initialize-repo.sh")

        _run(["bash", script_path], cwd=tmp_path, env=env)
        result2 = _run(["bash", script_path], cwd=tmp_path, env=env)
        assert result2.returncode == 0
        assert "already initialized" in result2.stderr

    def test_committed_files_appear_in_git_log(self, tmp_path: Path):
        """Files present before init are included in the initial commit."""
        scripts_dir = tmp_path / ".specify" / "extensions" / "git" / "scripts" / "bash"
        scripts_dir.mkdir(parents=True)
        shutil.copy(str(INITIALIZE_REPO_SH), str(scripts_dir / "initialize-repo.sh"))

        (tmp_path / "README.txt").write_text("Readme", encoding="utf-8")

        _run(
            ["bash", str(scripts_dir / "initialize-repo.sh")],
            cwd=tmp_path,
            env={
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )

        show = _git(["show", "--stat", "HEAD"], cwd=tmp_path)
        assert "README.txt" in show.stdout