# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD_BT contributors                            *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This library is free software; you can redistribute it and/or         *
# *   modify it under the terms of the GNU Library General Public           *
# *   License as published by the Free Software Foundation; either          *
# *   version 2 of the License, or (at your option) any later version.      *
# *                                                                         *
# *   This library  is distributed in the hope that it will be useful,      *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this library; see the file COPYING.LIB. If not,    *
# *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
# *   Suite 330, Boston, MA  02111-1307, USA                                *
# *                                                                         *
# ***************************************************************************/
"""Registry for first-principles / custom physics modules (COMSOL-like extensibility).

Workbenches and addons register equation factories that **First Principles Study**
and the **Guided Study Wizard** discover without hard-coding every PDE.

Factory contract
----------------
``factory(doc, solver)`` receives the active document and an Elmer (or other)
solver object already in an analysis. It should create equation / physics
document objects, typically via ``ObjectsFem.makeEquation*``, attach them to
``solver``, and return the created equation object (or a list).

Public API
----------
- ``register(name, factory, ...)`` — add or replace a module
- ``unregister(name)`` — remove one entry
- ``list_modules(tag=..., backend=...)`` — discover available modules
- ``default_module_names()`` — names pre-selected in First Principles Study
- ``get(name)`` / ``apply(name, *args, **kwargs)`` — lookup / invoke
- ``create_first_principles_equations(doc, solver, module_names=...)`` —
  attach selected equations
- ``format_catalog()`` — human-readable list for dialogs / console

Example (addon ``Init.py`` or workbench ``InitGui.py``)::

    from femtools import physics_modules

    def make_my_equation(doc, solver):
        import ObjectsFem
        # Create Elmer/CalculiX equation objects on *solver*
        return ObjectsFem.makeEquationHeat(doc, solver)

    physics_modules.register(
        "MyThermoelasticHeat",
        make_my_equation,
        description="Custom heat equation for battery pack FEA",
        tags=("elmer", "thermal", "drone"),
        backend="elmer",
        default=False,
    )

After registration, the module appears in First Principles Study's equation
picker and in the Guided Study Wizard module list. Prefer tags such as
``structural``, ``thermal``, ``drone``, ``robot`` so UI filters stay useful.

Do **not** register fake CFD here — FreeCAD FEM has no production CFD path yet;
use structural/thermal CalculiX presets (see ``femtools.study_presets``) for
drone frame / electronics heat cases until a real fluid solver is wired.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

__title__ = "FEM physics module registry"
__author__ = "FreeCAD_BT"
__url__ = "https://www.freecad.org"


@dataclass(frozen=True)
class PhysicsModule:
    """One discoverable PDE / physics factory.

    Attributes:
        name: Stable registry key (shown in UI).
        factory: Callable ``(doc, solver) -> equation_or_list``.
        description: Short user-facing summary.
        tags: Filter labels (``elmer``, ``structural``, ``thermal``, …).
        backend: Solver family hint (``elmer``, ``calculix``, ``custom``, …).
        default: If True, pre-selected when First Principles Study opens.
    """

    name: str
    factory: Callable
    description: str = ""
    tags: tuple[str, ...] = ()
    backend: str = ""
    default: bool = False


_REGISTRY: dict[str, PhysicsModule] = {}


def register(
    name: str,
    factory: Callable,
    description: str = "",
    tags: Iterable[str] | None = None,
    backend: str = "",
    default: bool = False,
) -> PhysicsModule:
    """Register or replace a physics module factory.

    Returns the stored :class:`PhysicsModule`. Raises ``ValueError`` if *name*
    is empty or *factory* is not callable.
    """
    if not name or not callable(factory):
        raise ValueError("physics module requires a non-empty name and callable factory")
    tag_tuple = tuple(tags or ())
    backend_key = (backend or "").strip().lower()
    if backend_key and backend_key not in tag_tuple:
        tag_tuple = tag_tuple + (backend_key,)
    mod = PhysicsModule(
        name=name,
        factory=factory,
        description=description or name,
        tags=tag_tuple,
        backend=backend_key,
        default=bool(default),
    )
    _REGISTRY[name] = mod
    return mod


def unregister(name: str) -> None:
    """Remove a registered module; no-op if missing."""
    _REGISTRY.pop(name, None)


def clear_registry(*, keep_builtin: bool = False) -> None:
    """Clear the registry (tests / reload). Optionally re-register builtins."""
    _REGISTRY.clear()
    if keep_builtin:
        ensure_builtin_elmer_modules()


def list_modules(
    tag: str | None = None,
    backend: str | None = None,
) -> list[PhysicsModule]:
    """Return registered modules, optionally filtered by tag and/or backend."""
    ensure_builtin_elmer_modules()
    modules = list(_REGISTRY.values())
    if tag:
        modules = [m for m in modules if tag in m.tags]
    if backend:
        be = backend.strip().lower()
        modules = [m for m in modules if m.backend == be or be in m.tags]
    return sorted(modules, key=lambda m: m.name.lower())


def list_module_names(tag: str | None = None, backend: str | None = None) -> list[str]:
    """Names only — convenient for command strings and tests."""
    return [m.name for m in list_modules(tag=tag, backend=backend)]


def default_module_names() -> list[str]:
    """Names marked ``default=True`` (fallback: Elmer elasticity + heat)."""
    ensure_builtin_elmer_modules()
    names = [m.name for m in list_modules() if m.default]
    if names:
        return names
    return ["ElmerElasticity", "ElmerHeat"]


def get(name: str) -> PhysicsModule | None:
    ensure_builtin_elmer_modules()
    return _REGISTRY.get(name)


def apply(name: str, *args, **kwargs):
    """Invoke a registered factory; raises ``KeyError`` if missing."""
    ensure_builtin_elmer_modules()
    mod = _REGISTRY[name]
    return mod.factory(*args, **kwargs)


def format_catalog(tag: str | None = None, backend: str | None = None) -> str:
    """Multi-line catalog for dialogs and the Report view."""
    lines = []
    for mod in list_modules(tag=tag, backend=backend):
        mark = "*" if mod.default else " "
        be = mod.backend or "-"
        tag_str = ",".join(mod.tags) if mod.tags else "-"
        lines.append(f"[{mark}] {mod.name} ({be}) - {mod.description} [{tag_str}]")
    if not lines:
        return "(no physics modules registered)"
    return "\n".join(lines)


def ensure_builtin_elmer_modules() -> None:
    """Idempotent registration of built-in Elmer equation factories.

    Defaults for First Principles Study: linear elasticity + heat.
    Additional Elmer equations are registered but not pre-selected so users
    (and addons) can opt in without inventing unsupported solvers.
    """
    if "ElmerElasticity" not in _REGISTRY:

        def _elasticity(doc, solver):
            import ObjectsFem

            return ObjectsFem.makeEquationElasticity(doc, solver)

        register(
            "ElmerElasticity",
            _elasticity,
            description="Linear elasticity (Elmer PDE) - frames, mounts, static load",
            tags=("elmer", "structural", "builtin", "drone", "robot"),
            backend="elmer",
            default=True,
        )

    if "ElmerHeat" not in _REGISTRY:

        def _heat(doc, solver):
            import ObjectsFem

            return ObjectsFem.makeEquationHeat(doc, solver)

        register(
            "ElmerHeat",
            _heat,
            description="Heat transfer (Elmer PDE) - electronics, motors, packs",
            tags=("elmer", "thermal", "builtin", "drone", "robot"),
            backend="elmer",
            default=True,
        )

    _register_optional_elmer_if_missing()


def _register_optional_elmer_if_missing() -> None:
    """Extra Elmer PDEs available for opt-in; not First Principles defaults."""

    optionals = (
        (
            "ElmerElectrostatic",
            "makeEquationElectrostatic",
            "Electrostatics (Elmer PDE)",
            ("elmer", "electromagnetic", "builtin"),
        ),
        (
            "ElmerFlux",
            "makeEquationFlux",
            "Flux / potential gradients (Elmer PDE)",
            ("elmer", "flux", "builtin"),
        ),
    )
    for name, maker, desc, tags in optionals:
        if name in _REGISTRY:
            continue

        def _factory(doc, solver, _maker=maker):
            import ObjectsFem

            return getattr(ObjectsFem, _maker)(doc, solver)

        register(
            name,
            _factory,
            description=desc,
            tags=tags,
            backend="elmer",
            default=False,
        )


def create_first_principles_equations(
    doc,
    solver,
    module_names: Iterable[str] | None = None,
):
    """Attach equation objects for the given module names.

    Default: modules with ``default=True`` (builtin elasticity + heat).
    Unknown names raise ``KeyError``.
    """
    ensure_builtin_elmer_modules()
    names = list(module_names) if module_names is not None else default_module_names()
    created = []
    for name in names:
        created.append(apply(name, doc, solver))
    return created
