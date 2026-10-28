#pragma once

#include <string>
#include <vector>
#include <map>
#include <variant>
#include <sstream>
#include <stdexcept>
#include <cstdint>
#include <cctype>
#include <iomanip>
#include <cmath>

namespace rexha {

enum class JsonType {
    Null,
    Boolean,
    Number,
    String,
    Array,
    Object
};

constexpr size_t MAX_JSON_DEPTH = 64;

class JsonValue {
public:
    using ArrayType = std::vector<JsonValue>;
    using ObjectType = std::map<std::string, JsonValue>;

    // Constructors
    JsonValue() : type_(JsonType::Null) {}
    JsonValue(std::nullptr_t) : type_(JsonType::Null) {}
    JsonValue(bool b) : type_(JsonType::Boolean), bool_val_(b) {}
    JsonValue(int i) : type_(JsonType::Number), num_val_(static_cast<double>(i)) {}
    JsonValue(int64_t i) : type_(JsonType::Number), num_val_(static_cast<double>(i)) {}
    JsonValue(uint32_t i) : type_(JsonType::Number), num_val_(static_cast<double>(i)) {}
    JsonValue(uint64_t i) : type_(JsonType::Number), num_val_(static_cast<double>(i)) {}
    JsonValue(double d) : type_(JsonType::Number), num_val_(d) {}
    JsonValue(const char* s) : type_(JsonType::String), str_val_(s ? s : "") {}
    JsonValue(std::string s) : type_(JsonType::String), str_val_(std::move(s)) {}
    JsonValue(ArrayType a) : type_(JsonType::Array), arr_val_(std::move(a)) {}
    JsonValue(ObjectType o) : type_(JsonType::Object), obj_val_(std::move(o)) {}

    // Factory methods
    static JsonValue null() { return JsonValue(); }
    static JsonValue array() { return JsonValue(ArrayType{}); }
    static JsonValue object() { return JsonValue(ObjectType{}); }

    // Type queries
    JsonType type() const { return type_; }
    bool is_null() const { return type_ == JsonType::Null; }
    bool is_bool() const { return type_ == JsonType::Boolean; }
    bool is_number() const { return type_ == JsonType::Number; }
    bool is_string() const { return type_ == JsonType::String; }
    bool is_array() const { return type_ == JsonType::Array; }
    bool is_object() const { return type_ == JsonType::Object; }

    // Accessors
    bool as_bool(bool default_val = false) const {
        return (type_ == JsonType::Boolean) ? bool_val_ : default_val;
    }

    double as_double(double default_val = 0.0) const {
        return (type_ == JsonType::Number) ? num_val_ : default_val;
    }

    int64_t as_int64(int64_t default_val = 0) const {
        return (type_ == JsonType::Number) ? static_cast<int64_t>(num_val_) : default_val;
    }

    int as_int(int default_val = 0) const {
        return (type_ == JsonType::Number) ? static_cast<int>(num_val_) : default_val;
    }

    const std::string& as_string() const {
        static const std::string empty;
        return (type_ == JsonType::String) ? str_val_ : empty;
    }

    const ArrayType& as_array() const {
        static const ArrayType empty;
        return (type_ == JsonType::Array) ? arr_val_ : empty;
    }

    ArrayType& as_array() {
        if (type_ != JsonType::Array) {
            type_ = JsonType::Array;
            arr_val_.clear();
        }
        return arr_val_;
    }

    const ObjectType& as_object() const {
        static const ObjectType empty;
        return (type_ == JsonType::Object) ? obj_val_ : empty;
    }

    ObjectType& as_object() {
        if (type_ != JsonType::Object) {
            type_ = JsonType::Object;
            obj_val_.clear();
        }
        return obj_val_;
    }

    // Object helpers
    bool has(const std::string& key) const {
        if (type_ != JsonType::Object) return false;
        return obj_val_.find(key) != obj_val_.end();
    }

    const JsonValue& get(const std::string& key) const {
        static const JsonValue null_val;
        if (type_ != JsonType::Object) return null_val;
        auto it = obj_val_.find(key);
        return (it != obj_val_.end()) ? it->second : null_val;
    }

    std::string get_string(const std::string& key, const std::string& default_val = "") const {
        const auto& val = get(key);
        return val.is_string() ? val.as_string() : default_val;
    }

    int get_int(const std::string& key, int default_val = 0) const {
        const auto& val = get(key);
        return val.is_number() ? val.as_int() : default_val;
    }

    int64_t get_int64(const std::string& key, int64_t default_val = 0) const {
        const auto& val = get(key);
        return val.is_number() ? val.as_int64() : default_val;
    }

    double get_double(const std::string& key, double default_val = 0.0) const {
        const auto& val = get(key);
        return val.is_number() ? val.as_double() : default_val;
    }

