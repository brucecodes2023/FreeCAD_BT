// SPDX-License-Identifier: LGPL-2.1-or-later

#include "PreCompiled.h"
#ifndef _PreComp_
# include <QApplication>
# include <QComboBox>
# include <QFrame>
# include <QHBoxLayout>
# include <QLabel>
# include <QMenu>
# include <QResizeEvent>
# include <QShowEvent>
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

class RibbonPageHost: public QWidget
{
public:
    explicit RibbonPageHost(QWidget* parent = nullptr)
        : QWidget(parent)
    {
        setObjectName(QStringLiteral("RibbonPage"));
        auto* layout = new QHBoxLayout(this);
        layout->setContentsMargins(4, 2, 4, 2);
        layout->setSpacing(0);
        layout->setAlignment(Qt::AlignLeft | Qt::AlignTop);

        _overflow = new QToolButton(this);
        _overflow->setObjectName(QStringLiteral("RibbonOverflowButton"));
        _overflow->setText(QStringLiteral("»"));
        _overflow->setToolTip(QApplication::translate("RibbonBar", "More commands"));
        _overflow->setAutoRaise(true);
        _overflow->setFocusPolicy(Qt::NoFocus);
        _overflow->setPopupMode(QToolButton::InstantPopup);
        _overflow->setMenu(new QMenu(_overflow));
        _overflow->hide();
    }

    void addGroup(QWidget* group)
    {
        _groups.append(group);
        layout()->addWidget(group);
    }

    void addDivider(QWidget* divider)
    {
        _dividers.append(divider);
        layout()->addWidget(divider);
    }

    void finish()
    {
        auto* lay = qobject_cast<QHBoxLayout*>(layout());
        lay->addWidget(_overflow, 0, Qt::AlignRight | Qt::AlignVCenter);
        lay->addStretch(1);
    }

protected:
    void resizeEvent(QResizeEvent* event) override
    {
        QWidget::resizeEvent(event);
        compact();
    }

    void showEvent(QShowEvent* event) override
    {
        QWidget::showEvent(event);
        compact();
    }

private:
    void compact()
    {
        for (QWidget* group : _groups) {
            group->show();
        }
        for (QWidget* divider : _dividers) {
            divider->show();
        }
        _overflow->menu()->clear();
        _overflow->hide();

        const int overflowReserve = 36;
        const int available = qMax(0, width() - overflowReserve);
        int used = 0;
        bool overflowing = false;

        for (int i = 0; i < _groups.size(); ++i) {
            int need = _groups[i]->sizeHint().width();
            if (i > 0 && i - 1 < _dividers.size()) {
                need += _dividers[i - 1]->sizeHint().width();
            }
            if (!overflowing && used + need <= available) {
                used += need;
                continue;
            }
            overflowing = true;
            _groups[i]->hide();
            if (i > 0 && i - 1 < _dividers.size()) {
                _dividers[i - 1]->hide();
            }
            const auto buttons = _groups[i]->findChildren<QToolButton*>();
            for (QToolButton* btn : buttons) {
                if (QAction* action = btn->defaultAction()) {
                    _overflow->menu()->addAction(action);
                }
            }
        }
        _overflow->setVisible(!_overflow->menu()->isEmpty());
    }

    QList<QWidget*> _groups;
    QList<QWidget*> _dividers;
    QToolButton* _overflow = nullptr;
};
}  // namespace

RibbonBar::RibbonBar(QWidget* parent)
    : QWidget(parent)
{
    setObjectName(QStringLiteral("RibbonBar"));
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);

    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    _qat = new QWidget(this);
    _qat->setObjectName(QStringLiteral("RibbonQuickAccessBar"));
    auto* qatLayout = new QHBoxLayout(_qat);
    qatLayout->setContentsMargins(8, 2, 8, 2);
    qatLayout->setSpacing(2);
    qatLayout->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    root->addWidget(_qat);

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
    return {800, 132};
}

QSize RibbonBar::minimumSizeHint() const
{
    return {200, 120};
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
    if (_qat) {
        qDeleteAll(_qat->findChildren<QWidget*>(QString(), Qt::FindDirectChildrenOnly));
    }
    _tabKeys.clear();
}

