// SPDX-License-Identifier: LGPL-2.1-or-later
/****************************************************************************
 *                                                                          *
 *   Copyright (c) 2024 The FreeCAD Project Association AISBL               *
 *                                                                          *
 *   This file is part of FreeCAD.                                          *
 *                                                                          *
 *   FreeCAD is free software: you can redistribute it and/or modify it     *
 *   under the terms of the GNU Lesser General Public License as            *
 *   published by the Free Software Foundation, either version 2.1 of the   *
 *   License, or (at your option) any later version.                        *
 *                                                                          *
 *   FreeCAD is distributed in the hope that it will be useful, but         *
 *   WITHOUT ANY WARRANTY; without even the implied warranty of             *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU       *
 *   Lesser General Public License for more details.                        *
 *                                                                          *
 *   You should have received a copy of the GNU Lesser General Public       *
 *   License along with FreeCAD. If not, see                                *
 *   <https://www.gnu.org/licenses/>.                                       *
 *                                                                          *
 ***************************************************************************/


#include <QApplication>
#include <QCheckBox>
#include <QDir>
#include <QFile>
#include <QFileDialog>
#include <QFrame>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QInputDialog>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QLineEdit>
#include <QListView>
#include <QMdiSubWindow>
#include <QMessageBox>
#include <QPushButton>
#include <QScrollArea>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>
#include <QStackedWidget>
#include <QShowEvent>
#include <QDateTime>

#include "StartView.h"
#include "FileCardDelegate.h"
#include "FileCardView.h"
#include "FirstStartWidget.h"
#include "FlowLayout.h"
#include "NewFileButton.h"
#include <App/Document.h>
#include <App/DocumentObject.h>
#include <App/Application.h>
#include <Base/Console.h>
#include <Base/Exception.h>
#include <Base/Interpreter.h>
#include <Base/Tools.h>
#include <Base/UnitsApi.h>
#include <Gui/Action.h>
#include <Gui/Application.h>
#include <Gui/Command.h>
#include <Gui/CommandCompleter.h>
#include <Gui/Document.h>
#include <Gui/MainWindow.h>
#include <Gui/ModuleIO.h>
#include <Gui/Navigation/NavigationStyle.h>
#include <Gui/PreferencePackManager.h>
#include <Gui/ProgramInformation.h>
#include <Gui/Utilities.h>
#include <Gui/View3DInventor.h>
#include <Gui/View3DInventorViewer.h>
#include <gsl/pointers>
#include <exception>
#include <string>

using namespace StartGui;

namespace
{
void applyModernCadOnboardingDefaults(const ParameterGrp::handle& startGrp)
{
    if (Gui::isInternalGuiTestRun()) {
        return;
    }
    if (startGrp->GetBool("ModernCADDefaultsApplied", false)) {
        return;
    }

    try {
        auto* packs = Gui::Application::Instance->prefPackManager();
        if (packs) {
            packs->apply("Modern CAD");
        }
        startGrp->SetBool("ModernCADDefaultsApplied", true);
    }
    catch (const std::exception& e) {
        Base::Console().warning(
            "Could not apply the Modern CAD preference pack during first-start setup: %s\n",
            e.what()
        );
    }
}
}  // namespace

TYPESYSTEM_SOURCE_ABSTRACT(StartGui::StartView, Gui::MDIView)  // NOLINT