    bool get_bool(const std::string& key, bool default_val = false) const {
        const auto& val = get(key);
        return val.is_bool() ? val.as_bool() : default_val;
    }

    void set(const std::string& key, JsonValue value) {
        if (type_ != JsonType::Object) {
            type_ = JsonType::Object;
            obj_val_.clear();
        }
        obj_val_[key] = std::move(value);
    }

    void push_back(JsonValue value) {
        if (type_ != JsonType::Array) {
            type_ = JsonType::Array;
            arr_val_.clear();
        }
        arr_val_.push_back(std::move(value));
    }

    // Serialization
    std::string serialize() const {
        std::ostringstream ss;
        serialize_to(ss);
        return ss.str();
    }

    // Parser
    static JsonValue parse(const std::string& json_str) {
        size_t index = 0;
        skip_whitespace(json_str, index);
        if (index >= json_str.size()) {
            throw std::runtime_error("Empty JSON string");
        }
        JsonValue val = parse_value(json_str, index, 0);
        skip_whitespace(json_str, index);
        if (index < json_str.size()) {
            throw std::runtime_error("Unexpected trailing characters in JSON");
        }
        return val;
    }

private:
    JsonType type_ = JsonType::Null;
    bool bool_val_ = false;
    double num_val_ = 0.0;
    std::string str_val_;
    ArrayType arr_val_;
    ObjectType obj_val_;

    void serialize_to(std::ostringstream& ss) const {
        switch (type_) {
            case JsonType::Null:
                ss << "null";
                break;
            case JsonType::Boolean:
                ss << (bool_val_ ? "true" : "false");
                break;
            case JsonType::Number:
                if (num_val_ == static_cast<int64_t>(num_val_) && !std::isnan(num_val_)) {
                    ss << static_cast<int64_t>(num_val_);
                } else {
                    ss << std::setprecision(10) << num_val_;
                }
                break;
            case JsonType::String:
                escape_string(ss, str_val_);
                break;
            case JsonType::Array: {
                ss << "[";
                for (size_t i = 0; i < arr_val_.size(); ++i) {
                    if (i > 0) ss << ",";
                    arr_val_[i].serialize_to(ss);
                }
                ss << "]";
                break;
            }
            case JsonType::Object: {
                ss << "{";
                bool first = true;
                for (const auto& [k, v] : obj_val_) {
                    if (!first) ss << ",";
                    first = false;
                    escape_string(ss, k);
                    ss << ":";
                    v.serialize_to(ss);
                }
                ss << "}";
                break;
            }
        }
    }

    static void escape_string(std::ostringstream& ss, const std::string& str) {
        ss << "\"";
        for (char c : str) {
            switch (c) {
                case '"': ss << "\\\""; break;
                case '\\': ss << "\\\\"; break;
                case '\b': ss << "\\b"; break;
                case '\f': ss << "\\f"; break;
                case '\n': ss << "\\n"; break;
                case '\r': ss << "\\r"; break;
                case '\t': ss << "\\t"; break;
                default:
                    if (static_cast<unsigned char>(c) < 0x20) {
                        ss << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c);
                    } else {
                        ss << c;
                    }
                    break;
            }
        }
        ss << "\"";
    }

