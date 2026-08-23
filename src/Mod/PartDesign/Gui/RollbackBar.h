// SPDX-License-Identifier: LGPL-2.1-or-later

#pragma once

#include <QWidget>
#include <vector>

#include <fastsignals/connection.h>
#include <App/DocumentObject.h>

class QLabel;
class QSlider;

namespace PartDesign
{
class Body;
}

namespace PartDesignGui
{

/** SolidWorks-style history slider under the Combo View.
 *  Moves Body::Tip through solid features so the 3D view shows that step.
 */
class RollbackBar: public QWidget
{
    Q_OBJECT

public:
    explicit RollbackBar(QWidget* parent = nullptr);
    static void install();

private Q_SLOTS:
    void onSliderPressed();
    void onSliderMoved(int index);
    void onSliderReleased();

private:
    void refresh();
    void applyTip(int index, bool commitTransaction);
    std::vector<App::DocumentObject*> solidFeatures(PartDesign::Body* body) const;
    PartDesign::Body* activeBody() const;

    QSlider* _slider = nullptr;
    QLabel* _caption = nullptr;
    QLabel* _feature = nullptr;
    bool _dragging = false;
    bool _updating = false;

    fastsignals::scoped_connection _connChanged;
    fastsignals::scoped_connection _connActive;
};

}  // namespace PartDesignGui
