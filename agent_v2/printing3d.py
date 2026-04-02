"""3D Printing module — generate printable 3D models via OpenSCAD scripts.

Allows the AI agent to design 3D-printable parts by generating OpenSCAD
code (.scad files).  OpenSCAD is a text-based parametric 3D CAD tool —
the agent writes code that defines the geometry, and the user can open
the .scad file in OpenSCAD (free, cross-platform) to preview and export
to STL for slicing and printing.

Features
--------
- **Part templates** — common parts (box, bracket, mount, gear, etc.)
  with parametric dimensions.
- **OpenSCAD code generation** — the agent writes .scad files directly.
- **Part library** — saves generated parts with metadata for reuse.
- **Export instructions** — tells the user how to get from .scad to STL
  to their printer.

No external dependencies — everything is pure Python generating text files.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_PARTS_DIR = os.path.join(os.path.dirname(__file__), "3d_parts")
_LIBRARY_FILE = os.path.join(_DATA_DIR, "parts_library.json")


# ---------------------------------------------------------------------------
# Part templates — parametric OpenSCAD code generators
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict[str, Any]] = {
    "box": {
        "description": "Simple box/enclosure with optional lid",
        "params": {
            "width": {"type": "number", "default": 60, "unit": "mm"},
            "depth": {"type": "number", "default": 40, "unit": "mm"},
            "height": {"type": "number", "default": 30, "unit": "mm"},
            "wall_thickness": {"type": "number", "default": 2, "unit": "mm"},
            "lid": {"type": "bool", "default": True},
            "corner_radius": {"type": "number", "default": 2, "unit": "mm"},
        },
    },
    "bracket": {
        "description": "L-shaped mounting bracket with screw holes",
        "params": {
            "width": {"type": "number", "default": 30, "unit": "mm"},
            "height": {"type": "number", "default": 40, "unit": "mm"},
            "depth": {"type": "number", "default": 20, "unit": "mm"},
            "thickness": {"type": "number", "default": 3, "unit": "mm"},
            "hole_diameter": {"type": "number", "default": 4, "unit": "mm"},
            "holes_per_side": {"type": "number", "default": 2},
        },
    },
    "cylinder_mount": {
        "description": "Cylindrical mount/holder (for pipes, rods, etc.)",
        "params": {
            "inner_diameter": {"type": "number", "default": 20, "unit": "mm"},
            "outer_diameter": {"type": "number", "default": 30, "unit": "mm"},
            "height": {"type": "number", "default": 25, "unit": "mm"},
            "base_width": {"type": "number", "default": 40, "unit": "mm"},
            "base_thickness": {"type": "number", "default": 3, "unit": "mm"},
            "screw_holes": {"type": "bool", "default": True},
        },
    },
    "gear": {
        "description": "Spur gear with configurable teeth",
        "params": {
            "num_teeth": {"type": "number", "default": 20},
            "module_val": {"type": "number", "default": 2, "unit": "mm"},
            "thickness": {"type": "number", "default": 5, "unit": "mm"},
            "bore_diameter": {"type": "number", "default": 6, "unit": "mm"},
            "pressure_angle": {"type": "number", "default": 20, "unit": "deg"},
        },
    },
    "phone_stand": {
        "description": "Adjustable phone/tablet stand",
        "params": {
            "width": {"type": "number", "default": 80, "unit": "mm"},
            "depth": {"type": "number", "default": 60, "unit": "mm"},
            "angle": {"type": "number", "default": 65, "unit": "deg"},
            "thickness": {"type": "number", "default": 3, "unit": "mm"},
            "lip_height": {"type": "number", "default": 10, "unit": "mm"},
        },
    },
    "cable_clip": {
        "description": "Adhesive cable management clip",
        "params": {
            "cable_diameter": {"type": "number", "default": 6, "unit": "mm"},
            "base_width": {"type": "number", "default": 15, "unit": "mm"},
            "base_height": {"type": "number", "default": 3, "unit": "mm"},
            "clip_gap": {"type": "number", "default": 2, "unit": "mm"},
        },
    },
    "hinge": {
        "description": "Print-in-place hinge",
        "params": {
            "width": {"type": "number", "default": 30, "unit": "mm"},
            "leaf_length": {"type": "number", "default": 25, "unit": "mm"},
            "thickness": {"type": "number", "default": 2, "unit": "mm"},
            "pin_diameter": {"type": "number", "default": 3, "unit": "mm"},
            "clearance": {"type": "number", "default": 0.3, "unit": "mm"},
        },
    },
    "spacer": {
        "description": "Cylindrical spacer/standoff",
        "params": {
            "outer_diameter": {"type": "number", "default": 10, "unit": "mm"},
            "inner_diameter": {"type": "number", "default": 4, "unit": "mm"},
            "height": {"type": "number", "default": 8, "unit": "mm"},
        },
    },
}


# ---------------------------------------------------------------------------
# OpenSCAD code generators
# ---------------------------------------------------------------------------

def _generate_box(params: dict[str, Any]) -> str:
    w = params.get("width", 60)
    d = params.get("depth", 40)
    h = params.get("height", 30)
    t = params.get("wall_thickness", 2)
    lid = params.get("lid", True)
    r = params.get("corner_radius", 2)

    code = f"""// Parametric Box — {w}x{d}x{h}mm, wall={t}mm
