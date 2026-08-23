// SPDX-License-Identifier: LGPL-2.1-or-later

/**************************************************************************
 *   Copyright (c) 2022 Werner Mayer <wmayer[at]users.sourceforge.net>     *
 *                                                                         *
 *   This file is part of the FreeCAD CAx development system.              *
 *                                                                         *
 *   This library is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU Library General Public           *
 *   License as published by the Free Software Foundation; either          *
 *   version 2 of the License, or (at your option) any later version.      *
 *                                                                         *
 *   This library  is distributed in the hope that it will be useful,      *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU Library General Public License for more details.                  *
 *                                                                         *
 *   You should have received a copy of the GNU Library General Public     *
 *   License along with this library; see the file COPYING.LIB. If not,    *
 *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
 *   Suite 330, Boston, MA  02111-1307, USA                                *
 *                                                                         *
 ***************************************************************************/

#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <boost/signals2.hpp>
#include <cctype>
#include <functional>
#include <map>
#include <string>
#include <vector>
#include <QApplication>
#include <QFormLayout>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QTimer>


#include "SketchWorkflow.h"
#include "DlgActiveBody.h"
#include "TaskFeaturePick.h"
#include "Utils.h"
#include "ViewProviderBody.h"
#include "WorkflowManager.h"
#include "ui_DlgReference.h"
#include <Mod/PartDesign/App/Body.h>
#include <Mod/PartDesign/App/DatumPlane.h>
#include <Mod/PartDesign/App/ShapeBinder.h>
#include <Mod/Part/App/AttachExtension.h>
#include <Mod/Part/App/Attacher.h>
#include <Mod/Part/App/Part2DObject.h>
#include <Mod/Part/App/TopoShape.h>
#include <Mod/Sketcher/Gui/ViewProviderSketch.h>

#include <App/Document.h>
#include <App/Application.h>
#include <App/Link.h>
#include <App/Origin.h>
#include <App/Datums.h>
#include <App/Part.h>
#include <Gui/Application.h>
#include <Gui/BitmapFactory.h>
#include <Gui/Command.h>
#include <Gui/Control.h>
#include <Gui/Document.h>
#include <Gui/MainWindow.h>
#include <Gui/ViewParams.h>
#include <Gui/ViewProviderCoordinateSystem.h>
#include <Gui/ViewProviderPlane.h>
#include <Gui/Selection/Selection.h>
#include <Gui/Selection/SelectionFilter.h>
#include <Gui/TaskView/TaskDialog.h>
#include <Gui/TaskView/TaskView.h>

using namespace PartDesignGui;

namespace
{
struct RejectException
{
};

struct WrongSelectionException
{
};

struct WrongSupportException
{
};

struct SupportNotPlanarException
{
};

struct MissingPlanesException
{
};

class SupportFaceValidator
{
public:
    explicit SupportFaceValidator(Gui::SelectionObject faceSelection)
        : faceSelection(faceSelection)
    {}

    void handleSelectedBody(PartDesign::Body* activeBody)
    {
        App::DocumentObject* object = faceSelection.getObject();
        std::vector<std::string> elements = faceSelection.getSubNames();

        // In case the selected face belongs to the body then it means its
        // Display Mode Body is set to Tip. But the body face is not allowed
        // to be used as support because otherwise it would cause a cyclic
        // dependency. So, instead we use the tip object as reference.
        // https://forum.freecad.org/viewtopic.php?f=3&t=37448
        if (object == activeBody) {
            App::DocumentObject* tip = activeBody->Tip.getValue();
            if (tip && tip->isDerivedFrom<Part::Feature>() && elements.size() == 1) {
                Gui::SelectionChanges msg;
                msg.pDocName = faceSelection.getDocName();
                msg.pObjectName = tip->getNameInDocument();
                msg.pSubName = elements[0].c_str();
                msg.TypeName = tip->getTypeId().getName();
                msg.pTypeName = msg.TypeName.c_str();

                faceSelection = Gui::SelectionObject {msg};

                // automatically switch to 'Through' mode
                setThroughModeOfBody(activeBody);
            }
        }
    }