StartView::StartView(QWidget* parent)
    : Gui::MDIView(nullptr, parent)
    , _contents(new QStackedWidget(parent))
    , _newFileLabel {nullptr}
    , _examplesLabel {nullptr}
    , _recentFilesLabel {nullptr}
    , _customFolderLabel {nullptr}
    , _showOnStartupCheckBox {nullptr}
{
    setObjectName(QLatin1String("StartView"));
    auto hGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start"
    );
    auto cardSpacing = hGrp->GetInt("FileCardSpacing", 15);  // NOLINT
    auto showExamples = hGrp->GetBool("ShowExamples", true);

    // Verify that the folder specified in preferences is available before showing it
    std::string customFolder(hGrp->GetASCII("CustomFolder", ""));
    bool showCustomFolder = false;
    if (!customFolder.empty()) {
        showCustomFolder = true;
    }

    // First start page
    auto firstStartScrollArea = gsl::owner<QScrollArea*>(new QScrollArea());
    auto firstStartScrollWidget = gsl::owner<QWidget*>(new QWidget(firstStartScrollArea));
    firstStartScrollArea->setWidget(firstStartScrollWidget);
    firstStartScrollArea->setWidgetResizable(true);

    auto firstStartRegion = gsl::owner<QHBoxLayout*>(new QHBoxLayout(firstStartScrollWidget));
    firstStartRegion->setAlignment(Qt::AlignCenter);
    auto firstStartWidget = gsl::owner<FirstStartWidget*>(new FirstStartWidget(this));
    connect(firstStartWidget, &FirstStartWidget::dismissed, this, &StartView::firstStartWidgetDismissed);
    firstStartRegion->addWidget(firstStartWidget);
    _contents->addWidget(firstStartScrollArea);

    // Documents page
    auto documentsWidget = gsl::owner<QWidget*>(new QWidget());
    _contents->addWidget(documentsWidget);
    auto documentsMainLayout = gsl::owner<QVBoxLayout*>(new QVBoxLayout());
    documentsWidget->setLayout(documentsMainLayout);
    auto documentsScrollArea = gsl::owner<QScrollArea*>(new QScrollArea());
    documentsScrollArea->setVerticalScrollBarPolicy(Qt::ScrollBarPolicy::ScrollBarAsNeeded);
    documentsMainLayout->addWidget(documentsScrollArea);
    auto documentsScrollWidget = gsl::owner<QWidget*>(new QWidget(documentsScrollArea));
    documentsScrollArea->setWidget(documentsScrollWidget);
    documentsScrollArea->setWidgetResizable(true);
    auto documentsContentLayout = gsl::owner<QVBoxLayout*>(new QVBoxLayout(documentsScrollWidget));
    documentsContentLayout->setSizeConstraint(QLayout::SizeConstraint::SetMinAndMaxSize);

    _dashboardTitle = gsl::owner<QLabel*>(new QLabel());
    _dashboardTitle->setObjectName(QStringLiteral("DashboardTitle"));
    documentsContentLayout->addWidget(_dashboardTitle);

    auto metricsRow = gsl::owner<QWidget*>(new QWidget);
    metricsRow->setObjectName(QStringLiteral("DashboardMetricsRow"));
    auto metricsLayout = gsl::owner<QHBoxLayout*>(new QHBoxLayout(metricsRow));
    metricsLayout->setContentsMargins({});
    metricsLayout->setSpacing(12);
    metricsLayout->addWidget(createMetricCard(_metricFilesTitle, _metricFilesValue));
    metricsLayout->addWidget(createMetricCard(_metricProjectsTitle, _metricProjectsValue));
    metricsLayout->addWidget(createMetricCard(_metricGraphicsTitle, _metricGraphicsValue));
    metricsLayout->addWidget(createMetricCard(_metricHealthTitle, _metricHealthValue));
    metricsLayout->addWidget(createMetricCard(_metricUnitsTitle, _metricUnitsValue));
    metricsLayout->addStretch();
    documentsContentLayout->addWidget(metricsRow);

    if (QWidget* tips = createTipsBanner()) {
        documentsContentLayout->addWidget(tips);
    }

    _commandSearch = gsl::owner<QLineEdit*>(new QLineEdit());
    _commandSearch->setObjectName(QStringLiteral("DashboardCommandSearch"));
    _commandSearch->setClearButtonEnabled(true);
    auto* completer = gsl::owner<Gui::CommandCompleter*>(
        new Gui::CommandCompleter(_commandSearch, _commandSearch)
    );
    connect(
        completer,
        &Gui::CommandCompleter::commandActivated,
        this,
        [](const QByteArray& name) {
            Gui::Application::Instance->commandManager().runCommandByName(name.constData());
        }
    );
    documentsContentLayout->addWidget(_commandSearch);

    _projectsLabel = gsl::owner<QLabel*>(new QLabel());
    documentsContentLayout->addWidget(_projectsLabel);

    _projectsRow = gsl::owner<QWidget*>(new QWidget);
    _projectsRow->setObjectName(QStringLiteral("DashboardProjectsRow"));
    auto projectsLayout = gsl::owner<FlowLayout*>(new FlowLayout);
    projectsLayout->setContentsMargins({});
    _projectsRow->setLayout(projectsLayout);
    documentsContentLayout->addWidget(_projectsRow);

    _newFileLabel = gsl::owner<QLabel*>(new QLabel());
    documentsContentLayout->addWidget(_newFileLabel);

    auto createNewRow = gsl::owner<QWidget*>(new QWidget);
    auto flowLayout = gsl::owner<FlowLayout*>(new FlowLayout);

    // Reset margins of layout to provide consistent spacing
    flowLayout->setContentsMargins({});

    // This allows new file widgets to be targeted via QSS
    createNewRow->setObjectName(QStringLiteral("CreateNewRow"));
    createNewRow->setLayout(flowLayout);

    documentsContentLayout->addWidget(createNewRow);
    configureNewFileButtons(flowLayout);

    _recentFilesLabel = gsl::owner<QLabel*>(new QLabel());
    documentsContentLayout->addWidget(_recentFilesLabel);
    auto recentFilesListWidget = gsl::owner<FileCardView*>(new FileCardView(_contents));
    connect(recentFilesListWidget, &QListView::clicked, this, &StartView::fileCardSelected);
    documentsContentLayout->addWidget(recentFilesListWidget);

    FileCardView* customFolderListWidget {};
    if (showCustomFolder) {
        customFolderListWidget = gsl::owner<FileCardView*>(new FileCardView(_contents));
        _customFolderLabel = gsl::owner<QLabel*>(new QLabel());
        documentsContentLayout->addWidget(_customFolderLabel);

        connect(customFolderListWidget, &QListView::clicked, this, &StartView::fileCardSelected);
        documentsContentLayout->addWidget(customFolderListWidget);
    }

    FileCardView* examplesListWidget {};
    if (showExamples) {
        examplesListWidget = gsl::owner<FileCardView*>(new FileCardView(_contents));
        _examplesLabel = gsl::owner<QLabel*>(new QLabel());
        documentsContentLayout->addWidget(_examplesLabel);

        connect(examplesListWidget, &QListView::clicked, this, &StartView::fileCardSelected);
        documentsContentLayout->addWidget(examplesListWidget);
    }

    documentsContentLayout->setSpacing(static_cast<int>(cardSpacing));
    documentsContentLayout->addStretch();


    // Documents page footer
    auto footerLayout = gsl::owner<QHBoxLayout*>(new QHBoxLayout());
    documentsMainLayout->addLayout(footerLayout);

    _openFirstStart = gsl::owner<QPushButton*>(new QPushButton());
    _openFirstStart->setIcon(QIcon(QLatin1String(":/icons/preferences-general.svg")));
    connect(_openFirstStart, &QPushButton::clicked, this, &StartView::openFirstStartClicked);

    _showOnStartupCheckBox = gsl::owner<QCheckBox*>(new QCheckBox());
    bool showOnStartup = hGrp->GetBool("ShowOnStartup", true);
    _showOnStartupCheckBox->setCheckState(
        showOnStartup ? Qt::CheckState::Unchecked : Qt::CheckState::Checked
    );
    connect(_showOnStartupCheckBox, &QCheckBox::toggled, this, &StartView::showOnStartupChanged);

    footerLayout->addWidget(_openFirstStart);
    footerLayout->addStretch();
    footerLayout->addWidget(_showOnStartupCheckBox);

    setCentralWidget(_contents);

    // Set startup widget according to the first start parameter
    auto firstStart = hGrp->GetBool("FirstStart2024", true);
    _contents->setCurrentWidget(firstStart ? firstStartScrollArea : documentsWidget);
    if (firstStart) {
        QTimer::singleShot(0, this, [hGrp]() {
            applyModernCadOnboardingDefaults(hGrp);
        });
    }
    if (customFolderListWidget) {
        configureCustomFolderListWidget(customFolderListWidget);
    }
    if (examplesListWidget) {
        configureExamplesListWidget(examplesListWidget);
    }
    configureRecentFilesListWidget(recentFilesListWidget, _recentFilesLabel);
    rebuildProjectCards();
    refreshDashboardMetrics();

    QTimer::singleShot(2000, [this, recentFilesListWidget]() {
        auto updateFun = [this, recentFilesListWidget]() {
            configureRecentFilesListWidget(recentFilesListWidget, _recentFilesLabel);
            refreshDashboardMetrics();
        };
        auto recentFiles = Gui::getMainWindow()->findChild<Gui::RecentFilesAction*>();
        if (recentFiles != nullptr) {
            connect(recentFiles, &Gui::RecentFilesAction::recentFilesListModified, this, updateFun);
        }
    });

    isInitialized = true;

    retranslateUi();
}

