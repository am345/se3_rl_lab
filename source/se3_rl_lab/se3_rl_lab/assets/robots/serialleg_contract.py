# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Validated declarative contract shared by SerialLeg asset and conversion code."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import tomllib

DEFAULT_SERIALLEG_CONTRACT_PATH = Path(__file__).resolve().parent / "serialleg" / "serialleg_contract.toml"


class SerialLegContractError(ValueError):
    """Raised when the SerialLeg contract is incomplete or inconsistent."""


@dataclass(frozen=True)
class TreeJointContract:
    name: str
    parent: str
    child: str
    armature: float
    source_damping: float
    source_friction: float
    default_position: float


@dataclass(frozen=True)
class LoopJointContract:
    name: str
    body0: str
    local_pos0: tuple[float, float, float]
    body1: str
    local_pos1: tuple[float, float, float]
    armature: float


@dataclass(frozen=True)
class ActuatorGroupContract:
    name: str
    joint_names: tuple[str, ...]
    policy: bool
    effort_limit_sim: float
    velocity_limit_sim: float | None
    stiffness: float
    damping: float
    action_scale: float | None


@dataclass(frozen=True)
class UsdGateContract:
    expected_total_mass: float
    expected_visual_count: int
    expected_collision_mesh_count: int
    expected_collision_face_count: int
    expected_collision_point_index_count: int
    max_collision_only_usd_bytes: int


@dataclass(frozen=True)
class SerialLegContract:
    schema_version: int
    robot_name: str
    root_link: str
    root_height: float
    canonical_urdf: str
    runtime_usd: str
    links: tuple[str, ...]
    policy_joint_order: tuple[str, ...]
    tree_joints: Mapping[str, TreeJointContract]
    loop_joints: Mapping[str, LoopJointContract]
    actuator_groups: Mapping[str, ActuatorGroupContract]
    usd_importer: Mapping[str, bool]
    usd_gate: UsdGateContract

    @property
    def default_joint_positions(self) -> dict[str, float]:
        return {name: joint.default_position for name, joint in self.tree_joints.items()}

    @property
    def passive_joint_names(self) -> tuple[str, ...]:
        return tuple(
            joint_name
            for group in self.actuator_groups.values()
            if not group.policy
            for joint_name in group.joint_names
        )


def _expect_keys(table: Mapping[str, Any], required: set[str], context: str) -> None:
    missing = required - set(table)
    unexpected = set(table) - required
    if missing or unexpected:
        raise SerialLegContractError(
            f"{context} keys changed: missing={sorted(missing)} unexpected={sorted(unexpected)}"
        )


