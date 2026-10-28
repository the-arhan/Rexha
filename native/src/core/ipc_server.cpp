#include "rexha/ipc_server.h"
#include <iostream>
#include <sddl.h>

#ifndef PIPE_REJECT_REMOTE_CLIENTS
#define PIPE_REJECT_REMOTE_CLIENTS 0x00000008
#endif

namespace rexha {

IpcServer::IpcServer(std::string pipe_name)
    : pipe_name_(std::move(pipe_name)) {}

IpcServer::~IpcServer() {
    stop();
}

void IpcServer::register_handler(const std::string& type, Handler handler) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    handlers_[type] = std::move(handler);
}

bool IpcServer::start() {
    if (running_.load()) return true;
    running_.store(true);
    server_thread_ = std::thread(&IpcServer::run_server_loop, this);
    return true;
}

void IpcServer::stop() {
    if (!running_.load()) return;
    running_.store(false);

    // Cancel pending I/O and close active client pipe if open
    {
        std::lock_guard<std::mutex> lock(client_mutex_);
        if (current_pipe_ != INVALID_HANDLE_VALUE) {
            CancelIoEx(current_pipe_, NULL);
            CloseHandle(current_pipe_);
            current_pipe_ = INVALID_HANDLE_VALUE;
        }
    }

    // Ping pipe with dummy connection to unblock ConnectNamedPipe if waiting
    HANDLE hDummy = CreateFileA(
        pipe_name_.c_str(),
        GENERIC_READ | GENERIC_WRITE,
        0,
        NULL,
        OPEN_EXISTING,
        0,
        NULL
    );
    if (hDummy != INVALID_HANDLE_VALUE) {
        CloseHandle(hDummy);
    }

    if (server_thread_.joinable()) {
        server_thread_.join();
    }
}

void IpcServer::broadcast_event(const Event& event) {
    std::string payload = event.to_json();
    std::lock_guard<std::mutex> lock(client_mutex_);
    if (current_pipe_ != INVALID_HANDLE_VALUE) {
        send_payload(current_pipe_, payload);
    }
}

bool IpcServer::send_payload(HANDLE hPipe, const std::string& payload) {
    auto frame = encode_frame(payload);
    DWORD total_written = 0;
    DWORD to_write = static_cast<DWORD>(frame.size());

    while (total_written < to_write) {
        DWORD chunk_written = 0;
        BOOL res = WriteFile(
            hPipe,
            frame.data() + total_written,
            to_write - total_written,
            &chunk_written,
            NULL
        );
        if (!res || chunk_written == 0) {
            return false;
        }
        total_written += chunk_written;
    }
    return true;
}

std::optional<std::string> IpcServer::read_payload(HANDLE hPipe) {
    uint8_t header[4] = {0};
    DWORD total_header_read = 0;

    // Read full 4-byte big-endian length prefix
    while (total_header_read < 4) {
        DWORD chunk_read = 0;
        BOOL res = ReadFile(
            hPipe,
            header + total_header_read,
            4 - total_header_read,
            &chunk_read,
            NULL
        );
        if (!res || chunk_read == 0) {
            return std::nullopt;
        }
        total_header_read += chunk_read;
    }

    uint32_t len = decode_frame_length(header);
    if (len > MAX_FRAME_SIZE || len == 0) {
        return std::nullopt;
    }

    std::vector<char> buf(len);
    DWORD total_read = 0;
    while (total_read < len) {
        DWORD chunk_read = 0;
        BOOL res = ReadFile(
            hPipe,
            buf.data() + total_read,
            len - total_read,
            &chunk_read,
            NULL
        );
        if (!res || chunk_read == 0) {
            return std::nullopt;
        }
        total_read += chunk_read;
    }

    return std::string(buf.data(), len);
}

Response IpcServer::dispatch_request(const Request& req) {
    Handler handler;
    {
        std::lock_guard<std::mutex> lock(handlers_mutex_);
        auto it = handlers_.find(req.type);
        if (it != handlers_.end()) {
            handler = it->second;
        }
    }

    if (!handler) {
        return Response::make_error(
            req.request_id,
            1005,
            "UNKNOWN_ACTION",
            "Action type '" + req.type + "' is not registered"
        );
    }

    try {
        return handler(req);
    } catch (const std::exception& ex) {
        return Response::make_error(req.request_id, 5000, "INTERNAL_ERROR", ex.what());
    } catch (...) {
        return Response::make_error(req.request_id, 5000, "INTERNAL_ERROR", "Unknown native exception");
    }
}

void IpcServer::handle_client_session(HANDLE hPipe) {
    {
        std::lock_guard<std::mutex> lock(client_mutex_);
        current_pipe_ = hPipe;
    }

    while (running_.load()) {
        auto payload_opt = read_payload(hPipe);
        if (!payload_opt) {
            break; // Client disconnected or error
        }

        auto req_opt = Request::from_json(*payload_opt);
        if (!req_opt) {
            Response err = Response::make_error("", 1002, "INVALID_JSON", "Failed to parse JSON request envelope");
            send_payload(hPipe, err.to_json());
            continue;
        }

        Response res = dispatch_request(*req_opt);
        if (!send_payload(hPipe, res.to_json())) {
            break;
        }
    }
}

void IpcServer::run_server_loop() {
    // Explicit security attributes restricting pipe access to Interactive Users
    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = FALSE;
    sa.lpSecurityDescriptor = NULL;

    PSECURITY_DESCRIPTOR pSD = NULL;
    if (ConvertStringSecurityDescriptorToSecurityDescriptorA(
            "D:(A;;GRGW;;;IU)", // Allow Interactive User read/write
            SDDL_REVISION_1,
            &pSD,
            NULL)) {
        sa.lpSecurityDescriptor = pSD;
    }

    while (running_.load()) {
        HANDLE hPipe = CreateNamedPipeA(
            pipe_name_.c_str(),
            PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
            PIPE_UNLIMITED_INSTANCES,
            65536,
            65536,
            0,
            sa.lpSecurityDescriptor ? &sa : NULL
        );

        if (hPipe == INVALID_HANDLE_VALUE) {
            std::this_thread::sleep_for(std::chrono::milliseconds(200));
            continue;
        }

        BOOL connected = ConnectNamedPipe(hPipe, NULL) ? TRUE : (GetLastError() == ERROR_PIPE_CONNECTED);

        if (connected && running_.load()) {
            handle_client_session(hPipe);
        }

        // Clean handle shutdown: only close if not already closed by stop()
        {
            std::lock_guard<std::mutex> lock(client_mutex_);
            if (current_pipe_ == hPipe) {
                DisconnectNamedPipe(hPipe);
                CloseHandle(hPipe);
                current_pipe_ = INVALID_HANDLE_VALUE;
            } else if (current_pipe_ == INVALID_HANDLE_VALUE && !running_.load()) {
                // Already closed by stop(), do not double close
            } else {
                DisconnectNamedPipe(hPipe);
                CloseHandle(hPipe);
            }
        }
    }

    if (pSD) {
        LocalFree(pSD);
    }
}

} // namespace rexha