    void throwIfInvalid()
    {
        App::DocumentObject* object = faceSelection.getObject();
        std::vector<std::string> elements = faceSelection.getSubNames();

        Part::Feature* partobject = dynamic_cast<Part::Feature*>(object);
        if (!partobject) {
            throw WrongSelectionException();
        }

        if (elements.size() != 1) {
            throw WrongSelectionException();
        }

        // get the selected sub shape (a Face)
        const Part::TopoShape& shape = partobject->Shape.getValue();
        Part::TopoShape subshape(shape.getSubShape(elements[0].c_str()));
        if (subshape.isNull()) {
            throw WrongSupportException();
        }

        if (!subshape.isPlanar(Attacher::AttachEnginePlane::planarPrecision())) {
            throw SupportNotPlanarException();
        }
    }

    std::string getSupport() const
    {
        return faceSelection.getAsPropertyLinkSubString();
    }

    App::DocumentObject* getObject() const
    {
        return faceSelection.getObject();
    }

private:
    void setThroughModeOfBody(PartDesign::Body* activeBody)
    {
        // automatically switch to 'Through' mode
        PartDesignGui::ViewProviderBody* vpBody = dynamic_cast<PartDesignGui::ViewProviderBody*>(
            Gui::Application::Instance->getViewProvider(activeBody)
        );
        if (vpBody) {
            vpBody->DisplayModeBody.setValue("Through");
        }
    }

private:
    mutable Gui::SelectionObject faceSelection;
};

class SupportPlaneValidator
{
public:
    explicit SupportPlaneValidator(Gui::SelectionObject faceSelection)
        : faceSelection(faceSelection)
    {}

    std::string getSupport() const
    {
        return faceSelection.getAsPropertyLinkSubString();
    }

    App::DocumentObject* getObject() const
    {
        return faceSelection.getObject();
    }

private:
    mutable Gui::SelectionObject faceSelection;
};

bool startsWithFace(const std::string& sub)
{
    auto pos = sub.rfind("Face");
    if (pos == std::string::npos) {
        return false;
    }
    if (pos != 0 && sub[pos - 1] != '.') {
        return false;
    }
    return pos + 4 == sub.size()
        || std::isdigit(static_cast<unsigned char>(sub[pos + 4]));
}

std::string supportStringFromOriginPlane(App::DocumentObject* obj)
{
    if (auto* plane = dynamic_cast<App::Plane*>(obj)) {
        if (auto* lcs = plane->getLCS()) {
            return Gui::Command::getObjectCmd(lcs, "(") + ",['" + plane->getNameInDocument()
                + "'])";
        }
        return Gui::Command::getObjectCmd(plane, "(", ",[''])");
    }
    return Gui::Command::getObjectCmd(obj, "(", ",[''])");
}

class SketchPlaneGate: public Gui::SelectionGate
{
public:
    bool allow(App::Document*, App::DocumentObject* obj, const char* sub) override
    {
        if (!obj) {
            return false;
        }
        if (obj->isDerivedFrom<App::Plane>() || obj->isDerivedFrom<PartDesign::Plane>()) {
            return true;
        }
        if (sub && startsWithFace(sub)) {
            return true;
        }
        if (obj->isDerivedFrom<PartDesign::ShapeBinder>()
            || obj->isDerivedFrom<PartDesign::SubShapeBinder>()) {
            return true;
        }
        notAllowedReason = QT_TR_NOOP("Pick a plane or planar face.");
        return false;
    }
};

class TaskSketchPlanePick: public Gui::TaskView::TaskBox, public Gui::SelectionObserver
{
public:
    TaskSketchPlanePick(App::Document* doc, PartDesign::Body* body)
        : TaskBox(
              Gui::BitmapFactory().pixmap("Sketcher_NewSketch"),
              QObject::tr("Sketch"),
              true,
              nullptr
          )
        , document(doc)
        , body(body)
    {
        auto* label = new QLabel(QObject::tr(
            "Click a plane or planar face in the 3D view. Origin planes are labeled XY, XZ, and YZ."
        ));
        label->setWordWrap(true);
        label->setMargin(8);
        groupLayout()->addWidget(label);

        planeField = new QLineEdit;
        planeField->setReadOnly(true);
        planeField->setPlaceholderText(QObject::tr("Click in the 3D view"));
        planeField->setClearButtonEnabled(false);
        auto* form = new QFormLayout;
        form->setContentsMargins(8, 4, 8, 8);
        form->addRow(QObject::tr("Sketch plane"), planeField);
        groupLayout()->addLayout(form);

        Gui::Selection().clearSelection();
        Gui::Selection().addSelectionGate(new SketchPlaneGate());
        Gui::getMainWindow()->showMessage(
            QObject::tr("Select a plane or planar face"),
            0
        );
    }

