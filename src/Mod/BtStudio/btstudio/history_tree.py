# SPDX-License-Identifier: LGPL-2.1-or-later

"""Floating feature history: Body Tip slider (Fusion timeline analogue)."""

from __future__ import annotations

from .qtutil import app_gui, qt

_DOCK = None


def _body_features(body):
    feats = []
    for obj in getattr(body, "Group", []) or []:
        tid = getattr(obj, "TypeId", "")
        if tid.startswith("App::Origin") or "OriginFeature" in tid:
            continue
        feats.append(obj)
    return feats


def _active_body():
    _, Gui = app_gui()
    try:
        return Gui.ActiveDocument.ActiveView.getActiveObject("pdbody")
    except Exception:
        return None


class HistoryDock:
    def __init__(self):
        QtCore, QtGui, QtWidgets = qt()
        self.widget = QtWidgets.QDockWidget("Feature history")
        self.widget.setObjectName("BtStudioHistory")
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        self.label = QtWidgets.QLabel("Activate a PartDesign Body.")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.valueChanged.connect(self._on_slide)
        layout.addWidget(self.slider)
        refresh = QtWidgets.QPushButton("Refresh from body")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        hint = QtWidgets.QLabel(
            "Drag to roll Tip back. DAG View (View → Panels) is the full graph."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        self.widget.setWidget(panel)
        self._feats = []

    def attach(self) -> None:
        _, Gui = app_gui()
        QtCore, QtGui, QtWidgets = qt()
        mw = Gui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.widget)
        self.widget.show()
        self.refresh()

    def refresh(self) -> None:
        body = _active_body()
        if body is None:
            self._feats = []
            self.label.setText("Activate a PartDesign Body.")
            self.slider.setEnabled(False)
            return
        self._feats = _body_features(body)
        self.slider.setEnabled(bool(self._feats))
        self.slider.setMinimum(0)
        self.slider.setMaximum(max(len(self._feats) - 1, 0))
        tip = getattr(body, "Tip", None)
        idx = self._feats.index(tip) if tip in self._feats else len(self._feats) - 1
        self.slider.blockSignals(True)
        self.slider.setValue(max(idx, 0))
        self.slider.blockSignals(False)
        self.label.setText(f"{body.Label}: Tip → {tip.Label if tip else '—'}")

    def _on_slide(self, value: int) -> None:
        App, _ = app_gui()
        body = _active_body()
        if body is None or not self._feats:
            return
        value = max(0, min(value, len(self._feats) - 1))
        feat = self._feats[value]
        try:
            body.Tip = feat
            App.ActiveDocument.recompute()
            self.label.setText(f"{body.Label}: Tip → {feat.Label}")
        except Exception as exc:
            self.label.setText(str(exc))


def show_history() -> None:
    global _DOCK
    if _DOCK is None:
        _DOCK = HistoryDock()
        _DOCK.attach()
    else:
        _DOCK.widget.show()
        _DOCK.refresh()
