// SPDX-License-Identifier: LGPL-2.1-or-later

#include "PreCompiled.h"
#ifndef _PreComp_
# include <QApplication>
# include <QComboBox>
# include <QFrame>
# include <QHBoxLayout>
# include <QLabel>
# include <QMenu>
# include <QScrollArea>
# include <QSizePolicy>
# include <QStackedWidget>
# include <QTabBar>
# include <QToolButton>
# include <QVBoxLayout>
#endif

#include "RibbonBar.h"
#include "Action.h"
#include "Application.h"
#include "Command.h"
#include "ToolBarManager.h"
#include "WorkbenchSelector.h"

#include <QAction>
#include <QApplication>
#include <QFrame>
#include <QSizePolicy>

using namespace Gui;

namespace
{
QString translateToolbarName(const std::string& name)
{
    return QApplication::translate("Workbench", name.c_str());
}

bool isSeparator(const ToolBarItem* item)
{
    return item && item->command() == "Separator";
}

bool isWorkbenchCommand(const ToolBarItem* item)
{
    return item && item->command() == "Std_Workbench";
}

bool toolbarIsWorkbenchOnly(ToolBarItem* item)
{
    if (!item) {
        return false;
    }
    for (ToolBarItem* child : item->getItems()) {
        if (isSeparator(child) || isWorkbenchCommand(child)) {
            continue;
        }
        return false;
    }
    return true;
}
}  // namespace

RibbonBar::RibbonBar(QWidget* parent)
    : QWidget(parent)
{
    setObjectName(QStringLiteral("RibbonBar"));
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);

    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    auto* tabRow = new QWidget(this);
    tabRow->setObjectName(QStringLiteral("RibbonTabRow"));
    auto* tabLayout = new QHBoxLayout(tabRow);
    tabLayout->setContentsMargins(8, 0, 8, 0);
    tabLayout->setSpacing(8);

    _tabs = new QTabBar(tabRow);
    _tabs->setObjectName(QStringLiteral("RibbonTabBar"));
    _tabs->setExpanding(false);
    _tabs->setDrawBase(false);
    _tabs->setUsesScrollButtons(true);
    tabLayout->addWidget(_tabs, 1);

    _workbenchHost = new QWidget(tabRow);
    _workbenchHost->setObjectName(QStringLiteral("RibbonWorkbenchHost"));
    auto* wbLayout = new QHBoxLayout(_workbenchHost);
    wbLayout->setContentsMargins(0, 4, 0, 4);
    wbLayout->setSpacing(0);
    tabLayout->addWidget(_workbenchHost, 0, Qt::AlignRight | Qt::AlignVCenter);

    root->addWidget(tabRow);

    _pages = new QStackedWidget(this);
    _pages->setObjectName(QStringLiteral("RibbonPages"));
    root->addWidget(_pages, 1);

    connect(_tabs, &QTabBar::currentChanged, _pages, &QStackedWidget::setCurrentIndex);
}

QSize RibbonBar::sizeHint() const
{
    return {800, 108};
}

QSize RibbonBar::minimumSizeHint() const
{
    return {200, 96};
}

void RibbonBar::clearRibbon()
{
    while (_tabs->count() > 0) {
        _tabs->removeTab(0);
    }
    while (_pages->count() > 0) {
        QWidget* page = _pages->widget(0);
        _pages->removeWidget(page);
        delete page;
    }
    qDeleteAll(_workbenchHost->findChildren<QWidget*>(QString(), Qt::FindDirectChildrenOnly));
    _tabKeys.clear();
}

void RibbonBar::placeWorkbenchSelector(QWidget* widget)
{
    if (!widget) {
        return;
    }
    widget->setParent(_workbenchHost);
    _workbenchHost->layout()->addWidget(widget);
}

QWidget* RibbonBar::makeGroup(const QString& title, QWidget* parent)
{
    auto* group = new QFrame(parent);
    group->setObjectName(QStringLiteral("RibbonGroup"));
    auto* layout = new QVBoxLayout(group);
    layout->setContentsMargins(8, 4, 8, 2);
    layout->setSpacing(2);

    auto* commands = new QWidget(group);
    commands->setObjectName(QStringLiteral("RibbonGroupCommands"));
    auto* commandsLayout = new QHBoxLayout(commands);
    commandsLayout->setContentsMargins(0, 0, 0, 0);
    commandsLayout->setSpacing(4);
    commandsLayout->setAlignment(Qt::AlignLeft | Qt::AlignTop);
    layout->addWidget(commands, 1);

    auto* label = new QLabel(title, group);
    label->setObjectName(QStringLiteral("RibbonGroupTitle"));
    label->setAlignment(Qt::AlignHCenter);
    layout->addWidget(label);

    return group;
}