void StartView::configureNewFileButtons(QLayout* layout) const
{
    auto newEmptyFile = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("Empty File"),
         tr("Creates a new empty FreeCAD file"),
         QLatin1String(":/icons/document-new.svg")}
    ));
    auto openFile = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("Open File"),
         tr("Opens an existing CAD file or 3D model"),
         QLatin1String(":/icons/document-open.svg")}
    ));
    auto partDesign = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("Parametric Body"),
         tr("Creates a body with the Part Design workbench"),
         QLatin1String(":/icons/PartDesignWorkbench.svg")}
    ));
    auto assembly = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("Assembly"),
         tr("Creates an assembly project"),
         QLatin1String(":/icons/AssemblyWorkbench.svg")}
    ));
    auto draft = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("2D Draft"), tr("Creates a 2D Draft document"), QLatin1String(":/icons/DraftWorkbench.svg")}
    ));
    auto arch = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("BIM/Architecture"),
         tr("Creates an architectural project"),
         QLatin1String(":/icons/BIMWorkbench.svg")}
    ));
    auto newProject = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("New Project"),
         tr("Creates a project folder for related parts, assemblies, and drawings"),
         QLatin1String(":/icons/folder.svg")}
    ));
    auto continueLast = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("Continue"),
         tr("Opens the last FreeCAD file you worked on"),
         QLatin1String(":/icons/document-open.svg")}
    ));
    auto drawing = gsl::owner<NewFileButton*>(new NewFileButton(
        {tr("Drawing"),
         tr("Creates a TechDraw page for 2D documentation"),
         QLatin1String(":/icons/actions/TechDraw_PageDefault.svg")}
    ));

    // TODO: Ensure all of the required WBs are actually available
    layout->addWidget(partDesign);
    layout->addWidget(assembly);
    layout->addWidget(drawing);
    layout->addWidget(draft);
    layout->addWidget(arch);
    layout->addWidget(newProject);
    layout->addWidget(continueLast);
    layout->addWidget(newEmptyFile);
    layout->addWidget(openFile);

    connect(newEmptyFile, &QPushButton::clicked, this, &StartView::newEmptyFile);
    connect(openFile, &QPushButton::clicked, this, &StartView::openExistingFile);
    connect(partDesign, &QPushButton::clicked, this, &StartView::newPartDesignFile);
    connect(assembly, &QPushButton::clicked, this, &StartView::newAssemblyFile);
    connect(drawing, &QPushButton::clicked, this, &StartView::newTechDrawFile);
    connect(draft, &QPushButton::clicked, this, &StartView::newDraftFile);
    connect(arch, &QPushButton::clicked, this, &StartView::newArchFile);
    connect(newProject, &QPushButton::clicked, this, &StartView::newProject);
    connect(continueLast, &QPushButton::clicked, this, &StartView::continueLastFile);
}

