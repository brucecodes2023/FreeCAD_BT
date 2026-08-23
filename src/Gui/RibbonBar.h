// SPDX-License-Identifier: LGPL-2.1-or-later

#pragma once

#include <QWidget>
#include <QStringList>

class QHBoxLayout;
class QStackedWidget;
class QTabBar;

namespace Gui
{

class ToolBarItem;

/** FreeCAD ribbon look: workbench tabs, large/small command groups, native macOS menus. */
class RibbonBar: public QWidget
{
    Q_OBJECT

public:
    explicit RibbonBar(QWidget* parent = nullptr);

    void setup(ToolBarItem* root);
    void retranslate();
    void clearRibbon();
    void applyContext(bool sketchInEdit);

    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;

private:
    enum class ButtonStyle
    {
        Large,
        Small
    };

    QWidget* makeCommandWidget(const char* name, QWidget* parent, ButtonStyle style);
    QWidget* makeGroup(const QString& title, QWidget* parent);
    void populateWorkbenchTabs();
    void appendToolbarPanel(QWidget* page, ToolBarItem* toolbar);
    void appendNamedPanel(QWidget* page, const QString& title, const QStringList& names);
    void addPanelToPage(QWidget* pageWidget, QWidget* group);
    void onWorkbenchTabChanged(int index);

    QTabBar* _tabs = nullptr;
    QStackedWidget* _pages = nullptr;
    QStringList _tabKeys;
    bool _updatingTabs = false;
};

}  // namespace Gui
