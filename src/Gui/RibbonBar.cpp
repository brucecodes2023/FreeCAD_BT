// SPDX-License-Identifier: LGPL-2.1-or-later

#include "PreCompiled.h"
#ifndef _PreComp_
# include <QApplication>
# include <QFrame>
# include <QGridLayout>
# include <QHBoxLayout>
# include <QIcon>
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
#include "PreferencePages/DlgSettingsWorkbenchesImp.h"
#include "ToolBarManager.h"
#include "WorkbenchManager.h"

#include <QAction>
#include <QSet>
#include <QSignalBlocker>

using namespace Gui;

namespace
{
bool isSeparator(const ToolBarItem* item)
{
    return item && item->command() == "Separator";
}

bool isWorkbenchCommand(const ToolBarItem* item)
{
    return item && item->command() == "Std_Workbench";
}

bool isMenuChromeToolbar(const std::string& name)
{
    return name == "File" || name == "Edit" || name == "View" || name == "Help"
        || name == "Workbench" || name == "Clipboard" || name == "Macro";
}

bool isSmallOnlyPanel(const QString& toolbarName)
{
    return toolbarName.contains(QLatin1String("Structure"), Qt::CaseInsensitive)
        || toolbarName.contains(QLatin1String("Individual Views"), Qt::CaseInsensitive)
        || toolbarName.contains(QLatin1String("View"), Qt::CaseInsensitive)
        || toolbarName.contains(QLatin1String("Tools"), Qt::CaseInsensitive)
        || toolbarName.contains(QLatin1String("Geometr"), Qt::CaseInsensitive)
        || toolbarName.contains(QLatin1String("Constraint"), Qt::CaseInsensitive)
        || toolbarName.contains(QLatin1String("B-Spline"), Qt::CaseInsensitive)
        || toolbarName.contains(QLatin1String("Visual"), Qt::CaseInsensitive);
}

bool isLargeCommand(const QString& name)
{
    static const QSet<QString> large {
        QStringLiteral("PartDesign_CompSketches"),
        QStringLiteral("PartDesign_NewSketch"),
        QStringLiteral("PartDesign_Pad"),
        QStringLiteral("PartDesign_Pocket"),
        QStringLiteral("PartDesign_Hole"),
        QStringLiteral("PartDesign_Revolution"),
        QStringLiteral("PartDesign_Fillet"),
        QStringLiteral("PartDesign_Chamfer"),
        QStringLiteral("PartDesign_Draft"),
        QStringLiteral("PartDesign_Thickness"),
        QStringLiteral("PartDesign_LinearPattern"),
        QStringLiteral("PartDesign_PolarPattern"),
        QStringLiteral("PartDesign_Mirrored"),
        QStringLiteral("Sketcher_NewSketch"),
        QStringLiteral("Part_Box"),
        QStringLiteral("Part_Extrude"),
        QStringLiteral("Part_Cut"),
        QStringLiteral("Part_Fuse"),
        QStringLiteral("Assembly_CreateMate"),
        QStringLiteral("Assembly_CreateJointFixed"),
        QStringLiteral("Assembly_CreateJointRevolute"),
        QStringLiteral("Assembly_Insert"),
        QStringLiteral("Assembly_SolveAssembly"),
        QStringLiteral("TechDraw_QuickDrawing"),
        QStringLiteral("TechDraw_PageDefault"),
        QStringLiteral("TechDraw_ProjectionGroup"),
        QStringLiteral("TechDraw_View"),
        QStringLiteral("TechDraw_CompDimensionTools"),
        QStringLiteral("TechDraw_Dimension"),
    };
    return large.contains(name);
}


QString ribbonCommandLabel(const QString& name, const QString& fallback)
{
    static const QHash<QString, QString> labels {
        {QStringLiteral("PartDesign_NewSketch"), QApplication::translate("RibbonBar", "Sketch")},
        {QStringLiteral("PartDesign_CompSketches"), QApplication::translate("RibbonBar", "Sketch")},
        {QStringLiteral("PartDesign_Pad"), QApplication::translate("RibbonBar", "Extrude")},
        {QStringLiteral("PartDesign_Pocket"), QApplication::translate("RibbonBar", "Extrude Cut")},
        {QStringLiteral("PartDesign_Hole"), QApplication::translate("RibbonBar", "Hole")},
        {QStringLiteral("PartDesign_Revolution"), QApplication::translate("RibbonBar", "Revolve")},
        {QStringLiteral("PartDesign_Groove"), QApplication::translate("RibbonBar", "Revolve Cut")},
        {QStringLiteral("PartDesign_Fillet"), QApplication::translate("RibbonBar", "Fillet")},
        {QStringLiteral("PartDesign_Chamfer"), QApplication::translate("RibbonBar", "Chamfer")},
        {QStringLiteral("PartDesign_Draft"), QApplication::translate("RibbonBar", "Draft")},
        {QStringLiteral("PartDesign_Thickness"), QApplication::translate("RibbonBar", "Shell")},
        {QStringLiteral("PartDesign_LinearPattern"), QApplication::translate("RibbonBar", "Pattern")},
        {QStringLiteral("PartDesign_PolarPattern"), QApplication::translate("RibbonBar", "Circular Pattern")},
        {QStringLiteral("PartDesign_Mirrored"), QApplication::translate("RibbonBar", "Mirror")},
        {QStringLiteral("PartDesign_AdditivePipe"), QApplication::translate("RibbonBar", "Sweep")},
        {QStringLiteral("PartDesign_AdditiveLoft"), QApplication::translate("RibbonBar", "Loft")},
        {QStringLiteral("PartDesign_AdditiveHelix"), QApplication::translate("RibbonBar", "Coil")},
        {QStringLiteral("Sketcher_NewSketch"), QApplication::translate("RibbonBar", "Sketch")},
        {QStringLiteral("Part_Extrude"), QApplication::translate("RibbonBar", "Extrude")},
    };
    return labels.value(name, fallback);
}

QString panelTitle(const std::string& toolbarName)
{
    const QString name = QString::fromUtf8(toolbarName.c_str());
    if (name.contains(QLatin1String("Helper"))) {
        return QApplication::translate("RibbonBar", "Construct");
    }
    if (name.contains(QLatin1String("Modeling"))) {
        return QApplication::translate("RibbonBar", "Create");
    }
    if (name.contains(QLatin1String("Dress-Up")) || name.contains(QLatin1String("Dress-up"))) {
        return QApplication::translate("RibbonBar", "Modify");
    }
    if (name.contains(QLatin1String("Transformation")) || name.contains(QLatin1String("Pattern"))) {
        return QApplication::translate("RibbonBar", "Patterns");
    }
    if (name.contains(QLatin1String("Individual Views"))) {
        return QApplication::translate("RibbonBar", "Views");
    }
    if (name.contains(QLatin1String("TechDraw Pages"))) {
        return QApplication::translate("RibbonBar", "Page");
    }
    if (name.contains(QLatin1String("TechDraw Views"))) {
        return QApplication::translate("RibbonBar", "Views");
    }
    if (name.contains(QLatin1String("TechDraw Dimensions"))) {
        return QApplication::translate("RibbonBar", "Dimensions");
    }
    if (name.contains(QLatin1String("TechDraw File Access"))) {
        return QApplication::translate("RibbonBar", "Export");
    }
    if (name.contains(QLatin1String("TechDraw Decsheets"))) {
        return QApplication::translate("RibbonBar", "Decorate");
    }
    if (name.contains(QLatin1String("TechDraw Annotation"))) {
        return QApplication::translate("RibbonBar", "Annotate");
    }
    if (name == QLatin1String("Structure")) {
        return QApplication::translate("RibbonBar", "Structure");
    }
    if (name.contains(QLatin1String("Geometr"))) {
        return QApplication::translate("RibbonBar", "Geometries");
    }
    if (name.contains(QLatin1String("Constraint"))) {
        return QApplication::translate("RibbonBar", "Constraints");
    }
    QString shortName = name;
    shortName.replace(QLatin1String(" Features"), QString());
    shortName.replace(QLatin1String(" Tools"), QString());
    shortName.replace(QLatin1String("TechDraw "), QString());
    return QApplication::translate("Workbench", shortName.toUtf8().constData());
}

void collectCommands(const ToolBarItem* item, QStringList& names)
{
    if (!item) {
        return;
    }
    for (ToolBarItem* child : item->getItems()) {
        if (!child || isSeparator(child) || isWorkbenchCommand(child)) {
            continue;
        }
        if (child->hasItems()) {
            collectCommands(child, names);
            continue;
        }
        names << QString::fromUtf8(child->command().c_str());
    }
}

class RibbonPageHost: public QWidget
{
public:
    explicit RibbonPageHost(QWidget* parent = nullptr)
        : QWidget(parent)
    {
        setObjectName(QStringLiteral("RibbonPage"));
        setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Minimum);
        setMinimumHeight(96);
        auto* layout = new QHBoxLayout(this);
        layout->setContentsMargins(4, 4, 4, 2);
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

