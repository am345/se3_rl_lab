"""Unified SerialLeg experiment command line."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from se3_rl_lab.tools.reports import compare_metrics
from se3_rl_lab.tools.runs import find_repo_root, list_runs, resolve_run, run_root

DEFAULT_TASK = "SerialLeg-Flat-ClosedChain-v0"


def _python(repo_root: Path) -> str:
    candidate = repo_root / ".venv" / "bin" / "python"
    return str(candidate if candidate.is_file() else Path(sys.executable))


def _run(command: list[str], *, repo_root: Path) -> int:
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=repo_root, check=False).returncode


def _training_command(args: argparse.Namespace, repo_root: Path, *, resume: bool) -> list[str]:
    command = [
        _python(repo_root),
        "-u",
        "scripts/rsl_rl/train.py",
        "--task",
        args.task,
        "--num_envs",
        str(args.envs),
        "--device",
        args.device,
        "--headless",
        "--max_iterations",
        str(args.iterations),
        "--run_name",
        args.run_name,
    ]
    if resume:
        run = resolve_run(args.run, repo_root=repo_root)
        command += ["--resume", "--load_run", run.path.name, "--checkpoint", run.checkpoint(args.checkpoint).name]
    command.extend(args.extra)
    return command


def _train(args: argparse.Namespace, *, resume: bool = False) -> int:
    repo_root = find_repo_root()
    root = run_root(repo_root)
    before = {path.resolve() for path in root.glob("*")} if root.is_dir() else set()
    command = _training_command(args, repo_root, resume=resume)
    code = _run(command, repo_root=repo_root)
    after = sorted((path.resolve() for path in root.glob("*") if path.is_dir()), key=lambda path: path.stat().st_mtime)
    created = [path for path in after if path not in before]
    target = created[-1] if created else (after[-1] if after else None)
    if target is not None:
        run = resolve_run(target, repo_root=repo_root)
        run.ensure_manifest(repo_root=repo_root, task=args.task, command=command)
        run.update_status(
            state="completed" if code == 0 else "failed",
            latest_checkpoint=str(run.checkpoint("latest")) if run.checkpoints else None,
            exit_code=code,
        )
        print(f"run_dir={run.path}")
    return code


def _play(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    run = resolve_run(args.run, repo_root=repo_root)
    command = [
        _python(repo_root),
        "-u",
        "scripts/rsl_rl/play.py",
        "--task",
        args.task,
        "--num_envs",
        "1",
        "--device",
        args.device,
        "--checkpoint",
        str(run.checkpoint(args.checkpoint)),
        "--show_colliders",
    ]
    return _run(command, repo_root=repo_root)


def _eval(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    run = resolve_run(args.run, repo_root=repo_root)
    checkpoint = run.checkpoint(args.checkpoint)
    context_dir = run.path / "isaac_eval" / "contexts"
    context_dir.mkdir(parents=True, exist_ok=True)
    context = {
        "schema_version": 1,
        "task": args.task,
        "suite": args.suite,
        "checkpoint": str(checkpoint),
        "run_dir": str(run.path),
        "device": args.device,
        "video": not args.no_video,
        "rerun": not args.no_rerun,
        "scenario_duration_s": args.scenario_duration,
    }
    context_path = context_dir / f"{checkpoint.stem}.isaac_eval.json"
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = [_python(repo_root), "-u", "-m", "se3_rl_lab.isaac_eval.worker", "--context", str(context_path)]
    code = _run(command, repo_root=repo_root)
    result_path = run.path / "isaac_eval" / "latest_result.json"
    if code == 0 and result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        run.ensure_manifest(repo_root=repo_root, task=args.task, command=command)
        status = run.read_status()
        best_score = float(status.get("best_score", "-inf"))
        updates = {
            "latest_checkpoint": str(checkpoint),
            "latest_evaluation": str(result["metrics_path"]),
            "latest_score": result["score"],
        }
        if result["score"] > best_score:
            updates.update(best_checkpoint=str(checkpoint), best_score=result["score"])
        run.update_status(**updates)
        return 0
    if code == 0:
        print(f"evaluation worker did not produce {result_path}", file=sys.stderr)
        return 1
    return code


def _runs(_args: argparse.Namespace) -> int:
    for run in list_runs():
        status = run.read_status()
        print(f"{run.path.name}\t{len(run.checkpoints)} checkpoints\t{status.get('latest_score', '-')}")
    return 0


def _compare(args: argparse.Namespace) -> int:
    paths = [Path(value).resolve() for value in args.metrics]
    compare_metrics(paths, Path(args.output).resolve())
    print(Path(args.output).resolve())
    return 0


def _add_training_arguments(parser: argparse.ArgumentParser, *, resume: bool) -> None:
    if resume:
        parser.add_argument("run")
        parser.add_argument("--checkpoint", default="latest")
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--envs", type=int, default=4096)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--run-name", default="se3rl")
    parser.add_argument("extra", nargs=argparse.REMAINDER)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="se3rl", description="SerialLeg experiment lifecycle CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    train = subparsers.add_parser("train", help="Start a new training run")
    _add_training_arguments(train, resume=False)
    train.set_defaults(handler=lambda args: _train(args, resume=False))
    resume = subparsers.add_parser("resume", help="Resume an existing run")
    _add_training_arguments(resume, resume=True)
    resume.set_defaults(handler=lambda args: _train(args, resume=True))
    play = subparsers.add_parser("play", help="Open an Isaac Sim checkpoint viewer")
    play.add_argument("run")
    play.add_argument("--checkpoint", default="best")
    play.add_argument("--task", default=DEFAULT_TASK)
    play.add_argument("--device", default="cuda:0")
    play.set_defaults(handler=_play)
    evaluate = subparsers.add_parser("eval", aliases=["record"], help="Evaluate and record a checkpoint")
    evaluate.add_argument("run")
    evaluate.add_argument("--checkpoint", default="latest")
    evaluate.add_argument("--suite", default="flat-basic", choices=["flat-basic"])
    evaluate.add_argument("--scenario-duration", type=float, default=4.0)
    evaluate.add_argument("--task", default=DEFAULT_TASK)
    evaluate.add_argument("--device", default="cuda:0")
    evaluate.add_argument("--no-video", action="store_true")
    evaluate.add_argument("--no-rerun", action="store_true")
    evaluate.set_defaults(handler=_eval)
    runs = subparsers.add_parser("runs", help="List local training runs")
    runs.set_defaults(handler=_runs)
    compare = subparsers.add_parser("compare", help="Build a Markdown evaluation comparison")
    compare.add_argument("metrics", nargs="+")
    compare.add_argument("--output", default="evaluation-comparison.md")
    compare.set_defaults(handler=_compare)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