void RibbonBar::populateQuickAccess()
{
    if (!_qat) {
        return;
    }
    auto* layout = qobject_cast<QHBoxLayout*>(_qat->layout());
    if (!layout) {
        return;
    }
    static const char* commands[] = {"Std_New", "Std_Save", "Std_Undo", "Std_Redo"};
    for (const char* name : commands) {
        if (QWidget* widget = makeCommandWidget(name, _qat, ButtonStyle::QuickAccess)) {
            layout->addWidget(widget);
        }
    }
    layout->addStretch(1);
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

QWidget* RibbonBar::makeCommandWidget(const char* name, QWidget* parent, ButtonStyle style)
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
    btn->setDefaultAction(act->action());
    btn->setAutoRaise(true);
    btn->setFocusPolicy(Qt::NoFocus);

    if (style == ButtonStyle::QuickAccess) {
        btn->setObjectName(QStringLiteral("RibbonQatButton"));
        btn->setToolButtonStyle(Qt::ToolButtonIconOnly);
        btn->setIconSize(QSize(20, 20));
    }
    else {
        btn->setObjectName(QStringLiteral("RibbonCommandButton"));
        btn->setToolButtonStyle(Qt::ToolButtonTextUnderIcon);
        const int iconPx = ToolBarManager::getInstance()->toolBarIconSize();
        btn->setIconSize(QSize(iconPx, iconPx));
    }

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
        if (QWidget* widget = makeCommandWidget(child->command().c_str(), parent, ButtonStyle::Ribbon)) {
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
    populateQuickAccess();
    if (!root) {
        return;
    }

    for (ToolBarItem* toolbar : root->getItems()) {
        if (!toolbar || toolbarIsWorkbenchOnly(toolbar)) {
            for (ToolBarItem* child : toolbar ? toolbar->getItems() : QList<ToolBarItem*>()) {
                if (isWorkbenchCommand(child)) {
                    if (QWidget* widget =
                            makeCommandWidget("Std_Workbench", _workbenchHost, ButtonStyle::Ribbon)) {
                        placeWorkbenchSelector(widget);
                    }
                }
            }
            continue;
        }

        // Classic-hidden toolbars (Clipboard, Macro, Individual Views) stay in the menus.
        if (toolbar->visibilityPolicy == ToolBarItem::DefaultVisibility::Hidden) {
            continue;
        }

        auto* page = new RibbonPageHost;

        auto* currentGroup = makeGroup(translateToolbarName(toolbar->command()), page);
        page->addGroup(currentGroup);
        auto* currentCommands = currentGroup->findChild<QWidget*>(QStringLiteral("RibbonGroupCommands"));
        auto* currentLayout = qobject_cast<QHBoxLayout*>(currentCommands->layout());

        bool groupHasCommands = false;
        for (ToolBarItem* child : toolbar->getItems()) {
            if (isWorkbenchCommand(child)) {
                if (QWidget* widget =
                        makeCommandWidget("Std_Workbench", _workbenchHost, ButtonStyle::Ribbon)) {
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
                    page->addDivider(divider);
                    currentGroup = makeGroup(translateToolbarName(toolbar->command()), page);
                    page->addGroup(currentGroup);
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
            if (QWidget* widget =
                    makeCommandWidget(child->command().c_str(), currentCommands, ButtonStyle::Ribbon)) {
                if (widget->objectName() == QLatin1String("RibbonWorkbenchBox")) {
                    placeWorkbenchSelector(widget);
                }
                else {
                    currentLayout->addWidget(widget);
                    groupHasCommands = true;
                }
            }
        }

        page->finish();

        const QString title = translateToolbarName(toolbar->command());
        _tabKeys << QString::fromUtf8(toolbar->command().c_str());
        const int index = _tabs->addTab(title);
        _tabs->setTabData(index, static_cast<int>(toolbar->visibilityPolicy));
        _pages->addWidget(page);
    }

    if (_tabs->count() > 0) {
        _tabs->setCurrentIndex(0);
        _pages->setCurrentIndex(0);
    }
}

void RibbonBar::applyContext(bool sketchInEdit)
{
    if (!_tabs) {
        return;
    }

    int firstVisible = -1;
    for (int i = 0; i < _tabs->count(); ++i) {
        const auto policy = static_cast<ToolBarItem::DefaultVisibility>(_tabs->tabData(i).toInt());
        const bool show = (policy != ToolBarItem::DefaultVisibility::Unavailable) || sketchInEdit;
        _tabs->setTabVisible(i, show);
        if (QWidget* page = _pages->widget(i)) {
            page->setEnabled(show);
        }
        if (show && firstVisible < 0) {
            firstVisible = i;
        }
    }

    if (_tabs->count() > 0 && !_tabs->isTabVisible(_tabs->currentIndex()) && firstVisible >= 0) {
        _tabs->setCurrentIndex(firstVisible);
        _pages->setCurrentIndex(firstVisible);
    }

    if (sketchInEdit) {
        for (int i = 0; i < _tabs->count(); ++i) {
            const auto policy = static_cast<ToolBarItem::DefaultVisibility>(_tabs->tabData(i).toInt());
            if (policy == ToolBarItem::DefaultVisibility::Unavailable) {
                _tabs->setCurrentIndex(i);
                _pages->setCurrentIndex(i);
                break;
            }
        }
    }
}

void RibbonBar::retranslate()
{
    for (int i = 0; i < _tabs->count() && i < _tabKeys.size(); ++i) {
        _tabs->setTabText(i, QApplication::translate("Workbench", _tabKeys.at(i).toUtf8().constData()));
    }
}
