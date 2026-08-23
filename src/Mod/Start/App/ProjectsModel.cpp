// SPDX-License-Identifier: LGPL-2.1-or-later

#include "ProjectsModel.h"

#include <fmt/format.h>
#include <QDateTime>
#include <QDir>
#include <QFileInfo>

#include <App/Application.h>

using namespace Start;

ProjectsModel::ProjectsModel(QObject* parent)
    : QAbstractListModel(parent)
{
    _parameterGroup = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start/Projects"
    );
}

int ProjectsModel::rowCount(const QModelIndex& parent) const
{
    if (parent.isValid()) {
        return 0;
    }
    return _paths.size();
}

QVariant ProjectsModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= _paths.size()) {
        return {};
    }
    const QString path = _paths.at(index.row());
    const QFileInfo info(path);
    switch (role) {
        case Qt::DisplayRole:
            return info.fileName().isEmpty() ? path : info.fileName();
        case Qt::ToolTipRole:
            return path;
        case PathRole:
            return path;
        case FileCountRole:
            return countCadFiles(path);
        case ModifiedRole:
            return info.lastModified();
        default:
            break;
    }
    return {};
}

void ProjectsModel::loadProjects()
{
    beginResetModel();
    _paths.clear();
    const int count = static_cast<int>(_parameterGroup->GetInt("Count", 0));
    for (int i = 0; i < count; ++i) {
        auto path = QString::fromStdString(
            _parameterGroup->GetASCII(fmt::format("MRU{}", i).c_str(), "")
        );
        if (!path.isEmpty() && QFileInfo::exists(path)) {
            _paths.push_back(path);
        }
    }
    endResetModel();
}

void ProjectsModel::addProject(const QString& path)
{
    const QString canonical = QFileInfo(path).absoluteFilePath();
    if (canonical.isEmpty()) {
        return;
    }
    _paths.removeAll(canonical);
    _paths.prepend(canonical);
    while (_paths.size() > 20) {
        _paths.removeLast();
    }
    saveProjects();
    loadProjects();
}

void ProjectsModel::removeProject(const QString& path)
{
    const QString canonical = QFileInfo(path).absoluteFilePath();
    if (canonical.isEmpty()) {
        return;
    }
    if (!_paths.contains(canonical) && !_paths.contains(path)) {
        return;
    }
    _paths.removeAll(canonical);
    _paths.removeAll(path);
    saveProjects();
    loadProjects();
}

QString ProjectsModel::pathAt(int row) const
{
    if (row < 0 || row >= _paths.size()) {
        return {};
    }
    return _paths.at(row);
}

int ProjectsModel::projectCount() const
{
    return _paths.size();
}

void ProjectsModel::saveProjects()
{
    const int oldCount = static_cast<int>(_parameterGroup->GetInt("Count", 0));
    _parameterGroup->SetInt("Count", _paths.size());
    for (int i = 0; i < _paths.size(); ++i) {
        _parameterGroup->SetASCII(fmt::format("MRU{}", i).c_str(), _paths.at(i).toStdString());
    }
    for (int i = _paths.size(); i < oldCount; ++i) {
        _parameterGroup->RemoveASCII(fmt::format("MRU{}", i).c_str());
    }
}

int ProjectsModel::countCadFiles(const QString& path)
{
    QDir dir(path);
    const QStringList files = dir.entryList(
        QStringList {QStringLiteral("*.FCStd"), QStringLiteral("*.fcstd")},
        QDir::Files
    );
    return files.size();
}
