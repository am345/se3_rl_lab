#!/usr/bin/env python3
"""Build reduced visual meshes suitable for the browser MuJoCo runtime."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = (
    ROOT
    / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/meshes/web_visual"
)
BASE_TARGET_FACES = 15_000
BASE_FINAL_TARGET_FACES = 10_000
LINK_TARGET_FACES = {
    "lf_calf_1_link.STL": 1_262,
    "lf_calf_2_link.STL": 624,
    "lf_calf_3_link.STL": 12_000,
    "lf_thigh_link.STL": 10_910,
    "lf_wheel_link.STL": 15_000,
    "rf_calf_1_link.STL": 1_248,
    "rf_calf_2_link.STL": 624,
    "rf_calf_3_link.STL": 12_000,
    "rf_thigh_link.STL": 10_912,
    "rf_wheel_link.STL": 15_000,
}


def _load_trimesh():
    try:
        import trimesh
    except ImportError as error:
        raise RuntimeError(
            "building browser visual meshes requires trimesh and fast-simplification"
        ) from error
    return trimesh


def _reduce(source: Path, destination: Path, target_faces: int) -> tuple[int, int]:
    trimesh = _load_trimesh()
    mesh = trimesh.load_mesh(source, process=True)
    source_faces = len(mesh.faces)
    if source_faces > target_faces:
        mesh = mesh.simplify_quadric_decimation(face_count=target_faces)
    destination.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(destination, file_type="stl")
    return source_faces, len(mesh.faces)


def build(source_mesh_dir: Path) -> None:
    base_source = source_mesh_dir / "sw_original_base"
    base_output = OUTPUT_DIR / "base"
    links_output = OUTPUT_DIR / "links"

    jobs = []
    for index in range(13):
        name = f"base_link_chunk_{index:02d}.stl"
        target = BASE_FINAL_TARGET_FACES if index == 12 else BASE_TARGET_FACES
        jobs.append((base_source / name, base_output / name, target))
    jobs.extend(
        (source_mesh_dir / name, links_output / name, target)
        for name, target in LINK_TARGET_FACES.items()
    )

    missing = [str(source) for source, _, _ in jobs if not source.is_file()]
    if missing:
        raise FileNotFoundError(f"missing source visual meshes: {missing}")

    total_source = 0
    total_output = 0
    for source, destination, target in jobs:
        source_faces, output_faces = _reduce(source, destination, target)
        total_source += source_faces
        total_output += output_faces
        print(
            f"{source.name}: {source_faces} -> {output_faces} faces "
            f"({destination.relative_to(ROOT)})"
        )
    print(f"total: {total_source} -> {total_output} faces")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source_mesh_dir",
        type=Path,
        help="directory containing the original visual STL files",
    )
    args = parser.parse_args()
    build(args.source_mesh_dir.resolve())


if __name__ == "__main__":
    main()
