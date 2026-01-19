cmake_minimum_required(VERSION 3.20)

project(retro_metadata
    VERSION 1.0.0
    DESCRIPTION "A unified interface for fetching game metadata from various providers"
    LANGUAGES CXX
)

# C++20 required
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Export compile commands for clang-tidy and IDEs
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Options
option(RETRO_METADATA_BUILD_TESTS "Build tests" ON)
option(RETRO_METADATA_BUILD_EXAMPLES "Build examples" ON)
option(RETRO_METADATA_USE_SYSTEM_DEPS "Use system-installed dependencies instead of FetchContent" OFF)

# Compiler warnings
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang|AppleClang")
    add_compile_options(
        -Wall
        -Wextra
        -Wpedantic
        -Wno-unused-parameter
        -Werror=return-type
    )
elseif(MSVC)
    add_compile_options(
        /W4
        /permissive-
    )
endif()

# Dependencies via FetchContent
include(FetchContent)

# nlohmann/json - header-only JSON library
FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE
)

# cpr - C++ Requests library (libcurl wrapper)
FetchContent_Declare(
    cpr
    GIT_REPOSITORY https://github.com/libcpr/cpr.git
    GIT_TAG 1.10.5
    GIT_SHALLOW TRUE
)

# rapidfuzz-cpp - Fast string matching
FetchContent_Declare(
    rapidfuzz
    GIT_REPOSITORY https://github.com/rapidfuzz/rapidfuzz-cpp.git
    GIT_TAG v3.0.4
    GIT_SHALLOW TRUE
)

# ICU for Unicode normalization (optional, use system ICU if available)
find_package(ICU COMPONENTS uc data)
if(NOT ICU_FOUND)
    message(STATUS "ICU not found, Unicode normalization will use simplified fallback")
    add_compile_definitions(RETRO_METADATA_NO_ICU)
endif()

# Fetch dependencies
message(STATUS "Fetching nlohmann_json...")
FetchContent_MakeAvailable(nlohmann_json)

message(STATUS "Fetching cpr...")
set(CPR_USE_SYSTEM_CURL ON CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(cpr)

message(STATUS "Fetching rapidfuzz...")
FetchContent_MakeAvailable(rapidfuzz)

# Library sources
set(RETRO_METADATA_SOURCES
    src/types.cpp
    src/errors.cpp
    src/config.cpp
    src/cache/memory.cpp
    src/platform/slug.cpp
    src/platform/mapping.cpp
    src/internal/normalization.cpp
    src/internal/matching.cpp
    src/filename/filename.cpp
    src/provider/base.cpp
    src/provider/registry.cpp
    src/provider/hltb.cpp
    src/provider/igdb.cpp
    src/provider/mobygames.cpp
    src/provider/screenscraper.cpp
    src/provider/retroachievements.cpp
    src/provider/steamgriddb.cpp
    src/provider/thegamesdb.cpp
    src/provider/launchbox.cpp
    src/provider/hasheous.cpp
    src/provider/flashpoint.cpp
    src/provider/playmatch.cpp
    src/provider/gamelist.cpp
)

# Create library
add_library(retro_metadata ${RETRO_METADATA_SOURCES})
add_library(retro_metadata::retro_metadata ALIAS retro_metadata)

target_include_directories(retro_metadata
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(retro_metadata
    PUBLIC
        nlohmann_json::nlohmann_json
    PRIVATE
        cpr::cpr
        rapidfuzz::rapidfuzz
)

if(ICU_FOUND)
    target_link_libraries(retro_metadata PRIVATE ICU::uc ICU::data)
endif()

# Tests
if(RETRO_METADATA_BUILD_TESTS)
    enable_testing()

    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.14.0
        GIT_SHALLOW TRUE
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    add_subdirectory(tests)
endif()

# Examples
if(RETRO_METADATA_BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# Install
include(GNUInstallDirs)

install(TARGETS retro_metadata
    EXPORT retro_metadata-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/retro_metadata
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT retro_metadata-targets
    FILE retro_metadata-targets.cmake
    NAMESPACE retro_metadata::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retro_metadata
)

# Package config
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/retro_metadata-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/retro_metadata-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retro_metadata
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/retro_metadata-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/retro_metadata-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/retro_metadata-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retro_metadata
)