// Generated by Cornerstone AI 3D Print Module

$fn = 50;

module rounded_box(w, d, h, r) {{
    minkowski() {{
        cube([w - 2*r, d - 2*r, h - r], center=false);
        cylinder(r=r, h=r);
    }}
}}

module box_body() {{
    difference() {{
        rounded_box({w}, {d}, {h}, {r});
        translate([{t}, {t}, {t}])
            rounded_box({w} - 2*{t}, {d} - 2*{t}, {h}, {r});
    }}
}}

box_body();
"""
    if lid:
        code += f"""
// Lid — print separately
module lid() {{
    translate([0, {d} + 10, 0]) {{
        // Outer shell
        rounded_box({w}, {d}, {t} + 1, {r});
        // Inner lip
        translate([{t} - 0.2, {t} - 0.2, {t}])
            rounded_box({w} - 2*{t} + 0.4, {d} - 2*{t} + 0.4, 1, {r});
    }}
}}

lid();
"""
    return code


def _generate_bracket(params: dict[str, Any]) -> str:
    w = params.get("width", 30)
    h = params.get("height", 40)
    d = params.get("depth", 20)
    t = params.get("thickness", 3)
    hole_d = params.get("hole_diameter", 4)
    holes = params.get("holes_per_side", 2)

    code = f"""// L-Bracket — {w}x{h}x{d}mm, {t}mm thick
// Generated by Cornerstone AI 3D Print Module

$fn = 40;

