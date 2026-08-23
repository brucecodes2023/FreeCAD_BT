# SPDX-License-Identifier: LGPL-2.1-or-later
# /**************************************************************************
#                                                                           *
#    Copyright (c) 2026 FreeCAD_BT contributors                             *
#                                                                           *
#    This file is part of FreeCAD.                                          *
#                                                                           *
# **************************************************************************/

"""Unit tests for Assembly edit-part helpers (no GUI required)."""

import unittest
from unittest.mock import MagicMock

import FreeCAD as App

# Import under test; GuiUp may be false in headless App tests.
import CommandEditPart


class TestFindEditableBody(unittest.TestCase):
    def test_body_returns_self(self):
        body = MagicMock()
        body.TypeId = "PartDesign::Body"
        self.assertIs(CommandEditPart.findEditableBody(body), body)

    def test_part_returns_first_body(self):
        body = MagicMock()
        body.TypeId = "PartDesign::Body"
        part = MagicMock()
        part.TypeId = "App::Part"
        part.Group = [MagicMock(TypeId="App::Origin"), body]
        self.assertIs(CommandEditPart.findEditableBody(part), body)

    def test_none_and_unknown(self):
        self.assertIsNone(CommandEditPart.findEditableBody(None))
        box = MagicMock()
        box.TypeId = "Part::Box"
        self.assertIsNone(CommandEditPart.findEditableBody(box))


class TestResolveLinkedTarget(unittest.TestCase):
    def test_plain_object(self):
        obj = MagicMock()
        obj.isDerivedFrom = lambda t: False
        self.assertIs(CommandEditPart.resolveLinkedTarget(obj), obj)

    def test_link_uses_linked_object(self):
        linked = MagicMock(Name="Target")
        link = MagicMock()
        link.isDerivedFrom = lambda t: t in ("App::Link",)
        link.getLinkedObject = MagicMock(return_value=linked)
        # UtilsAssembly.isLink may also be true; keep TypeId consistent.
        link.TypeId = "App::Link"
        link.ElementCount = 0
        self.assertIs(CommandEditPart.resolveLinkedTarget(link), linked)

    def test_none(self):
        self.assertIsNone(CommandEditPart.resolveLinkedTarget(None))


class TestEditSessionState(unittest.TestCase):
    def tearDown(self):
        CommandEditPart.clearEditSession()

    def test_session_starts_empty(self):
        CommandEditPart.clearEditSession()
        self.assertIsNone(CommandEditPart.getEditSession())


if __name__ == "__main__":
    unittest.main()