    bool isEmpty() const
    {
        return _groups.isEmpty();
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
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Minimum);

    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    auto* tabRow = new QWidget(this);
    tabRow->setObjectName(QStringLiteral("RibbonTabRow"));
    auto* tabLayout = new QHBoxLayout(tabRow);
    tabLayout->setContentsMargins(0, 0, 0, 0);
    tabLayout->setSpacing(0);

    _tabs = new QTabBar(tabRow);
    _tabs->setObjectName(QStringLiteral("RibbonTabBar"));
    _tabs->setExpanding(false);
    _tabs->setDrawBase(false);
    _tabs->setUsesScrollButtons(true);
    _tabs->setDocumentMode(true);
    _tabs->setIconSize(QSize(16, 16));
    tabLayout->addWidget(_tabs, 1);
    root->addWidget(tabRow);

    _pages = new QStackedWidget(this);
    _pages->setObjectName(QStringLiteral("RibbonPages"));
    _pages->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::MinimumExpanding);
    _pages->setMinimumHeight(96);
    root->addWidget(_pages, 1);

    connect(this->_tabs, &QTabBar::currentChanged, this, &RibbonBar::onWorkbenchTabChanged);
}

QSize RibbonBar::sizeHint() const
{
    const QSize hint = QWidget::sizeHint();
    return {qMax(hint.width(), 800), qMax(hint.height(), 148)};
}

