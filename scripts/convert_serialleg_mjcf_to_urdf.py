#!/usr/bin/env python3
"""Convert the collision-only canonical SerialLeg MJCF tree and loop closures to URDF.

The canonical MJCF already stores the physical rigid bodies and hinge joints as
a tree.  This converter inserts one narrow-range virtual revolute/mount pair per
side so each pair of sibling leg roots has a legal common-ancestor joint for a
future PhysX fixed tendon.  Its two ``equality/connect`` elements are converted
to Isaac Sim's spherical ``loop_joint`` URDF extension.  The converter does not
yet author PhysX tendon schemas or translate other MJCF-only solver semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/mjcf"
    / "serialleg_closed_chain_complex_collision.xml"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/urdf"
    / "serialleg_closed_chain_complex_collision.urdf"
)

EXPECTED_LINK_NAMES = {
    "base_link",
    "lf0_Link",
    "lf1_Link",
    "l_wheel_Link",
    "l_drive_bar_Link",
    "l_coupler_Link",
    "rf0_Link",
    "rf1_Link",
    "r_wheel_Link",
    "r_drive_bar_Link",
    "r_coupler_Link",
}
EXPECTED_JOINT_NAMES = (
    "lf0_Joint",
    "lf1_Joint",
    "l_wheel_Joint",
    "l_drive_bar_Joint",
    "l_coupler_Joint",
    "rf0_Joint",
    "rf1_Joint",
    "r_wheel_Joint",
    "r_drive_bar_Joint",
    "r_coupler_Joint",
)
EXPECTED_LOOP_NAMES = {
    "l_coupler_to_lf_calf",
    "r_coupler_to_rf_calf",
}
EXPECTED_FIXED_TENDONS = {
    "l_active_rod_angle": {
        "axes": (("lf0_Joint", 1.0), ("l_drive_bar_Joint", -1.0)),
        "range": (0.0, 1.509535270050),
        "solref": (0.010, 1.0),
        "solimp": (0.99, 0.999, 0.00001, 0.5, 2.0),
    },
    "r_active_rod_angle": {
        "axes": (("r_drive_bar_Joint", 1.0), ("rf0_Joint", -1.0)),
        "range": (0.0, 1.509535270050),
        "solref": (0.010, 1.0),
        "solimp": (0.99, 0.999, 0.00001, 0.5, 2.0),
    },
}
VIRTUAL_MOUNTS = (
    {
        "joint": "l_tendon_root_Joint",
        "link": "l_tendon_mount_Link",
        "axis": (0.0, 1.0, 0.0),
        "children": ("lf0_Joint", "l_drive_bar_Joint"),
        "tendon": "l_active_rod_angle",
    },
    {
        "joint": "r_tendon_root_Joint",
        "link": "r_tendon_mount_Link",
        "axis": (0.0, -1.0, 0.0),
        "children": ("rf0_Joint", "r_drive_bar_Joint"),
        "tendon": "r_active_rod_angle",
    },
)
VIRTUAL_LINK_NAMES = {str(spec["link"]) for spec in VIRTUAL_MOUNTS}
VIRTUAL_JOINT_NAMES = {str(spec["joint"]) for spec in VIRTUAL_MOUNTS}
GENERATED_LINK_NAMES = EXPECTED_LINK_NAMES | VIRTUAL_LINK_NAMES
VIRTUAL_MOUNT_MASS = 1.0e-4
VIRTUAL_MOUNT_INERTIA = 1.0e-7
VIRTUAL_JOINT_LOWER = -1.0e-4
VIRTUAL_JOINT_UPPER = 1.0e-4
VIRTUAL_JOINT_EFFORT = 40.0
VIRTUAL_JOINT_VELOCITY = 0.1
VIRTUAL_JOINT_DAMPING = 10.0
EXPECTED_TOTAL_MASS = 12.72874558
EXPECTED_VISUAL_COUNT = 0
EXPECTED_COLLISION_COUNT = 56
EXPECTED_MESH_COUNT = 54
IDENTITY_RPY = (0.0, 0.0, 0.0)

Vector3: TypeAlias = tuple[float, float, float]
Matrix3: TypeAlias = tuple[Vector3, Vector3, Vector3]
Transform: TypeAlias = tuple[Matrix3, Vector3]


class ConversionError(ValueError):
    """Raised when the canonical source no longer matches supported semantics."""


@dataclass(frozen=True)
class BodyRecord:
    """Canonical MJCF body plus the URDF joint-frame rebase metadata."""

    element: ET.Element
    name: str
    parent_name: str | None
    body_position: Vector3
    joint: ET.Element | None
    joint_position: Vector3
    joint_origin: Vector3


@dataclass(frozen=True)
class LoopRecord:
    """A site-based MJCF equality/connect expressed in URDF link frames."""

    name: str
    link1: str
    xyz1: Vector3
    link2: str
    xyz2: Vector3


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Canonical closed-chain MJCF")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Generated URDF path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that the existing output is byte-for-byte current; do not write it",
    )
    return parser.parse_args()


def _vector(text: str | None, *, default: Vector3 = (0.0, 0.0, 0.0)) -> Vector3:
    if text is None:
        return default
    values = tuple(float(value) for value in text.split())
    if len(values) != 3:
        raise ConversionError(f"expected a 3-vector, got {text!r}")
    return values  # type: ignore[return-value]


def _numbers(text: str | None, size: int, context: str) -> tuple[float, ...]:
    if text is None:
        raise ConversionError(f"{context} is missing")
    values = tuple(float(value) for value in text.split())
    if len(values) != size or not all(math.isfinite(value) for value in values):
        raise ConversionError(f"{context} must contain {size} finite numbers")
    return values


def _subtract(lhs: Vector3, rhs: Vector3) -> Vector3:
    return lhs[0] - rhs[0], lhs[1] - rhs[1], lhs[2] - rhs[2]


def _add(lhs: Vector3, rhs: Vector3) -> Vector3:
    return lhs[0] + rhs[0], lhs[1] + rhs[1], lhs[2] + rhs[2]


def _format_number(value: float) -> str:
    if abs(value) < 5.0e-16:
        value = 0.0
    return f"{value:.15g}"


def _format_vector(values: Vector3) -> str:
    return " ".join(_format_number(value) for value in values)


def _require_identity_orientation(element: ET.Element, context: str) -> None:
    for attribute in ("quat", "euler", "axisangle", "xyaxes", "zaxis"):
        if attribute in element.attrib:
            raise ConversionError(f"{context} has unsupported orientation attribute {attribute!r}")


def _origin(parent: ET.Element, xyz: Vector3, rpy: Vector3 = IDENTITY_RPY) -> ET.Element:
    return ET.SubElement(parent, "origin", {"xyz": _format_vector(xyz), "rpy": _format_vector(rpy)})


def _identity_matrix() -> Matrix3:
    return (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


def _matrix_vector(matrix: Matrix3, vector: Vector3) -> Vector3:
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _matrix_multiply(lhs: Matrix3, rhs: Matrix3) -> Matrix3:
    return tuple(
        tuple(sum(lhs[row][inner] * rhs[inner][column] for inner in range(3)) for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _matrix_add(lhs: Matrix3, rhs: Matrix3) -> Matrix3:
    return tuple(tuple(lhs[row][column] + rhs[row][column] for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _matrix_subtract(lhs: Matrix3, rhs: Matrix3) -> Matrix3:
    return tuple(tuple(lhs[row][column] - rhs[row][column] for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _matrix_scale(matrix: Matrix3, scalar: float) -> Matrix3:
    return tuple(tuple(matrix[row][column] * scalar for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _outer(vector: Vector3) -> Matrix3:
    return tuple(tuple(vector[row] * vector[column] for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _parallel_axis(mass: float, displacement: Vector3) -> Matrix3:
    squared_distance = sum(value * value for value in displacement)
    return _matrix_scale(
        _matrix_subtract(_matrix_scale(_identity_matrix(), squared_distance), _outer(displacement)),
        mass,
    )


def _full_inertia_matrix(values: tuple[float, ...]) -> Matrix3:
    if len(values) != 6:
        raise ConversionError("full inertia must contain six values")
    ixx, iyy, izz, ixy, ixz, iyz = values
    return (ixx, ixy, ixz), (ixy, iyy, iyz), (ixz, iyz, izz)


def _inertia_attributes(matrix: Matrix3) -> dict[str, str]:
    return {
        "ixx": _format_number(matrix[0][0]),
        "ixy": _format_number(matrix[0][1]),
        "ixz": _format_number(matrix[0][2]),
        "iyy": _format_number(matrix[1][1]),
        "iyz": _format_number(matrix[1][2]),
        "izz": _format_number(matrix[2][2]),
    }


def _rotation(axis: Vector3, angle: float) -> Matrix3:
    norm = math.sqrt(sum(component * component for component in axis))
    if norm <= 0.0:
        raise ConversionError("joint axis must be non-zero")
    x, y, z = (component / norm for component in axis)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    complement = 1.0 - cosine
    return (
        (
            cosine + x * x * complement,
            x * y * complement - z * sine,
            x * z * complement + y * sine,
        ),
        (
            y * x * complement + z * sine,
            cosine + y * y * complement,
            y * z * complement - x * sine,
        ),
        (
            z * x * complement - y * sine,
            z * y * complement + x * sine,
            cosine + z * z * complement,
        ),
    )


def _compose(lhs: Transform, rhs: Transform) -> Transform:
    lhs_rotation, lhs_translation = lhs
    rhs_rotation, rhs_translation = rhs
    return (
        _matrix_multiply(lhs_rotation, rhs_rotation),
        _add(lhs_translation, _matrix_vector(lhs_rotation, rhs_translation)),
    )


def _translation(vector: Vector3) -> Transform:
    return _identity_matrix(), vector


def _rotation_transform(axis: Vector3, angle: float) -> Transform:
    return _rotation(axis, angle), (0.0, 0.0, 0.0)


def _transform_point(transform: Transform, point: Vector3) -> Vector3:
    rotation, translation = transform
    return _add(translation, _matrix_vector(rotation, point))


def _distance(lhs: Vector3, rhs: Vector3) -> float:
    return math.sqrt(sum((lhs[index] - rhs[index]) ** 2 for index in range(3)))


def _require_vector_close(actual: Vector3, expected: Vector3, context: str, *, tolerance: float = 1.0e-12) -> None:
    if _distance(actual, expected) > tolerance:
        raise ConversionError(f"{context} mismatch: actual={actual}, expected={expected}")


def _body_records(root_body: ET.Element) -> list[BodyRecord]:
    records: list[BodyRecord] = []

    def visit(body: ET.Element, parent: BodyRecord | None) -> None:
        name = body.get("name")
        if not name:
            raise ConversionError("every MJCF body must have a name")
        _require_identity_orientation(body, f"body {name}")
        body_position = _vector(body.get("pos"))
        joints = body.findall("joint")

        if parent is None:
            if joints or len(body.findall("freejoint")) != 1:
                raise ConversionError("root body must have exactly one freejoint and no regular joint")
            joint = None
            joint_position = (0.0, 0.0, 0.0)
            joint_origin = (0.0, 0.0, 0.0)
        else:
            if len(joints) != 1 or body.findall("freejoint"):
                raise ConversionError(f"body {name} must have exactly one regular joint")
            joint = joints[0]
            if joint.get("type", "hinge") != "hinge":
                raise ConversionError(f"body {name} uses unsupported joint type {joint.get('type')!r}")
            _require_identity_orientation(joint, f"joint {joint.get('name', '<unnamed>')}")
            if joint.get("ref") is not None or joint.get("springref") is not None:
                raise ConversionError(f"joint {joint.get('name')} uses ref/springref semantics that need conversion")
            if joint.get("range") is not None or joint.get("limited", "false").lower() == "true":
                raise ConversionError(f"joint {joint.get('name')} is limited; do not fabricate continuous semantics")
            joint_position = _vector(joint.get("pos"))
            joint_origin = _subtract(_add(body_position, joint_position), parent.joint_position)

        record = BodyRecord(
            element=body,
            name=name,
            parent_name=None if parent is None else parent.name,
            body_position=body_position,
            joint=joint,
            joint_position=joint_position,
            joint_origin=joint_origin,
        )
        records.append(record)
        for child in body.findall("body"):
            visit(child, record)

    visit(root_body, None)
    return records


def _site_owners(records: list[BodyRecord]) -> dict[str, tuple[BodyRecord, ET.Element]]:
    owners: dict[str, tuple[BodyRecord, ET.Element]] = {}
    for record in records:
        for site in record.element.findall("site"):
            name = site.get("name")
            if not name:
                raise ConversionError(f"body {record.name} has an unnamed site")
            if name in owners:
                raise ConversionError(f"duplicate site name {name!r}")
            _require_identity_orientation(site, f"site {name}")
            owners[name] = record, site
    return owners


def _loop_records(mjcf_root: ET.Element, records: list[BodyRecord]) -> list[LoopRecord]:
    equality = mjcf_root.find("equality")
    if equality is None:
        raise ConversionError("canonical MJCF has no equality section")
    if any(child.tag != "connect" for child in equality):
        raise ConversionError("only equality/connect constraints can become spherical loop joints")

    site_owners = _site_owners(records)
    loops: list[LoopRecord] = []
    for connect in equality.findall("connect"):
        name = connect.get("name")
        site1_name = connect.get("site1")
        site2_name = connect.get("site2")
        if not name or not site1_name or not site2_name:
            raise ConversionError("every equality/connect must use a name plus site1/site2")
        if site1_name not in site_owners or site2_name not in site_owners:
            raise ConversionError(f"loop {name} references an unknown site")
        owner1, site1 = site_owners[site1_name]
        owner2, site2 = site_owners[site2_name]
        loops.append(
            LoopRecord(
                name=name,
                link1=owner1.name,
                xyz1=_subtract(_vector(site1.get("pos")), owner1.joint_position),
                link2=owner2.name,
                xyz2=_subtract(_vector(site2.get("pos")), owner2.joint_position),
            )
        )
    return loops


def _mesh_definitions(mjcf_root: ET.Element, source: Path) -> dict[str, Path]:
    compiler = mjcf_root.find("compiler")
    if compiler is None or compiler.get("angle", "degree") != "radian":
        raise ConversionError("canonical MJCF must declare compiler angle='radian'")
    if compiler.get("eulerseq") not in (None, "xyz"):
        raise ConversionError("canonical MJCF uses a non-xyz Euler sequence that needs explicit conversion")
    mesh_directory = compiler.get("meshdir")
    if not mesh_directory:
        raise ConversionError("canonical MJCF must declare compiler meshdir")

    asset = mjcf_root.find("asset")
    if asset is None:
        raise ConversionError("canonical MJCF has no asset section")
    meshes: dict[str, Path] = {}
    for mesh in asset.findall("mesh"):
        name = mesh.get("name")
        filename = mesh.get("file")
        if not name or not filename:
            raise ConversionError("every mesh asset must have name and file")
        if mesh.get("scale") is not None:
            raise ConversionError(f"mesh {name} has a scale that the converter does not silently bake")
        path = (source.parent / mesh_directory / filename).resolve()
        if not path.is_file():
            raise ConversionError(f"mesh {name} does not exist: {path}")
        meshes[name] = path
    return meshes


def _geom_category(geom: ET.Element) -> str:
    group = int(geom.get("group", "0"))
    contype = int(geom.get("contype", "1"))
    conaffinity = int(geom.get("conaffinity", "1"))
    if group == 1 and contype == 0 and conaffinity == 0:
        return "visual"
    if group == 0 and contype == 1 and conaffinity == 2:
        return "collision"
    raise ConversionError(
        f"geom {geom.get('name', '<unnamed>')} has ambiguous group/contact classification: "
        f"group={group}, contype={contype}, conaffinity={conaffinity}"
    )


def _append_geometry(
    destination: ET.Element,
    geom: ET.Element,
    *,
    record: BodyRecord,
    mesh_paths: dict[str, str],
    category: str,
) -> None:
    geometry_type = geom.get("type", "mesh" if geom.get("mesh") else "sphere")
    if geom.get("quat") is not None or geom.get("axisangle") is not None:
        raise ConversionError(f"geom {geom.get('name')} uses an unsupported orientation encoding")
    xyz = _subtract(_vector(geom.get("pos")), record.joint_position)
    rpy = _vector(geom.get("euler"))

    item_attributes = {}
    if geom.get("name"):
        item_attributes["name"] = geom.get("name", "")
    item = ET.SubElement(destination, category, item_attributes)
    _origin(item, xyz, rpy)
    geometry = ET.SubElement(item, "geometry")
    if geometry_type == "mesh":
        mesh_name = geom.get("mesh")
        if not mesh_name or mesh_name not in mesh_paths:
            raise ConversionError(f"geom {geom.get('name')} references unknown mesh {mesh_name!r}")
        ET.SubElement(geometry, "mesh", {"filename": mesh_paths[mesh_name]})
    elif geometry_type == "cylinder":
        size = tuple(float(value) for value in geom.get("size", "").split())
        if len(size) != 2:
            raise ConversionError(f"cylinder geom {geom.get('name')} must use radius and half-length")
        ET.SubElement(
            geometry,
            "cylinder",
            {"radius": _format_number(size[0]), "length": _format_number(2.0 * size[1])},
        )
    else:
        raise ConversionError(f"geom {geom.get('name')} uses unsupported type {geometry_type!r}")

    if category == "visual":
        ET.SubElement(item, "material", {"name": "serialleg_visual"})


def _append_inertial(
    link: ET.Element,
    *,
    position: Vector3,
    mass: float,
    inertia: Matrix3,
) -> None:
    inertial = ET.SubElement(link, "inertial")
    _origin(inertial, position)
    ET.SubElement(inertial, "mass", {"value": _format_number(mass)})
    ET.SubElement(inertial, "inertia", _inertia_attributes(inertia))


def _split_base_inertial(source_inertial: ET.Element) -> tuple[float, Vector3, Matrix3]:
    """Remove both virtual mounts from base inertia while preserving the zero-pose aggregate exactly."""
    source_mass = float(source_inertial.get("mass", "nan"))
    source_com = _vector(source_inertial.get("pos"))
    source_inertia = _full_inertia_matrix(
        tuple(float(value) for value in source_inertial.get("fullinertia", "").split())
    )
    mount_count = len(VIRTUAL_MOUNTS)
    base_mass = source_mass - mount_count * VIRTUAL_MOUNT_MASS
    if base_mass <= 0.0:
        raise ConversionError("virtual mount mass leaves a non-positive base mass")
    base_com = tuple(source_mass * value / base_mass for value in source_com)
    base_displacement = _subtract(base_com, source_com)  # type: ignore[arg-type]
    mount_displacement = tuple(-value for value in source_com)
    mount_inertia = _matrix_scale(_identity_matrix(), VIRTUAL_MOUNT_INERTIA)
    correction = _parallel_axis(base_mass, base_displacement)
    for _ in VIRTUAL_MOUNTS:
        correction = _matrix_add(
            correction,
            _matrix_add(
                mount_inertia,
                _parallel_axis(VIRTUAL_MOUNT_MASS, mount_displacement),  # type: ignore[arg-type]
            ),
        )
    return base_mass, base_com, _matrix_subtract(source_inertia, correction)  # type: ignore[arg-type]


def _append_link(robot: ET.Element, record: BodyRecord, mesh_paths: dict[str, str]) -> None:
    link = ET.SubElement(robot, "link", {"name": record.name})
    inertials = record.element.findall("inertial")
    if len(inertials) != 1:
        raise ConversionError(f"body {record.name} must have exactly one explicit inertial")
    source_inertial = inertials[0]
    _require_identity_orientation(source_inertial, f"inertial on {record.name}")
    full_inertia = tuple(float(value) for value in source_inertial.get("fullinertia", "").split())
    if len(full_inertia) != 6:
        raise ConversionError(f"body {record.name} must use MJCF fullinertia")
    if record.name == "base_link":
        mass, position, inertia = _split_base_inertial(source_inertial)
    else:
        mass = float(source_inertial.get("mass", "nan"))
        position = _subtract(_vector(source_inertial.get("pos")), record.joint_position)
        inertia = _full_inertia_matrix(full_inertia)
    _append_inertial(link, position=position, mass=mass, inertia=inertia)

    for geom in record.element.findall("geom"):
        category = _geom_category(geom)
        _append_geometry(link, geom, record=record, mesh_paths=mesh_paths, category=category)


def _append_virtual_mount_links(robot: ET.Element) -> None:
    inertia = _matrix_scale(_identity_matrix(), VIRTUAL_MOUNT_INERTIA)
    for spec in VIRTUAL_MOUNTS:
        link = ET.SubElement(robot, "link", {"name": str(spec["link"])})
        _append_inertial(
            link,
            position=(0.0, 0.0, 0.0),
            mass=VIRTUAL_MOUNT_MASS,
            inertia=inertia,
        )


def _append_joint(robot: ET.Element, record: BodyRecord, default_damping: float) -> None:
    if record.joint is None or record.parent_name is None:
        return
    name = record.joint.get("name")
    if not name:
        raise ConversionError(f"body {record.name} has an unnamed hinge")
    damping = float(record.joint.get("damping", _format_number(default_damping)))
    friction = float(record.joint.get("frictionloss", "0"))
    armature = float(record.joint.get("armature", "0"))
    robot.append(
        ET.Comment(
            f" Source MJCF metadata for {name}: armature={_format_number(armature)}; "
            "armature requires USD post-processing. "
        )
    )
    joint = ET.SubElement(robot, "joint", {"name": name, "type": "continuous"})
    _origin(joint, record.joint_origin)
    parent_name = record.parent_name
    for spec in VIRTUAL_MOUNTS:
        if name in spec["children"]:
            parent_name = str(spec["link"])
            break
    ET.SubElement(joint, "parent", {"link": parent_name})
    ET.SubElement(joint, "child", {"link": record.name})
    ET.SubElement(joint, "axis", {"xyz": _format_vector(_vector(record.joint.get("axis"), default=(0.0, 0.0, 1.0)))})
    ET.SubElement(
        joint,
        "dynamics",
        {"damping": _format_number(damping), "friction": _format_number(friction)},
    )


def _append_virtual_mount_joints(robot: ET.Element) -> None:
    for spec in VIRTUAL_MOUNTS:
        robot.append(
            ET.Comment(
                f" Virtual root for future PhysX fixed tendon {spec['tendon']}: "
                "planned root gearing=0 and forceCoefficient=0; narrow non-locked range is intentional. "
            )
        )
        joint = ET.SubElement(robot, "joint", {"name": str(spec["joint"]), "type": "revolute"})
        _origin(joint, (0.0, 0.0, 0.0))
        ET.SubElement(joint, "parent", {"link": "base_link"})
        ET.SubElement(joint, "child", {"link": str(spec["link"])})
        ET.SubElement(joint, "axis", {"xyz": _format_vector(spec["axis"])})  # type: ignore[arg-type]
        ET.SubElement(
            joint,
            "limit",
            {
                "lower": _format_number(VIRTUAL_JOINT_LOWER),
                "upper": _format_number(VIRTUAL_JOINT_UPPER),
                "effort": _format_number(VIRTUAL_JOINT_EFFORT),
                "velocity": _format_number(VIRTUAL_JOINT_VELOCITY),
            },
        )
        ET.SubElement(
            joint,
            "dynamics",
            {"damping": _format_number(VIRTUAL_JOINT_DAMPING), "friction": "0"},
        )


def _append_loop_joint(robot: ET.Element, loop: LoopRecord) -> None:
    loop_joint = ET.SubElement(robot, "loop_joint", {"name": loop.name, "type": "spherical"})
    ET.SubElement(
        loop_joint,
        "link1",
        {"link": loop.link1, "rpy": "0 0 0", "xyz": _format_vector(loop.xyz1)},
    )
    ET.SubElement(
        loop_joint,
        "link2",
        {"link": loop.link2, "rpy": "0 0 0", "xyz": _format_vector(loop.xyz2)},
    )


def _default_joint_damping(mjcf_root: ET.Element) -> float:
    default_joint = mjcf_root.find("./default/joint")
    return 0.0 if default_joint is None else float(default_joint.get("damping", "0"))


def _validate_fixed_tendon_source(mjcf_root: ET.Element) -> None:
    tendon_section = mjcf_root.find("tendon")
    if tendon_section is None:
        raise ConversionError("canonical MJCF has no tendon section")
    fixed_tendons = {fixed.get("name", ""): fixed for fixed in tendon_section.findall("fixed")}
    if set(fixed_tendons) != set(EXPECTED_FIXED_TENDONS):
        raise ConversionError(f"canonical fixed-tendon set changed: {sorted(fixed_tendons)}")
    for name, expected in EXPECTED_FIXED_TENDONS.items():
        fixed = fixed_tendons[name]
        if fixed.get("limited") != "true":
            raise ConversionError(f"fixed tendon {name} must remain limited")
        for attribute, expected_values in (
            ("range", expected["range"]),
            ("solreflimit", expected["solref"]),
            ("solimplimit", expected["solimp"]),
        ):
            actual_values = _numbers(fixed.get(attribute), len(expected_values), f"fixed tendon {name} {attribute}")
            if any(
                not math.isclose(actual, float(reference), rel_tol=0.0, abs_tol=1.0e-12)
                for actual, reference in zip(actual_values, expected_values, strict=True)
            ):
                raise ConversionError(f"fixed tendon {name} {attribute} changed: {actual_values}")
        axes = tuple((joint.get("joint", ""), float(joint.get("coef", "nan"))) for joint in fixed.findall("joint"))
        if axes != expected["axes"]:
            raise ConversionError(f"fixed tendon {name} axes changed: {axes}")


def _validate_source(
    mjcf_root: ET.Element,
    records: list[BodyRecord],
    loops: list[LoopRecord],
    meshes: dict[str, Path],
) -> None:
    if mjcf_root.get("model") != "serialleg_closed_chain_complex_collision":
        raise ConversionError(f"unexpected source model {mjcf_root.get('model')!r}")
    if {record.name for record in records} != EXPECTED_LINK_NAMES or len(records) != 11:
        raise ConversionError("canonical body/link set changed")
    joint_names = tuple(record.joint.get("name") for record in records if record.joint is not None)
    if joint_names != EXPECTED_JOINT_NAMES:
        raise ConversionError(f"canonical joint order changed: {joint_names}")
    if {loop.name for loop in loops} != EXPECTED_LOOP_NAMES or len(loops) != 2:
        raise ConversionError("canonical loop closure set changed")
    _validate_fixed_tendon_source(mjcf_root)
    if len(meshes) != EXPECTED_MESH_COUNT:
        raise ConversionError(f"expected {EXPECTED_MESH_COUNT} mesh assets, got {len(meshes)}")

    total_mass = sum(float(record.element.find("inertial").get("mass", "nan")) for record in records)  # type: ignore[union-attr]
    if not math.isclose(total_mass, EXPECTED_TOTAL_MASS, rel_tol=0.0, abs_tol=1.0e-10):
        raise ConversionError(f"unexpected total mass {total_mass:.12f}")

    categories = Counter(_geom_category(geom) for record in records for geom in record.element.findall("geom"))
    if categories != Counter({"visual": EXPECTED_VISUAL_COUNT, "collision": EXPECTED_COLLISION_COUNT}):
        raise ConversionError(f"unexpected robot geometry counts: {categories}")
    mesh_references = [
        geom.get("mesh")
        for record in records
        for geom in record.element.findall("geom")
        if geom.get("mesh") is not None
    ]
    if len(mesh_references) != EXPECTED_MESH_COUNT or Counter(mesh_references) != Counter(meshes.keys()):
        raise ConversionError("canonical mesh assets and robot mesh references must remain one-to-one")

    root = records[0]
    if root.name != "base_link" or root.body_position != (0.0, 0.0, 0.22):
        raise ConversionError("base_link must remain the floating root with MJCF spawn position z=0.22")


def _validate_tree(robot: ET.Element) -> dict[str, ET.Element]:
    links = {link.get("name", ""): link for link in robot.findall("link")}
    joints = robot.findall("joint")
    loops = robot.findall("loop_joint")
    if set(links) != GENERATED_LINK_NAMES or len(links) != 13:
        raise ConversionError("generated URDF link set is invalid")
    joints_by_name = {joint.get("name", ""): joint for joint in joints}
    if len(joints_by_name) != 12 or set(joints_by_name) != set(EXPECTED_JOINT_NAMES) | VIRTUAL_JOINT_NAMES:
        raise ConversionError("generated URDF tree-joint set is invalid")
    if any(joints_by_name[name].get("type") != "continuous" for name in EXPECTED_JOINT_NAMES):
        raise ConversionError("the ten source tree joints must remain continuous")
    if any(joints_by_name[name].get("type") != "revolute" for name in VIRTUAL_JOINT_NAMES):
        raise ConversionError("the two virtual tendon-root joints must be revolute")
    if len(loops) != 2 or {loop.get("name") for loop in loops} != EXPECTED_LOOP_NAMES:
        raise ConversionError("generated URDF must contain the two expected loop joints")
    if any(loop.get("type") != "spherical" for loop in loops):
        raise ConversionError("all generated loop joints must be spherical")

    parent_by_child: dict[str, str] = {}
    children_by_parent: dict[str, list[str]] = {name: [] for name in links}
    for joint in joints:
        parent = joint.find("parent")
        child = joint.find("child")
        if parent is None or child is None:
            raise ConversionError("tree joint is missing parent/child")
        parent_name = parent.get("link", "")
        child_name = child.get("link", "")
        if parent_name not in links or child_name not in links or child_name in parent_by_child:
            raise ConversionError("tree joint parent/child graph is invalid")
        parent_by_child[child_name] = parent_name
        children_by_parent[parent_name].append(child_name)
    roots = set(links) - set(parent_by_child)
    if roots != {"base_link"}:
        raise ConversionError(f"generated URDF has invalid roots: {sorted(roots)}")
    reachable = {"base_link"}
    frontier = ["base_link"]
    while frontier:
        parent = frontier.pop()
        for child in children_by_parent[parent]:
            if child in reachable:
                raise ConversionError("generated URDF tree contains a cycle")
            reachable.add(child)
            frontier.append(child)
    if reachable != set(links):
        raise ConversionError("generated URDF tree is disconnected")

    for spec in VIRTUAL_MOUNTS:
        joint = joints_by_name[str(spec["joint"])]
        origin = joint.find("origin")
        parent = joint.find("parent")
        child = joint.find("child")
        axis = joint.find("axis")
        limit = joint.find("limit")
        dynamics = joint.find("dynamics")
        if any(item is None for item in (origin, parent, child, axis, limit, dynamics)):
            raise ConversionError(f"virtual joint {spec['joint']} is incomplete")
        if _vector(origin.get("xyz")) != (0.0, 0.0, 0.0) or _vector(origin.get("rpy")) != IDENTITY_RPY:
            raise ConversionError(f"virtual joint {spec['joint']} must be coincident with base_link")
        if parent.get("link") != "base_link" or child.get("link") != spec["link"]:
            raise ConversionError(f"virtual joint {spec['joint']} parent/child changed")
        _require_vector_close(_vector(axis.get("xyz")), spec["axis"], f"virtual joint {spec['joint']} axis")  # type: ignore[arg-type]
        expected_limit = {
            "lower": VIRTUAL_JOINT_LOWER,
            "upper": VIRTUAL_JOINT_UPPER,
            "effort": VIRTUAL_JOINT_EFFORT,
            "velocity": VIRTUAL_JOINT_VELOCITY,
        }
        for attribute, expected in expected_limit.items():
            if not math.isclose(float(limit.get(attribute, "nan")), expected, rel_tol=0.0, abs_tol=1.0e-15):
                raise ConversionError(f"virtual joint {spec['joint']} {attribute} changed")
        if not float(limit.get("lower", "nan")) < 0.0 < float(limit.get("upper", "nan")):
            raise ConversionError(f"virtual joint {spec['joint']} must have a non-locked range around zero")
        if (
            not math.isclose(float(dynamics.get("damping", "nan")), VIRTUAL_JOINT_DAMPING, rel_tol=0.0, abs_tol=1.0e-15)
            or float(dynamics.get("friction", "nan")) != 0.0
        ):
            raise ConversionError(f"virtual joint {spec['joint']} dynamics changed")
        for source_joint_name in spec["children"]:
            source_parent = joints_by_name[str(source_joint_name)].find("parent")
            if source_parent is None or source_parent.get("link") != spec["link"]:
                raise ConversionError(f"{source_joint_name} is not parented under {spec['link']}")
    return links


def _joint_positions_from_keyframe(mjcf_root: ET.Element) -> dict[str, float]:
    key = mjcf_root.find("./keyframe/key[@name='standing']")
    if key is None:
        raise ConversionError("canonical MJCF has no standing keyframe")
    qpos = tuple(float(value) for value in key.get("qpos", "").split())
    if len(qpos) != 7 + len(EXPECTED_JOINT_NAMES):
        raise ConversionError(f"standing keyframe has unexpected qpos width {len(qpos)}")
    return dict(zip(EXPECTED_JOINT_NAMES, qpos[7:], strict=True))


def _urdf_fk(robot: ET.Element, joint_positions: dict[str, float]) -> dict[str, Transform]:
    joints_by_parent: dict[str, list[ET.Element]] = {}
    for joint in robot.findall("joint"):
        parent = joint.find("parent")
        if parent is None:
            raise ConversionError("generated joint has no parent")
        joints_by_parent.setdefault(parent.get("link", ""), []).append(joint)

    transforms: dict[str, Transform] = {"base_link": (_identity_matrix(), (0.0, 0.0, 0.0))}
    frontier = ["base_link"]
    while frontier:
        parent_name = frontier.pop()
        for joint in joints_by_parent.get(parent_name, []):
            child = joint.find("child")
            origin = joint.find("origin")
            axis = joint.find("axis")
            if child is None or origin is None or axis is None:
                raise ConversionError("generated joint is missing child/origin/axis")
            if _vector(origin.get("rpy")) != IDENTITY_RPY:
                raise ConversionError("canonical generated tree joint rpy must remain zero")
            joint_transform = _compose(
                _translation(_vector(origin.get("xyz"))),
                _rotation_transform(_vector(axis.get("xyz")), joint_positions.get(joint.get("name", ""), 0.0)),
            )
            child_name = child.get("link", "")
            transforms[child_name] = _compose(transforms[parent_name], joint_transform)
            frontier.append(child_name)
    return transforms


def _source_fk(records: list[BodyRecord], joint_positions: dict[str, float]) -> dict[str, Transform]:
    transforms: dict[str, Transform] = {"base_link": (_identity_matrix(), (0.0, 0.0, 0.0))}
    for record in records[1:]:
        if record.parent_name is None or record.joint is None:
            raise ConversionError(f"body record {record.name} has invalid parent/joint")
        joint_name = record.joint.get("name", "")
        axis = _vector(record.joint.get("axis"), default=(0.0, 0.0, 1.0))
        body_transform = _compose(
            _translation(record.body_position),
            _compose(
                _translation(record.joint_position),
                _compose(
                    _rotation_transform(axis, joint_positions.get(joint_name, 0.0)),
                    _translation(tuple(-value for value in record.joint_position)),  # type: ignore[arg-type]
                ),
            ),
        )
        transforms[record.name] = _compose(transforms[record.parent_name], body_transform)
    return transforms


def _validate_fk(robot: ET.Element, records: list[BodyRecord], mjcf_root: ET.Element) -> tuple[float, float]:
    standing = _joint_positions_from_keyframe(mjcf_root)
    deterministic = {
        name: value
        for name, value in zip(
            EXPECTED_JOINT_NAMES,
            (0.31, -0.47, 0.83, -0.62, 0.29, -0.21, 0.44, -0.71, 0.57, -0.35),
            strict=True,
        )
    }
    for joint_positions in ({}, standing, deterministic):
        source_transforms = _source_fk(records, joint_positions)
        urdf_transforms = _urdf_fk(robot, joint_positions)
        for record in records:
            urdf_body_transform = _compose(
                urdf_transforms[record.name],
                _translation(tuple(-value for value in record.joint_position)),  # type: ignore[arg-type]
            )
            source_rotation, source_translation = source_transforms[record.name]
            urdf_rotation, urdf_translation = urdf_body_transform
            if _distance(source_translation, urdf_translation) > 1.0e-12:
                raise ConversionError(f"URDF rebase changes body translation for {record.name}")
            rotation_error = max(
                abs(source_rotation[row][column] - urdf_rotation[row][column])
                for row in range(3)
                for column in range(3)
            )
            if rotation_error > 1.0e-12:
                raise ConversionError(f"URDF rebase changes body rotation for {record.name}")

    def closure_residual(joint_positions: dict[str, float], loop: ET.Element) -> float:
        transforms = _urdf_fk(robot, joint_positions)
        link1 = loop.find("link1")
        link2 = loop.find("link2")
        if link1 is None or link2 is None:
            raise ConversionError("loop joint is missing link1/link2")
        point1 = _transform_point(transforms[link1.get("link", "")], _vector(link1.get("xyz")))
        point2 = _transform_point(transforms[link2.get("link", "")], _vector(link2.get("xyz")))
        return _distance(point1, point2)

    zero_residual = max(closure_residual({}, loop) for loop in robot.findall("loop_joint"))
    standing_residual = max(closure_residual(standing, loop) for loop in robot.findall("loop_joint"))
    if zero_residual > 1.0e-12:
        raise ConversionError(f"zero-pose loop residual is too large: {zero_residual:.3e} m")
    if standing_residual > 1.0e-6:
        raise ConversionError(f"standing loop residual is too large: {standing_residual:.3e} m")
    return zero_residual, standing_residual


def _validate_inertia_tensor(inertia: ET.Element, context: str) -> None:
    values = {name: float(inertia.get(name, "nan")) for name in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz")}
    if not all(math.isfinite(value) for value in values.values()):
        raise ConversionError(f"{context} inertia contains non-finite values")
    ixx = values["ixx"]
    ixy = values["ixy"]
    ixz = values["ixz"]
    iyy = values["iyy"]
    iyz = values["iyz"]
    izz = values["izz"]
    leading_minor_2 = ixx * iyy - ixy * ixy
    determinant = ixx * (iyy * izz - iyz * iyz) - ixy * (ixy * izz - ixz * iyz) + ixz * (ixy * iyz - ixz * iyy)
    if ixx <= 0.0 or leading_minor_2 <= 0.0 or determinant <= 0.0:
        raise ConversionError(f"{context} inertia tensor is not positive definite")
    if ixx + iyy < izz or ixx + izz < iyy or iyy + izz < ixx:
        raise ConversionError(f"{context} inertia tensor violates a principal-moment triangle inequality")


def _validate_link_inertial(record: BodyRecord, link: ET.Element) -> None:
    source_inertial = record.element.find("inertial")
    target_inertial = link.find("inertial")
    if source_inertial is None or target_inertial is None:
        raise ConversionError(f"link {record.name} is missing an inertial")
    source_full = tuple(float(value) for value in source_inertial.get("fullinertia", "").split())
    if len(source_full) != 6:
        raise ConversionError(f"source body {record.name} does not have six fullinertia values")
    target_origin = target_inertial.find("origin")
    target_mass = target_inertial.find("mass")
    target_tensor = target_inertial.find("inertia")
    if target_origin is None or target_mass is None or target_tensor is None:
        raise ConversionError(f"generated link {record.name} has an incomplete inertial")
    if record.name == "base_link":
        expected_mass, expected_position, expected_inertia = _split_base_inertial(source_inertial)
    else:
        expected_mass = float(source_inertial.get("mass", "nan"))
        expected_position = _subtract(_vector(source_inertial.get("pos")), record.joint_position)
        expected_inertia = _full_inertia_matrix(source_full)
    _require_vector_close(_vector(target_origin.get("xyz")), expected_position, f"link {record.name} inertial origin")
    if _vector(target_origin.get("rpy")) != IDENTITY_RPY:
        raise ConversionError(f"link {record.name} inertial rpy must remain zero")
    if not math.isclose(
        float(target_mass.get("value", "nan")),
        expected_mass,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ConversionError(f"link {record.name} mass changed during conversion")
    expected_tensor = {name: float(value) for name, value in _inertia_attributes(expected_inertia).items()}
    for name, expected in expected_tensor.items():
        if not math.isclose(float(target_tensor.get(name, "nan")), expected, rel_tol=0.0, abs_tol=1.0e-15):
            raise ConversionError(f"link {record.name} inertia field {name} changed during conversion")
    _validate_inertia_tensor(target_tensor, f"link {record.name}")


def _read_link_inertial(link: ET.Element) -> tuple[float, Vector3, Matrix3]:
    inertial = link.find("inertial")
    if inertial is None:
        raise ConversionError(f"link {link.get('name')} is missing inertial")
    origin = inertial.find("origin")
    mass_element = inertial.find("mass")
    inertia_element = inertial.find("inertia")
    if origin is None or mass_element is None or inertia_element is None:
        raise ConversionError(f"link {link.get('name')} has incomplete inertial data")
    matrix = (
        (
            float(inertia_element.get("ixx", "nan")),
            float(inertia_element.get("ixy", "nan")),
            float(inertia_element.get("ixz", "nan")),
        ),
        (
            float(inertia_element.get("ixy", "nan")),
            float(inertia_element.get("iyy", "nan")),
            float(inertia_element.get("iyz", "nan")),
        ),
        (
            float(inertia_element.get("ixz", "nan")),
            float(inertia_element.get("iyz", "nan")),
            float(inertia_element.get("izz", "nan")),
        ),
    )
    return float(mass_element.get("value", "nan")), _vector(origin.get("xyz")), matrix


def _require_matrix_close(actual: Matrix3, expected: Matrix3, context: str, tolerance: float = 1.0e-12) -> None:
    error = max(abs(actual[row][column] - expected[row][column]) for row in range(3) for column in range(3))
    if error > tolerance:
        raise ConversionError(f"{context} mismatch: max_error={error:.3e}")


def _validate_virtual_mount_inertials(links: dict[str, ET.Element], base_record: BodyRecord) -> None:
    expected_mount_inertia = _matrix_scale(_identity_matrix(), VIRTUAL_MOUNT_INERTIA)
    components: list[tuple[float, Vector3, Matrix3]] = []
    for link_name in ("base_link", *sorted(VIRTUAL_LINK_NAMES)):
        mass, position, inertia = _read_link_inertial(links[link_name])
        if link_name in VIRTUAL_LINK_NAMES:
            if not math.isclose(mass, VIRTUAL_MOUNT_MASS, rel_tol=0.0, abs_tol=1.0e-15):
                raise ConversionError(f"virtual mount {link_name} mass changed")
            _require_vector_close(position, (0.0, 0.0, 0.0), f"virtual mount {link_name} COM")
            _require_matrix_close(inertia, expected_mount_inertia, f"virtual mount {link_name} inertia", 1.0e-15)
            _validate_inertia_tensor(links[link_name].find("./inertial/inertia"), f"virtual mount {link_name}")  # type: ignore[arg-type]
        components.append((mass, position, inertia))

    aggregate_mass = sum(mass for mass, _position, _inertia in components)
    aggregate_com = tuple(
        sum(mass * position[axis] for mass, position, _inertia in components) / aggregate_mass for axis in range(3)
    )
    aggregate_inertia: Matrix3 = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    for mass, position, inertia in components:
        aggregate_inertia = _matrix_add(
            aggregate_inertia,
            _matrix_add(inertia, _parallel_axis(mass, _subtract(position, aggregate_com))),  # type: ignore[arg-type]
        )

    source = base_record.element.find("inertial")
    if source is None:
        raise ConversionError("source base_link is missing inertial")
    source_mass = float(source.get("mass", "nan"))
    source_com = _vector(source.get("pos"))
    source_inertia = _full_inertia_matrix(tuple(float(value) for value in source.get("fullinertia", "").split()))
    if not math.isclose(aggregate_mass, source_mass, rel_tol=0.0, abs_tol=1.0e-12):
        raise ConversionError("base plus virtual mounts do not preserve source mass")
    _require_vector_close(aggregate_com, source_com, "base plus virtual mounts aggregate COM", tolerance=1.0e-12)  # type: ignore[arg-type]
    _require_matrix_close(
        aggregate_inertia,
        source_inertia,
        "base plus virtual mounts aggregate inertia",
        tolerance=1.0e-12,
    )


def _validate_link_geometries(record: BodyRecord, link: ET.Element, mesh_paths: dict[str, str]) -> None:
    for category in ("visual", "collision"):
        source_geometries = [geom for geom in record.element.findall("geom") if _geom_category(geom) == category]
        target_geometries = link.findall(category)
        if len(source_geometries) != len(target_geometries):
            raise ConversionError(f"link {record.name} {category} count changed during conversion")
        for source_geom, target_geom in zip(source_geometries, target_geometries, strict=True):
            source_name = source_geom.get("name")
            if source_name and target_geom.get("name") != source_name:
                raise ConversionError(f"link {record.name} {category} name changed for {source_name}")
            target_origin = target_geom.find("origin")
            if target_origin is None:
                raise ConversionError(f"link {record.name} {category} {source_name} has no origin")
            _require_vector_close(
                _vector(target_origin.get("xyz")),
                _subtract(_vector(source_geom.get("pos")), record.joint_position),
                f"link {record.name} {category} {source_name} origin",
            )
            _require_vector_close(
                _vector(target_origin.get("rpy")),
                _vector(source_geom.get("euler")),
                f"link {record.name} {category} {source_name} rpy",
            )

            source_type = source_geom.get("type", "mesh" if source_geom.get("mesh") else "sphere")
            if source_type == "mesh":
                source_mesh = source_geom.get("mesh")
                target_mesh = target_geom.find("./geometry/mesh")
                if source_mesh is None or target_mesh is None or target_mesh.get("filename") != mesh_paths[source_mesh]:
                    raise ConversionError(f"link {record.name} {category} {source_name} mesh path changed")
            elif source_type == "cylinder":
                source_size = tuple(float(value) for value in source_geom.get("size", "").split())
                target_cylinder = target_geom.find("./geometry/cylinder")
                if len(source_size) != 2 or target_cylinder is None:
                    raise ConversionError(f"link {record.name} cylinder {source_name} is malformed")
                if not math.isclose(float(target_cylinder.get("radius", "nan")), source_size[0]) or not math.isclose(
                    float(target_cylinder.get("length", "nan")), 2.0 * source_size[1]
                ):
                    raise ConversionError(f"link {record.name} cylinder {source_name} dimensions changed")
            else:
                raise ConversionError(f"link {record.name} has unsupported source geom type {source_type}")


def _validate_output(
    robot: ET.Element,
    output: Path,
    records: list[BodyRecord],
    mjcf_root: ET.Element,
    mesh_paths: dict[str, str],
) -> tuple[float, float]:
    links = _validate_tree(robot)
    total_mass = 0.0
    for record in records:
        link = links[record.name]
        _validate_link_inertial(record, link)
        _validate_link_geometries(record, link, mesh_paths)
    _validate_virtual_mount_inertials(links, records[0])
    for link in links.values():
        mass = link.find("./inertial/mass")
        if mass is None:
            raise ConversionError(f"link {link.get('name')} has no mass")
        total_mass += float(mass.get("value", "nan"))
    if not math.isclose(total_mass, EXPECTED_TOTAL_MASS, rel_tol=0.0, abs_tol=1.0e-10):
        raise ConversionError(f"generated URDF total mass is {total_mass:.12f}")

    visual_count = len(robot.findall("./link/visual"))
    collision_count = len(robot.findall("./link/collision"))
    mesh_elements = robot.findall("./link/visual/geometry/mesh") + robot.findall("./link/collision/geometry/mesh")
    if (visual_count, collision_count, len(mesh_elements)) != (
        EXPECTED_VISUAL_COUNT,
        EXPECTED_COLLISION_COUNT,
        EXPECTED_MESH_COUNT,
    ):
        raise ConversionError(
            f"generated geometry counts are visual={visual_count}, collision={collision_count}, "
            f"mesh={len(mesh_elements)}"
        )
    for mesh in mesh_elements:
        filename = mesh.get("filename")
        if not filename or not (output.parent / filename).resolve().is_file():
            raise ConversionError(f"generated URDF references missing mesh {filename!r}")

    cylinders = robot.findall("./link/collision/geometry/cylinder")
    if len(cylinders) != 2 or any(
        not math.isclose(float(cylinder.get("radius", "nan")), 0.06)
        or not math.isclose(float(cylinder.get("length", "nan")), 0.02)
        for cylinder in cylinders
    ):
        raise ConversionError("wheel cylinders must preserve radius=0.060 and full length=0.020")
    return _validate_fk(robot, records, mjcf_root)


def _build_urdf(source: Path, output: Path) -> tuple[bytes, float, float]:
    if not source.is_file():
        raise ConversionError(f"source MJCF does not exist: {source}")
    mjcf_tree = ET.parse(source)
    mjcf_root = mjcf_tree.getroot()
    worldbody = mjcf_root.find("worldbody")
    if worldbody is None or len(worldbody.findall("body")) != 1:
        raise ConversionError("canonical MJCF must contain exactly one root body")

    records = _body_records(worldbody.findall("body")[0])
    loops = _loop_records(mjcf_root, records)
    meshes = _mesh_definitions(mjcf_root, source)
    _validate_source(mjcf_root, records, loops, meshes)

    mesh_paths = {
        name: Path(os.path.relpath(path, output.parent.resolve())).as_posix() for name, path in meshes.items()
    }
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    robot = ET.Element("robot", {"name": "serialleg_closed_chain_complex_collision"})
    robot.append(
        ET.Comment(
            " DO NOT EDIT: regenerate with scripts/convert_serialleg_mjcf_to_urdf.py. "
            "Canonical source: source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/mjcf/"
            "serialleg_closed_chain_complex_collision.xml. "
            f"Source SHA256: {source_sha256}. "
        )
    )
    robot.append(
        ET.Comment(
            " Intentionally deferred MJCF-only semantics: joint armature; PhysX fixed-tendon schemas; "
            "spatial-tendon sites; option timestep/solver/cone; geom/equality solref and solimp; "
            "contact masks/friction; standing keyframe; world floor/light and debug display materials. "
        )
    )
    robot.append(
        ET.Comment(
            " Deferred coupled limits: 0 <= q_lf0_Joint - q_l_drive_bar_Joint <= 1.509535270050; "
            "0 <= q_r_drive_bar_Joint - q_rf0_Joint <= 1.509535270050. "
        )
    )
    robot.append(
        ET.Comment(" The MJCF base_link world/spawn z=0.22 is intentionally not baked into this floating-root URDF. ")
    )
    for record in records:
        _append_link(robot, record, mesh_paths)
    _append_virtual_mount_links(robot)
    default_damping = _default_joint_damping(mjcf_root)
    _append_virtual_mount_joints(robot)
    for record in records:
        _append_joint(robot, record, default_damping)
    for loop in loops:
        _append_loop_joint(robot, loop)

    zero_residual, standing_residual = _validate_output(robot, output, records, mjcf_root, mesh_paths)
    ET.indent(robot, space="  ")
    payload = ET.tostring(robot, encoding="utf-8", xml_declaration=True, short_empty_elements=True) + b"\n"
    return payload, zero_residual, standing_residual


def main() -> int:
    args = _parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    payload, zero_residual, standing_residual = _build_urdf(source, output)

    if args.check:
        if not output.is_file():
            raise ConversionError(f"generated URDF is missing: {output}")
        if output.read_bytes() != payload:
            raise ConversionError(f"generated URDF is stale; rerun without --check: {output}")
        action = "checked"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        action = "wrote"

    print(
        f"{action} {output}\n"
        f"links=13 tree_joints=12 source_dofs=10 virtual_dofs=2 loop_joints=2 visuals={EXPECTED_VISUAL_COUNT} "
        f"collision_meshes={EXPECTED_MESH_COUNT} total_mass={EXPECTED_TOTAL_MASS:.8f}kg\n"
        f"zero_loop_residual={zero_residual:.3e}m standing_loop_residual={standing_residual:.3e}m"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
