#include "rexha/process_manager.h"
#include <psapi.h>
#include <sstream>

namespace rexha {

std::wstring ProcessManager::utf8_to_wide(const std::string& str) {
    if (str.empty()) return L"";
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, str.data(), static_cast<int>(str.size()), NULL, 0);
    std::wstring wstr(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, str.data(), static_cast<int>(str.size()), wstr.data(), size_needed);
    return wstr;
}

std::string ProcessManager::wide_to_utf8(const std::wstring& wstr) {
    if (wstr.empty()) return "";
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, wstr.data(), static_cast<int>(wstr.size()), NULL, 0, NULL, NULL);
    std::string str(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, wstr.data(), static_cast<int>(wstr.size()), str.data(), size_needed, NULL, NULL);
    return str;
}

std::wstring ProcessManager::format_command_line(const std::string& exe, const std::vector<std::string>& args) {
    std::wostringstream ss;
    // Quote executable path
    ss << L"\"" << utf8_to_wide(exe) << L"\"";

    for (const auto& arg : args) {
        ss << L" ";
        std::wstring warg = utf8_to_wide(arg);
        if (warg.find(L' ') != std::wstring::npos || warg.find(L'\t') != std::wstring::npos || warg.find(L'\"') != std::wstring::npos || warg.empty()) {
            ss << L"\"";
            for (size_t i = 0; i < warg.size(); ++i) {
                if (warg[i] == L'\"') {
                    ss << L"\\\"";
                } else if (warg[i] == L'\\') {
                    size_t bs = 1;
                    while (i + 1 < warg.size() && warg[i + 1] == L'\\') {
                        ++bs;
                        ++i;
                    }
                    if (i + 1 == warg.size() || warg[i + 1] == L'\"') {
                        ss << std::wstring(bs * 2, L'\\');
                    } else {
                        ss << std::wstring(bs, L'\\');
                    }
                } else {
                    ss << warg[i];
                }
            }
            ss << L"\"";
        } else {
            ss << warg;
        }
    }
    return ss.str();
}

JsonValue ProcessStatus::to_json() const {
    JsonValue obj = JsonValue::object();
    obj.set("pid", static_cast<int64_t>(pid));
    obj.set("is_running", is_running);
    obj.set("exit_code", static_cast<int64_t>(exit_code));
    obj.set("memory_mb", memory_mb);
    return obj;
}

std::optional<uint32_t> ProcessManager::launch_process(
    const std::string& executable_path,
    const std::vector<std::string>& arguments,
    const std::string& working_directory
) {
    std::wstring cmd_line = format_command_line(executable_path, arguments);
    std::vector<wchar_t> cmd_buf(cmd_line.begin(), cmd_line.end());
    cmd_buf.push_back(L'\0');

    std::wstring w_workdir = utf8_to_wide(working_directory);
    const wchar_t* p_workdir = w_workdir.empty() ? NULL : w_workdir.c_str();

    STARTUPINFOW si;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);

    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(pi));

    BOOL success = CreateProcessW(
        NULL,
        cmd_buf.data(),
        NULL,
        NULL,
        FALSE,
        0,
        NULL,
        p_workdir,
        &si,
        &pi
    );

    if (!success) {
        return std::nullopt;
    }

    uint32_t pid = pi.dwProcessId;
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return pid;
}

std::optional<ProcessStatus> ProcessManager::get_process_status(uint32_t pid) {
    if (pid == 0) return std::nullopt;

    HANDLE hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!hProcess) {
        // Fallback with just QUERY_LIMITED_INFORMATION
        hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    }
    if (!hProcess) {
        return std::nullopt;
    }

    ProcessStatus status;
    status.pid = pid;

    DWORD exit_code = 0;
    if (GetExitCodeProcess(hProcess, &exit_code)) {
        if (exit_code == STILL_ACTIVE) {
            status.is_running = true;
            status.exit_code = 0;
        } else {
            status.is_running = false;
            status.exit_code = static_cast<int32_t>(exit_code);
        }
    }

    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(hProcess, &pmc, sizeof(pmc))) {
        status.memory_mb = static_cast<double>(pmc.WorkingSetSize) / (1024.0 * 1024.0);
    }

    CloseHandle(hProcess);
    return status;
}

struct CloseEnumContext {
    DWORD target_pid;
    std::vector<HWND> windows;
};

static BOOL CALLBACK CloseWindowCallback(HWND hwnd, LPARAM lParam) {
    CloseEnumContext* ctx = reinterpret_cast<CloseEnumContext*>(lParam);
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == ctx->target_pid) {
        ctx->windows.push_back(hwnd);
    }
    return TRUE;
}

bool ProcessManager::terminate_process(uint32_t pid, bool force) {
    if (pid == 0) return false;

    if (!force) {
        // Try posting WM_CLOSE to all top-level windows of this process
        CloseEnumContext ctx;
        ctx.target_pid = pid;
        EnumWindows(CloseWindowCallback, reinterpret_cast<LPARAM>(&ctx));

        for (HWND hwnd : ctx.windows) {
            PostMessageW(hwnd, WM_CLOSE, 0, 0);
        }
        return true;
    }

    HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (!hProcess) return false;

    BOOL res = TerminateProcess(hProcess, 1);
    CloseHandle(hProcess);
    return res != FALSE;
}

} // namespace rexha

