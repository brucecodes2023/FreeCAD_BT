# SPDX-License-Identifier: LGPL-2.1-or-later

"""OpenFOAM entry point — opens the shared Analysis walkthrough on Fluids."""

from __future__ import annotations

from .analysis_wizard import AnalysisWizardDock, show_wizard as show_analysis_wizard
from .core import PHYSICS_FLUIDS

# Back-compat alias: older code imported FoamWizardDock.
FoamWizardDock = AnalysisWizardDock


def show_wizard() -> None:
    show_analysis_wizard(PHYSICS_FLUIDS)
