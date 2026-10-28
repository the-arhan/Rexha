#pragma once

#include <string>
#include <vector>
#include <cstdint>
#include <optional>
#include "rexha/json.h"

namespace rexha {

constexpr int PROTOCOL_VERSION = 1;
constexpr uint32_t MAX_FRAME_SIZE = 1048576; // 1 MB

struct Request {
    int protocol_version = PROTOCOL_VERSION;
    std::string request_id;
    std::string type;
    JsonValue arguments = JsonValue::object();

    static std::optional<Request> from_json(const std::string& json_str);
    std::string to_json() const;
};

struct Response {
    int protocol_version = PROTOCOL_VERSION;
    std::string request_id;
    std::string type = "result";
    bool success = true;
    JsonValue data = JsonValue::null();
    JsonValue error = JsonValue::null();

    static Response make_success(const std::string& req_id, JsonValue data);
    static Response make_error(const std::string& req_id, int code, const std::string& message, const std::string& details = "");

    static std::optional<Response> from_json(const std::string& json_str);
    std::string to_json() const;
};

struct Event {
    int protocol_version = PROTOCOL_VERSION;
    std::string request_id = "";
    std::string type = "event";
    std::string event_name;
    JsonValue data = JsonValue::object();

    static Event make(const std::string& event_name, JsonValue data);
    std::string to_json() const;
};

// Framing utilities
std::vector<uint8_t> encode_frame(const std::string& payload);
uint32_t decode_frame_length(const uint8_t* header_4_bytes);

} // namespace rexha

