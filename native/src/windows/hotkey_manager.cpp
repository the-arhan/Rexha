#include "rexha/hotkey_manager.h"
#include <iostream>

namespace rexha {

constexpr UINT WM_REXHA_REGISTER = WM_APP + 1;
constexpr UINT WM_REXHA_UNREGISTER = WM_APP + 2;

HotkeyManager::HotkeyManager() {
    start();
}

HotkeyManager::~HotkeyManager() {
    stop();
}

void HotkeyManager::set_trigger_callback(TriggerCallback cb) {
    std::lock_guard<std::mutex> lock(mutex_);
    callback_ = std::move(cb);
}

void HotkeyManager::start() {
    if (running_.load()) return;
    running_.store(true);
    worker_thread_ = std::thread(&HotkeyManager::run_message_loop, this);

    // Wait until thread message queue is ready
    while (thread_id_.load() == 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
}

void HotkeyManager::stop() {
    if (!running_.load()) return;
    running_.store(false);

    DWORD tid = thread_id_.load();
    if (tid != 0) {
        PostThreadMessageW(tid, WM_QUIT, 0, 0);
    }

    if (worker_thread_.joinable()) {
        worker_thread_.join();
    }
    thread_id_.store(0);
}

bool HotkeyManager::register_hotkey(int id, uint32_t modifiers, uint32_t vk) {
    if (!running_.load()) return false;

    {
        std::lock_guard<std::mutex> lock(mutex_);
        hotkeys_[id] = HotkeyDef{id, modifiers, vk};
    }

    DWORD tid = thread_id_.load();
    if (tid != 0) {
        // Post message to the worker thread to execute RegisterHotKey on its queue
        PostThreadMessageW(tid, WM_REXHA_REGISTER, static_cast<WPARAM>(id), 0);
        return true;
    }
    return false;
}

bool HotkeyManager::unregister_hotkey(int id) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = hotkeys_.find(id);
        if (it == hotkeys_.end()) return false;
        hotkeys_.erase(it);
    }

    DWORD tid = thread_id_.load();
    if (tid != 0) {
        PostThreadMessageW(tid, WM_REXHA_UNREGISTER, static_cast<WPARAM>(id), 0);
        return true;
    }
    return false;
}

void HotkeyManager::run_message_loop() {
    // Force message queue creation for this thread
    MSG msg;
    PeekMessageW(&msg, NULL, WM_USER, WM_USER, PM_NOREMOVE);
    thread_id_.store(GetCurrentThreadId());

    // Register any initially queued hotkeys
    {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& [id, def] : hotkeys_) {
            RegisterHotKey(NULL, def.id, def.modifiers | MOD_NOREPEAT, def.vk);
        }
    }

    // Blocking GetMessageW loop: 0% CPU consumption while waiting!
    while (running_.load()) {
        BOOL bRet = GetMessageW(&msg, NULL, 0, 0);
        if (bRet <= 0) {
            // WM_QUIT or error
            break;
        }

        if (msg.message == WM_HOTKEY) {
            int hotkey_id = static_cast<int>(msg.wParam);
            TriggerCallback cb;
            {
                std::lock_guard<std::mutex> lock(mutex_);
                cb = callback_;
            }
            if (cb) {
                cb(hotkey_id);
            }
        } else if (msg.message == WM_REXHA_REGISTER) {
            int hotkey_id = static_cast<int>(msg.wParam);
            std::lock_guard<std::mutex> lock(mutex_);
            auto it = hotkeys_.find(hotkey_id);
            if (it != hotkeys_.end()) {
                UnregisterHotKey(NULL, hotkey_id);
                RegisterHotKey(NULL, it->second.id, it->second.modifiers | MOD_NOREPEAT, it->second.vk);
            }
        } else if (msg.message == WM_REXHA_UNREGISTER) {
            int hotkey_id = static_cast<int>(msg.wParam);
            UnregisterHotKey(NULL, hotkey_id);
        } else {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }

    // Cleanup all hotkeys on thread exit
    std::lock_guard<std::mutex> lock(mutex_);
    for (const auto& [id, def] : hotkeys_) {
        UnregisterHotKey(NULL, id);
    }
}

} // namespace rexha