    ~TaskSketchPlanePick() override
    {
        Gui::Selection().rmvSelectionGate();
        Gui::getMainWindow()->showMessage(QString(), 1);
    }

    bool hasPick() const
    {
        return !supportString.empty();
    }

    const std::string& getSupport() const
    {
        return supportString;
    }

protected:
    void onSelectionChanged(const Gui::SelectionChanges& msg) override
    {
        if (msg.Type != Gui::SelectionChanges::AddSelection || !msg.pDocName || !msg.pObjectName) {
            return;
        }
        App::Document* doc = App::GetApplication().getDocument(msg.pDocName);
        if (!doc) {
            return;
        }
        App::DocumentObject* obj = doc->getObject(msg.pObjectName);
        if (!obj) {
            return;
        }

        std::string support;
        if (obj->isDerivedFrom<App::Plane>() || obj->isDerivedFrom<PartDesign::Plane>()) {
            support = supportStringFromOriginPlane(obj);
        }
        else {
            Gui::SelectionObject sel {msg};
            const auto& subs = sel.getSubNames();
            if (subs.empty() || !startsWithFace(subs[0])) {
                if (auto* feat = dynamic_cast<Part::Feature*>(obj)) {
                    if (!feat->Shape.getShape().isPlanar()) {
                        return;
                    }
                    support = Gui::Command::getObjectCmd(obj, "(", ",[''])");
                }
                else {
                    return;
                }
            }
            else {
                try {
                    SupportFaceValidator validator {sel};
                    validator.handleSelectedBody(body);
                    validator.throwIfInvalid();
                    support = validator.getSupport();
                }
                catch (...) {
                    return;
                }
            }
        }

        supportString = std::move(support);
        if (planeField) {
            const char* label = obj->Label.getValue();
            planeField->setText(label && label[0] ? QString::fromUtf8(label) : QString::fromUtf8(obj->getNameInDocument()));
        }
        App::Document* docPtr = document;
        QTimer::singleShot(0, [docPtr]() { Gui::Control().accept(docPtr); });
    }

private:
    App::Document* document;
    PartDesign::Body* body;
    std::string supportString;
    QLineEdit* planeField {nullptr};
};

class TaskDlgSketchPlanePick: public Gui::TaskView::TaskDialog
{
public:
    TaskDlgSketchPlanePick(
        App::Document* doc,
        PartDesign::Body* body,
        std::function<void(const std::string&)> work,
        std::function<void()> abort
    )
        : workFunction(std::move(work))
        , abortFunction(std::move(abort))
    {
        pick = new TaskSketchPlanePick(doc, body);
        Content.push_back(pick);
        setObjectName(QStringLiteral("Sketch"));
        setAutoCloseOnDeletedDocument(true);
        if (doc) {
            setDocumentName(doc->getName());
        }
    }

    ~TaskDlgSketchPlanePick() override
    {
        if (accepted) {
            try {
                workFunction(pick->getSupport());
            }
            catch (...) {
            }
        }
        else if (abortFunction) {
            try {
                abortFunction();
            }
            catch (...) {
            }
        }
    }

