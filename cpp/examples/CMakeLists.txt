# Examples for retro_metadata library

# Basic search example
add_executable(basic_search basic_search/main.cpp)
target_link_libraries(basic_search PRIVATE retro_metadata)

# With cache example
add_executable(with_cache with_cache/main.cpp)
target_link_libraries(with_cache PRIVATE retro_metadata)

# Identify game example
add_executable(identify_game identify_game/main.cpp)
target_link_libraries(identify_game PRIVATE retro_metadata)

# Multi-provider example
add_executable(multi_provider multi_provider/main.cpp)
target_link_libraries(multi_provider PRIVATE retro_metadata)

# Filename parsing example
add_executable(filename_parsing filename_parsing/main.cpp)
target_link_libraries(filename_parsing PRIVATE retro_metadata)

# Set output directory for examples
set_target_properties(
    basic_search
    with_cache
    identify_game
    multi_provider
    filename_parsing
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/examples
)
