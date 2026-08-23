# SPDX-License-Identifier: LGPL-2.1-or-later

add_subdirectory(App)
if(BUILD_GUI)
    add_subdirectory(Gui)
endif(BUILD_GUI)

set(Robot_Scripts
    Init.py
    KukaExporter.py
    RobotExample.py
    RobotExampleTrajectoryOutOfShapes.py
)

if(BUILD_GUI)
    list (APPEND Robot_Scripts
        InitGui.py
        MovieTool.py
    )
endif(BUILD_GUI)

set(Robot_Tools
    RobotTools/__init__.py
    RobotTools/chain_graph.py
    RobotTools/assembly_chain.py
    RobotTools/joint_inventory.py
    RobotTools/CommandFromAssembly.py
    RobotTools/CommandExportJoints.py
)

add_custom_target(RobotScripts ALL
    SOURCES ${Robot_Scripts} ${Robot_Tools} ${Robot_Resources}
)

fc_target_copy_resource(RobotScripts
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/Mod/Robot
    ${Robot_Scripts}
)

fc_target_copy_resource(RobotScripts
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/Mod/Robot
    ${Robot_Tools}
)

if (DEFINED Robot_Resources)
fc_target_copy_resource(RobotScripts
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_DATADIR}/Mod/Robot
    ${Robot_Resources})
endif()

INSTALL(
    FILES
        ${Robot_Scripts}
    DESTINATION
        Mod/Robot
)

INSTALL(
    DIRECTORY
        RobotTools
    DESTINATION
        Mod/Robot
    FILES_MATCHING
        PATTERN "*.py"
)

if (DEFINED Robot_Resources)
INSTALL(
    DIRECTORY
        Lib
    DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Mod/Robot
    PATTERN "Makefile*" EXCLUDE
    PATTERN "testprog.*" EXCLUDE
)
endif()
