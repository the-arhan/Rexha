#include "rexha/ipc_server.h"
#include "rexha/hotkey_manager.h"
#include "rexha/window_manager.h"
#include "rexha/process_manager.h"
#include "rexha/system_metrics.h"
#include <iostream>
#include <csignal>

using namespace rexha;

static std::atomic<bool> g_keep_running{true};

static void signal_handler(int) {
    g_keep_running.store(false);
}

int main(int argc, char* argv[]) {
    std::cout << "[Rexha Native Core] Starting native supervisor (v0.1.0)...\n";
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    std::string pipe_name = "\\\\.\\pipe\\rexha_ipc";
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--pipe" && i + 1 < argc) {
            pipe_name = argv[++i];
        }
    }

    IpcServer server(pipe_name);
    HotkeyManager hotkey_mgr;
    WindowManager window_mgr;
    ProcessManager process_mgr;
    SystemMetrics sys_metrics;

    // Connect hotkey triggers to broadcast IPC events
    hotkey_mgr.set_trigger_callback([&server](int id) {
        std::cout << "[Rexha Native Core] Hotkey pressed: ID=" << id << "\n";
        JsonValue data = JsonValue::object();
        data.set("hotkey_id", id);
        Event ev = Event::make("hotkey.triggered", data);
        server.broadcast_event(ev);
    });

    // Register Handlers
    // 1. System handlers
    server.register_handler("system.ping", [](const Request& req) {
        JsonValue data = JsonValue::object();
        data.set("pong", true);
        return Response::make_success(req.request_id, data);
    });

    server.register_handler("system.get_status", [&sys_metrics](const Request& req) {
        return Response::make_success(req.request_id, sys_metrics.get_status());
    });

    server.register_handler("system.get_metrics", [&sys_metrics](const Request& req) {
        return Response::make_success(req.request_id, sys_metrics.get_metrics());
    });

    server.register_handler("system.shutdown", [](const Request& req) {
        std::cout << "[Rexha Native Core] Shutdown requested via IPC\n";
        g_keep_running.store(false);
        JsonValue data = JsonValue::object();
        data.set("shutting_down", true);
        return Response::make_success(req.request_id, data);
    });

    // 2. Hotkey handlers
    server.register_handler("hotkey.register", [&hotkey_mgr](const Request& req) {
        int id = req.arguments.get_int("id", 101);
        uint32_t vk = req.arguments.get_int("vk", 0x20); // VK_SPACE default
        uint32_t mod = 0;
        const auto& mods_val = req.arguments.get("modifiers");
        if (mods_val.is_array()) {
            for (const auto& m : mods_val.as_array()) {
                std::string s = m.as_string();
                if (s == "ctrl" || s == "control") mod |= MOD_CONTROL;
                else if (s == "alt") mod |= MOD_ALT;
                else if (s == "shift") mod |= MOD_SHIFT;
                else if (s == "win") mod |= MOD_WIN;
            }
        } else {
            mod = MOD_CONTROL;
        }

        bool ok = hotkey_mgr.register_hotkey(id, mod, vk);
        if (ok) {
            JsonValue data = JsonValue::object();
            data.set("registered", true);
            data.set("id", id);
            return Response::make_success(req.request_id, data);
        } else {
            return Response::make_error(req.request_id, 3001, "HOTKEY_REGISTRATION_FAILED", "Could not register hotkey");
        }
    });

    server.register_handler("hotkey.unregister", [&hotkey_mgr](const Request& req) {
        int id = req.arguments.get_int("id", 101);
        bool ok = hotkey_mgr.unregister_hotkey(id);
        JsonValue data = JsonValue::object();
        data.set("unregistered", ok);
        return Response::make_success(req.request_id, data);
    });

    // 3. Window handlers
    server.register_handler("window.get_foreground", [&window_mgr](const Request& req) {
        auto fg = window_mgr.get_foreground_window();
        if (fg) {
            return Response::make_success(req.request_id, fg->to_json());
        } else {
            return Response::make_error(req.request_id, 3002, "WINDOW_NOT_FOUND", "No foreground window active");
        }
    });

    server.register_handler("window.list", [&window_mgr](const Request& req) {
        bool visible = req.arguments.get_bool("visible_only", true);
        bool filter_empty = req.arguments.get_bool("filter_empty_titles", true);
        auto windows = window_mgr.list_windows(visible, filter_empty);

        JsonValue arr = JsonValue::array();
        for (const auto& w : windows) {
            arr.push_back(w.to_json());
        }
        JsonValue data = JsonValue::object();
        data.set("windows", arr);
        return Response::make_success(req.request_id, data);
    });

    server.register_handler("window.set_state", [&window_mgr](const Request& req) {
        int64_t hwnd = req.arguments.get_int64("hwnd", 0);
        std::string state = req.arguments.get_string("state", "restore");
        bool ok = window_mgr.set_window_state(static_cast<uint64_t>(hwnd), state);
        if (ok) {
            JsonValue data = JsonValue::object();
            data.set("success", true);
            return Response::make_success(req.request_id, data);
        } else {
            return Response::make_error(req.request_id, 3002, "WINDOW_NOT_FOUND", "Could not set window state");
        }
    });

    server.register_handler("window.close", [&window_mgr](const Request& req) {
        int64_t hwnd = req.arguments.get_int64("hwnd", 0);
        bool graceful = req.arguments.get_bool("graceful", true);
        int timeout_ms = req.arguments.get_int("timeout_ms", 3000);
        bool closed = window_mgr.close_window(static_cast<uint64_t>(hwnd), graceful, timeout_ms);
        JsonValue data = JsonValue::object();
        data.set("closed", closed);
        data.set("method", graceful ? "WM_CLOSE" : "FORCE_TERMINATE");
        return Response::make_success(req.request_id, data);
    });

    // 4. Process handlers
    server.register_handler("process.launch", [&process_mgr](const Request& req) {
        std::string exe = req.arguments.get_string("executable_path");
        if (exe.empty()) {
            return Response::make_error(req.request_id, 1006, "INVALID_ARGUMENTS", "executable_path is required");
        }

        std::vector<std::string> args;
        const auto& args_val = req.arguments.get("arguments");
        if (args_val.is_array()) {
            for (const auto& a : args_val.as_array()) {
                args.push_back(a.as_string());
            }
        }
        std::string workdir = req.arguments.get_string("working_directory", "");

        auto pid_opt = process_mgr.launch_process(exe, args, workdir);
        if (pid_opt) {
            JsonValue data = JsonValue::object();
            data.set("pid", static_cast<int64_t>(*pid_opt));
            data.set("launched", true);
            return Response::make_success(req.request_id, data);
        } else {
            return Response::make_error(req.request_id, 3003, "PROCESS_SPAWN_FAILED", "Failed to launch process: " + exe);
        }
    });

    server.register_handler("process.get_status", [&process_mgr](const Request& req) {
        int64_t pid = req.arguments.get_int64("pid", 0);
        auto status = process_mgr.get_process_status(static_cast<uint32_t>(pid));
        if (status) {
            return Response::make_success(req.request_id, status->to_json());
        } else {
            return Response::make_error(req.request_id, 3004, "PROCESS_NOT_FOUND", "Process not found or access denied");
        }
    });

    server.register_handler("process.terminate", [&process_mgr](const Request& req) {
        int64_t pid = req.arguments.get_int64("pid", 0);
        bool force = req.arguments.get_bool("force", false);
        bool ok = process_mgr.terminate_process(static_cast<uint32_t>(pid), force);
        JsonValue data = JsonValue::object();
        data.set("terminated", ok);
        return Response::make_success(req.request_id, data);
    });

    if (!server.start()) {
        std::cerr << "[Rexha Native Core] Failed to start IPC server on " << pipe_name << "\n";
        return 1;
    }

    std::cout << "[Rexha Native Core] Online and listening on: " << pipe_name << "\n";

    while (g_keep_running.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    std::cout << "[Rexha Native Core] Stopping services...\n";
    hotkey_mgr.stop();
    server.stop();
    std::cout << "[Rexha Native Core] Clean shutdown complete.\n";
    return 0;
}

