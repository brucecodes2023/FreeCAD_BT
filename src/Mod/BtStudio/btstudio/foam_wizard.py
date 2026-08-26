# SPDX-License-Identifier: LGPL-2.1-or-later

"""Right-sidebar OpenFOAM checklist (Fluent-like case walkthrough)."""

from __future__ import annotations

from .core import FOAM_WIZARD_STEPS
from .qtutil import app_gui, qt

_DOCK = None


class FoamWizardDock:
    def __init__(self):
        QtCore, QtGui, QtWidgets = qt()
        self.widget = QtWidgets.QDockWidget("OpenFOAM walkthrough")
        self.widget.setObjectName("BtStudioFoamWizard")
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        intro = QtWidgets.QLabel(
            "Writes a simpleFoam case tree (0/, constant/, system/) from the "
            "selected solid's bounding box. Does not run blockMesh or the solver."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.checks = []
        for i, step in enumerate(FOAM_WIZARD_STEPS, start=1):
            box = QtWidgets.QGroupBox(f"{i}. {step['title']}")
            v = QtWidgets.QVBoxLayout(box)
            hint = QtWidgets.QLabel(step["hint"])
            hint.setWordWrap(True)
            v.addWidget(hint)
            row = QtWidgets.QHBoxLayout()
            chk = QtWidgets.QCheckBox("Done")
            self.checks.append(chk)
            row.addWidget(chk)
            if step["command"]:
                btn = QtWidgets.QPushButton("Run")
                btn.clicked.connect(lambda _=False, c=step["command"], k=chk: self._run(c, k))
                row.addWidget(btn)
            row.addStretch(1)
            v.addLayout(row)
            layout.addWidget(box)
        docs = QtWidgets.QPushButton("Open OpenFOAM architecture")
        docs.clicked.connect(self._open_docs)
        layout.addWidget(docs)
        layout.addStretch(1)
        self.widget.setWidget(panel)

    def attach(self) -> None:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.widget)
        tasks = [
            d
            for d in mw.findChildren(QtWidgets.QDockWidget)
            if (d.windowTitle() or "").lower().startswith("task")
        ]
        if tasks:
            mw.tabifyDockWidget(tasks[0], self.widget)
        self.widget.show()
        self.widget.raise_()

    def _run(self, command: str, chk) -> None:
        _, Gui = app_gui()
        try:
            if command == "BtStudio_FoamNewCase":
                from solvers.foam_objects import make_foam_case

                make_foam_case()
            elif command == "BtStudio_FoamWriteCase":
                from solvers.foam_objects import write_foam_case

                write_foam_case()
            else:
                Gui.runCommand(command)
            chk.setChecked(True)
        except Exception as exc:
            Gui.getMainWindow().statusBar().showMessage(str(exc), 8000)

    def _open_docs(self) -> None:
        import os

        QtCore, QtGui, QtWidgets = qt()
        here = os.path.join(os.path.dirname(__file__), "..", "docs", "OPENFOAM_ARCHITECTURE.md")
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.abspath(here)))


def show_wizard() -> None:
    global _DOCK
    if _DOCK is None:
        _DOCK = FoamWizardDock()
        _DOCK.attach()
    else:
        _DOCK.widget.show()
        _DOCK.widget.raise_()
