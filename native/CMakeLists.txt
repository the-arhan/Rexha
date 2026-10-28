cmake_minimum_required(VERSION 3.25)
project(rexha_native VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(MSVC)
    add_compile_options(/W4 /permissive- /utf-8 /EHsc)
else()
    add_compile_options(-Wall -Wextra -pedantic)
endif()

# Include directories
set(REXHA_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${REXHA_INCLUDE_DIR})

# Core Native Library
add_library(rexha_native_lib STATIC
    src/core/protocol.cpp
    src/core/ipc_server.cpp
    src/windows/hotkey_manager.cpp
    src/windows/window_manager.cpp
    src/windows/system_metrics.cpp
    src/process/process_manager.cpp
)

target_include_directories(rexha_native_lib PUBLIC ${REXHA_INCLUDE_DIR})
target_link_libraries(rexha_native_lib PUBLIC
    user32
    kernel32
    psapi
    advapi32
)

# Native Core Server Executable
add_executable(rexha_native_core
    src/main.cpp
)

target_link_libraries(rexha_native_core PRIVATE rexha_native_lib)

# Copy output executable to src/rexha/bin for runtime discovery by Python
set(REXHA_PYTHON_BIN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../src/rexha/bin)
add_custom_command(TARGET rexha_native_core POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory ${REXHA_PYTHON_BIN_DIR}
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:rexha_native_core>
        ${REXHA_PYTHON_BIN_DIR}/rexha_native_core.exe
    COMMENT "Copying rexha_native_core.exe to python bin directory"
)

# Native Unit Test Executable
add_executable(rexha_native_tests
    tests/test_native.cpp
)

target_link_libraries(rexha_native_tests PRIVATE rexha_native_lib)

enable_testing()
add_test(NAME NativeUnitTests COMMAND rexha_native_tests)

