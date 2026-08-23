// SPDX-License-Identifier: LGPL-2.1-or-later

#include <cstring>

#include <QGridLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QSlider>
#include <QTimer>
#include <QTreeWidget>
#include <QVBoxLayout>

#include <App/Application.h>
#include <App/Document.h>
#include <Gui/Application.h>
#include <Gui/Command.h>
#include <Gui/Document.h>
#include <Gui/MainWindow.h>
#include <Mod/PartDesign/App/Body.h>

#include "RollbackBar.h"
#include "Utils.h"


using namespace PartDesignGui;

RollbackBar::RollbackBar(QWidget* parent)
    : QWidget(parent)
{
    setObjectName(QStringLiteral("RollbackBar"));

    auto* layout = new QHBoxLayout(this);
    layout->setContentsMargins(8, 4, 8, 4);
    layout->setSpacing(8);

    _caption = new QLabel(tr("History"), this);
    _caption->setObjectName(QStringLiteral("RollbackBarCaption"));

    _slider = new QSlider(Qt::Horizontal, this);
    _slider->setObjectName(QStringLiteral("RollbackBarSlider"));
    _slider->setTickPosition(QSlider::TicksBelow);
    _slider->setTickInterval(1);
    _slider->setSingleStep(1);
    _slider->setPageStep(1);
    _slider->setMinimum(0);
    _slider->setMaximum(0);

    _feature = new QLabel(this);
    _feature->setObjectName(QStringLiteral("RollbackBarLabel"));
    _feature->setMinimumWidth(72);

    layout->addWidget(_caption);
    layout->addWidget(_slider, 1);
    layout->addWidget(_feature);

    setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Maximum);
    setMaximumHeight(48);

    connect(_slider, &QSlider::sliderPressed, this, &RollbackBar::onSliderPressed);
    connect(_slider, &QSlider::valueChanged, this, &RollbackBar::onSliderMoved);
    connect(_slider, &QSlider::sliderReleased, this, &RollbackBar::onSliderReleased);

    _connChanged = App::GetApplication().signalChangedObject.connect(
        [this](const App::DocumentObject& obj, const App::Property& prop) {
            Q_UNUSED(obj)
            const char* name = prop.getName();
            if (!name) {
                return;
            }
            if (strcmp(name, "Tip") == 0 || strcmp(name, "Group") == 0
                || strcmp(name, "Label") == 0) {
                QTimer::singleShot(0, this, [this]() { refresh(); });
            }
        }
    );
    if (Gui::Application::Instance) {
        _connActive = Gui::Application::Instance->signalActiveDocument.connect(
            [this](const Gui::Document&) { QTimer::singleShot(0, this, [this]() { refresh(); }); }
        );
    }

    refresh();
}

void RollbackBar::install()
{
    auto* main = Gui::getMainWindow();
    if (!main) {
        return;
    }
    auto* combo = main->findChild<QWidget*>(QStringLiteral("Model"));
    if (!combo) {
        return;
    }
    if (combo->findChild<QWidget*>(QStringLiteral("RollbackBar"))) {
        return;
    }

    // Sit under the Feature tree (above the property editor), like SolidWorks.
    QWidget* host = combo;
    QLayout* hostLayout = combo->layout();
    if (auto* tree = combo->findChild<QTreeWidget*>()) {
        if (auto* panel = tree->parentWidget()) {
            if (auto* vbox = qobject_cast<QVBoxLayout*>(panel->layout())) {
                host = panel;
                hostLayout = vbox;
            }
        }
    }
    if (!hostLayout) {
        return;
    }

    auto* bar = new RollbackBar(host);
    if (auto* grid = qobject_cast<QGridLayout*>(hostLayout)) {
        grid->setRowStretch(0, 1);
        grid->addWidget(bar, 1, 0);
    }
    else if (auto* vbox = qobject_cast<QVBoxLayout*>(hostLayout)) {
        vbox->addWidget(bar);
    }
    else {
        delete bar;
    }
}

PartDesign::Body* RollbackBar::activeBody() const
{
    return PartDesignGui::getBody(false);
}

std::vector<App::DocumentObject*> RollbackBar::solidFeatures(PartDesign::Body* body) const
{
    std::vector<App::DocumentObject*> features;
    if (!body) {
        return features;
    }
    for (auto* obj : body->Group.getValues()) {
        if (PartDesign::Body::isSolidFeature(obj)) {
            features.push_back(obj);
        }
    }
    return features;
}

void RollbackBar::refresh()
{
    if (_updating || _dragging) {
        return;
    }

    PartDesign::Body* body = activeBody();
    const auto features = solidFeatures(body);
    if (!body || features.empty()) {
        hide();
        return;
    }

    show();
    _updating = true;
    _slider->setMinimum(0);
    _slider->setMaximum(static_cast<int>(features.size()) - 1);

    int index = static_cast<int>(features.size()) - 1;
    if (App::DocumentObject* tip = body->Tip.getValue()) {
        for (int i = 0; i < static_cast<int>(features.size()); ++i) {
            if (features[static_cast<size_t>(i)] == tip) {
                index = i;
                break;
            }
        }
    }
    _slider->setValue(index);
    _feature->setText(QString::fromUtf8(features[static_cast<size_t>(index)]->Label.getValue()));
    setToolTip(tr("Drag to roll the body back to an earlier feature (moves the Tip)."));
    _updating = false;
}

void RollbackBar::onSliderPressed()
{
    PartDesign::Body* body = activeBody();
    if (!body || !body->getDocument()) {
        return;
    }
    _dragging = true;
    body->getDocument()->openTransaction("Rollback");
}

void RollbackBar::onSliderMoved(int index)
{
    if (_updating) {
        return;
    }
    applyTip(index, !_dragging);
}

void RollbackBar::onSliderReleased()
{
    PartDesign::Body* body = activeBody();
    applyTip(_slider->value(), false);
    if (body && body->getDocument() && _dragging) {
        body->getDocument()->commitTransaction();
    }
    _dragging = false;
    Gui::Command::updateActive();
}

void RollbackBar::applyTip(int index, bool commitTransaction)
{
    PartDesign::Body* body = activeBody();
    const auto features = solidFeatures(body);
    if (!body || index < 0 || index >= static_cast<int>(features.size())) {
        return;
    }

    App::DocumentObject* feature = features[static_cast<size_t>(index)];
    _feature->setText(QString::fromUtf8(feature->Label.getValue()));
    if (body->Tip.getValue() == feature) {
        return;
    }

    App::Document* doc = body->getDocument();
    if (commitTransaction && doc) {
        doc->openTransaction("Rollback");
    }
    body->Tip.setValue(feature);
    if (doc) {
        doc->recompute();
    }
    if (commitTransaction && doc) {
        doc->commitTransaction();
        Gui::Command::updateActive();
    }
}