    bool accept() override
    {
        accepted = pick->hasPick();
        return accepted;
    }

    bool reject() override
    {
        accepted = false;
        return true;
    }

    QDialogButtonBox::StandardButtons getStandardButtons() const override
    {
        return QDialogButtonBox::Cancel;
    }

    bool isAllowedAlterDocument() const override
    {
        return false;
    }

private:
    TaskSketchPlanePick* pick;
    bool accepted {false};
    std::function<void(const std::string&)> workFunction;
    std::function<void()> abortFunction;
};

class SketchPreselection
{
public:
    SketchPreselection(
        Gui::Document* guidocument,
        PartDesign::Body* activeBody,
        std::tuple<Gui::SelectionFilter, Gui::SelectionFilter, Gui::SelectionFilter> filter
    )
        : guidocument(guidocument)
        , activeBody(activeBody)
        , faceFilter(std::get<0>(filter))
        , planeFilter(std::get<1>(filter))
        , sketchFilter(std::get<2>(filter))
    {}

    bool matches()
    {
        return faceFilter.match() || planeFilter.match() || sketchFilter.match();
    }

    // True only when a single planar face or datum plane is selected (not a sketch).
    // Used for the fast-path that skips the attachment dialog.
    bool isSingleFaceOrPlane()
    {
        return (faceFilter.match() || planeFilter.match()) && !sketchFilter.match();
    }

    std::string getSupport() const
    {
        return supportString;
    }

    void createSupport()
    {
        createBodyOrThrow();

        // get the selected object
        App::DocumentObject* selectedObject {};

        if (faceFilter.match()) {
            Gui::SelectionObject faceSelObject = faceFilter.Result[0][0];
            SupportFaceValidator validator {faceSelObject};
            validator.handleSelectedBody(activeBody);
            validator.throwIfInvalid();

            selectedObject = validator.getObject();
            supportString = validator.getSupport();
        }
        else if (planeFilter.match()) {
            SupportPlaneValidator validator(planeFilter.Result[0][0]);
            selectedObject = validator.getObject();
            supportString = validator.getSupport();
        }
        else {
            // For a sketch, the support is the object itself with no sub-element.
            Gui::SelectionObject sketchSelObject = sketchFilter.Result[0][0];
            selectedObject = sketchSelObject.getObject();
            supportString = sketchSelObject.getAsPropertyLinkSubString();
        }

        handleIfSupportOutOfBody(selectedObject);
    }

    void createSketchOnSupport(const std::string& supportString)
    {
        // create Sketch on Face or Plane
        App::Document* appdocument = guidocument->getDocument();
        std::string FeatName = appdocument->getUniqueObjectName("Sketch");

        guidocument->openCommand(QT_TRANSLATE_NOOP("Command", "Sketch on Face"));
        FCMD_OBJ_CMD(activeBody, "newObject('Sketcher::SketchObject','" << FeatName << "')");
        auto Feat = activeBody->getDocument()->getObject(FeatName.c_str());
        FCMD_OBJ_CMD(Feat, "Label = 'Sketch'");
        FCMD_OBJ_CMD(Feat, "AttachmentSupport = " << supportString);
        if (sketchFilter.match()) {
            FCMD_OBJ_CMD(
                Feat,
                "MapMode = '" << Attacher::AttachEngine::getModeName(Attacher::mmObjectXY) << "'"
            );
        }
        else {  // For Face or Plane
            FCMD_OBJ_CMD(
                Feat,
                "MapMode = '" << Attacher::AttachEngine::getModeName(Attacher::mmFlatFace) << "'"
            );
        }
        Gui::Command::updateActive();
        PartDesignGui::setEdit(Feat, activeBody);
    }

private:
    void createBodyOrThrow()
    {
        if (!activeBody) {
            activeBody = PartDesignGui::getBody(/* messageIfNot = */ true);
            if (activeBody) {
                tryAddNewBodyToActivePart();
            }
            else {
                throw RejectException();
            }
        }
    }

