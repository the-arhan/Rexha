#include "rexha/protocol.h"

namespace rexha {

std::optional<Request> Request::from_json(const std::string& json_str) {
    try {
        JsonValue val = JsonValue::parse(json_str);
        if (!val.is_object()) return std::nullopt;

        Request req;
        req.protocol_version = val.get_int("protocol_version", PROTOCOL_VERSION);
        req.request_id = val.get_string("request_id");
        req.type = val.get_string("type");
        if (req.type.empty()) return std::nullopt;

        if (val.has("arguments")) {
            req.arguments = val.get("arguments");
        }
        return req;
    } catch (...) {
        return std::nullopt;
    }
}

std::string Request::to_json() const {
    JsonValue obj = JsonValue::object();
    obj.set("protocol_version", protocol_version);
    obj.set("request_id", request_id);
    obj.set("type", type);
    obj.set("arguments", arguments);
    return obj.serialize();
}

Response Response::make_success(const std::string& req_id, JsonValue data) {
    Response res;
    res.request_id = req_id;
    res.success = true;
    res.data = std::move(data);
    return res;
}

Response Response::make_error(const std::string& req_id, int code, const std::string& message, const std::string& details) {
    Response res;
    res.request_id = req_id;
    res.type = "error";
    res.success = false;
    JsonValue err = JsonValue::object();
    err.set("code", code);
    err.set("message", message);
    if (!details.empty()) {
        err.set("details", details);
    }
    res.error = std::move(err);
    return res;
}

std::optional<Response> Response::from_json(const std::string& json_str) {
    try {
        JsonValue val = JsonValue::parse(json_str);
        if (!val.is_object()) return std::nullopt;

        Response res;
        res.protocol_version = val.get_int("protocol_version", PROTOCOL_VERSION);
        res.request_id = val.get_string("request_id");
        res.type = val.get_string("type", "result");
        res.success = val.get_bool("success", false);
        if (val.has("data")) res.data = val.get("data");
        if (val.has("error")) res.error = val.get("error");
        return res;
    } catch (...) {
        return std::nullopt;
    }
}

std::string Response::to_json() const {
    JsonValue obj = JsonValue::object();
    obj.set("protocol_version", protocol_version);
    obj.set("request_id", request_id);
    obj.set("type", type);
    obj.set("success", success);
    obj.set("data", data);
    obj.set("error", error);
    return obj.serialize();
}

Event Event::make(const std::string& event_name, JsonValue data) {
    Event ev;
    ev.event_name = event_name;
    ev.data = std::move(data);
    return ev;
}

std::string Event::to_json() const {
    JsonValue obj = JsonValue::object();
    obj.set("protocol_version", protocol_version);
    obj.set("request_id", request_id);
    obj.set("type", type);
    obj.set("event_name", event_name);
    obj.set("data", data);
    return obj.serialize();
}

std::vector<uint8_t> encode_frame(const std::string& payload) {
    uint32_t len = static_cast<uint32_t>(payload.size());
    std::vector<uint8_t> frame(4 + len);
    // Big-endian 4-byte header
    frame[0] = static_cast<uint8_t>((len >> 24) & 0xFF);
    frame[1] = static_cast<uint8_t>((len >> 16) & 0xFF);
    frame[2] = static_cast<uint8_t>((len >> 8) & 0xFF);
    frame[3] = static_cast<uint8_t>(len & 0xFF);
    std::memcpy(frame.data() + 4, payload.data(), len);
    return frame;
}

uint32_t decode_frame_length(const uint8_t* header) {
    return (static_cast<uint32_t>(header[0]) << 24) |
           (static_cast<uint32_t>(header[1]) << 16) |
           (static_cast<uint32_t>(header[2]) << 8)  |
           (static_cast<uint32_t>(header[3]));
}

} // namespace rexha