QSize RibbonBar::minimumSizeHint() const
{
    const QSize hint = QWidget::minimumSizeHint();
    return {qMax(hint.width(), 200), qMax(hint.height(), 140)};
}

void RibbonBar::clearRibbon()
{
    const QSignalBlocker blocker(_tabs);
    while (_tabs->count() > 0) {
        _tabs->removeTab(0);
    }
    while (_pages->count() > 0) {
        QWidget* page = _pages->widget(0);
        _pages->removeWidget(page);
        delete page;
    }
    _tabKeys.clear();
}

void RibbonBar::populateWorkbenchTabs()
{
    const QStringList enabled = Dialog::DlgSettingsWorkbenchesImp::getEnabledWorkbenches();
    const QString active = QString::fromStdString(WorkbenchManager::instance()->activeName());
    int activeIndex = 0;

    const QSignalBlocker blocker(_tabs);
    for (const QString& wbName : enabled) {
        if (wbName == QLatin1String("StartWorkbench")
            || wbName == QLatin1String("NoneWorkbench")) {
            continue;
        }
        const QString text = Application::Instance->workbenchMenuText(wbName);
        const QPixmap px = Application::Instance->workbenchIcon(wbName);
        const int index = px.isNull() ? _tabs->addTab(text) : _tabs->addTab(QIcon(px), text);
        _tabs->setTabData(index, wbName);
        _tabs->setTabToolTip(index, text);
        _tabKeys << wbName;
        if (wbName == active) {
            activeIndex = _tabs->count() - 1;
        }
    }
    if (_tabs->count() > 0) {
        _tabs->setCurrentIndex(activeIndex);
    }
}