    void tryAddNewBodyToActivePart()
    {
        App::Part* activePart = PartDesignGui::getActivePart();
        if (activePart) {
            activePart->addObject(activeBody);
        }
    }

    void handleIfSupportOutOfBody(App::DocumentObject* selectedObject)
    {
        if (!activeBody->hasObject(selectedObject)) {
            if (!selectedObject->isDerivedFrom(App::Plane::getClassTypeId())) {
                // TODO check here if the plane associated with right part/body (2015-09-01, Fat-Zer)

                // check the prerequisites for the selected objects
                // the user has to decide which option we should take if external references are used
                //  TODO share this with UnifiedDatumCommand() (2015-10-20, Fat-Zer)
                QDialog dia(Gui::getMainWindow());
                PartDesignGui::Ui_DlgReference dlg;
                dlg.setupUi(&dia);
                dia.setModal(true);
                int result = dia.exec();
                if (result == QDialog::Rejected) {
                    throw RejectException();
                }

                if (!dlg.radioXRef->isChecked()) {
                    guidocument->openCommand(QT_TRANSLATE_NOOP("Command", "Make copy"));
                    auto copy = makeCopy(selectedObject, dlg.radioIndependent->isChecked());
                    supportString = supportFromCopy(copy);
                    guidocument->commitCommand();
                }
            }
        }
    }

    App::DocumentObject* makeCopy(App::DocumentObject* selectedObject, bool independent)
    {
        std::string sub;
        if (faceFilter.match()) {
            sub = faceFilter.Result[0][0].getSubNames()[0];
        }
        auto copy = PartDesignGui::TaskFeaturePick::makeCopy(selectedObject, sub, independent);

        addToBodyOrPart(copy);

        return copy;
    }

    std::string supportFromCopy(App::DocumentObject* copy)
    {
        std::string supportString;
        if (planeFilter.match()) {
            supportString = Gui::Command::getObjectCmd(copy, "(", ",'')");
        }
        else {
            // it is ensured that only a single face is selected, hence it must always be Face1 of
            // the shapebinder
            supportString = Gui::Command::getObjectCmd(copy, "(", ",'Face1')");
        }
        return supportString;
    }

    void addToBodyOrPart(App::DocumentObject* object)
    {
        auto activePart = PartDesignGui::getPartFor(activeBody, false);
        if (activeBody) {
            activeBody->addObject(object);
        }
        else if (activePart) {
            activePart->addObject(object);
        }
    }

private:
    Gui::Document* guidocument;
    PartDesign::Body* activeBody;
    Gui::SelectionFilter faceFilter;
    Gui::SelectionFilter planeFilter;
    Gui::SelectionFilter sketchFilter;
    std::string supportString;
};

class SketchRequestSelection
{
public:
    SketchRequestSelection(Gui::Document* guidocument, PartDesign::Body* activeBody)
        : guidocument(guidocument)
        , activeBody(activeBody)
    {}

    void findSupport(bool useAttachmentDialog)
    {
        try {
            // Start command early, so undo will undo any Body creation
            guidocument->openCommand(QT_TRANSLATE_NOOP("Command", "New Sketch"));
            tryFindSupport(useAttachmentDialog);
        }
        catch (const RejectException&) {
            guidocument->abortCommand();
            throw;
        }
        catch (const MissingPlanesException&) {
            guidocument->abortCommand();
            throw;
        }
    }

private:
    void tryFindSupport(bool useAttachmentDialog)
    {
        createBodyOrThrow();

        if (useAttachmentDialog) {
            createSketchAndShowAttachment();
        }
        else {
            pickPlaneInView();
        }
    }

    void createBodyOrThrow()
    {
        if (!activeBody) {
            App::Document* appdocument = guidocument->getDocument();
            activeBody = PartDesignGui::makeBody(appdocument);
            if (activeBody) {
                tryAddNewBodyToActivePart();
            }
            else {
                throw RejectException();
            }
        }
    }

