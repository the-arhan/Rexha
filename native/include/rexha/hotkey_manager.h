#pragma once

#include <functional>
#include <thread>
#include <atomic>
#include <mutex>
#include <map>
#include <cstdint>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

namespace rexha {

class HotkeyManager {
public:
    using TriggerCallback = std::function<void(int hotkey_id)>;

    HotkeyManager();
    ~HotkeyManager();

    bool register_hotkey(int id, uint32_t modifiers, uint32_t vk);
    bool unregister_hotkey(int id);
    void set_trigger_callback(TriggerCallback cb);

    void start();
    void stop();

private:
    struct HotkeyDef {
        int id;
        uint32_t modifiers;
        uint32_t vk;
    };

    std::thread worker_thread_;
    std::atomic<DWORD> thread_id_{0};
    std::atomic<bool> running_{false};
    std::mutex mutex_;
    std::map<int, HotkeyDef> hotkeys_;
    TriggerCallback callback_;

    void run_message_loop();
};

} // namespace rexha