def _finite_float(value: Any, context: str, *, non_negative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SerialLegContractError(f"{context} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (non_negative and result < 0.0):
        raise SerialLegContractError(f"{context} must be finite and {'non-negative' if non_negative else 'valid'}")
    return result


def _positive_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SerialLegContractError(f"{context} must be a positive integer")
    return value


def _nonnegative_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SerialLegContractError(f"{context} must be a non-negative integer")
    return value


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SerialLegContractError(f"{context} must be a non-empty string")
    return value


def _string_tuple(value: Any, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SerialLegContractError(f"{context} must be an array")
    result = tuple(_string(item, f"{context}[]") for item in value)
    if len(result) != len(set(result)):
        raise SerialLegContractError(f"{context} contains duplicates")
    return result


def _vector3(value: Any, context: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise SerialLegContractError(f"{context} must contain exactly three numbers")
    return tuple(_finite_float(item, f"{context}[]") for item in value)  # type: ignore[return-value]


def _relative_asset_path(value: Any, context: str) -> str:
    result = _string(value, context)
    path = Path(result)
    if path.is_absolute() or ".." in path.parts:
        raise SerialLegContractError(f"{context} must stay relative to the SerialLeg asset directory")
    return result


def _load_tree_joints(raw: Any, links: set[str]) -> dict[str, TreeJointContract]:
    if not isinstance(raw, dict) or not raw:
        raise SerialLegContractError("tree_joints must be a non-empty table")
    result: dict[str, TreeJointContract] = {}
    required = {
        "parent",
        "child",
        "armature",
        "source_damping",
        "source_friction",
        "default_position",
    }
    for name, value in raw.items():
        joint_name = _string(name, "tree_joints key")
        if not isinstance(value, dict):
            raise SerialLegContractError(f"tree_joints.{joint_name} must be a table")
        _expect_keys(value, required, f"tree_joints.{joint_name}")
        parent = _string(value["parent"], f"tree_joints.{joint_name}.parent")
        child = _string(value["child"], f"tree_joints.{joint_name}.child")
        if parent not in links or child not in links or parent == child:
            raise SerialLegContractError(f"tree_joints.{joint_name} has invalid link endpoints")
        result[joint_name] = TreeJointContract(
            name=joint_name,
            parent=parent,
            child=child,
            armature=_finite_float(value["armature"], f"tree_joints.{joint_name}.armature", non_negative=True),
            source_damping=_finite_float(
                value["source_damping"], f"tree_joints.{joint_name}.source_damping", non_negative=True
            ),
            source_friction=_finite_float(
                value["source_friction"], f"tree_joints.{joint_name}.source_friction", non_negative=True
            ),
            default_position=_finite_float(value["default_position"], f"tree_joints.{joint_name}.default_position"),
        )
    return result


def _load_loop_joints(raw: Any, links: set[str]) -> dict[str, LoopJointContract]:
    if not isinstance(raw, list) or not raw:
        raise SerialLegContractError("loop_joints must be a non-empty array of tables")
    result: dict[str, LoopJointContract] = {}
    required = {"name", "body0", "local_pos0", "body1", "local_pos1", "armature"}
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise SerialLegContractError(f"loop_joints[{index}] must be a table")
        _expect_keys(value, required, f"loop_joints[{index}]")
        name = _string(value["name"], f"loop_joints[{index}].name")
        if name in result:
            raise SerialLegContractError(f"duplicate loop joint {name}")
        body0 = _string(value["body0"], f"loop_joints[{index}].body0")
        body1 = _string(value["body1"], f"loop_joints[{index}].body1")
        if body0 not in links or body1 not in links or body0 == body1:
            raise SerialLegContractError(f"loop_joints[{index}] has invalid body endpoints")
        result[name] = LoopJointContract(
            name=name,
            body0=body0,
            local_pos0=_vector3(value["local_pos0"], f"loop_joints[{index}].local_pos0"),
            body1=body1,
            local_pos1=_vector3(value["local_pos1"], f"loop_joints[{index}].local_pos1"),
            armature=_finite_float(value["armature"], f"loop_joints[{index}].armature", non_negative=True),
        )
    return result


def _load_actuator_groups(raw: Any, tree_joint_names: set[str]) -> dict[str, ActuatorGroupContract]:
    if not isinstance(raw, dict) or not raw:
        raise SerialLegContractError("actuator_groups must be a non-empty table")
    result: dict[str, ActuatorGroupContract] = {}
    assigned: list[str] = []
    required = {"joint_names", "policy", "effort_limit_sim", "stiffness", "damping"}
    optional = {"velocity_limit_sim", "action_scale"}
    for name, value in raw.items():
        group_name = _string(name, "actuator_groups key")
        if not isinstance(value, dict):
            raise SerialLegContractError(f"actuator_groups.{group_name} must be a table")
        missing = required - set(value)
        unexpected = set(value) - required - optional
        if missing or unexpected:
            raise SerialLegContractError(
                f"actuator_groups.{group_name} keys changed: missing={sorted(missing)} unexpected={sorted(unexpected)}"
            )
        joint_names = _string_tuple(value["joint_names"], f"actuator_groups.{group_name}.joint_names")
        if not joint_names or not set(joint_names) <= tree_joint_names:
            raise SerialLegContractError(f"actuator_groups.{group_name} has unknown or empty joint_names")
        assigned.extend(joint_names)
        policy = value["policy"]
        if not isinstance(policy, bool):
            raise SerialLegContractError(f"actuator_groups.{group_name}.policy must be boolean")
        velocity = value.get("velocity_limit_sim")
        action_scale = value.get("action_scale")
        result[group_name] = ActuatorGroupContract(
            name=group_name,
            joint_names=joint_names,
            policy=policy,
            effort_limit_sim=_finite_float(
                value["effort_limit_sim"], f"actuator_groups.{group_name}.effort_limit_sim", non_negative=True
            ),
            velocity_limit_sim=None
            if velocity is None
            else _finite_float(velocity, f"actuator_groups.{group_name}.velocity_limit_sim", non_negative=True),
            stiffness=_finite_float(value["stiffness"], f"actuator_groups.{group_name}.stiffness", non_negative=True),
            damping=_finite_float(value["damping"], f"actuator_groups.{group_name}.damping", non_negative=True),
            action_scale=None
            if action_scale is None
            else _finite_float(action_scale, f"actuator_groups.{group_name}.action_scale", non_negative=True),
        )
        if policy and (velocity is None or action_scale is None):
            raise SerialLegContractError(f"policy actuator group {group_name} requires velocity_limit_sim/action_scale")
        if not policy and action_scale is not None:
            raise SerialLegContractError(f"passive actuator group {group_name} must not define action_scale")
    if len(assigned) != len(set(assigned)) or set(assigned) != tree_joint_names:
        raise SerialLegContractError("actuator_groups must partition the tree joints exactly once")
    return result


def load_serialleg_contract(path: Path = DEFAULT_SERIALLEG_CONTRACT_PATH) -> SerialLegContract:
    """Load and strongly validate the canonical SerialLeg TOML contract."""
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    top_level_keys = {
        "schema_version",
        "robot_name",
        "root_link",
        "root_height",
        "canonical_urdf",
        "runtime_usd",
        "links",
        "policy_joint_order",
        "usd_importer",
        "usd_gate",
        "actuator_groups",
        "tree_joints",
        "loop_joints",
    }
    _expect_keys(raw, top_level_keys, "contract")
    schema_version = _positive_int(raw["schema_version"], "schema_version")
    if schema_version != 1:
        raise SerialLegContractError(f"unsupported schema_version {schema_version}")
    links = _string_tuple(raw["links"], "links")
    link_set = set(links)
    root_link = _string(raw["root_link"], "root_link")
    if root_link not in link_set:
        raise SerialLegContractError("root_link is not present in links")
    tree_joints = _load_tree_joints(raw["tree_joints"], link_set)
    if len(tree_joints) != len(links) - 1:
        raise SerialLegContractError("tree_joints must contain exactly links-1 edges")
    child_links = [joint.child for joint in tree_joints.values()]
    if len(child_links) != len(set(child_links)) or set(child_links) != link_set - {root_link}:
        raise SerialLegContractError("tree_joints do not form a rooted tree by child ownership")
    children_by_parent: dict[str, list[str]] = {link: [] for link in links}
    for joint in tree_joints.values():
        children_by_parent[joint.parent].append(joint.child)
    reachable = {root_link}
    pending = [root_link]
    while pending:
        parent = pending.pop()
        for child in children_by_parent[parent]:
            if child in reachable:
                raise SerialLegContractError("tree_joints contain a cycle")
            reachable.add(child)
            pending.append(child)
    if reachable != link_set:
        raise SerialLegContractError(f"tree_joints are disconnected from root_link: {sorted(link_set - reachable)}")
    loop_joints = _load_loop_joints(raw["loop_joints"], link_set)
    actuator_groups = _load_actuator_groups(raw["actuator_groups"], set(tree_joints))
    policy_joint_order = _string_tuple(raw["policy_joint_order"], "policy_joint_order")
    policy_joint_set = {
        joint_name for group in actuator_groups.values() if group.policy for joint_name in group.joint_names
    }
    if set(policy_joint_order) != policy_joint_set:
        raise SerialLegContractError("policy_joint_order does not match policy actuator groups")

    importer = raw["usd_importer"]
    importer_keys = {
        "fix_base",
        "merge_fixed_joints",
        "import_inertia_tensor",
        "make_default_prim",
        "create_physics_scene",
        "self_collision",
        "collision_from_visuals",
        "replace_cylinders_with_capsules",
    }
    if not isinstance(importer, dict):
        raise SerialLegContractError("usd_importer must be a table")
    _expect_keys(importer, importer_keys, "usd_importer")
    if any(not isinstance(value, bool) for value in importer.values()):
        raise SerialLegContractError("all usd_importer values must be boolean")
    if importer["replace_cylinders_with_capsules"]:
        raise SerialLegContractError("SerialLeg wheel cylinders must not be replaced by capsules")
    if importer["collision_from_visuals"]:
        raise SerialLegContractError("collision_from_visuals must remain disabled")

    gate = raw["usd_gate"]
    gate_keys = {
        "expected_total_mass",
        "expected_visual_count",
        "expected_collision_mesh_count",
        "expected_collision_face_count",
        "expected_collision_point_index_count",
        "max_collision_only_usd_bytes",
    }
    if not isinstance(gate, dict):
        raise SerialLegContractError("usd_gate must be a table")
    _expect_keys(gate, gate_keys, "usd_gate")
    usd_gate = UsdGateContract(
        expected_total_mass=_finite_float(
            gate["expected_total_mass"], "usd_gate.expected_total_mass", non_negative=True
        ),
        expected_visual_count=_nonnegative_int(gate["expected_visual_count"], "usd_gate.expected_visual_count"),
        expected_collision_mesh_count=_positive_int(
            gate["expected_collision_mesh_count"], "usd_gate.expected_collision_mesh_count"
        ),
        expected_collision_face_count=_positive_int(
            gate["expected_collision_face_count"], "usd_gate.expected_collision_face_count"
        ),
        expected_collision_point_index_count=_positive_int(
            gate["expected_collision_point_index_count"], "usd_gate.expected_collision_point_index_count"
        ),
        max_collision_only_usd_bytes=_positive_int(
            gate["max_collision_only_usd_bytes"], "usd_gate.max_collision_only_usd_bytes"
        ),
    )
    return SerialLegContract(
        schema_version=schema_version,
        robot_name=_string(raw["robot_name"], "robot_name"),
        root_link=root_link,
        root_height=_finite_float(raw["root_height"], "root_height", non_negative=True),
        canonical_urdf=_relative_asset_path(raw["canonical_urdf"], "canonical_urdf"),
        runtime_usd=_relative_asset_path(raw["runtime_usd"], "runtime_usd"),
        links=links,
        policy_joint_order=policy_joint_order,
        tree_joints=MappingProxyType(tree_joints),
        loop_joints=MappingProxyType(loop_joints),
        actuator_groups=MappingProxyType(actuator_groups),
        usd_importer=MappingProxyType(dict(importer)),
        usd_gate=usd_gate,
    )


SERIALLEG_CONTRACT = load_serialleg_contract()