QWidget* RibbonBar::makeGroup(const QString& title, QWidget* parent)
{
    auto* group = new QFrame(parent);
    group->setObjectName(QStringLiteral("RibbonGroup"));
    auto* layout = new QVBoxLayout(group);
    layout->setContentsMargins(6, 4, 6, 2);
    layout->setSpacing(2);

    auto* commands = new QWidget(group);
    commands->setObjectName(QStringLiteral("RibbonGroupCommands"));
    auto* commandsLayout = new QHBoxLayout(commands);
    commandsLayout->setContentsMargins(0, 0, 0, 0);
    commandsLayout->setSpacing(2);
    commandsLayout->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    layout->addWidget(commands, 1);

    auto* label = new QLabel(title, group);
    label->setObjectName(QStringLiteral("RibbonGroupTitle"));
    label->setAlignment(Qt::AlignHCenter | Qt::AlignBottom);
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

    if (dynamic_cast<WorkbenchGroup*>(act)) {
        return nullptr;
    }

    auto* btn = new QToolButton(parent);
    btn->setDefaultAction(act->action());
    // Fusion-style short labels on ribbon (iconText); menus keep menu text.
    {
        const QString fusion = ribbonCommandLabel(QString::fromUtf8(name), act->action()->text());
        if (fusion != act->action()->text()) {
            act->action()->setIconText(fusion);
        }
    }
    btn->setAutoRaise(true);
    btn->setFocusPolicy(Qt::NoFocus);

    if (style == ButtonStyle::Small) {
        btn->setObjectName(QStringLiteral("RibbonSmallButton"));
        btn->setToolButtonStyle(Qt::ToolButtonIconOnly);
        btn->setIconSize(QSize(24, 24));
        btn->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
    }
    else {
        btn->setObjectName(QStringLiteral("RibbonLargeButton"));
        btn->setToolButtonStyle(Qt::ToolButtonTextUnderIcon);
        btn->setIconSize(QSize(32, 32));
        btn->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Minimum);
    }

    if (auto* group = dynamic_cast<ActionGroup*>(act)) {
        const QList<QAction*> actions = group->actions();
        if (!actions.isEmpty()) {
            auto* menu = new QMenu(btn);
            menu->addActions(actions);
            btn->setMenu(menu);
            // Small icons cannot spare a split chevron; large buttons keep a
            // separate menu strip below the icon so it does not cover the graphic.
            if (style == ButtonStyle::Small) {
                btn->setPopupMode(QToolButton::InstantPopup);
                btn->setMinimumWidth(36);
                btn->setMaximumWidth(40);
            }
            else {
                btn->setPopupMode(QToolButton::MenuButtonPopup);
                btn->setMinimumWidth(72);
                btn->setMaximumWidth(100);
            }
        }
    }

    return btn;
}

void RibbonBar::addPanelToPage(QWidget* pageWidget, QWidget* group)
{
    auto* page = static_cast<RibbonPageHost*>(pageWidget);
    if (!page->isEmpty()) {
        auto* divider = new QFrame(page);
        divider->setObjectName(QStringLiteral("RibbonGroupDivider"));
        divider->setFrameShape(QFrame::NoFrame);
        divider->setFixedWidth(1);
        page->addDivider(divider);
    }
    page->addGroup(group);
}

