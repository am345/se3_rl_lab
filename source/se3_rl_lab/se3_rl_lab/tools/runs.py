"""Run-directory discovery and durable metadata helpers."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHECKPOINT_RE = re.compile(r"model_(\d+)\.pt$")
DEFAULT_EXPERIMENT = "serialleg_flat_closed_chain"
FLAT_OBSERVATION_DIMS = (34, 40)
RECOVERY_OBSERVATION_DIMS = (138, 168)


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "scripts" / "rsl_rl" / "train.py").is_file() and (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"unable to locate se3_rl_lab repository root from {current}")


def checkpoint_iteration(path: Path) -> int:
    match = CHECKPOINT_RE.search(path.name)
    if match is None:
        raise ValueError(f"not an RSL-RL checkpoint: {path}")
    return int(match.group(1))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


@dataclass(frozen=True)
class RunDirectory:
    path: Path

    @property
    def manifest_path(self) -> Path:
        return self.path / "manifest.json"

    @property
    def status_path(self) -> Path:
        return self.path / "status.json"

    @property
    def checkpoints(self) -> list[Path]:
        return sorted(self.path.glob("model_*.pt"), key=checkpoint_iteration)

    def checkpoint(self, selector: str = "latest") -> Path:
        candidate = Path(selector)
        if candidate.is_file():
            return candidate.resolve()
        if selector == "best":
            status = self.read_status()
            best = status.get("best_checkpoint")
            if best and Path(best).is_file():
                return Path(best).resolve()
        checkpoints = self.checkpoints
        if not checkpoints:
            raise FileNotFoundError(f"no model_*.pt found in {self.path}")
        if selector == "latest":
            return checkpoints[-1].resolve()
        if selector.isdigit():
            requested = self.path / f"model_{selector}.pt"
            if requested.is_file():
                return requested.resolve()
        raise FileNotFoundError(f"checkpoint selector {selector!r} was not found in {self.path}")

    def read_status(self) -> dict[str, Any]:
        if not self.status_path.is_file():
            return {}
        return json.loads(self.status_path.read_text(encoding="utf-8"))

    def update_status(self, **updates: Any) -> dict[str, Any]:
        status = self.read_status()
        status.update(updates)
        status["updated_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_json(self.status_path, status)
        return status

    def ensure_manifest(self, *, repo_root: Path, task: str, command: list[str]) -> dict[str, Any]:
        if self.manifest_path.is_file():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        actor_observation_dim, critic_observation_dim = (
            RECOVERY_OBSERVATION_DIMS if "Recovery" in task else FLAT_OBSERVATION_DIMS
        )
        payload = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task": task,
            "run_dir": str(self.path.resolve()),
            "command": command,
            "git_sha": _git(repo_root, "rev-parse", "HEAD"),
            "git_status": _git(repo_root, "status", "--short"),
            "isaaclab_source": "../IsaacLab",
            "action_contract": "SerialLeg delayed 6D",
            "actor_observation_dim": actor_observation_dim,
            "critic_observation_dim": critic_observation_dim,
            "reward_profile": "recovery_discovery" if "Recovery" in task else "official_base",
        }
        _atomic_json(self.manifest_path, payload)
        return payload


def run_root(repo_root: Path, experiment: str = DEFAULT_EXPERIMENT) -> Path:
    return repo_root / "logs" / "rsl_rl" / experiment


def resolve_run(value: str | Path, *, repo_root: Path | None = None) -> RunDirectory:
    repo_root = repo_root or find_repo_root()
    candidate = Path(value)
    if candidate.is_dir():
        return RunDirectory(candidate.resolve())
    root = run_root(repo_root)
    exact = root / str(value)
    if exact.is_dir():
        return RunDirectory(exact.resolve())
    matches = sorted(path for path in root.glob(f"*{value}*") if path.is_dir())
    if len(matches) == 1:
        return RunDirectory(matches[0].resolve())
    if not matches:
        raise FileNotFoundError(f"run {value!r} not found below {root}")
    raise RuntimeError(f"run selector {value!r} is ambiguous: {[path.name for path in matches]}")


def list_runs(repo_root: Path | None = None) -> list[RunDirectory]:
    root = run_root(repo_root or find_repo_root())
    if not root.is_dir():
        return []
    return [RunDirectory(path) for path in sorted(root.iterdir(), reverse=True) if path.is_dir()]
