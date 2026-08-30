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

__title__ = "CalculiX study preset unit tests"
__author__ = "FreeCAD contributors"
__url__ = "https://www.freecad.org"

import unittest

import FreeCAD

import ObjectsFem
from femtools import study_presets
from .support_utils import fcc_print


class TestStudyPresets(unittest.TestCase):
    fcc_print("import TestStudyPresets")

    def setUp(self):
        self.document = FreeCAD.newDocument(self.__class__.__name__)

    def tearDown(self):
        FreeCAD.closeDocument(self.document.Name)

    def test_00print(self):
        fcc_print(
            "\n{0}\n{1} run FEM TestStudyPresets tests {2}\n{0}".format(
                100 * "*", 10 * "*", 56 * "*"
            )
        )

    def test_calculix_static_preset(self):
        analysis, solver, material = study_presets.setup_calculix_static_study(self.document)
        self.document.recompute()

        self.assertEqual(analysis.TypeId, "Fem::FemAnalysis")
        self.assertEqual(solver.Proxy.Type, "Fem::SolverCalculiX")
        self.assertEqual(solver.AnalysisType, "static")
        self.assertIn(solver, analysis.Group)
        self.assertIsNotNone(material)
        self.assertEqual(material.Category, "Solid")
        self.assertIn(material, analysis.Group)
        self.assertFalse(any(obj.isDerivedFrom("Fem::FemMeshObject") for obj in analysis.Group))

    def test_calculix_thermal_preset(self):
        analysis, solver, material = study_presets.setup_calculix_thermal_study(self.document)
        self.document.recompute()

        self.assertEqual(solver.Proxy.Type, "Fem::SolverCalculiX")
        self.assertEqual(solver.AnalysisType, "thermomech")
        self.assertTrue(hasattr(solver, "ThermoMechType"))
        self.assertEqual(solver.ThermoMechType, "pure heat transfer")
        self.assertIn(solver, analysis.Group)
        self.assertIn(material, analysis.Group)

    def test_reuse_analysis_without_extra_mesh(self):
        analysis = ObjectsFem.makeAnalysis(self.document, "ExistingAnalysis")
        analysis, solver, material = study_presets.setup_calculix_static_study(
            self.document, analysis
        )
        self.assertEqual(analysis.Name, "ExistingAnalysis")
        self.assertEqual(solver.AnalysisType, "static")
        self.assertIsNotNone(material)

    def test_study_checklist(self):
        analysis = ObjectsFem.makeAnalysis(self.document, "ChecklistAnalysis")
        status = study_presets.get_study_checklist(analysis)
        self.assertFalse(status["has_mesh"])
        self.assertFalse(status["has_material"])
        self.assertFalse(status["has_constraint"])
        self.assertFalse(status["ready"])

        mesh = ObjectsFem.makeMeshGmsh(self.document, "MeshGmsh")
        analysis.addObject(mesh)
        material = ObjectsFem.makeMaterialSolid(self.document, "MaterialSolid")
        analysis.addObject(material)
        constraint = ObjectsFem.makeConstraintFixed(self.document, "Fixed")
        analysis.addObject(constraint)
        self.document.recompute()

        status = study_presets.get_study_checklist(analysis)
        self.assertTrue(status["has_mesh"])
        self.assertTrue(status["has_material"])
        self.assertTrue(status["has_constraint"])
        self.assertTrue(status["ready"])
        self.assertIn(mesh, status["meshes"])
        self.assertIn(material, status["materials"])
        self.assertIn(constraint, status["constraints"])
