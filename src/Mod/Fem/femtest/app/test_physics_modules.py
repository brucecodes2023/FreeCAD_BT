# SPDX-License-Identifier: LGPL-2.1-or-later

# ***************************************************************************
# *   Copyright (c) 2026 FreeCAD contributors                              *
# *                                                                         *
# *   This file is part of FreeCAD.                                         *
# *                                                                         *
# *   FreeCAD is free software: you can redistribute it and/or modify it    *
# *   under the terms of the GNU Lesser General Public License as           *
# *   published by the Free Software Foundation, either version 2.1 of the  *
# *   License, or (at your option) any later version.                       *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful, but        *
# *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
# *   Lesser General Public License for more details.                       *
# *                                                                         *
# *   You should have received a copy of the GNU Lesser General Public      *
# *   License along with FreeCAD. If not, see                               *
# *   <https://www.gnu.org/licenses/>.                                      *
# *                                                                         *
# ***************************************************************************

__title__ = "FEM physics module registry unit tests"
__author__ = "FreeCAD contributors"
__url__ = "https://www.freecad.org"

import unittest

from femtools import physics_modules
from .support_utils import fcc_print


class TestPhysicsModules(unittest.TestCase):
    fcc_print("import TestPhysicsModules")

    def setUp(self):
        # Keep builtins; drop any leftover custom test modules.
        physics_modules.unregister("TestCustomPDE")
        physics_modules.ensure_builtin_elmer_modules()

    def tearDown(self):
        physics_modules.unregister("TestCustomPDE")

    def test_00print(self):
        fcc_print(
            "\n{0}\n{1} run FEM TestPhysicsModules tests {2}\n{0}".format(
                100 * "*", 10 * "*", 54 * "*"
            )
        )

    def test_builtins_registered(self):
        names = physics_modules.list_module_names()
        self.assertIn("ElmerElasticity", names)
        self.assertIn("ElmerHeat", names)
        defaults = physics_modules.default_module_names()
        self.assertIn("ElmerElasticity", defaults)
        self.assertIn("ElmerHeat", defaults)

    def test_register_custom_and_list(self):
        def factory(doc, solver):
            return ("ok", doc, solver)

        mod = physics_modules.register(
            "TestCustomPDE",
            factory,
            description="Unit-test custom PDE",
            tags=("custom", "drone"),
            backend="custom",
            default=False,
        )
        self.assertEqual(mod.name, "TestCustomPDE")
        self.assertIn("TestCustomPDE", physics_modules.list_module_names())
        self.assertIn("TestCustomPDE", physics_modules.list_module_names(tag="drone"))
        self.assertNotIn(
            "TestCustomPDE", physics_modules.list_module_names(tag="structural")
        )
        got = physics_modules.get("TestCustomPDE")
        self.assertIsNotNone(got)
        self.assertEqual(got.description, "Unit-test custom PDE")
        self.assertEqual(physics_modules.apply("TestCustomPDE", "D", "S"), ("ok", "D", "S"))

    def test_format_catalog_mentions_defaults(self):
        text = physics_modules.format_catalog()
        self.assertIn("ElmerElasticity", text)
        self.assertIn("[*]", text)

    def test_unregister(self):
        physics_modules.register("TestCustomPDE", lambda d, s: None, description="x")
        physics_modules.unregister("TestCustomPDE")
        self.assertIsNone(physics_modules.get("TestCustomPDE"))
        self.assertNotIn("TestCustomPDE", physics_modules.list_module_names())
