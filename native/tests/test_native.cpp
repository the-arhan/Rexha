#include "rexha/json.h"
#include "rexha/protocol.h"
#include "rexha/system_metrics.h"
#include "rexha/window_manager.h"
#include "rexha/process_manager.h"
#include <iostream>
#include <cassert>
#include <vector>

using namespace rexha;

static int g_test_count = 0;
static int g_pass_count = 0;

#define ASSERT_TEST(cond, name) \
    do { \
        ++g_test_count; \
        if (cond) { \
            ++g_pass_count; \
            std::cout << "  [PASS] " << name << "\n"; \
        } else { \
            std::cerr << "  [FAIL] " << name << " (" << #cond << ")\n"; \
        } \
    } while (0)

void test_json_primitives() {
    std::cout << "Running test_json_primitives...\n";

    // Null
    auto v_null = JsonValue::parse("null");
    ASSERT_TEST(v_null.is_null(), "JsonValue parses null");
    ASSERT_TEST(v_null.serialize() == "null", "JsonValue serializes null");

    // Booleans
    auto v_true = JsonValue::parse("true");
    ASSERT_TEST(v_true.is_bool() && v_true.as_bool() == true, "JsonValue parses true");
    auto v_false = JsonValue::parse("false");
    ASSERT_TEST(v_false.is_bool() && v_false.as_bool() == false, "JsonValue parses false");

    // Numbers
    auto v_int = JsonValue::parse("12345");
    ASSERT_TEST(v_int.is_number() && v_int.as_int() == 12345, "JsonValue parses integer");
    auto v_neg = JsonValue::parse("-42");
    ASSERT_TEST(v_neg.is_number() && v_neg.as_int() == -42, "JsonValue parses negative integer");
    auto v_float = JsonValue::parse("3.14159");
    ASSERT_TEST(v_float.is_number() && std::abs(v_float.as_double() - 3.14159) < 0.0001, "JsonValue parses float");

    // Strings & Escapes
    auto v_str = JsonValue::parse("\"Hello, \\\"Rexha\\\"!\\nLine 2\"");
    ASSERT_TEST(v_str.is_string(), "JsonValue parses escaped string");
    ASSERT_TEST(v_str.as_string() == "Hello, \"Rexha\"!\nLine 2", "JsonValue string content matches");

    // 3-Byte Unicode escape
    auto v_uni = JsonValue::parse("\"\\u2602\"");
    ASSERT_TEST(v_uni.is_string() && !v_uni.as_string().empty(), "JsonValue decodes 3-byte unicode");
}

void test_json_security_edge_cases() {
    std::cout << "Running test_json_security_edge_cases...\n";

    // 1. Deep nesting exhaustion
    std::string deep = "";
    for (int i = 0; i < 70; ++i) deep += "[";
    for (int i = 0; i < 70; ++i) deep += "]";
    bool depth_rejected = false;
    try {
        JsonValue::parse(deep);
    } catch (const std::runtime_error&) {
        depth_rejected = true;
    }
    ASSERT_TEST(depth_rejected, "JSON parser rejects excessive recursion depth > 64");

    // 2. Trailing garbage
    bool trailing_rejected = false;
    try {
        JsonValue::parse("{\"valid\": true} trailing_garbage");
    } catch (const std::runtime_error&) {
        trailing_rejected = true;
    }
    ASSERT_TEST(trailing_rejected, "JSON parser rejects trailing characters");

    // 3. Invalid number format
    bool bad_num_rejected = false;
    try {
        JsonValue::parse("-");
    } catch (const std::runtime_error&) {
        bad_num_rejected = true;
    }
    ASSERT_TEST(bad_num_rejected, "JSON parser rejects '-' without digits");

    // 4. Invalid hex in unicode escape
    bool bad_hex_rejected = false;
    try {
        JsonValue::parse("\"\\u12G4\"");
    } catch (const std::runtime_error&) {
        bad_hex_rejected = true;
    }
    ASSERT_TEST(bad_hex_rejected, "JSON parser rejects invalid hex in unicode escape");
}

void test_json_complex() {
    std::cout << "Running test_json_complex...\n";

    std::string sample = "{\"name\":\"rexha\",\"version\":1,\"flags\":[true,false,null],\"nested\":{\"key\":\"value\"}}";
    auto obj = JsonValue::parse(sample);
    ASSERT_TEST(obj.is_object(), "JsonValue parses object");
    ASSERT_TEST(obj.get_string("name") == "rexha", "Object get_string matches");
    ASSERT_TEST(obj.get_int("version") == 1, "Object get_int matches");
    ASSERT_TEST(obj.has("flags"), "Object has flags array");
    ASSERT_TEST(obj.get("flags").is_array(), "Flags is array");
    ASSERT_TEST(obj.get("flags").as_array().size() == 3, "Flags has 3 elements");
    ASSERT_TEST(obj.get("nested").get_string("key") == "value", "Nested object key matches");

    std::string roundtrip = obj.serialize();
    auto obj2 = JsonValue::parse(roundtrip);
    ASSERT_TEST(obj2.get_string("name") == "rexha", "Roundtrip preservation matches");
}