void StartView::configureFileCardWidget(QListView* fileCardWidget)
{
    auto delegate = gsl::owner<FileCardDelegate*>(new FileCardDelegate(fileCardWidget));
    fileCardWidget->setItemDelegate(delegate);

    fileCardWidget->setMinimumWidth(fileCardWidget->parentWidget()->width());
    //    fileCardWidget->setGridSize(
    //        fileCardWidget->itemDelegate()->sizeHint(QStyleOptionViewItem(),
    //                                                 fileCardWidget->model()->index(0, 0)));
}


void StartView::configureRecentFilesListWidget(QListView* recentFilesListWidget, QLabel* recentFilesLabel)
{
    _recentFilesModel.loadRecentFiles();
    recentFilesListWidget->setModel(&_recentFilesModel);
    configureFileCardWidget(recentFilesListWidget);

    auto recentFilesGroup = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/RecentFiles"
    );
    auto numRecentFiles {recentFilesGroup->GetInt("RecentFiles", 0)};
    if (numRecentFiles == 0) {
        recentFilesListWidget->hide();
        recentFilesLabel->hide();
    }
    else {
        recentFilesListWidget->show();
        recentFilesLabel->show();
    }
}


void StartView::configureExamplesListWidget(QListView* examplesListWidget)
{
    _examplesModel.loadExamples();
    examplesListWidget->setModel(&_examplesModel);
    configureFileCardWidget(examplesListWidget);
}


void StartView::configureCustomFolderListWidget(QListView* customFolderListWidget)
{
    _customFolderModel.loadCustomFolder();
    customFolderListWidget->setModel(&_customFolderModel);
    configureFileCardWidget(customFolderListWidget);
}


void StartView::newEmptyFile()
{
    Gui::Application::Instance->commandManager().runCommandByName("Std_New");
    postStart(PostStartBehavior::switchWorkbench);
}