    void tryAddNewBodyToActivePart()
    {
        App::Part* activePart = PartDesignGui::getActivePart();
        if (activePart) {
            activePart->addObject(activeBody);
        }
    }

    void setOriginTemporaryVisibility()
    {
        auto* origin = activeBody->getOrigin();
        auto* vpo = dynamic_cast<Gui::ViewProviderCoordinateSystem*>(
            Gui::Application::Instance->getViewProvider(origin)
        );
        if (vpo) {
            vpo->setTemporaryVisibility(Gui::DatumElement::Planes | Gui::DatumElement::Axes);
            vpo->setTemporaryScale(Gui::ViewParams::instance()->getDatumTemporaryScaleFactor());
            vpo->setPlaneLabelVisibility(true);
        }
    }

    void createSketchAndShowAttachment()
    {
        setOriginTemporaryVisibility();

        // Capture selection before clearing it to pre-populate the attachment dialog.
        // This mirrors UnifiedDatumCommand: use attacher to find the best fit mode.
        App::PropertyLinkSubList support;
        Gui::Selection().getAsPropertyLinkSubList(support);
        support.removeValue(activeBody);

        // Don't pre-populate when the selection contains sketches. A sketch selected
        // from prior work should not automatically become the attachment reference —
        // the user can choose a face or plane in the dialog.
        bool hasSketch = std::ranges::any_of(support.getValues(), [](App::DocumentObject* obj) {
            return obj && obj->isDerivedFrom<Part::Part2DObject>();
        });

        // Create sketch
        App::Document* doc = activeBody->getDocument();
        std::string FeatName = doc->getUniqueObjectName("Sketch");
        FCMD_OBJ_CMD(activeBody, "newObject('Sketcher::SketchObject','" << FeatName << "')");
        auto sketch = doc->getObject(FeatName.c_str());
        FCMD_OBJ_CMD(sketch, "Label = 'Sketch'");

        if (!hasSketch && support.getSize() > 0) {
            if (auto* pcAttach = sketch->getExtensionByType<Part::AttachExtension>()) {
                pcAttach->attacher().setReferences(support);
                Attacher::SuggestResult sugr;
                pcAttach->attacher().suggestMapModes(sugr);
                if (sugr.message == Attacher::SuggestResult::srOK) {
                    FCMD_OBJ_CMD(sketch, "AttachmentSupport = " << support.getPyReprString());
                    FCMD_OBJ_CMD(
                        sketch,
                        "MapMode = '" << Attacher::AttachEngine::getModeName(sugr.bestFitMode) << "'"
                    );
                    Gui::Command::updateActive();
                }
            }
        }

        PartDesign::Body* partDesignBody = activeBody;
        auto onAccept = [partDesignBody, sketch]() {
            resetOriginVisibility(partDesignBody);

            Gui::Selection().clearSelection();

            PartDesignGui::setEdit(sketch, partDesignBody);
        };
        auto onReject = [partDesignBody]() {
            resetOriginVisibility(partDesignBody);
        };

        Gui::Selection().clearSelection();

        // Open attachment dialog
        auto* vps = dynamic_cast<SketcherGui::ViewProviderSketch*>(
            Gui::Application::Instance->getViewProvider(sketch)
        );
        vps->showAttachmentEditor(onAccept, onReject);
    }

    static void resetOriginVisibility(PartDesign::Body* partDesignBody)
    {
        auto* origin = partDesignBody->getOrigin();
        auto* vpo = dynamic_cast<Gui::ViewProviderCoordinateSystem*>(
            Gui::Application::Instance->getViewProvider(origin)
        );
        if (vpo) {
            vpo->resetTemporaryVisibility();
            vpo->resetTemporarySize();
            vpo->showPersistentOrigin();
        }
    }