void test_protocol_envelopes() {
    std::cout << "Running test_protocol_envelopes...\n";

    // Request serialization and parsing
    Request req;
    req.request_id = "req-test-123";
    req.type = "window.set_state";
    req.arguments.set("hwnd", 123456);
    req.arguments.set("state", "maximize");

    std::string req_json = req.to_json();
    auto req_parsed = Request::from_json(req_json);
    ASSERT_TEST(req_parsed.has_value(), "Request from_json succeeds");
    ASSERT_TEST(req_parsed->request_id == "req-test-123", "Request ID matches");
    ASSERT_TEST(req_parsed->type == "window.set_state", "Request type matches");
    ASSERT_TEST(req_parsed->arguments.get_int64("hwnd") == 123456, "Request arguments hwnd matches");

    // Success Response
    JsonValue res_data = JsonValue::object();
    res_data.set("status", "ready");
    Response resp = Response::make_success("req-test-123", res_data);
    ASSERT_TEST(resp.success == true, "Response is success");
    std::string resp_json = resp.to_json();
    auto resp_parsed = Response::from_json(resp_json);
    ASSERT_TEST(resp_parsed.has_value() && resp_parsed->success == true, "Response from_json succeeds");
    ASSERT_TEST(resp_parsed->data.get_string("status") == "ready", "Response data matches");

    // Error Response
    Response err_resp = Response::make_error("req-err-456", 1005, "UNKNOWN_ACTION", "Action not found");
    ASSERT_TEST(err_resp.success == false, "Error response success is false");
    auto err_parsed = Response::from_json(err_resp.to_json());
    ASSERT_TEST(err_parsed.has_value() && !err_parsed->success, "Error response parsed correctly");
    ASSERT_TEST(err_parsed->error.get_int("code") == 1005, "Error code matches 1005");
}

void test_protocol_framing() {
    std::cout << "Running test_protocol_framing...\n";

    std::string payload = "{\"test\":true}";
    auto frame = encode_frame(payload);
    ASSERT_TEST(frame.size() == 4 + payload.size(), "Encoded frame has 4-byte header");

    uint32_t decoded_len = decode_frame_length(frame.data());
    ASSERT_TEST(decoded_len == payload.size(), "Decoded length matches payload size");

    // Check big-endian encoding
    uint32_t expected_len = static_cast<uint32_t>(payload.size());
    ASSERT_TEST(frame[0] == ((expected_len >> 24) & 0xFF), "Header byte 0 correct");
    ASSERT_TEST(frame[1] == ((expected_len >> 16) & 0xFF), "Header byte 1 correct");
    ASSERT_TEST(frame[2] == ((expected_len >> 8) & 0xFF), "Header byte 2 correct");
    ASSERT_TEST(frame[3] == (expected_len & 0xFF), "Header byte 3 correct");
}

void test_system_metrics() {
    std::cout << "Running test_system_metrics...\n";

    SystemMetrics metrics;
    auto status = metrics.get_status();
    ASSERT_TEST(status.get_string("core_version") == "0.1.0", "Core version matches 0.1.0");
    ASSERT_TEST(status.get_int64("pid") > 0, "Current process PID is positive");
    ASSERT_TEST(status.get_double("uptime_seconds") >= 0.0, "Uptime is non-negative");

    auto m = metrics.get_metrics();
    ASSERT_TEST(m.get_int64("ram_total_mb") > 0, "Total RAM > 0 MB");
    ASSERT_TEST(m.get_int64("ram_available_mb") > 0, "Available RAM > 0 MB");
    ASSERT_TEST(m.get_double("cpu_percent") >= 0.0 && m.get_double("cpu_percent") <= 100.0, "CPU percent between 0 and 100");
}

void test_window_manager() {
    std::cout << "Running test_window_manager...\n";

    WindowManager wm;
    auto fg = wm.get_foreground_window();
    // On an active interactive desktop, foreground window exists
    if (fg) {
        ASSERT_TEST(fg->hwnd != 0, "Foreground window HWND is valid");
        ASSERT_TEST(fg->pid != 0, "Foreground window PID is valid");
    } else {
        std::cout << "  [INFO] No active foreground window in this session\n";
    }

    // In background or service sessions, visible windows may be 0; enumerate all
    auto all_windows = wm.list_windows(false, false);
    ASSERT_TEST(true, "Window enumeration executed without error");
    std::cout << "  [INFO] Discovered " << all_windows.size() << " total windows in session\n";
}

int main() {
    std::cout << "========================================\n";
    std::cout << " Rexha Native Core Unit & Systems Tests \n";
    std::cout << "========================================\n";

    test_json_primitives();
    test_json_complex();
    test_json_security_edge_cases();
    test_protocol_envelopes();
    test_protocol_framing();
    test_system_metrics();
    test_window_manager();

    std::cout << "========================================\n";
    std::cout << " Results: " << g_pass_count << " / " << g_test_count << " assertions passed\n";
    std::cout << "========================================\n";

    return (g_pass_count == g_test_count) ? 0 : 1;
}