module bracket() {{
    difference() {{
        union() {{
            // Vertical plate
            cube([{w}, {t}, {h}]);
            // Horizontal plate
            cube([{w}, {d}, {t}]);
            // Fillet
            translate([0, {t}, {t}])
                rotate([0, 90, 0])
                    linear_extrude(height={w})
                        polygon([[0,0], [{t}*2, 0], [0, {t}*2]]);
        }}
"""
    # Vertical holes
    for i in range(holes):
        y_off = t / 2
        z_off = t + (h - t) / (holes + 1) * (i + 1)
        x_off = w / (holes + 1) * (i + 1)
        code += f"""
        // Vertical plate hole {i + 1}
        translate([{x_off}, -{t}, {z_off}])
            rotate([-90, 0, 0])
                cylinder(d={hole_d}, h={t} * 3);
"""

    # Horizontal holes
    for i in range(holes):
        x_off = w / (holes + 1) * (i + 1)
        y_off = d / (holes + 1) * (i + 1)
        code += f"""
        // Horizontal plate hole {i + 1}
        translate([{x_off}, {y_off}, -{t}])
            cylinder(d={hole_d}, h={t} * 3);
"""

    code += """    }
}

bracket();
"""
    return code


def _generate_cylinder_mount(params: dict[str, Any]) -> str:
    inner_d = params.get("inner_diameter", 20)
    outer_d = params.get("outer_diameter", 30)
    h = params.get("height", 25)
    base_w = params.get("base_width", 40)
    base_t = params.get("base_thickness", 3)
    screws = params.get("screw_holes", True)

    code = f"""// Cylinder Mount — ID={inner_d}mm, OD={outer_d}mm, H={h}mm
// Generated by Cornerstone AI 3D Print Module

$fn = 60;

module mount() {{
    difference() {{
        union() {{
            // Base plate
            translate([-{base_w}/2, -{base_w}/2, 0])
                cube([{base_w}, {base_w}, {base_t}]);
            // Cylinder body
            cylinder(d={outer_d}, h={h});
        }}
        // Inner bore
        translate([0, 0, -1])
            cylinder(d={inner_d}, h={h} + 2);
"""
    if screws:
        offset = base_w / 2 - 5
        code += f"""
        // Screw holes
        for (pos = [[-{offset}, -{offset}], [-{offset}, {offset}],
                     [{offset}, -{offset}], [{offset}, {offset}]]) {{
            translate([pos[0], pos[1], -1])
                cylinder(d=3.5, h={base_t} + 2);
            // Countersink
            translate([pos[0], pos[1], {base_t} - 1.5])
                cylinder(d=6, h=2);
        }}
"""
    code += """    }
}

mount();
"""
    return code


def _generate_gear(params: dict[str, Any]) -> str:
    n = params.get("num_teeth", 20)
    m = params.get("module_val", 2)
    t = params.get("thickness", 5)
    bore = params.get("bore_diameter", 6)
    pa = params.get("pressure_angle", 20)

    code = f"""// Spur Gear — {n} teeth, module={m}, thickness={t}mm
// Generated by Cornerstone AI 3D Print Module
// NOTE: For precision gears, verify tooth profile in OpenSCAD preview

$fn = 100;

module gear(num_teeth={n}, module_val={m}, thickness={t},
            bore_d={bore}, pressure_angle={pa}) {{

    pitch_r = num_teeth * module_val / 2;
    outer_r = pitch_r + module_val;
    root_r = pitch_r - 1.25 * module_val;

    difference() {{
        linear_extrude(height=thickness) {{
            difference() {{
                // Simplified gear profile using circles
                union() {{
                    circle(r=pitch_r);
                    for (i = [0:num_teeth-1]) {{
                        rotate([0, 0, i * 360 / num_teeth])
                            translate([pitch_r, 0])
                                circle(d=module_val * 1.8);
                    }}
                }}
            }}
        }}
        // Center bore
        translate([0, 0, -1])
            cylinder(d=bore_d, h=thickness + 2);
    }}
}}

gear();
"""
    return code


def _generate_phone_stand(params: dict[str, Any]) -> str:
    w = params.get("width", 80)
    d = params.get("depth", 60)
    angle = params.get("angle", 65)
    t = params.get("thickness", 3)
    lip = params.get("lip_height", 10)

    code = f"""// Phone Stand — {w}mm wide, {angle}deg angle
// Generated by Cornerstone AI 3D Print Module

$fn = 40;

module phone_stand() {{
    // Base
    cube([{w}, {d}, {t}]);

    // Back support
    translate([0, {d} - {t}, 0])
        rotate([{90 - angle}, 0, 0])
            cube([{w}, {t}, {d} * 1.2]);

    // Front lip
    cube([{w}, {t}, {lip}]);

    // Side supports
    for (x = [0, {w} - {t}]) {{
        translate([x, 0, 0])
            linear_extrude(height={t})
                polygon([[0, 0], [{t}, 0], [{t}, {d}], [0, {d}]]);
    }}
}}

phone_stand();
"""
    return code


def _generate_cable_clip(params: dict[str, Any]) -> str:
    cd = params.get("cable_diameter", 6)
    bw = params.get("base_width", 15)
    bh = params.get("base_height", 3)
    gap = params.get("clip_gap", 2)

    code = f"""// Cable Clip — {cd}mm cable diameter
// Generated by Cornerstone AI 3D Print Module

$fn = 50;

module cable_clip() {{
    // Base
    translate([-{bw}/2, -{bw}/2, 0])
        cube([{bw}, {bw}, {bh}]);

