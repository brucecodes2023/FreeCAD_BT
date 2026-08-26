# SPDX-License-Identifier: LGPL-2.1-or-later

"""FEM entry point — opens the shared Analysis walkthrough on Structures."""

from __future__ import annotations

from .analysis_wizard import AnalysisWizardDock, show_wizard as show_analysis_wizard
from .core import PHYSICS_STRUCTURES

# Back-compat alias: older code imported WizardDock.
WizardDock = AnalysisWizardDock


def show_wizard() -> None:
    show_analysis_wizard(PHYSICS_STRUCTURES)
