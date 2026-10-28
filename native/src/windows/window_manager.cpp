#include "rexha/window_manager.h"
#include <psapi.h>
#include <thread>
#include <chrono>

namespace rexha {

static std::string wide_to_utf8(const std::wstring& wstr) {
    if (wstr.empty()) return "";
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, wstr.data(), static_cast<int>(wstr.size()), NULL, 0, NULL, NULL);
    std::string str(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, wstr.data(), static_cast<int>(wstr.size()), str.data(), size_needed, NULL, NULL);
    return str;
}

JsonValue WindowInfo::to_json() const {
    JsonValue obj = JsonValue::object();
    obj.set("hwnd", static_cast<int64_t>(hwnd));
    obj.set("title", title);
    obj.set("process_name", process_name);
    obj.set("pid", static_cast<int64_t>(pid));
    obj.set("is_visible", is_visible);
    obj.set("is_minimized", is_minimized);
    obj.set("is_maximized", is_maximized);
    return obj;
}

std::string WindowManager::get_process_name_for_pid(DWORD pid) {
    if (pid == 0) return "";
    HANDLE hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!hProcess) return "";

    wchar_t exe_path[MAX_PATH] = {0};
    DWORD size = MAX_PATH;
    std::string name;
    if (QueryFullProcessImageNameW(hProcess, 0, exe_path, &size)) {
        std::wstring full_path(exe_path);
        size_t last_slash = full_path.find_last_of(L"\\/");
        if (last_slash != std::wstring::npos) {
            name = wide_to_utf8(full_path.substr(last_slash + 1));
        } else {
            name = wide_to_utf8(full_path);
        }
    }
    CloseHandle(hProcess);
    return name;
}

WindowInfo WindowManager::get_window_info(HWND hwnd) {
    WindowInfo info;
    info.hwnd = reinterpret_cast<uint64_t>(hwnd);

    // Title
    wchar_t title_buf[512] = {0};
    GetWindowTextW(hwnd, title_buf, 512);
    info.title = wide_to_utf8(title_buf);

    // PID & Process Name
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    info.pid = pid;
    info.process_name = get_process_name_for_pid(pid);

    // State
    info.is_visible = IsWindowVisible(hwnd) != FALSE;

    WINDOWPLACEMENT wp;
    wp.length = sizeof(wp);
    if (GetWindowPlacement(hwnd, &wp)) {
        info.is_minimized = (wp.showCmd == SW_SHOWMINIMIZED);
        info.is_maximized = (wp.showCmd == SW_SHOWMAXIMIZED);
    }

    return info;
}

std::optional<WindowInfo> WindowManager::get_foreground_window() {
    HWND fg = GetForegroundWindow();
    if (!fg) return std::nullopt;
    return get_window_info(fg);
}

struct EnumContext {
    std::vector<WindowInfo> list;
    bool visible_only;
    bool filter_empty_titles;
};

static BOOL CALLBACK EnumWindowsCallback(HWND hwnd, LPARAM lParam) {
    EnumContext* ctx = reinterpret_cast<EnumContext*>(lParam);

    if (ctx->visible_only && !IsWindowVisible(hwnd)) {
        return TRUE;
    }

    wchar_t title_buf[512] = {0};
    GetWindowTextW(hwnd, title_buf, 512);
    if (ctx->filter_empty_titles && title_buf[0] == L'\0') {
        return TRUE;
    }

    // Skip zero-dimension windows or tooltips
    RECT rc;
    if (GetWindowRect(hwnd, &rc)) {
        if (rc.right - rc.left <= 0 || rc.bottom - rc.top <= 0) {
            return TRUE;
        }
    }

    WindowInfo info;
    info.hwnd = reinterpret_cast<uint64_t>(hwnd);
    info.title = wide_to_utf8(title_buf);

    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    info.pid = pid;
    info.process_name = WindowManager::get_process_name_for_pid(pid);
    info.is_visible = true;

    WINDOWPLACEMENT wp;
    wp.length = sizeof(wp);
    if (GetWindowPlacement(hwnd, &wp)) {
        info.is_minimized = (wp.showCmd == SW_SHOWMINIMIZED);
        info.is_maximized = (wp.showCmd == SW_SHOWMAXIMIZED);
    }

    ctx->list.push_back(std::move(info));
    return TRUE;
}

std::vector<WindowInfo> WindowManager::list_windows(bool visible_only, bool filter_empty_titles) {
    EnumContext ctx;
    ctx.visible_only = visible_only;
    ctx.filter_empty_titles = filter_empty_titles;

    EnumWindows(EnumWindowsCallback, reinterpret_cast<LPARAM>(&ctx));
    return ctx.list;
}

bool WindowManager::set_window_state(uint64_t hwnd_val, const std::string& state) {
    HWND hwnd = reinterpret_cast<HWND>(hwnd_val);
    if (!IsWindow(hwnd)) return false;

    if (state == "minimize") {
        return ShowWindow(hwnd, SW_MINIMIZE) != FALSE;
    } else if (state == "maximize") {
        return ShowWindow(hwnd, SW_MAXIMIZE) != FALSE;
    } else if (state == "restore") {
        return ShowWindow(hwnd, SW_RESTORE) != FALSE;
    } else if (state == "bring_to_front" || state == "focus") {
        ShowWindow(hwnd, SW_RESTORE);
        BringWindowToTop(hwnd);
        SetForegroundWindow(hwnd);
        return true;
    }
    return false;
}

bool WindowManager::close_window(uint64_t hwnd_val, bool graceful, uint32_t timeout_ms) {
    HWND hwnd = reinterpret_cast<HWND>(hwnd_val);
    if (!IsWindow(hwnd)) return false;

    // Cap timeout to a safe upper bound (10 seconds)
    uint32_t safe_timeout = (timeout_ms > 10000) ? 10000 : timeout_ms;

    if (graceful) {
        PostMessageW(hwnd, WM_CLOSE, 0, 0);
        // Wait up to safe_timeout to see if it closed
        auto start = std::chrono::steady_clock::now();
        while (IsWindow(hwnd)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - start).count();
            if (elapsed >= safe_timeout) {
                return false; // Still open (likely unsaved changes dialog)
            }
        }
        return true;
    } else {
        // Force close: get PID and terminate
        DWORD pid = 0;
        GetWindowThreadProcessId(hwnd, &pid);
        if (pid == 0) return false;
        HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
        if (!hProcess) return false;
        BOOL res = TerminateProcess(hProcess, 1);
        CloseHandle(hProcess);
        return res != FALSE;
    }
}

} // namespace rexha

