// SPDX-License-Identifier: LGPL-2.1-or-later

#pragma once

#include <FCGlobal.h>

namespace Gui
{

class RibbonBar;
class ToolBarItem;

/**
 * Owns the Fusion-style ribbon, hides classic toolbars when it is enabled,
 * and hides the ribbon itself while the Start dashboard is the active view.
 */
class GuiExport RibbonManager
{
public:
    static RibbonManager* getInstance();
    static void destruct();

    static bool useRibbon();

    void ensureInstalled();
    void setup(ToolBarItem* root);
    void retranslate();
    void syncVisibility();
    void applyPreference();

    RibbonBar* ribbonBar() const
    {
        return _bar;
    }

private:
    RibbonManager() = default;
    ~RibbonManager() = default;

    static RibbonManager* _instance;
    RibbonBar* _bar = nullptr;
    bool _installed = false;
    bool _dashboard = false;
};

}  // namespace Gui