    static void skip_whitespace(const std::string& s, size_t& i) {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) {
            ++i;
        }
    }

    static JsonValue parse_value(const std::string& s, size_t& i, size_t depth) {
        if (depth > MAX_JSON_DEPTH) {
            throw std::runtime_error("Exceeded maximum JSON nesting depth");
        }

        skip_whitespace(s, i);
        if (i >= s.size()) throw std::runtime_error("Unexpected end of JSON input");

        char c = s[i];
        if (c == 'n') return parse_null(s, i);
        if (c == 't' || c == 'f') return parse_bool(s, i);
        if (c == '"') return parse_string(s, i);
        if (c == '[') return parse_array(s, i, depth + 1);
        if (c == '{') return parse_object(s, i, depth + 1);
        if (c == '-' || (c >= '0' && c <= '9')) return parse_number(s, i);

        throw std::runtime_error(std::string("Invalid character in JSON: '") + c + "'");
    }

    static JsonValue parse_null(const std::string& s, size_t& i) {
        if (i + 4 <= s.size() && s.substr(i, 4) == "null") {
            i += 4;
            return JsonValue(nullptr);
        }
        throw std::runtime_error("Failed to parse 'null'");
    }

    static JsonValue parse_bool(const std::string& s, size_t& i) {
        if (i + 4 <= s.size() && s.substr(i, 4) == "true") {
            i += 4;
            return JsonValue(true);
        }
        if (i + 5 <= s.size() && s.substr(i, 5) == "false") {
            i += 5;
            return JsonValue(false);
        }
        throw std::runtime_error("Failed to parse boolean");
    }

    static JsonValue parse_string(const std::string& s, size_t& i) {
        ++i; // skip initial "
        std::string res;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') {
                return JsonValue(res);
            }
            if (c == '\\') {
                if (i >= s.size()) throw std::runtime_error("Unterminated escape sequence");
                char esc = s[i++];
                switch (esc) {
                    case '"': res += '"'; break;
                    case '\\': res += '\\'; break;
                    case '/': res += '/'; break;
                    case 'b': res += '\b'; break;
                    case 'f': res += '\f'; break;
                    case 'n': res += '\n'; break;
                    case 'r': res += '\r'; break;
                    case 't': res += '\t'; break;
                    case 'u': {
                        if (i + 4 > s.size()) throw std::runtime_error("Invalid unicode escape");
                        for (size_t k = 0; k < 4; ++k) {
                            if (!std::isxdigit(static_cast<unsigned char>(s[i + k]))) {
                                throw std::runtime_error("Invalid hex digit in unicode escape");
                            }
                        }
                        std::string hex_str = s.substr(i, 4);
                        i += 4;
                        uint16_t code = static_cast<uint16_t>(std::stoul(hex_str, nullptr, 16));
                        if (code < 0x80) {
                            res += static_cast<char>(code);
                        } else if (code < 0x800) {
                            res += static_cast<char>(0xC0 | ((code >> 6) & 0x1F));
                            res += static_cast<char>(0x80 | (code & 0x3F));
                        } else {
                            res += static_cast<char>(0xE0 | ((code >> 12) & 0x0F));
                            res += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
                            res += static_cast<char>(0x80 | (code & 0x3F));
                        }
                        break;
                    }
                    default:
                        res += esc;
                        break;
                }
            } else {
                res += c;
            }
        }
        throw std::runtime_error("Unterminated string in JSON");
    }

    static JsonValue parse_number(const std::string& s, size_t& i) {
        size_t start = i;
        if (s[i] == '-') ++i;

        if (i >= s.size() || (s[i] < '0' || s[i] > '9')) {
            throw std::runtime_error("Invalid number format in JSON");
        }

        while (i < s.size() && (s[i] >= '0' && s[i] <= '9')) ++i;
        if (i < s.size() && s[i] == '.') {
            ++i;
            if (i >= s.size() || (s[i] < '0' || s[i] > '9')) {
                throw std::runtime_error("Invalid fractional part in JSON number");
            }
            while (i < s.size() && (s[i] >= '0' && s[i] <= '9')) ++i;
        }
        if (i < s.size() && (s[i] == 'e' || s[i] == 'E')) {
            ++i;
            if (i < s.size() && (s[i] == '+' || s[i] == '-')) ++i;
            if (i >= s.size() || (s[i] < '0' || s[i] > '9')) {
                throw std::runtime_error("Invalid exponent part in JSON number");
            }
            while (i < s.size() && (s[i] >= '0' && s[i] <= '9')) ++i;
        }

        std::string num_str = s.substr(start, i - start);
        try {
            double d = std::stod(num_str);
            return JsonValue(d);
        } catch (...) {
            throw std::runtime_error("Failed to parse number in JSON");
        }
    }

    static JsonValue parse_array(const std::string& s, size_t& i, size_t depth) {
        ++i; // skip [
        ArrayType arr;
        skip_whitespace(s, i);
        if (i < s.size() && s[i] == ']') {
            ++i;
            return JsonValue(arr);
        }

        while (i < s.size()) {
            arr.push_back(parse_value(s, i, depth));
            skip_whitespace(s, i);
            if (i < s.size() && s[i] == ']') {
                ++i;
                return JsonValue(arr);
            }
            if (i < s.size() && s[i] == ',') {
                ++i;
            } else {
                throw std::runtime_error("Expected ',' or ']' in array");
            }
        }
        throw std::runtime_error("Unterminated array in JSON");
    }

    static JsonValue parse_object(const std::string& s, size_t& i, size_t depth) {
        ++i; // skip {
        ObjectType obj;
        skip_whitespace(s, i);
        if (i < s.size() && s[i] == '}') {
            ++i;
            return JsonValue(obj);
        }

        while (i < s.size()) {
            skip_whitespace(s, i);
            if (i >= s.size() || s[i] != '"') {
                throw std::runtime_error("Expected string key in object");
            }
            std::string key = parse_string(s, i).as_string();
            skip_whitespace(s, i);
            if (i >= s.size() || s[i] != ':') {
                throw std::runtime_error("Expected ':' after object key");
            }
            ++i; // skip :
            obj[key] = parse_value(s, i, depth);
            skip_whitespace(s, i);
            if (i < s.size() && s[i] == '}') {
                ++i;
                return JsonValue(obj);
            }
            if (i < s.size() && s[i] == ',') {
                ++i;
            } else {
                throw std::runtime_error("Expected ',' or '}' in object");
            }
        }
        throw std::runtime_error("Unterminated object in JSON");
    }
};

} // namespace rexha
