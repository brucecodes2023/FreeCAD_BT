// SPDX-License-Identifier: LGPL-2.1-or-later

#include "PreCompiled.h"
#ifndef _PreComp_
# include <QMdiArea>
# include <QMdiSubWindow>
# include <QVBoxLayout>
#endif

#include "RibbonManager.h"
#include "RibbonBar.h"
#include "Application.h"
#include "Document.h"
#include "MainWindow.h"
#include "MDIView.h"
#include "ToolBarManager.h"
#include "Utilities.h"
#include "ViewProviderDocumentObject.h"
#include "Workbench.h"
#include "WorkbenchManager.h"

#include <App/Application.h>
#include <App/DocumentObject.h>
#include <Base/Type.h>

using namespace Gui;

RibbonManager* RibbonManager::_instance = nullptr;

RibbonManager* RibbonManager::getInstance()
{
    if (!_instance) {
        _instance = new RibbonManager;
    }
    return _instance;
}

void RibbonManager::destruct()
{
    delete _instance;
    _instance = nullptr;
}

bool RibbonManager::useRibbon()
{
    if (Gui::isInternalGuiTestRun()) {
        return false;
    }
    auto hGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/MainWindow"
    );
    return hGrp->GetBool("UseRibbon", true);
}

void RibbonManager::ensureInstalled()
{
    if (_installed) {
        return;
    }

    MainWindow* mw = getMainWindow();
    if (!mw || !mw->getMdiArea()) {
        return;
    }

    _bar = new RibbonBar(mw);
    _bar->hide();

    auto* host = new QWidget(mw);
    host->setObjectName(QStringLiteral("RibbonCentralHost"));
    auto* layout = new QVBoxLayout(host);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    layout->addWidget(_bar);

    QMdiArea* mdi = mw->getMdiArea();
    layout->addWidget(mdi, 1);
    mw->setCentralWidget(host);

    _installed = true;
}

void RibbonManager::setup(ToolBarItem* root)
{
    ensureInstalled();
    if (!_bar) {
        return;
    }
    if (!useRibbon()) {
        _bar->hide();
        _bar->clearRibbon();
        return;
    }
    _bar->setup(root);
    syncVisibility();
}

void RibbonManager::retranslate()
{
    if (_bar) {
        _bar->retranslate();
    }
}

void RibbonManager::syncVisibility()
{
    if (!_bar) {
        return;
    }

    _dashboard = false;
    if (MainWindow* mw = getMainWindow()) {
        if (MDIView* view = mw->activeWindow()) {
            _dashboard = view->objectName() == QLatin1String("StartView");
        }
    }

    const bool show = useRibbon() && !_dashboard;
    _bar->setVisible(show);
    if (show) {
        ToolBarManager::getInstance()->hideAllForRibbon();
        bool sketchInEdit = false;
        if (Document* doc = Application::Instance->activeDocument()) {
            auto* vp = dynamic_cast<ViewProviderDocumentObject*>(doc->getInEdit());
            if (vp && vp->getObject()) {
                const Base::Type sketchType = Base::Type::fromName("Sketcher::SketchObject");
                sketchInEdit = !sketchType.isBad() && vp->getObject()->isDerivedFrom(sketchType);
            }
        }
        _bar->applyContext(sketchInEdit);
    }
}

void RibbonManager::applyPreference()
{
    ensureInstalled();
    if (auto* wb = WorkbenchManager::instance()->active()) {
        wb->activate();
    }
    syncVisibility();
}