    // Clip ring
    difference() {{
        cylinder(d={cd} + 4, h={bh} + {cd}/2 + 2);
        translate([0, 0, {bh}])
            cylinder(d={cd}, h={cd} + 4);
        // Opening gap
        translate([-{gap}/2, 0, {bh} + {cd}/4])
            cube([{gap}, {cd}, {cd}]);
    }}
}}

cable_clip();
"""
    return code


def _generate_hinge(params: dict[str, Any]) -> str:
    w = params.get("width", 30)
    ll = params.get("leaf_length", 25)
    t = params.get("thickness", 2)
    pd = params.get("pin_diameter", 3)
    cl = params.get("clearance", 0.3)

    code = f"""// Print-in-Place Hinge — {w}mm wide
// Generated by Cornerstone AI 3D Print Module
// Print flat, no supports needed

$fn = 40;

module hinge() {{
    pin_r = {pd} / 2;

    // Left leaf
    translate([-{ll}, -{w}/2, 0]) {{
        cube([{ll}, {w}, {t}]);
        // Knuckles (odd)
        for (i = [0:2:{w}/{pd}/2]) {{
            translate([{ll}, i * {pd} * 2 + {pd}/2, {t}])
                rotate([0, 90, 0])
                    translate([0, 0, -{pd}])
                        cylinder(r=pin_r + {t}/2, h={pd} * 2 - {cl});
        }}
    }}

    // Right leaf
    translate([0, -{w}/2, 0]) {{
        cube([{ll}, {w}, {t}]);
        // Knuckles (even)
        for (i = [0:2:{w}/{pd}/2 - 1]) {{
            translate([0, (i * 2 + 1) * {pd} + {pd}/2, {t}])
                rotate([0, 90, 0])
                    translate([0, 0, -{pd}])
                        cylinder(r=pin_r + {t}/2, h={pd} * 2 - {cl});
        }}
    }}

    // Pin
    translate([0, -{w}/2, {t}])
        rotate([-90, 0, 0])
            cylinder(r=pin_r - {cl}, h={w});
}}

hinge();
"""
    return code


def _generate_spacer(params: dict[str, Any]) -> str:
    od = params.get("outer_diameter", 10)
    inner_d = params.get("inner_diameter", 4)
    h = params.get("height", 8)

    code = f"""// Spacer/Standoff — OD={od}mm, ID={inner_d}mm, H={h}mm
// Generated by Cornerstone AI 3D Print Module

$fn = 60;

difference() {{
    cylinder(d={od}, h={h});
    translate([0, 0, -1])
        cylinder(d={inner_d}, h={h} + 2);
}}
"""
    return code


_GENERATORS: dict[str, Any] = {
    "box": _generate_box,
    "bracket": _generate_bracket,
    "cylinder_mount": _generate_cylinder_mount,
    "gear": _generate_gear,
    "phone_stand": _generate_phone_stand,
    "cable_clip": _generate_cable_clip,
    "hinge": _generate_hinge,
    "spacer": _generate_spacer,
}


# ---------------------------------------------------------------------------
# Tool functions (called by the agent)
# ---------------------------------------------------------------------------

def generate_3d_part(
    part_type: str = "",
    name: str = "",
    params: str = "{}",
    custom_scad: str = "",
) -> str:
    """Generate a 3D printable part (.scad file).

