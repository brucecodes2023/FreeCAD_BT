// SPDX-License-Identifier: LGPL-2.1-or-later

#pragma once

#include <QWidget>

class QHBoxLayout;
class QStackedWidget;
class QTabBar;

namespace Gui
{

class ToolBarItem;

/** Fusion-style ribbon: tabs per workbench toolbar, grouped command buttons. */
class RibbonBar: public QWidget
{
    Q_OBJECT

public:
    explicit RibbonBar(QWidget* parent = nullptr);

    void setup(ToolBarItem* root);
    void retranslate();
    void clearRibbon();

    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;

private:
    QWidget* makeCommandWidget(const char* name, QWidget* parent);
    QWidget* makeGroup(const QString& title, QWidget* parent);
    void addCommandsToGroup(ToolBarItem* item, QHBoxLayout* groupLayout, QWidget* parent);
    void placeWorkbenchSelector(QWidget* widget);

    QTabBar* _tabs = nullptr;
    QStackedWidget* _pages = nullptr;
    QWidget* _workbenchHost = nullptr;
    QStringList _tabKeys;
};

}  // namespace Gui