    void pickPlaneInView()
    {
        setOriginTemporaryVisibility();

        App::Document* documentOfBody = guidocument->getDocument();
        PartDesign::Body* partDesignBody = activeBody;

        auto restoreOrigin = [partDesignBody]() {
            resetOriginVisibility(partDesignBody);
        };

        auto processFunction = [documentOfBody, partDesignBody, restoreOrigin](const std::string& support) {
            restoreOrigin();
            Gui::Selection().clearSelection();
            createSketchOnSupport(documentOfBody, partDesignBody, support);
        };

        std::string docname = documentOfBody->getName();
        auto rejectFunction = [docname, restoreOrigin]() {
            restoreOrigin();
            Gui::Document* document = Gui::Application::Instance->getDocument(docname.c_str());
            if (document) {
                document->abortCommand();
            }
        };

        checkForShownDialog();
        Gui::Selection().clearSelection();
        Gui::Control().showDialog(
            new TaskDlgSketchPlanePick(documentOfBody, partDesignBody, processFunction, rejectFunction)
        );
    }

    void checkForShownDialog()
    {
        App::Document* appdocument = guidocument->getDocument();
        Gui::TaskView::TaskDialog* dlg = Gui::Control().activeDialog(appdocument);
        if (!dlg) {
            return;
        }

        QMessageBox msgBox(Gui::getMainWindow());
        msgBox.setText(QObject::tr("A dialog is already open in the task panel"));
        msgBox.setInformativeText(QObject::tr("Close this dialog?"));
        msgBox.setStandardButtons(QMessageBox::Yes | QMessageBox::No);
        msgBox.setDefaultButton(QMessageBox::Yes);
        if (msgBox.exec() != QMessageBox::Yes) {
            throw RejectException();
        }
        Gui::Control().closeDialog();
    }

    static void createSketchOnSupport(
        App::Document* documentOfBody,
        PartDesign::Body* partDesignBody,
        const std::string& supportString
    )
    {
        if (supportString.empty()) {
            return;
        }

        std::string FeatName = documentOfBody->getUniqueObjectName("Sketch");
        App::Document* doc = partDesignBody->getDocument();
        if (!doc->hasPendingTransaction()) {
            doc->openTransaction(QT_TRANSLATE_NOOP("Command", "New Sketch"));
        }

        FCMD_OBJ_CMD(partDesignBody, "newObject('Sketcher::SketchObject','" << FeatName << "')");
        auto Feat = doc->getObject(FeatName.c_str());
        FCMD_OBJ_CMD(Feat, "Label = 'Sketch'");
        FCMD_OBJ_CMD(Feat, "AttachmentSupport = " << supportString);
        FCMD_OBJ_CMD(
            Feat,
            "MapMode = '" << Attacher::AttachEngine::getModeName(Attacher::mmFlatFace) << "'"
        );
        Gui::Command::updateActive();
        PartDesignGui::setEdit(Feat, partDesignBody);
    }

private:
    Gui::Document* guidocument;
    PartDesign::Body* activeBody;
};

}  // namespace

SketchWorkflow::SketchWorkflow(Gui::Document* document)
    : guidocument(document)
{
    appdocument = guidocument->getDocument();
}

void SketchWorkflow::createSketch()
{
    try {
        tryCreateSketch();
    }
    catch (const RejectException&) {
    }
    catch (const WrongSelectionException&) {
        QMessageBox::warning(
            Gui::getMainWindow(),
            QObject::tr("Several sub-elements selected"),
            QObject::tr("Select a single face as support for a sketch!")
        );
    }
    catch (const WrongSupportException&) {
        QMessageBox::warning(
            Gui::getMainWindow(),
            QObject::tr("No support face selected"),
            QObject::tr("Select a face as support for a sketch!")
        );
    }
    catch (const SupportNotPlanarException&) {
        QMessageBox::warning(
            Gui::getMainWindow(),
            QObject::tr("No planar support"),
            QObject::tr("Need a planar face as support for a sketch!")
        );
    }
    catch (const MissingPlanesException&) {
        QMessageBox::warning(
            Gui::getMainWindow(),
            QObject::tr("No valid planes in this document"),
            QObject::tr("Create a plane first or select a face to sketch on")
        );
    }
}