void StartView::newPartDesignFile()
{
    Gui::Application::Instance->commandManager().runCommandByName("Std_New");
    Gui::Application::Instance->activateWorkbench("PartDesignWorkbench");
    Gui::Application::Instance->commandManager().runCommandByName("PartDesign_Body");
    postStart(PostStartBehavior::doNotSwitchWorkbench);
}

void StartView::openExistingFile()
{
    auto originalDocument = Gui::Application::Instance->activeDocument();
    Gui::Application::Instance->commandManager().runCommandByName("Std_Open");
    Gui::Application::checkForRecomputes();
    if (Gui::Application::Instance->activeDocument() != originalDocument) {
        // Only run this if the user chose a new document to open (that is, they didn't cancel the
        // open file dialog)
        postStart(PostStartBehavior::switchWorkbench);
    }
}

void StartView::newAssemblyFile()
{
    Gui::Application::Instance->commandManager().runCommandByName("Std_New");
    Gui::Application::Instance->activateWorkbench("AssemblyWorkbench");
    Gui::Application::Instance->commandManager().runCommandByName("Assembly_CreateAssembly");
    Gui::Application::Instance->commandManager().runCommandByName("Std_Refresh");
    postStart(PostStartBehavior::doNotSwitchWorkbench);
}

void StartView::newDraftFile()
{
    Gui::Application::Instance->commandManager().runCommandByName("Std_New");
    Gui::Application::Instance->activateWorkbench("DraftWorkbench");
    Gui::Application::Instance->commandManager().runCommandByName("Std_ViewTop");
    postStart(PostStartBehavior::doNotSwitchWorkbench);
}

void StartView::newArchFile()
{
    Gui::Application::Instance->commandManager().runCommandByName("Std_New");
    try {
        Gui::Application::Instance->activateWorkbench("BIMWorkbench");
    }
    catch (...) {
        Gui::Application::Instance->activateWorkbench("ArchWorkbench");
    }

    // Set the camera zoom level to 10 m, which is more appropriate for architectural projects
    Gui::Command::doCommand(
        Gui::Command::Gui,
        "Gui.activeDocument().activeView().viewDefaultOrientation(None, 10000.0)"
    );
    postStart(PostStartBehavior::doNotSwitchWorkbench);
}

void StartView::newTechDrawFile()
{
    Gui::Application::Instance->commandManager().runCommandByName("Std_New");
    Gui::Application::Instance->activateWorkbench("TechDrawWorkbench");
    if (Gui::Application::Instance->commandManager().getCommandByName("TechDraw_PageDefault")) {
        Gui::Application::Instance->commandManager().runCommandByName("TechDraw_PageDefault");
    }
    postStart(PostStartBehavior::doNotSwitchWorkbench);
}

void StartView::continueLastFile()
{
    auto recentGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/RecentFiles"
    );
    const std::string path = recentGrp->GetASCII("MRU0", "");
    if (path.empty()) {
        QMessageBox::information(
            this,
            tr("Continue"),
            tr("No recent file yet. Open or create a document first.")
        );
        return;
    }
    try {
        Gui::ModuleIO::verifyAndOpenFile(QString::fromUtf8(path.c_str()));
        postStart(PostStartBehavior::switchWorkbench);
    }
    catch (Base::Exception& e) {
        e.reportException();
        Base::Console().error(e.getMessage().c_str());
    }
}

void StartView::newProject()
{
    const QString parent = QFileDialog::getExistingDirectory(
        this,
        tr("Choose a location for the new project")
    );
    if (parent.isEmpty()) {
        return;
    }

    bool ok = false;
    const QString name = QInputDialog::getText(
        this,
        tr("New Project"),
        tr("Project name:"),
        QLineEdit::Normal,
        tr("Project"),
        &ok
    );
    if (!ok || name.trimmed().isEmpty()) {
        return;
    }

    QDir dir(parent);
    if (!dir.mkdir(name) && !QDir(dir.filePath(name)).exists()) {
        QMessageBox::warning(this, tr("New Project"), tr("Could not create the project folder."));
        return;
    }

    const QString projectPath = dir.filePath(name);
    QFile marker(QDir(projectPath).filePath(QStringLiteral(".freecad-project")));
    if (marker.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text)) {
        QJsonObject json;
        json.insert(QStringLiteral("name"), name);
        json.insert(QStringLiteral("created"), QDateTime::currentDateTimeUtc().toString(Qt::ISODate));
        marker.write(QJsonDocument(json).toJson());
    }

    _projectsModel.addProject(projectPath);
    rebuildProjectCards();
    refreshDashboardMetrics();
}

