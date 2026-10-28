#pragma once

#include "rexha/json.h"
#include <vector>
#include <optional>
#include <string>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

namespace rexha {

struct WindowInfo {
    uint64_t hwnd = 0;
    std::string title;
    std::string process_name;
    uint32_t pid = 0;
    bool is_visible = false;
    bool is_minimized = false;
    bool is_maximized = false;

    JsonValue to_json() const;
};

class WindowManager {
public:
    WindowManager() = default;

    std::optional<WindowInfo> get_foreground_window();
    std::vector<WindowInfo> list_windows(bool visible_only = true, bool filter_empty_titles = true);
    bool set_window_state(uint64_t hwnd_val, const std::string& state);
    bool close_window(uint64_t hwnd_val, bool graceful = true, uint32_t timeout_ms = 3000);
    static std::string get_process_name_for_pid(DWORD pid);

private:
    static WindowInfo get_window_info(HWND hwnd);
};

} // namespace rexha