void SketchWorkflow::tryCreateSketch()
{
    auto result = shouldCreateBody();
    auto shouldMakeBody = std::get<0>(result);
    activeBody = std::get<1>(result);
    if (shouldAbort(shouldMakeBody)) {
        return;
    }

    bool useAttachment = App::GetApplication()
                             .GetParameterGroupByPath(
                                 "User parameter:BaseApp/Preferences/Mod/PartDesign"
                             )
                             ->GetBool("NewSketchUseAttachmentDialog", false);

    bool shiftHeld = QApplication::queryKeyboardModifiers() & Qt::ShiftModifier;

    auto filters = getFilters();
    SketchPreselection sketchOnFace {guidocument, activeBody, filters};

    // Fast path: single face or datum plane already selected.
    // If the face turns out to be non-planar or otherwise invalid, fall through
    // to picking a plane in the 3D view.
    if (!useAttachment && !shiftHeld && sketchOnFace.isSingleFaceOrPlane()) {
        try {
            sketchOnFace.createSupport();
            sketchOnFace.createSketchOnSupport(sketchOnFace.getSupport());
            return;
        }
        catch (const WrongSupportException&) {
        }
        catch (const WrongSelectionException&) {
        }
        catch (const SupportNotPlanarException&) {
        }
    }

    SketchRequestSelection requestSelection {guidocument, activeBody};
    requestSelection.findSupport(useAttachment || shiftHeld);
}

std::tuple<bool, PartDesign::Body*> SketchWorkflow::shouldCreateBody()
{
    auto shouldMakeBody {false};

    // We need either an active Body, or for there to be no Body
    // objects (in which case, just make one) to make a new sketch.
    // If we are inside a link, we need to use its placement.
    App::DocumentObject* topParent;
    PartDesign::Body* pdBody
        = PartDesignGui::getBody(/* messageIfNot = */ false, true, true, &topParent);
    if (pdBody && topParent->isLink()) {
        auto* xLink = dynamic_cast<App::Link*>(topParent);
        pdBody->Placement.setValue(xLink->Placement.getValue());
    }
    if (!pdBody) {
        if (appdocument->countObjectsOfType<PartDesign::Body>() == 0) {
            shouldMakeBody = true;
        }
        else {
            PartDesignGui::DlgActiveBody dia(Gui::getMainWindow(), appdocument);
            if (dia.exec() == QDialog::Accepted) {
                pdBody = dia.getActiveBody();
            }
        }
    }

    return std::make_tuple(shouldMakeBody, pdBody);
}

bool SketchWorkflow::shouldAbort(bool shouldMakeBody) const
{
    return !shouldMakeBody && !activeBody;
}

std::tuple<Gui::SelectionFilter, Gui::SelectionFilter, Gui::SelectionFilter> SketchWorkflow::getFilters() const
{
    // Hint:
    // The behaviour of this command has changed with respect to a selected sketch:
    // It doesn't try any more to edit a selected sketch but always tries to create
    // a new sketch.
    // See https://forum.freecad.org/viewtopic.php?f=3&t=44070

    Gui::SelectionFilter FaceFilter("SELECT Part::Feature SUBELEMENT Face COUNT 1");
    Gui::SelectionFilter PlaneFilter("SELECT App::Plane COUNT 1", activeBody);
    Gui::SelectionFilter PlaneFilter2("SELECT PartDesign::Plane COUNT 1", activeBody);
    Gui::SelectionFilter SketchFilter("SELECT Part::Part2DObject COUNT 1", activeBody);

    if (PlaneFilter2.match()) {
        PlaneFilter = PlaneFilter2;
    }

    return std::make_tuple(FaceFilter, PlaneFilter, SketchFilter);
}
