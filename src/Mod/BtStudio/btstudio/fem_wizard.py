# SPDX-License-Identifier: LGPL-2.1-or-later

"""Right-sidebar FEM checklist (ANSYS Mechanical-style walkthrough)."""

from __future__ import annotations

from .core import FEM_WIZARD_STEPS
from .qtutil import app_gui, qt

_DOCK = None


class WizardDock:
    def __init__(self):
        QtCore, QtGui, QtWidgets = qt()
        self.widget = QtWidgets.QDockWidget("FEM walkthrough")
        self.widget.setObjectName("BtStudioFemWizard")
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        intro = QtWidgets.QLabel(
            "Work top to bottom. Each Run button calls the stock FEM command "
            "when there is one. Mesh uses BtStudio Auto Mesh (Gmsh, h = D/20)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.checks = []
        for i, step in enumerate(FEM_WIZARD_STEPS, start=1):
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
        docs = QtWidgets.QPushButton("Open FEM theory guide")
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
            if command == "BtStudio_FemAutoMesh":
                from .fem_automesh import auto_mesh

                auto_mesh()
            else:
                Gui.runCommand(command)
            chk.setChecked(True)
        except Exception as exc:
            Gui.getMainWindow().statusBar().showMessage(str(exc), 8000)

    def _open_docs(self) -> None:
        import os
        from .qtutil import qt

        QtCore, QtGui, QtWidgets = qt()
        here = os.path.join(os.path.dirname(__file__), "..", "docs", "FEM_THEORY_GUIDE.md")
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.abspath(here)))


def show_wizard() -> None:
    global _DOCK
    if _DOCK is None:
        _DOCK = WizardDock()
        _DOCK.attach()
    else:
        _DOCK.widget.show()
        _DOCK.widget.raise_()
