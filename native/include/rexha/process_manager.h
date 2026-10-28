#pragma once

#include "rexha/json.h"
#include <string>
#include <vector>
#include <optional>
#include <cstdint>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

namespace rexha {

struct ProcessStatus {
    uint32_t pid = 0;
    bool is_running = false;
    int32_t exit_code = 0;
    double memory_mb = 0.0;

    JsonValue to_json() const;
};

class ProcessManager {
public:
    ProcessManager() = default;

    std::optional<uint32_t> launch_process(
        const std::string& executable_path,
        const std::vector<std::string>& arguments = {},
        const std::string& working_directory = ""
    );

    std::optional<ProcessStatus> get_process_status(uint32_t pid);
    bool terminate_process(uint32_t pid, bool force = false);

private:
    static std::wstring utf8_to_wide(const std::string& str);
    static std::string wide_to_utf8(const std::wstring& wstr);
    static std::wstring format_command_line(const std::string& exe, const std::vector<std::string>& args);
};

} // namespace rexha

