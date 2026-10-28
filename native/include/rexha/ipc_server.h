#pragma once

#include "rexha/protocol.h"
#include <string>
#include <functional>
#include <map>
#include <thread>
#include <atomic>
#include <mutex>
#include <vector>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

namespace rexha {

class IpcServer {
public:
    using Handler = std::function<Response(const Request&)>;

    explicit IpcServer(std::string pipe_name = "\\\\.\\pipe\\rexha_ipc");
    ~IpcServer();

    void register_handler(const std::string& type, Handler handler);
    void broadcast_event(const Event& event);

    bool start();
    void stop();
    bool is_running() const { return running_.load(); }

private:
    std::string pipe_name_;
    std::atomic<bool> running_{false};
    std::thread server_thread_;
    std::mutex handlers_mutex_;
    std::map<std::string, Handler> handlers_;

    std::mutex client_mutex_;
    HANDLE current_pipe_ = INVALID_HANDLE_VALUE;

    void run_server_loop();
    void handle_client_session(HANDLE hPipe);
    bool send_payload(HANDLE hPipe, const std::string& payload);
    std::optional<std::string> read_payload(HANDLE hPipe);
    Response dispatch_request(const Request& req);
};

} // namespace rexha