QWidget* StartView::createMetricCard(QLabel*& title, QLabel*& value)
{
    auto* card = gsl::owner<QFrame*>(new QFrame());
    card->setObjectName(QStringLiteral("DashboardMetricCard"));
    auto* layout = gsl::owner<QVBoxLayout*>(new QVBoxLayout(card));
    value = gsl::owner<QLabel*>(new QLabel(QStringLiteral("—")));
    value->setObjectName(QStringLiteral("DashboardMetricValue"));
    title = gsl::owner<QLabel*>(new QLabel());
    layout->addWidget(value);
    layout->addWidget(title);
    return card;
}

QWidget* StartView::createTipsBanner()
{
    auto startGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start"
    );
    if (startGrp->GetBool("DashboardTipsDismissed", false)) {
        return nullptr;
    }

    _tipsFrame = gsl::owner<QFrame*>(new QFrame());
    _tipsFrame->setObjectName(QStringLiteral("DashboardTips"));
    auto* layout = gsl::owner<QHBoxLayout*>(new QHBoxLayout(_tipsFrame));
    _tipsLabel = gsl::owner<QLabel*>(new QLabel());
    _tipsLabel->setWordWrap(true);
    _tipsDismiss = gsl::owner<QPushButton*>(new QPushButton());
    connect(_tipsDismiss, &QPushButton::clicked, this, &StartView::dismissDashboardTips);
    layout->addWidget(_tipsLabel, 1);
    layout->addWidget(_tipsDismiss, 0, Qt::AlignTop);
    return _tipsFrame;
}

void StartView::dismissDashboardTips()
{
    auto startGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start"
    );
    startGrp->SetBool("DashboardTipsDismissed", true);
    if (_tipsFrame) {
        _tipsFrame->hide();
    }
}

int StartView::countDocumentErrors() const
{
    int errors = 0;
    for (auto* doc : App::GetApplication().getDocuments()) {
        if (!doc) {
            continue;
        }
        for (auto* obj : doc->getObjects()) {
            if (obj && obj->isError()) {
                ++errors;
            }
        }
    }
    return errors;
}

void StartView::rebuildProjectCards()
{
    if (!_projectsRow) {
        return;
    }
    auto* layout = qobject_cast<FlowLayout*>(_projectsRow->layout());
    if (!layout) {
        return;
    }
    while (QLayoutItem* item = layout->takeAt(0)) {
        delete item->widget();
        delete item;
    }

    _projectsModel.loadProjects();
    if (_projectsModel.projectCount() == 0) {
        auto* empty = gsl::owner<QLabel*>(
            new QLabel(tr("No projects yet. Create a project folder to group related files."))
        );
        layout->addWidget(empty);
        return;
    }

    for (int row = 0; row < _projectsModel.rowCount(); ++row) {
        const QString name = _projectsModel.data(_projectsModel.index(row, 0), Qt::DisplayRole).toString();
        const int fileCount =
            _projectsModel.data(_projectsModel.index(row, 0), Start::ProjectsModel::FileCountRole)
                .toInt();
        auto* button = gsl::owner<NewFileButton*>(new NewFileButton(
            {name,
             tr("%1 FreeCAD file(s)").arg(fileCount),
             QLatin1String(":/icons/folder.svg")}
        ));
        connect(button, &QPushButton::clicked, this, [this, row]() { openProjectAt(row); });
        layout->addWidget(button);
    }
}

void StartView::openProjectAt(int row)
{
    const QString path = _projectsModel.pathAt(row);
    if (path.isEmpty()) {
        return;
    }
    const QString filename = QFileDialog::getOpenFileName(
        this,
        tr("Open File in Project"),
        path,
        tr("FreeCAD files (*.FCStd *.fcstd);;All files (*)")
    );
    if (filename.isEmpty()) {
        return;
    }
    try {
        Gui::ModuleIO::verifyAndOpenFile(filename);
    }
    catch (Base::Exception& e) {
        Base::Console().error(e.getMessage().c_str());
    }
}

