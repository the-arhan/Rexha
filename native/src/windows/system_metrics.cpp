#include "rexha/system_metrics.h"

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <psapi.h>

namespace rexha {

static uint64_t filetime_to_uint64(const FILETIME& ft) {
    return (static_cast<uint64_t>(ft.dwHighDateTime) << 32) | ft.dwLowDateTime;
}

SystemMetrics::SystemMetrics() {
    start_time_ = std::chrono::steady_clock::now();
    FILETIME idle, kernel, user;
    if (GetSystemTimes(&idle, &kernel, &user)) {
        last_idle_time_ = filetime_to_uint64(idle);
        last_kernel_time_ = filetime_to_uint64(kernel);
        last_user_time_ = filetime_to_uint64(user);
    }
}

double SystemMetrics::calculate_cpu_percent() {
    FILETIME idle, kernel, user;
    if (!GetSystemTimes(&idle, &kernel, &user)) {
        return 0.0;
    }

    uint64_t cur_idle = filetime_to_uint64(idle);
    uint64_t cur_kernel = filetime_to_uint64(kernel);
    uint64_t cur_user = filetime_to_uint64(user);

    uint64_t diff_idle = cur_idle - last_idle_time_;
    uint64_t diff_kernel = cur_kernel - last_kernel_time_;
    uint64_t diff_user = cur_user - last_user_time_;

    last_idle_time_ = cur_idle;
    last_kernel_time_ = cur_kernel;
    last_user_time_ = cur_user;

    uint64_t total_sys = diff_kernel + diff_user;
    if (total_sys == 0) return 0.0;

    double cpu_usage = (static_cast<double>(total_sys - diff_idle) * 100.0) / static_cast<double>(total_sys);
    if (cpu_usage < 0.0) cpu_usage = 0.0;
    if (cpu_usage > 100.0) cpu_usage = 100.0;
    return cpu_usage;
}

JsonValue SystemMetrics::get_metrics() {
    JsonValue res = JsonValue::object();

    // CPU Percent
    double cpu_pct = calculate_cpu_percent();
    res.set("cpu_percent", cpu_pct);

    // RAM Metrics
    MEMORYSTATUSEX mem_status;
    mem_status.dwLength = sizeof(mem_status);
    if (GlobalMemoryStatusEx(&mem_status)) {
        uint64_t total_mb = mem_status.ullTotalPhys / (1024 * 1024);
        uint64_t avail_mb = mem_status.ullAvailPhys / (1024 * 1024);
        uint64_t used_mb = total_mb - avail_mb;
        res.set("ram_total_mb", total_mb);
        res.set("ram_available_mb", avail_mb);
        res.set("ram_used_mb", used_mb);
        res.set("ram_used_percent", static_cast<int>(mem_status.dwMemoryLoad));
    }

    // Process RAM
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        double process_mb = static_cast<double>(pmc.WorkingSetSize) / (1024.0 * 1024.0);
        res.set("process_working_set_mb", process_mb);
    }

    return res;
}

JsonValue SystemMetrics::get_status() {
    JsonValue res = JsonValue::object();
    res.set("core_version", "0.1.0");
    res.set("platform", "Windows x64");
    res.set("pid", static_cast<int64_t>(GetCurrentProcessId()));

    auto now = std::chrono::steady_clock::now();
    double uptime = std::chrono::duration<double>(now - start_time_).count();
    res.set("uptime_seconds", uptime);

    return res;
}

} // namespace rexha

