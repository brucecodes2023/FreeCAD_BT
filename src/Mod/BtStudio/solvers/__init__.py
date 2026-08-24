# SPDX-License-Identifier: LGPL-2.1-or-later

from .registry import PHYSICS, by_domain, planned_backends
from .openfoam import case_tree

__all__ = ["PHYSICS", "by_domain", "planned_backends", "case_tree"]
