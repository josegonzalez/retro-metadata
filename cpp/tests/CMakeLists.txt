# Test configuration for retro_metadata

# Find testdata directory
set(TESTDATA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../testdata")
if(NOT EXISTS "${TESTDATA_DIR}")
    message(FATAL_ERROR "testdata directory not found at ${TESTDATA_DIR}")
endif()

# Define test source files
set(TEST_SOURCES
    test_filename.cpp
    test_matching.cpp
    test_normalization.cpp
    test_platform.cpp
    test_cache.cpp
    test_providers.cpp
)

# Create test executable
add_executable(retro_metadata_tests ${TEST_SOURCES})

target_link_libraries(retro_metadata_tests
    PRIVATE
        retro_metadata
        GTest::gtest
        GTest::gtest_main
        GTest::gmock
        nlohmann_json::nlohmann_json
)

target_include_directories(retro_metadata_tests
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/testutil
)

# Define testdata path for tests
target_compile_definitions(retro_metadata_tests
    PRIVATE
        TESTDATA_DIR="${TESTDATA_DIR}"
)

# Enable testing
include(GoogleTest)
gtest_discover_tests(retro_metadata_tests)

# Add individual test targets for convenience
add_custom_target(test_filename
    COMMAND retro_metadata_tests --gtest_filter=FilenameTest.*
    DEPENDS retro_metadata_tests
)

add_custom_target(test_matching
    COMMAND retro_metadata_tests --gtest_filter=MatchingTest.*
    DEPENDS retro_metadata_tests
)

add_custom_target(test_normalization
    COMMAND retro_metadata_tests --gtest_filter=NormalizationTest.*
    DEPENDS retro_metadata_tests
)

add_custom_target(test_platform
    COMMAND retro_metadata_tests --gtest_filter=PlatformTest.*
    DEPENDS retro_metadata_tests
)

add_custom_target(test_cache
    COMMAND retro_metadata_tests --gtest_filter=CacheTest.*
    DEPENDS retro_metadata_tests
)

add_custom_target(test_providers
    COMMAND retro_metadata_tests --gtest_filter=ProviderTest.*
    DEPENDS retro_metadata_tests
)