void StartView::refreshDashboardMetrics()
{
    if (!_metricFilesValue) {
        return;
    }
    auto recentGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/RecentFiles"
    );
    _metricFilesValue->setText(QString::number(recentGrp->GetInt("RecentFiles", 0)));
    _metricProjectsValue->setText(QString::number(_projectsModel.projectCount()));

    const std::string renderer = Gui::ProgramInformation::openGLRenderer();
    QString graphics = QString::fromStdString(renderer);
    if (graphics.isEmpty()) {
#ifdef Q_OS_MAC
        graphics = QStringLiteral("OpenGL → Metal");
#else
        graphics = QStringLiteral("OpenGL");
#endif
    }
    _metricGraphicsValue->setText(graphics);
    const bool metalWarning = graphics.contains(QLatin1String("Metal"), Qt::CaseInsensitive)
        && graphics.contains(QLatin1String("90."));
    if (metalWarning) {
        _metricGraphicsValue->setToolTip(tr(
            "Apple is translating OpenGL to Metal (renderer 90.x). If the 3D view lags, "
            "turn on Preferences → Display → 3D View → Use software OpenGL and restart."
        ));
    }
    else {
        _metricGraphicsValue->setToolTip(graphics);
    }

    if (_metricHealthValue) {
        const int errors = countDocumentErrors();
        _metricHealthValue->setText(QString::number(errors));
        _metricHealthValue->setToolTip(
            errors == 0 ? tr("No recompute errors in open documents")
                        : tr("%1 object(s) in error. Open the document and recompute.")
                              .arg(errors)
        );
    }

    if (_metricUnitsValue) {
        auto unitsGrp = App::GetApplication().GetParameterGroupByPath(
            "User parameter:BaseApp/Preferences/Units"
        );
        const auto descriptions = Base::UnitsApi::getDescriptions();
        const int schema = static_cast<int>(unitsGrp->GetInt("UserSchema", 0));
        QString units = tr("Units");
        if (schema >= 0 && schema < static_cast<int>(descriptions.size())) {
            units = QString::fromStdString(descriptions[static_cast<size_t>(schema)]);
        }
        auto viewGrp = App::GetApplication().GetParameterGroupByPath(
            "User parameter:BaseApp/Preferences/View"
        );
        const std::string nav = viewGrp->GetASCII("NavigationStyle", Gui::DefaultNavigationStyleName);
        QString navName = QString::fromStdString(nav);
        navName.remove(QLatin1String("Gui::"));
        navName.remove(QLatin1String("NavigationStyle"));
        _metricUnitsValue->setText(navName);
        _metricUnitsValue->setToolTip(units + QLatin1String(" · ") + navName);
    }
}

bool StartView::onHasMsg(const char* pMsg) const
{
    if (strcmp("AllowsOverlayOnHover", pMsg) == 0) {
        return false;
    }

    return MDIView::onHasMsg(pMsg);
}

void StartView::postStart(PostStartBehavior behavior)
{
    auto hGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start"
    );

    if (behavior == PostStartBehavior::switchWorkbench) {
        auto wb = hGrp->GetASCII("AutoloadModule", "");
        if (wb == "$LastModule") {
            wb = App::GetApplication()
                     .GetParameterGroupByPath("User parameter:BaseApp/Preferences/General")
                     ->GetASCII("LastModule", "");
        }
        if (!wb.empty()) {
            Gui::Application::Instance->activateWorkbench(wb.c_str());
        }
    }
    if (hGrp->GetBool("closeStart", false)) {
        for (QWidget* w = this; w != nullptr; w = w->parentWidget()) {
            if (auto mdiSub = qobject_cast<QMdiSubWindow*>(w)) {
                mdiSub->close();
                return;
            }
        }
    }
}


void StartView::fileCardSelected(const QModelIndex& index)
{
    try {
        auto filename = index.data(static_cast<int>(Start::DisplayedFilesModelRoles::path)).toString();
        Gui::ModuleIO::verifyAndOpenFile(filename);
    }
    catch (Base::PyException& e) {
        Base::Console().error(e.getMessage().c_str());
    }
    catch (Base::Exception& e) {
        Base::Console().error(e.getMessage().c_str());
    }
    catch (...) {
        Base::Console().error("An unknown error occurred");
    }
}

void StartView::showOnStartupChanged(bool checked)
{
    auto hGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start"
    );
    hGrp->SetBool(
        "ShowOnStartup",
        !checked
    );  // The sense of this option has been reversed: the checkbox actually says
        // "*Don't* show on startup" now, but the option is preserved in its
        // original sense, so is stored inverted.
}

void StartView::openFirstStartClicked()
{
    _contents->setCurrentIndex(0);
}

void StartView::firstStartWidgetDismissed()
{
    auto hGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start"
    );
    hGrp->SetBool("FirstStart2024", false);
    _contents->setCurrentIndex(1);
}

