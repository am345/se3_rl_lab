# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Strongly validated SerialLeg config derived from canonical URDF and MJCF sources."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

DEFAULT_SERIALLEG_CONTRACT_PATH = Path(__file__).resolve().parent / "serialleg" / "robot_config.yaml"


class SerialLegContractError(ValueError):
    """Raised when the SerialLeg config or its canonical URDF is inconsistent."""


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
class FixedTendonContract:
    name: str
    root_joint: str
    joint_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    force_coefficients: tuple[float, ...]
    lower: float
    upper: float
    source_solref_limit: tuple[float, float]
    source_solimp_limit: tuple[float, float, float, float, float]
    root_gearing: float
    root_force_coefficient: float
    stiffness: float
    damping: float
    limit_stiffness: float
    offset: float
    rest_length: float


@dataclass(frozen=True)
class ActuatorGroupContract:
    name: str
    joint_names: tuple[str, ...]
    policy: bool
    actuated: bool
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
    root_position: tuple[float, float, float]
    root_rotation_wxyz: tuple[float, float, float, float]
    canonical_mjcf: str
    canonical_urdf: str
    runtime_usd: str
    links: tuple[str, ...]
    policy_joint_order: tuple[str, ...]
    tree_joints: Mapping[str, TreeJointContract]
    loop_joints: Mapping[str, LoopJointContract]
    fixed_tendons: Mapping[str, FixedTendonContract]
    actuator_groups: Mapping[str, ActuatorGroupContract]
    usd_importer: Mapping[str, bool]
    usd_gate: UsdGateContract

    @property
    def root_height(self) -> float:
        return self.root_position[2]

    @property
    def default_joint_positions(self) -> dict[str, float]:
        return {name: joint.default_position for name, joint in self.tree_joints.items()}

    @property
    def passive_joint_names(self) -> tuple[str, ...]:
        return tuple(
            joint_name
            for group in self.actuator_groups.values()
            if group.actuated and not group.policy
            for joint_name in group.joint_names
        )

    @property
    def tendon_root_joint_names(self) -> tuple[str, ...]:
        return tuple(
            joint_name
            for group in self.actuator_groups.values()
            if not group.actuated
            for joint_name in group.joint_names
        )


def _expect_keys(table: Mapping[str, Any], required: set[str], context: str) -> None:
    missing = required - set(table)
    unexpected = set(table) - required
    if missing or unexpected:
        raise SerialLegContractError(
            f"{context} keys changed: missing={sorted(missing)} unexpected={sorted(unexpected)}"
        )


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SerialLegContractError(f"{context} must be a mapping")
    return value


