#pragma once

#include "rexha/json.h"
#include <chrono>

namespace rexha {

class SystemMetrics {
public:
    SystemMetrics();
    JsonValue get_metrics();
    JsonValue get_status();

private:
    std::chrono::steady_clock::time_point start_time_;
    uint64_t last_idle_time_ = 0;
    uint64_t last_kernel_time_ = 0;
    uint64_t last_user_time_ = 0;

    double calculate_cpu_percent();
};

} // namespace rexha