    If *part_type* matches a template, generates from template with *params*.
    If *custom_scad* is provided, writes raw OpenSCAD code directly.
    """
    os.makedirs(_PARTS_DIR, exist_ok=True)

    if custom_scad:
        # Custom OpenSCAD code from the agent
        filename = name or f"custom_{int(time.time())}"
        if not filename.endswith(".scad"):
            filename += ".scad"
        filepath = os.path.join(_PARTS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(custom_scad)
        _save_to_library(filename, "custom", {}, filepath)
        return (
            f"3D part saved: {filepath}\n"
            f"To preview and export:\n"
            f"  1. Install OpenSCAD: https://openscad.org/downloads.html\n"
            f"  2. Open {filename} in OpenSCAD\n"
            f"  3. Press F5 to preview, F6 to render\n"
            f"  4. File > Export > STL to get a printable file"
        )

    if not part_type:
        available = ", ".join(sorted(TEMPLATES.keys()))
        return (
            f"Error: specify part_type or custom_scad. "
            f"Available templates: {available}"
        )

    if part_type not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES.keys()))
        return (
            f"Error: unknown part_type '{part_type}'. "
            f"Available: {available}"
        )

    # Parse params
    try:
        param_dict = json.loads(params) if isinstance(params, str) else params
    except json.JSONDecodeError:
        param_dict = {}

    # Merge with defaults
    template = TEMPLATES[part_type]
    final_params: dict[str, Any] = {}
    for key, spec in template["params"].items():
        final_params[key] = param_dict.get(key, spec["default"])

    # Generate code
    generator = _GENERATORS.get(part_type)
    if generator is None:
        return f"Error: no generator for '{part_type}'"

    scad_code = generator(final_params)

    # Save file
    filename = name or f"{part_type}_{int(time.time())}"
    if not filename.endswith(".scad"):
        filename += ".scad"
    filepath = os.path.join(_PARTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(scad_code)

    _save_to_library(filename, part_type, final_params, filepath)

    return (
        f"3D part generated: {filepath}\n"
        f"Template: {part_type} — {template['description']}\n"
        f"Parameters: {json.dumps(final_params)}\n\n"
        f"To preview and export to STL:\n"
        f"  1. Install OpenSCAD: https://openscad.org/downloads.html\n"
        f"  2. Open {filename} in OpenSCAD\n"
        f"  3. Press F5 to preview, F6 to render\n"
        f"  4. File > Export > STL to get a printable file\n"
        f"  5. Open STL in your slicer (Cura, PrusaSlicer, etc.)\n"
        f"  6. Slice and print!"
    )


def list_3d_templates() -> str:
    """List all available 3D part templates."""
    lines = ["Available 3D part templates:\n"]
    for name, tmpl in sorted(TEMPLATES.items()):
        params_str = ", ".join(
            f"{k}={v['default']}{v.get('unit', '')}"
            for k, v in tmpl["params"].items()
        )
        lines.append(f"  {name}: {tmpl['description']}")
        lines.append(f"    Parameters: {params_str}")
        lines.append("")
    return "\n".join(lines)


def list_3d_parts() -> str:
    """List all generated 3D parts."""
    library = _load_library()
    if not library:
        return "No 3D parts generated yet. Use generate_3d_part to create one."

    lines = [f"Generated 3D parts ({len(library)}):\n"]
    for i, part in enumerate(library):
        lines.append(
            f"  {i}. {part.get('filename', '?')} "
            f"({part.get('template', 'custom')}) — "
            f"{part.get('filepath', '?')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Library persistence
# ---------------------------------------------------------------------------

def _load_library() -> list[dict[str, Any]]:
    if os.path.isfile(_LIBRARY_FILE):
        try:
            with open(_LIBRARY_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_to_library(
    filename: str,
    template: str,
    params: dict[str, Any],
    filepath: str,
) -> None:
    library = _load_library()
    library.append({
        "filename": filename,
        "template": template,
        "params": params,
        "filepath": filepath,
        "created_at": time.time(),
    })
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_LIBRARY_FILE, "w", encoding="utf-8") as fh:
        json.dump(library, fh, indent=2, default=str)


# ---------------------------------------------------------------------------
# Display helpers (for /3dprint command)
# ---------------------------------------------------------------------------

def print_3d_status() -> None:
    """Print 3D printing module status."""
    library = _load_library()
    table = Table(title="3D Printing Module")
    table.add_column("Item", style="bold cyan")
    table.add_column("Value")
    table.add_row("Templates available", str(len(TEMPLATES)))
    table.add_row("Parts generated", str(len(library)))
    table.add_row("Parts directory", _PARTS_DIR)
    table.add_row(
        "Templates",
        ", ".join(sorted(TEMPLATES.keys())),
    )
    console.print(table)

    if library:
        parts_table = Table(title="Generated Parts")
        parts_table.add_column("#", style="bold")
        parts_table.add_column("File")
        parts_table.add_column("Template", style="cyan")
        parts_table.add_column("Path", style="dim")
        for i, part in enumerate(library[-10:]):
            parts_table.add_row(
                str(i),
                part.get("filename", "?"),
                part.get("template", "custom"),
                part.get("filepath", "?")[:60],
            )
        console.print(parts_table)
