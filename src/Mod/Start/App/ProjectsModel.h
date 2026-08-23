// SPDX-License-Identifier: LGPL-2.1-or-later

#pragma once

#include <QAbstractListModel>
#include <QStringList>
#include <Base/Parameter.h>

#include "../StartGlobal.h"

namespace Start
{

/// Recent project folders stored in user parameters.
class StartExport ProjectsModel: public QAbstractListModel
{
    Q_OBJECT
public:
    enum Roles
    {
        PathRole = Qt::UserRole + 1,
        FileCountRole,
        ModifiedRole
    };

    explicit ProjectsModel(QObject* parent = nullptr);

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;

    void loadProjects();
    void addProject(const QString& path);
    void removeProject(const QString& path);
    QString pathAt(int row) const;
    int projectCount() const;

private:
    void saveProjects();
    static int countCadFiles(const QString& path);

    Base::Reference<ParameterGrp> _parameterGroup;
    QStringList _paths;
};

}  // namespace Start