QWidget* RibbonBar::makeCommandWidget(const char* name, QWidget* parent)
{
    CommandManager& mgr = Application::Instance->commandManager();
    Command* cmd = mgr.getCommandByName(name);
    if (!cmd) {
        return nullptr;
    }

    cmd->initAction();
    Action* act = cmd->getAction();
    if (!act || !act->action()) {
        return nullptr;
    }

    if (auto* wbGroup = dynamic_cast<WorkbenchGroup*>(act)) {
        auto* combo = new WorkbenchComboBox(wbGroup, parent);
        combo->setObjectName(QStringLiteral("RibbonWorkbenchBox"));
        combo->setMinimumWidth(180);
        combo->setSizeAdjustPolicy(QComboBox::AdjustToContents);
        return combo;
    }

    auto* btn = new QToolButton(parent);
    btn->setObjectName(QStringLiteral("RibbonCommandButton"));
    btn->setDefaultAction(act->action());
    btn->setToolButtonStyle(Qt::ToolButtonTextUnderIcon);
    btn->setIconSize(QSize(28, 28));
    btn->setAutoRaise(true);
    btn->setFocusPolicy(Qt::NoFocus);

    if (auto* group = dynamic_cast<ActionGroup*>(act)) {
        const QList<QAction*> actions = group->actions();
        if (!actions.isEmpty()) {
            auto* menu = new QMenu(btn);
            menu->addActions(actions);
            btn->setMenu(menu);
            btn->setPopupMode(QToolButton::MenuButtonPopup);
        }
    }

    return btn;
}

void RibbonBar::addCommandsToGroup(ToolBarItem* item, QHBoxLayout* groupLayout, QWidget* parent)
{
    if (!item || !groupLayout) {
        return;
    }

    for (ToolBarItem* child : item->getItems()) {
        if (isSeparator(child) || isWorkbenchCommand(child)) {
            continue;
        }
        if (child->hasItems()) {
            addCommandsToGroup(child, groupLayout, parent);
            continue;
        }
        if (QWidget* widget = makeCommandWidget(child->command().c_str(), parent)) {
            if (widget->objectName() == QLatin1String("RibbonWorkbenchBox")) {
                placeWorkbenchSelector(widget);
            }
            else {
                groupLayout->addWidget(widget);
            }
        }
    }
}

void RibbonBar::setup(ToolBarItem* root)
{
    clearRibbon();
    if (!root) {
        return;
    }

    for (ToolBarItem* toolbar : root->getItems()) {
        if (!toolbar || toolbarIsWorkbenchOnly(toolbar)) {
            for (ToolBarItem* child : toolbar ? toolbar->getItems() : QList<ToolBarItem*>()) {
                if (isWorkbenchCommand(child)) {
                    if (QWidget* widget = makeCommandWidget("Std_Workbench", _workbenchHost)) {
                        placeWorkbenchSelector(widget);
                    }
                }
            }
            continue;
        }

        auto* page = new QWidget;
        page->setObjectName(QStringLiteral("RibbonPage"));
        auto* pageLayout = new QHBoxLayout(page);
        pageLayout->setContentsMargins(4, 2, 4, 2);
        pageLayout->setSpacing(0);
        pageLayout->setAlignment(Qt::AlignLeft | Qt::AlignTop);

        auto* scroll = new QScrollArea;
        scroll->setObjectName(QStringLiteral("RibbonPageScroll"));
        scroll->setWidgetResizable(true);
        scroll->setFrameShape(QFrame::NoFrame);
        scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAsNeeded);
        scroll->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        scroll->setWidget(page);

        auto* currentGroup = makeGroup(translateToolbarName(toolbar->command()), page);
        pageLayout->addWidget(currentGroup);
        auto* currentCommands = currentGroup->findChild<QWidget*>(QStringLiteral("RibbonGroupCommands"));
        auto* currentLayout = qobject_cast<QHBoxLayout*>(currentCommands->layout());

        bool groupHasCommands = false;
        for (ToolBarItem* child : toolbar->getItems()) {
            if (isWorkbenchCommand(child)) {
                if (QWidget* widget = makeCommandWidget("Std_Workbench", _workbenchHost)) {
                    placeWorkbenchSelector(widget);
                }
                continue;
            }
            if (isSeparator(child)) {
                if (groupHasCommands) {
                    auto* divider = new QFrame(page);
                    divider->setObjectName(QStringLiteral("RibbonGroupDivider"));
                    divider->setFrameShape(QFrame::VLine);
                    divider->setFrameShadow(QFrame::Plain);
                    pageLayout->addWidget(divider);
                    currentGroup = makeGroup(translateToolbarName(toolbar->command()), page);
                    pageLayout->addWidget(currentGroup);
                    currentCommands =
                        currentGroup->findChild<QWidget*>(QStringLiteral("RibbonGroupCommands"));
                    currentLayout = qobject_cast<QHBoxLayout*>(currentCommands->layout());
                    groupHasCommands = false;
                }
                continue;
            }
            if (child->hasItems()) {
                addCommandsToGroup(child, currentLayout, currentCommands);
                groupHasCommands = true;
                continue;
            }
            if (QWidget* widget = makeCommandWidget(child->command().c_str(), currentCommands)) {
                if (widget->objectName() == QLatin1String("RibbonWorkbenchBox")) {
                    placeWorkbenchSelector(widget);
                }
                else {
                    currentLayout->addWidget(widget);
                    groupHasCommands = true;
                }
            }
        }

        pageLayout->addStretch(1);

        const QString title = translateToolbarName(toolbar->command());
        _tabKeys << QString::fromUtf8(toolbar->command().c_str());
        _tabs->addTab(title);
        _pages->addWidget(scroll);
    }

    if (_tabs->count() > 0) {
        _tabs->setCurrentIndex(0);
        _pages->setCurrentIndex(0);
    }
}

void RibbonBar::retranslate()
{
    for (int i = 0; i < _tabs->count() && i < _tabKeys.size(); ++i) {
        _tabs->setTabText(i, QApplication::translate("Workbench", _tabKeys.at(i).toUtf8().constData()));
    }
}