void StartView::changeEvent(QEvent* event)
{
    if (!isInitialized) {
        return;
    }

    _openFirstStart->setEnabled(true);
    Gui::Document* doc = Gui::Application::Instance->activeDocument();
    if (doc) {
        if (auto view = dynamic_cast<Gui::View3DInventor*>(doc->getActiveView())) {
            Gui::View3DInventorViewer* viewer = view->getViewer();
            if (viewer->isEditing()) {
                _openFirstStart->setEnabled(false);
            }
        }
    }

    if (event->type() == QEvent::LanguageChange) {
        this->retranslateUi();
    }

    Gui::MDIView::changeEvent(event);
}

void StartView::showEvent(QShowEvent* event)
{
    if (auto mainWindow = Gui::getMainWindow()) {
        if (auto mdiArea = mainWindow->findChild<QMdiArea*>()) {
            connect(
                mdiArea,
                &QMdiArea::subWindowActivated,
                this,
                &StartView::onMdiSubWindowActivated,
                Qt::UniqueConnection
            );
        }
    }
    Gui::MDIView::showEvent(event);
}

void StartView::onMdiSubWindowActivated(QMdiSubWindow* subWindow)
{
    // check if start view is activated subwindow if yes, then enable updates
    // so we can once again receive paint events
    bool isOurWindow = subWindow && subWindow->isAncestorOf(this);
    setListViewUpdatesEnabled(isOurWindow);
}

void StartView::setListViewUpdatesEnabled(bool enabled)
{
    // disable updates on all QListView widgets when inactive to prevent unnecessary paint events
    QList<QListView*> listViews = findChildren<QListView*>();
    for (QListView* listView : listViews) {
        listView->setUpdatesEnabled(enabled);
        if (listView->viewport()) {
            listView->viewport()->setUpdatesEnabled(enabled);
        }
    }
}

void StartView::recentFileAdded(const QString& filename)
{
    _recentFilesModel.recentFileAdded(filename);
}

void StartView::retranslateUi()
{
    QString title = QCoreApplication::translate("Workbench", "Start");
    setWindowTitle(title);

    const QLatin1String h1Start("<h1>");
    const QLatin1String h1End("</h1>");
    const QLatin1String h2Start("<h2>");
    const QLatin1String h2End("</h2>");

    if (_dashboardTitle) {
        _dashboardTitle->setText(tr("Home"));
    }
    if (_projectsLabel) {
        _projectsLabel->setText(h2Start + tr("Projects") + h2End);
    }
    if (_metricFilesTitle) {
        _metricFilesTitle->setText(tr("Recent files"));
        _metricProjectsTitle->setText(tr("Projects"));
        _metricGraphicsTitle->setText(tr("3D graphics"));
        if (_metricHealthTitle) {
            _metricHealthTitle->setText(tr("Recompute errors"));
        }
        if (_metricUnitsTitle) {
            _metricUnitsTitle->setText(tr("Navigation"));
        }
    }
    if (_tipsLabel) {
        _tipsLabel->setText(tr(
            "Home never shows the ribbon. Open a file to model. "
            "New profiles use SolidWorks navigation; Fusion 360 is in Preferences → Display → Navigation. "
            "On Apple Silicon, use software OpenGL if the 3D view lags."
        ));
    }
    if (_tipsDismiss) {
        _tipsDismiss->setText(tr("Dismiss"));
    }
    if (_commandSearch) {
        _commandSearch->setPlaceholderText(tr("Search commands…"));
    }

    _newFileLabel->setText(h2Start + tr("New File") + h2End);
    if (_examplesLabel) {
        _examplesLabel->setText(h1Start + tr("Examples") + h1End);
    }
    _recentFilesLabel->setText(h1Start + tr("Recent Files") + h1End);

    auto hGrp = App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Start"
    );
    std::string customFolder(hGrp->GetASCII("CustomFolder", ""));
    if (!customFolder.empty() && _customFolderLabel) {
        if (hGrp->GetBool("ShortCustomFolder", true)) {
            _customFolderLabel->setToolTip(QString::fromUtf8(customFolder.c_str()));
            customFolder = customFolder.substr(customFolder.find_last_of("/\\") + 1);
        }
        _customFolderLabel->setText(h1Start + QString::fromUtf8(customFolder.c_str()) + h1End);
    }

    QString application = QString::fromUtf8(App::Application::Config()["ExeName"].c_str());
    _openFirstStart->setText(tr("Open First Start Setup"));
    _showOnStartupCheckBox->setText(tr("Do not show this Start page again (start with blank screen)"));
}
