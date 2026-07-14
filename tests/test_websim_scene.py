import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg"


def test_browser_scene_preserves_closed_chain_and_adds_policy_actuators() -> None:
    root = ET.parse(ASSET_DIR / "scene.xml").getroot()

    assert root.find("compiler").attrib["meshdir"] == "meshes"
    option = root.find("option").attrib
    assert float(option["timestep"]) == 0.005
    assert option["integrator"] == "implicitfast"
    assert option["solver"] == "Newton"
    assert int(option["iterations"]) == 100
    assert len(root.findall("./equality/connect")) == 2
    assert len(root.findall("./tendon/fixed")) == 2
    assert len(root.findall('.//geom[@group="1"]')) == 23
    assert [key.attrib["name"] for key in root.findall("./keyframe/key")] == ["standing"]
    assert [motor.attrib["joint"] for motor in root.findall("./actuator/motor")] == [
        "lf0_Joint",
        "l_drive_bar_Joint",
        "rf0_Joint",
        "r_drive_bar_Joint",
        "l_wheel_Joint",
        "r_wheel_Joint",
    ]


def test_browser_asset_manifest_is_complete_and_minimal() -> None:
    root = ET.parse(ASSET_DIR / "scene.xml").getroot()
    manifest = json.loads((ASSET_DIR / "websim_manifest.json").read_text(encoding="utf-8"))
    mesh_files_by_name = {
        element.attrib["name"]: element.attrib["file"]
        for element in root.findall("./asset/mesh")
    }
    visual_mesh_files = {
        mesh_files_by_name[geom.attrib["mesh"]]
        for geom in root.findall('.//geom[@group="1"]')
    }
    referenced_meshes = {
        f"meshes/{element.attrib['file']}" for element in root.findall("./asset/mesh")
    }

    assert manifest["schemaVersion"] == 1
    assert manifest["entrypoint"] == "scene.xml"
    assert manifest["files"][0] == "scene.xml"
    assert set(manifest["files"][1:]) == referenced_meshes
    assert all((ASSET_DIR / relative).is_file() for relative in manifest["files"])
    assert len(visual_mesh_files) == 23
    assert all(relative.startswith("web_visual/") for relative in visual_mesh_files)
    assert sum((ASSET_DIR / relative).stat().st_size for relative in manifest["files"]) < 30_000_000
