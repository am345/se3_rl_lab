"""Render-only geometry for the collision-only SerialLeg USD."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CollisionPreview:
    """World-space render copies driven explicitly from articulation body state."""

    mesh_count: int
    cylinder_count: int
    body_names: tuple[str, ...]
    transform_ops: tuple[Any, ...]

    def update(self, robot) -> None:
        from pxr import Gf

        for body_name, transform_op in zip(self.body_names, self.transform_ops, strict=True):
            body_id = robot.body_names.index(body_name)
            position = robot.data.body_pos_w[0, body_id].detach().cpu().tolist()
            quaternion = robot.data.body_quat_w[0, body_id].detach().cpu().tolist()
            matrix = Gf.Matrix4d(1.0)
            matrix.SetRotate(Gf.Quatd(quaternion[0], Gf.Vec3d(*quaternion[1:4])))
            matrix.SetTranslateOnly(Gf.Vec3d(*position))
            transform_op.Set(matrix)


def spawn_collision_preview(robot_root_path: str) -> CollisionPreview:
    from pxr import Usd, UsdGeom, UsdShade

    import isaaclab.sim as sim_utils

    stage = sim_utils.get_current_stage()
    material_path = "/World/Looks/SerialLegEvalPreview"
    root = stage.GetPrimAtPath(robot_root_path)
    if not root:
        raise RuntimeError(f"robot root does not exist: {robot_root_path}")
    meshes = [
        prim
        for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
        if prim.GetPath().HasPrefix(robot_root_path) and prim.IsA(UsdGeom.Mesh)
    ]
    cylinders = [
        prim
        for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
        if prim.GetPath().HasPrefix(robot_root_path) and prim.IsA(UsdGeom.Cylinder)
    ]
    if len(meshes) != 54 or len(cylinders) != 2:
        raise RuntimeError(f"unexpected collision geometry: meshes={len(meshes)} cylinders={len(cylinders)}")

    material_cfg = sim_utils.PreviewSurfaceCfg(
        diffuse_color=(0.24, 0.52, 0.78), emissive_color=(0.025, 0.05, 0.08), metallic=0.1, roughness=0.35
    )
    material_cfg.func(material_path, material_cfg)
    material = UsdShade.Material.Get(stage, material_path)
    cache = UsdGeom.XformCache()
    preview_root_path = "/World/SerialLegEvalPreview"
    UsdGeom.Xform.Define(stage, preview_root_path)
    preview_roots: dict[str, Any] = {}
    transform_ops: dict[str, Any] = {}

    def body_ancestor(prim):
        ancestor = prim
        while ancestor.GetParent() and str(ancestor.GetParent().GetPath()) != robot_root_path:
            ancestor = ancestor.GetParent()
        if not ancestor.GetParent() or str(ancestor.GetParent().GetPath()) != robot_root_path:
            raise RuntimeError(f"geometry is not below a direct robot body: {prim.GetPath()}")
        return ancestor

    def preview_root(prim):
        body = body_ancestor(prim)
        body_path = str(body.GetPath())
        if body_path not in preview_roots:
            body_name = body.GetName()
            preview_xform = UsdGeom.Xform.Define(stage, f"{preview_root_path}/{body_name}")
            preview = preview_xform.GetPrim()
            UsdShade.MaterialBindingAPI.Apply(preview).Bind(
                material, bindingStrength=UsdShade.Tokens.strongerThanDescendants
            )
            preview_roots[body_path] = preview
            transform_ops[body_name] = preview_xform.AddTransformOp()
        return body, preview_roots[body_path]

    for index, source_prim in enumerate(meshes):
        body, parent = preview_root(source_prim)
        source = UsdGeom.Mesh(source_prim)
        target = UsdGeom.Mesh.Define(stage, f"{parent.GetPath()}/mesh_{index:02d}")
        target.CreatePointsAttr(source.GetPointsAttr().Get())
        target.CreateFaceVertexCountsAttr(source.GetFaceVertexCountsAttr().Get())
        target.CreateFaceVertexIndicesAttr(source.GetFaceVertexIndicesAttr().Get())
        target.CreateOrientationAttr(source.GetOrientationAttr().Get() or UsdGeom.Tokens.rightHanded)
        target.CreateDoubleSidedAttr(True)
        body_world = cache.GetLocalToWorldTransform(body)
        source_world = cache.GetLocalToWorldTransform(source_prim)
        UsdGeom.Xformable(target).AddTransformOp().Set(source_world * body_world.GetInverse())

    for index, source_prim in enumerate(cylinders):
        body, parent = preview_root(source_prim)
        source = UsdGeom.Cylinder(source_prim)
        target = UsdGeom.Cylinder.Define(stage, f"{parent.GetPath()}/cylinder_{index:02d}")
        target.CreateRadiusAttr(source.GetRadiusAttr().Get())
        target.CreateHeightAttr(source.GetHeightAttr().Get())
        target.CreateAxisAttr(source.GetAxisAttr().Get() or UsdGeom.Tokens.z)
        target.CreateDoubleSidedAttr(True)
        body_world = cache.GetLocalToWorldTransform(body)
        source_world = cache.GetLocalToWorldTransform(source_prim)
        UsdGeom.Xformable(target).AddTransformOp().Set(source_world * body_world.GetInverse())
    body_names = tuple(transform_ops)
    return CollisionPreview(
        mesh_count=len(meshes),
        cylinder_count=len(cylinders),
        body_names=body_names,
        transform_ops=tuple(transform_ops[name] for name in body_names),
    )