void RibbonBar::appendNamedPanel(QWidget* pageWidget, const QString& title, const QStringList& names)
{
    if (names.isEmpty()) {
        return;
    }
    auto* page = static_cast<RibbonPageHost*>(pageWidget);
    auto* group = makeGroup(title, page);
    auto* commands = group->findChild<QWidget*>(QStringLiteral("RibbonGroupCommands"));
    auto* layout = qobject_cast<QHBoxLayout*>(commands->layout());

    auto* smallHost = new QWidget(commands);
    auto* grid = new QGridLayout(smallHost);
    grid->setContentsMargins(0, 0, 0, 0);
    grid->setHorizontalSpacing(2);
    grid->setVerticalSpacing(2);

    int smallIndex = 0;
    bool added = false;
    const bool smallOnly = isSmallOnlyPanel(title);
    bool sawKnownLarge = false;
    for (const QString& name : names) {
        if (isLargeCommand(name)) {
            sawKnownLarge = true;
        }
    }

    int addedCount = 0;
    for (const QString& name : names) {
        const bool large = isLargeCommand(name)
            || (!smallOnly && !sawKnownLarge && addedCount == 0);
        const ButtonStyle style = large ? ButtonStyle::Large : ButtonStyle::Small;
        QWidget* widget = makeCommandWidget(name.toUtf8().constData(), commands, style);
        if (!widget) {
            continue;
        }
        added = true;
        ++addedCount;
        if (style == ButtonStyle::Large) {
            layout->addWidget(widget, 0, Qt::AlignTop);
        }
        else {
            grid->addWidget(widget, smallIndex % 3, smallIndex / 3, Qt::AlignTop);
            ++smallIndex;
        }
    }

    if (smallIndex > 0) {
        layout->addWidget(smallHost, 0, Qt::AlignVCenter);
    }
    else {
        delete smallHost;
    }

    if (added) {
        addPanelToPage(page, group);
    }
    else {
        delete group;
    }
}

void RibbonBar::appendToolbarPanel(QWidget* pageWidget, ToolBarItem* toolbar)
{
    if (!toolbar) {
        return;
    }
    QStringList names;
    collectCommands(toolbar, names);
    if (names.isEmpty()) {
        return;
    }
    appendNamedPanel(pageWidget, panelTitle(toolbar->command()), names);
}

void RibbonBar::setup(ToolBarItem* root)
{
    _updatingTabs = true;
    clearRibbon();
    populateWorkbenchTabs();
    if (!root) {
        _updatingTabs = false;
        return;
    }

    auto* page = new RibbonPageHost;
    QStringList toolCommands;

    for (ToolBarItem* toolbar : root->getItems()) {
        if (!toolbar) {
            continue;
        }
        const std::string& name = toolbar->command();
        if (isMenuChromeToolbar(name)) {
            if (name == "View") {
                QStringList viewCommands;
                collectCommands(toolbar, viewCommands);
                for (const QString& command : viewCommands) {
                    if (command == QLatin1String("Std_Measure")
                        || command == QLatin1String("Std_MassProperties")) {
                        toolCommands << command;
                    }
                }
            }
            continue;
        }
        if (toolbar->visibilityPolicy == ToolBarItem::DefaultVisibility::Hidden
            && name != "Individual Views") {
            continue;
        }
        appendToolbarPanel(page, toolbar);
    }

    if (!toolCommands.isEmpty()) {
        appendNamedPanel(
            page,
            QApplication::translate("RibbonBar", "Tools"),
            toolCommands
        );
    }

    page->finish();
    _pages->addWidget(page);
    _pages->setCurrentIndex(0);
    _updatingTabs = false;
}

void RibbonBar::onWorkbenchTabChanged(int index)
{
    if (_updatingTabs || index < 0 || !_tabs) {
        return;
    }
    const QString name = _tabs->tabData(index).toString();
    if (name.isEmpty()) {
        return;
    }
    const QString active = QString::fromStdString(WorkbenchManager::instance()->activeName());
    if (name == active) {
        return;
    }
    Application::Instance->activateWorkbench(name.toUtf8().constData());
}

void RibbonBar::applyContext(bool)
{
}

void RibbonBar::retranslate()
{
    for (int i = 0; i < _tabs->count(); ++i) {
        const QString wbName = _tabs->tabData(i).toString();
        if (!wbName.isEmpty()) {
            const QString text = Application::Instance->workbenchMenuText(wbName);
            _tabs->setTabText(i, text);
            _tabs->setTabToolTip(i, text);
        }
    }
}