def _finite_float(value: Any, context: str, *, non_negative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SerialLegContractError(f"{context} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (non_negative and result < 0.0):
        qualifier = "finite and non-negative" if non_negative else "finite"
        raise SerialLegContractError(f"{context} must be {qualifier}")
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
        raise SerialLegContractError(f"{context} must be a list")
    result = tuple(_string(item, f"{context}[]") for item in value)
    if len(result) != len(set(result)):
        raise SerialLegContractError(f"{context} contains duplicates")
    return result


def _numeric_tuple(value: Any, size: int, context: str) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != size:
        raise SerialLegContractError(f"{context} must contain exactly {size} numbers")
    return tuple(_finite_float(item, f"{context}[]") for item in value)


def _vector3_text(value: str | None, context: str) -> tuple[float, float, float]:
    if value is None:
        raise SerialLegContractError(f"{context} is missing")
    parts = value.split()
    if len(parts) != 3:
        raise SerialLegContractError(f"{context} must contain exactly three numbers")
    return tuple(_finite_float(float(item), f"{context}[]") for item in parts)  # type: ignore[return-value]


def _numeric_text(value: str | None, size: int, context: str) -> tuple[float, ...]:
    if value is None:
        raise SerialLegContractError(f"{context} is missing")
    parts = value.split()
    if len(parts) != size:
        raise SerialLegContractError(f"{context} must contain exactly {size} numbers")
    return tuple(_finite_float(float(item), f"{context}[]") for item in parts)


def _relative_asset_path(value: Any, context: str) -> str:
    result = _string(value, context)
    path = Path(result)
    if path.is_absolute() or ".." in path.parts:
        raise SerialLegContractError(f"{context} must stay relative to the SerialLeg asset directory")
    return result


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, tag: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == tag]


def _single_child(element: ET.Element, tag: str, context: str) -> ET.Element:
    matches = _children(element, tag)
    if len(matches) != 1:
        raise SerialLegContractError(f"{context} must contain exactly one <{tag}>")
    return matches[0]


def _validate_rooted_tree(links: tuple[str, ...], root_link: str, tree_joints: Mapping[str, TreeJointContract]) -> None:
    link_set = set(links)
    if len(tree_joints) != len(links) - 1:
        raise SerialLegContractError("canonical URDF tree joints must contain exactly links-1 edges")
    child_links = [joint.child for joint in tree_joints.values()]
    if len(child_links) != len(set(child_links)) or set(child_links) != link_set - {root_link}:
        raise SerialLegContractError("canonical URDF joints do not form a rooted tree by child ownership")
    children_by_parent: dict[str, list[str]] = {link: [] for link in links}
    for joint in tree_joints.values():
        children_by_parent[joint.parent].append(joint.child)
    reachable = {root_link}
    pending = [root_link]
    while pending:
        parent = pending.pop()
        for child in children_by_parent[parent]:
            if child in reachable:
                raise SerialLegContractError("canonical URDF tree joints contain a cycle")
            reachable.add(child)
            pending.append(child)
    if reachable != link_set:
        raise SerialLegContractError(f"canonical URDF tree is disconnected: {sorted(link_set - reachable)}")


def _load_profiles(raw: Any) -> dict[str, dict[str, float | None]]:
    profiles_raw = _mapping(raw, "joint_profiles")
    if not profiles_raw:
        raise SerialLegContractError("joint_profiles must not be empty")
    profiles: dict[str, dict[str, float | None]] = {}
    required = {"armature", "effort_limit_sim", "stiffness", "damping"}
    optional = {"velocity_limit_sim"}
    for raw_name, raw_profile in profiles_raw.items():
        name = _string(raw_name, "joint_profiles key")
        profile = _mapping(raw_profile, f"joint_profiles.{name}")
        missing = required - set(profile)
        unexpected = set(profile) - required - optional
        if missing or unexpected:
            raise SerialLegContractError(
                f"joint_profiles.{name} keys changed: missing={sorted(missing)} unexpected={sorted(unexpected)}"
            )
        velocity = profile.get("velocity_limit_sim")
        profiles[name] = {
            "armature": _finite_float(profile["armature"], f"joint_profiles.{name}.armature", non_negative=True),
            "effort_limit_sim": _finite_float(
                profile["effort_limit_sim"], f"joint_profiles.{name}.effort_limit_sim", non_negative=True
            ),
            "velocity_limit_sim": None
            if velocity is None
            else _finite_float(velocity, f"joint_profiles.{name}.velocity_limit_sim", non_negative=True),
            "stiffness": _finite_float(profile["stiffness"], f"joint_profiles.{name}.stiffness", non_negative=True),
            "damping": _finite_float(profile["damping"], f"joint_profiles.{name}.damping", non_negative=True),
        }
    return profiles


def _load_groups(
    raw: Any, profiles: Mapping[str, Mapping[str, float | None]]
) -> tuple[dict[str, ActuatorGroupContract], dict[str, str]]:
    groups_raw = _mapping(raw, "joints.groups")
    if set(groups_raw) != {"legs", "wheels", "closed_chain_passive", "tendon_roots"}:
        raise SerialLegContractError("joints.groups must define legs, wheels, closed_chain_passive, and tendon_roots")
    groups: dict[str, ActuatorGroupContract] = {}
    joint_profiles: dict[str, str] = {}
    for raw_name, raw_group in groups_raw.items():
        name = _string(raw_name, "joints.groups key")
        group = _mapping(raw_group, f"joints.groups.{name}")
        role = group.get("role")
        if role not in {"active", "passive", "tendon_root"}:
            raise SerialLegContractError(f"joints.groups.{name}.role is invalid")
        required = {"role", "profile", "joints"}
        optional = {"action_scale"}
        missing = required - set(group)
        unexpected = set(group) - required - optional
        if missing or unexpected:
            raise SerialLegContractError(
                f"joints.groups.{name} keys changed: missing={sorted(missing)} unexpected={sorted(unexpected)}"
            )
        profile_name = _string(group["profile"], f"joints.groups.{name}.profile")
        if profile_name not in profiles:
            raise SerialLegContractError(f"joints.groups.{name} references unknown profile {profile_name!r}")
        joint_names = _string_tuple(group["joints"], f"joints.groups.{name}.joints")
        if not joint_names:
            raise SerialLegContractError(f"joints.groups.{name}.joints must not be empty")
        overlap = set(joint_profiles).intersection(joint_names)
        if overlap:
            raise SerialLegContractError(f"joint groups overlap: {sorted(overlap)}")
        joint_profiles.update({joint_name: profile_name for joint_name in joint_names})
        profile = profiles[profile_name]
        action_scale_raw = group.get("action_scale")
        action_scale = (
            None
            if action_scale_raw is None
            else _finite_float(action_scale_raw, f"joints.groups.{name}.action_scale", non_negative=True)
        )
        policy = role == "active"
        actuated = role != "tendon_root"
        if policy and (profile["velocity_limit_sim"] is None or action_scale is None):
            raise SerialLegContractError(f"active group {name} requires velocity_limit_sim and action_scale")
        if not policy and action_scale is not None:
            raise SerialLegContractError(f"passive group {name} must not define action_scale")
        groups[name] = ActuatorGroupContract(
            name=name,
            joint_names=joint_names,
            policy=policy,
            actuated=actuated,
            effort_limit_sim=float(profile["effort_limit_sim"]),
            velocity_limit_sim=profile["velocity_limit_sim"],
            stiffness=float(profile["stiffness"]),
            damping=float(profile["damping"]),
            action_scale=action_scale,
        )
    return groups, joint_profiles


def _parse_canonical_urdf(
    urdf_path: Path,
    *,
    robot_name: str,
    root_link: str,
    default_positions: Mapping[str, float],
    joint_profile_names: Mapping[str, str],
    profiles: Mapping[str, Mapping[str, float | None]],
    loop_armature: float,
    tendon_root_names: set[str],
) -> tuple[tuple[str, ...], dict[str, TreeJointContract], dict[str, LoopJointContract]]:
    if not urdf_path.is_file():
        raise SerialLegContractError(f"canonical URDF does not exist: {urdf_path}")
    try:
        robot = ET.parse(urdf_path).getroot()
    except ET.ParseError as exc:
        raise SerialLegContractError(f"invalid canonical URDF {urdf_path}: {exc}") from exc
    if _local_name(robot.tag) != "robot" or robot.attrib.get("name") != robot_name:
        raise SerialLegContractError("robot.name must match canonical URDF <robot name>")

    links = tuple(_string(link.attrib.get("name"), "canonical URDF link name") for link in _children(robot, "link"))
    if not links or len(links) != len(set(links)) or root_link not in links:
        raise SerialLegContractError("canonical URDF links are empty, duplicated, or missing robot.root_link")

    tree_joints: dict[str, TreeJointContract] = {}
    for joint in _children(robot, "joint"):
        name = _string(joint.attrib.get("name"), "canonical URDF joint name")
        if name in tree_joints:
            raise SerialLegContractError(f"duplicate canonical URDF joint {name}")
        joint_type = joint.attrib.get("type")
        expected_type = "revolute" if name in tendon_root_names else "continuous"
        if joint_type != expected_type:
            raise SerialLegContractError(f"canonical URDF joint {name} must use type={expected_type}")
        parent = _string(_single_child(joint, "parent", name).attrib.get("link"), f"{name}.parent")
        child = _string(_single_child(joint, "child", name).attrib.get("link"), f"{name}.child")
        if parent not in links or child not in links or parent == child:
            raise SerialLegContractError(f"canonical URDF joint {name} has invalid endpoints")
        if name in tendon_root_names:
            limit = _single_child(joint, "limit", name)
            lower = _finite_float(float(limit.attrib.get("lower", "nan")), f"{name}.limit.lower")
            upper = _finite_float(float(limit.attrib.get("upper", "nan")), f"{name}.limit.upper")
            if not lower < 0.0 < upper:
                raise SerialLegContractError(f"tendon root {name} must have a non-locked range around zero")
        dynamics = _single_child(joint, "dynamics", name)
        damping = _finite_float(
            float(dynamics.attrib.get("damping", "nan")), f"{name}.dynamics.damping", non_negative=True
        )
        friction = _finite_float(
            float(dynamics.attrib.get("friction", "nan")), f"{name}.dynamics.friction", non_negative=True
        )
        if name not in default_positions or name not in joint_profile_names:
            raise SerialLegContractError(f"canonical URDF joint {name} is missing from init_state or joints.groups")
        profile = profiles[joint_profile_names[name]]
        tree_joints[name] = TreeJointContract(
            name=name,
            parent=parent,
            child=child,
            armature=float(profile["armature"]),
            source_damping=damping,
            source_friction=friction,
            default_position=default_positions[name],
        )
    if set(default_positions) != set(tree_joints) or set(joint_profile_names) != set(tree_joints):
        raise SerialLegContractError(
            "init_state.joint_pos and joints.groups must partition canonical URDF joints exactly"
        )
    _validate_rooted_tree(links, root_link, tree_joints)

    loop_joints: dict[str, LoopJointContract] = {}
    for loop in _children(robot, "loop_joint"):
        name = _string(loop.attrib.get("name"), "canonical URDF loop_joint name")
        if name in loop_joints or loop.attrib.get("type") != "spherical":
            raise SerialLegContractError(f"loop joint {name} must be unique and spherical")
        link1 = _single_child(loop, "link1", name)
        link2 = _single_child(loop, "link2", name)
        body0 = _string(link1.attrib.get("link"), f"{name}.link1.link")
        body1 = _string(link2.attrib.get("link"), f"{name}.link2.link")
        if body0 not in links or body1 not in links or body0 == body1:
            raise SerialLegContractError(f"loop joint {name} has invalid endpoints")
        if link1.attrib.get("rpy", "0 0 0") != "0 0 0" or link2.attrib.get("rpy", "0 0 0") != "0 0 0":
            raise SerialLegContractError(f"loop joint {name} currently requires zero local rotations")
        loop_joints[name] = LoopJointContract(
            name=name,
            body0=body0,
            local_pos0=_vector3_text(link1.attrib.get("xyz"), f"{name}.link1.xyz"),
            body1=body1,
            local_pos1=_vector3_text(link2.attrib.get("xyz"), f"{name}.link2.xyz"),
            armature=loop_armature,
        )
    if not loop_joints:
        raise SerialLegContractError("canonical URDF must contain at least one spherical loop_joint")
    return links, tree_joints, loop_joints


def _parse_fixed_tendons(
    mjcf_path: Path,
    *,
    robot_name: str,
    tree_joints: Mapping[str, TreeJointContract],
    policy_joint_order: tuple[str, ...],
    tendon_root_names: tuple[str, ...],
    raw: Any,
) -> dict[str, FixedTendonContract]:
    if not mjcf_path.is_file():
        raise SerialLegContractError(f"canonical MJCF does not exist: {mjcf_path}")
    try:
        mujoco = ET.parse(mjcf_path).getroot()
    except ET.ParseError as exc:
        raise SerialLegContractError(f"invalid canonical MJCF {mjcf_path}: {exc}") from exc
    if _local_name(mujoco.tag) != "mujoco" or mujoco.attrib.get("model") != robot_name:
        raise SerialLegContractError("robot.name must match canonical MJCF <mujoco model>")
    tendon_section = _single_child(mujoco, "tendon", "canonical MJCF")
    fixed_elements = _children(tendon_section, "fixed")
    if not fixed_elements:
        raise SerialLegContractError("canonical MJCF must define fixed tendons")

    cfg = _mapping(raw, "closed_chain.fixed_tendon")
    _expect_keys(
        cfg,
        {
            "root_joints",
            "root_gearing",
            "root_force_coefficient",
            "stiffness",
            "damping",
            "limit_stiffness",
            "offset",
            "rest_length",
        },
        "closed_chain.fixed_tendon",
    )
    root_joints_raw = _mapping(cfg["root_joints"], "closed_chain.fixed_tendon.root_joints")
    root_joints = {
        _string(name, "fixed tendon name"): _string(joint, f"fixed tendon {name} root")
        for name, joint in root_joints_raw.items()
    }
    if set(root_joints.values()) != set(tendon_root_names) or len(root_joints) != len(tendon_root_names):
        raise SerialLegContractError("fixed tendon roots must partition tendon_root joints exactly")
    parameters = {
        key: _finite_float(cfg[key], f"closed_chain.fixed_tendon.{key}", non_negative=True)
        for key in (
            "root_gearing",
            "root_force_coefficient",
            "stiffness",
            "damping",
            "limit_stiffness",
            "offset",
            "rest_length",
        )
    }
    if parameters["root_gearing"] != 0.0 or parameters["root_force_coefficient"] != 0.0:
        raise SerialLegContractError("structural fixed-tendon roots require zero gearing and force coefficient")

    policy_set = set(policy_joint_order)
    covered: list[str] = []
    tendons: dict[str, FixedTendonContract] = {}
    for fixed in fixed_elements:
        name = _string(fixed.attrib.get("name"), "canonical MJCF fixed tendon name")
        if name in tendons or name not in root_joints or fixed.attrib.get("limited") != "true":
            raise SerialLegContractError(f"fixed tendon {name!r} is duplicated, unmapped, or not limited")
        lower, upper = _numeric_text(fixed.attrib.get("range"), 2, f"{name}.range")
        if not lower < upper:
            raise SerialLegContractError(f"fixed tendon {name} must have lower < upper")
        joint_names: list[str] = []
        coefficients: list[float] = []
        for joint in _children(fixed, "joint"):
            joint_name = _string(joint.attrib.get("joint"), f"{name}.joint")
            coefficient = _finite_float(float(joint.attrib.get("coef", "nan")), f"{name}.{joint_name}.coef")
            if joint_name in joint_names or coefficient == 0.0 or joint_name not in policy_set:
                raise SerialLegContractError(f"fixed tendon {name} has an invalid policy joint axis")
            joint_names.append(joint_name)
            coefficients.append(coefficient)
        if len(joint_names) != 2:
            raise SerialLegContractError(f"fixed tendon {name} must contain exactly two policy axes")
        root_joint = root_joints[name]
        mount_link = tree_joints[root_joint].child
        if any(tree_joints[joint_name].parent != mount_link for joint_name in joint_names):
            raise SerialLegContractError(f"fixed tendon {name} axes are not direct children of root mount")
        default_length = sum(
            coefficient * tree_joints[joint_name].default_position
            for joint_name, coefficient in zip(joint_names, coefficients, strict=True)
        )
        if not lower <= default_length <= upper:
            raise SerialLegContractError(f"standing state violates fixed tendon {name}")
        covered.extend(joint_names)
        tendons[name] = FixedTendonContract(
            name=name,
            root_joint=root_joint,
            joint_names=tuple(joint_names),
            coefficients=tuple(coefficients),
            force_coefficients=tuple(coefficients),
            lower=lower,
            upper=upper,
            source_solref_limit=_numeric_text(fixed.attrib.get("solreflimit"), 2, f"{name}.solreflimit"),  # type: ignore[arg-type]
            source_solimp_limit=_numeric_text(fixed.attrib.get("solimplimit"), 5, f"{name}.solimplimit"),  # type: ignore[arg-type]
            root_gearing=parameters["root_gearing"],
            root_force_coefficient=parameters["root_force_coefficient"],
            stiffness=parameters["stiffness"],
            damping=parameters["damping"],
            limit_stiffness=parameters["limit_stiffness"],
            offset=parameters["offset"],
            rest_length=parameters["rest_length"],
        )
    if set(tendons) != set(root_joints) or set(covered) != set(policy_joint_order[:4]):
        raise SerialLegContractError("fixed tendons must partition the four policy leg joints exactly")
    return tendons


def _load_usd(raw: Any) -> tuple[dict[str, bool], UsdGateContract]:
    usd = _mapping(raw, "usd")
    _expect_keys(usd, {"importer", "gate"}, "usd")
    importer = _mapping(usd["importer"], "usd.importer")
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
    _expect_keys(importer, importer_keys, "usd.importer")
    if any(not isinstance(value, bool) for value in importer.values()):
        raise SerialLegContractError("all usd.importer values must be boolean")
    if importer["replace_cylinders_with_capsules"]:
        raise SerialLegContractError("SerialLeg wheel cylinders must not be replaced by capsules")
    if importer["collision_from_visuals"]:
        raise SerialLegContractError("collision_from_visuals must remain disabled")

    gate = _mapping(usd["gate"], "usd.gate")
    gate_keys = {
        "expected_total_mass",
        "expected_visual_count",
        "expected_collision_mesh_count",
        "expected_collision_face_count",
        "expected_collision_point_index_count",
        "max_collision_only_usd_bytes",
    }
    _expect_keys(gate, gate_keys, "usd.gate")
    usd_gate = UsdGateContract(
        expected_total_mass=_finite_float(
            gate["expected_total_mass"], "usd.gate.expected_total_mass", non_negative=True
        ),
        expected_visual_count=_nonnegative_int(gate["expected_visual_count"], "usd.gate.expected_visual_count"),
        expected_collision_mesh_count=_positive_int(
            gate["expected_collision_mesh_count"], "usd.gate.expected_collision_mesh_count"
        ),
        expected_collision_face_count=_positive_int(
            gate["expected_collision_face_count"], "usd.gate.expected_collision_face_count"
        ),
        expected_collision_point_index_count=_positive_int(
            gate["expected_collision_point_index_count"], "usd.gate.expected_collision_point_index_count"
        ),
        max_collision_only_usd_bytes=_positive_int(
            gate["max_collision_only_usd_bytes"], "usd.gate.max_collision_only_usd_bytes"
        ),
    )
    return dict(importer), usd_gate


def load_serialleg_contract(path: Path = DEFAULT_SERIALLEG_CONTRACT_PATH) -> SerialLegContract:
    """Load robot_config.yaml and derive strongly validated topology from its canonical URDF."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SerialLegContractError(f"failed to load SerialLeg config {path}: {exc}") from exc
    raw = _mapping(raw, "robot_config")
    _expect_keys(
        raw,
        {"schema_version", "robot", "init_state", "joints", "joint_profiles", "closed_chain", "usd"},
        "robot_config",
    )
    schema_version = _positive_int(raw["schema_version"], "schema_version")
    if schema_version != 3:
        raise SerialLegContractError(f"unsupported schema_version {schema_version}")

    robot = _mapping(raw["robot"], "robot")
    _expect_keys(robot, {"name", "root_link", "canonical_mjcf", "canonical_urdf", "runtime_usd"}, "robot")
    robot_name = _string(robot["name"], "robot.name")
    root_link = _string(robot["root_link"], "robot.root_link")
    canonical_mjcf = _relative_asset_path(robot["canonical_mjcf"], "robot.canonical_mjcf")
    canonical_urdf = _relative_asset_path(robot["canonical_urdf"], "robot.canonical_urdf")
    runtime_usd = _relative_asset_path(robot["runtime_usd"], "robot.runtime_usd")

    init_state = _mapping(raw["init_state"], "init_state")
    _expect_keys(init_state, {"root_pos", "root_rot", "joint_pos"}, "init_state")
    root_position = _numeric_tuple(init_state["root_pos"], 3, "init_state.root_pos")
    root_rotation_xyzw = _numeric_tuple(init_state["root_rot"], 4, "init_state.root_rot")
    norm = math.sqrt(sum(value * value for value in root_rotation_xyzw))
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1.0e-6):
        raise SerialLegContractError("init_state.root_rot must be a unit quaternion")
    root_rotation_wxyz = (
        root_rotation_xyzw[3],
        root_rotation_xyzw[0],
        root_rotation_xyzw[1],
        root_rotation_xyzw[2],
    )
    joint_pos_raw = _mapping(init_state["joint_pos"], "init_state.joint_pos")
    default_positions = {
        _string(name, "init_state.joint_pos key"): _finite_float(value, f"init_state.joint_pos.{name}")
        for name, value in joint_pos_raw.items()
    }

    joints = _mapping(raw["joints"], "joints")
    _expect_keys(joints, {"policy_order", "groups"}, "joints")
    profiles = _load_profiles(raw["joint_profiles"])
    actuator_groups, joint_profile_names = _load_groups(joints["groups"], profiles)
    policy_joint_order = _string_tuple(joints["policy_order"], "joints.policy_order")
    policy_joint_set = {
        joint_name for group in actuator_groups.values() if group.policy for joint_name in group.joint_names
    }
    if set(policy_joint_order) != policy_joint_set:
        raise SerialLegContractError("joints.policy_order does not match active joint groups")

    closed_chain = _mapping(raw["closed_chain"], "closed_chain")
    _expect_keys(closed_chain, {"loop_armature", "fixed_tendon"}, "closed_chain")
    loop_armature = _finite_float(closed_chain["loop_armature"], "closed_chain.loop_armature", non_negative=True)
    tendon_root_names = tuple(
        joint_name for group in actuator_groups.values() if not group.actuated for joint_name in group.joint_names
    )
    urdf_path = path.parent / canonical_urdf
    links, tree_joints, loop_joints = _parse_canonical_urdf(
        urdf_path,
        robot_name=robot_name,
        root_link=root_link,
        default_positions=default_positions,
        joint_profile_names=joint_profile_names,
        profiles=profiles,
        loop_armature=loop_armature,
        tendon_root_names=set(tendon_root_names),
    )
    fixed_tendons = _parse_fixed_tendons(
        path.parent / canonical_mjcf,
        robot_name=robot_name,
        tree_joints=tree_joints,
        policy_joint_order=policy_joint_order,
        tendon_root_names=tendon_root_names,
        raw=closed_chain["fixed_tendon"],
    )
    usd_importer, usd_gate = _load_usd(raw["usd"])
    return SerialLegContract(
        schema_version=schema_version,
        robot_name=robot_name,
        root_link=root_link,
        root_position=root_position,  # type: ignore[arg-type]
        root_rotation_wxyz=root_rotation_wxyz,
        canonical_mjcf=canonical_mjcf,
        canonical_urdf=canonical_urdf,
        runtime_usd=runtime_usd,
        links=links,
        policy_joint_order=policy_joint_order,
        tree_joints=MappingProxyType(tree_joints),
        loop_joints=MappingProxyType(loop_joints),
        fixed_tendons=MappingProxyType(fixed_tendons),
        actuator_groups=MappingProxyType(actuator_groups),
        usd_importer=MappingProxyType(usd_importer),
        usd_gate=usd_gate,
    )


SERIALLEG_CONTRACT = load_serialleg_contract()
