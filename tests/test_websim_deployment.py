from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import onnx
from onnx import TensorProto, helper

MODULE_PATH = (
    Path(__file__).parents[1]
    / "source/se3_rl_lab/se3_rl_lab/websim/deployment.py"
)
SPEC = importlib.util.spec_from_file_location("websim_deployment_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
deployment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deployment)


def _model(path: Path) -> None:
    graph = helper.make_graph(
        [helper.make_node("Identity", ["obs"], ["actions"])],
        "policy",
        [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, 138])],
        [helper.make_tensor_value_info("actions", TensorProto.FLOAT, [1, 6])],
    )
    onnx.save(helper.make_model(graph), path)


def test_metadata_key_is_project_owned() -> None:
    assert deployment.METADATA_KEY == "se3_rl_lab.websim.deployment.v1"
    assert deployment.SCHEMA_NAME == "se3_rl_lab.websim.deployment"


def test_attach_replaces_existing_project_metadata(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "policy.onnx"
    _model(path)
    first = {
        "meta": {"schema_name": deployment.SCHEMA_NAME, "schema_version": 1},
        "marker": 1,
    }
    second = {**first, "marker": 2}
    monkeypatch.setattr(deployment, "build_serialleg_descriptor", lambda **_: first)
    deployment.attach_serialleg_websim_metadata(
        path, task_name="SerialLeg-Recovery-v0", sim_dt=0.005, policy_dt=0.02
    )
    monkeypatch.setattr(deployment, "build_serialleg_descriptor", lambda **_: second)
    deployment.attach_serialleg_websim_metadata(
        path, task_name="SerialLeg-Recovery-v0", sim_dt=0.005, policy_dt=0.02
    )

    model = onnx.load(path, load_external_data=False)
    entries = [entry for entry in model.metadata_props if entry.key == deployment.METADATA_KEY]

    assert len(entries) == 1
    assert json.loads(entries[0].value)["marker"] == 2
