#!/usr/bin/env python3
"""Build the browser-ready SerialLeg MuJoCo scene and asset manifest."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg"
SOURCE_SCENE = ASSET_DIR / "mjcf/serialleg_closed_chain_visual.xml"
OUTPUT_SCENE = ASSET_DIR / "scene.xml"
OUTPUT_MANIFEST = ASSET_DIR / "websim_manifest.json"
SIM_DT = 0.005
ACTUATORS = (
    ("lf0_torque", "lf0_Joint"),
    ("l_drive_bar_torque", "l_drive_bar_Joint"),
    ("rf0_torque", "rf0_Joint"),
    ("r_drive_bar_torque", "r_drive_bar_Joint"),
    ("l_wheel_torque", "l_wheel_Joint"),
    ("r_wheel_torque", "r_wheel_Joint"),
)


def build() -> tuple[Path, Path]:
    tree = ET.parse(SOURCE_SCENE)
    root = tree.getroot()
    compiler = root.find("compiler")
    option = root.find("option")
    if compiler is None or option is None:
        raise RuntimeError("canonical scene is missing compiler or option")
    compiler.set("meshdir", "meshes")
    option.set("timestep", f"{SIM_DT:.3f}")
    option.set("integrator", "implicitfast")
    option.set("solver", "Newton")
    option.set("iterations", "100")

    previous = root.find("actuator")
    if previous is not None:
        root.remove(previous)
    actuator = ET.Element("actuator")
    for name, joint in ACTUATORS:
        ET.SubElement(actuator, "motor", name=name, joint=joint, gear="1")
    keyframe = root.find("keyframe")
    root.insert(list(root).index(keyframe) if keyframe is not None else len(root), actuator)

    ET.indent(tree, space="  ")
    tree.write(OUTPUT_SCENE, encoding="unicode", xml_declaration=False)
    with OUTPUT_SCENE.open("a", encoding="utf-8") as stream:
        stream.write("\n")

    mesh_files = sorted(
        {f"meshes/{element.attrib['file']}" for element in root.findall("./asset/mesh")}
    )
    missing = [relative for relative in mesh_files if not (ASSET_DIR / relative).is_file()]
    if missing:
        raise RuntimeError(f"scene references missing mesh assets: {missing}")
    manifest = {
        "schemaVersion": 1,
        "entrypoint": "scene.xml",
        "files": ["scene.xml", *mesh_files],
    }
    OUTPUT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return OUTPUT_SCENE, OUTPUT_MANIFEST


if __name__ == "__main__":
    scene, manifest = build()
    print(f"built {scene.relative_to(ROOT)}")
    print(f"built {manifest.relative_to(ROOT)}")
