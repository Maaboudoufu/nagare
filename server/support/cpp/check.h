// Tiny test helper for the C++ lessons. CHECK / CHECK_EQ print ✔/✘ per case; check_done() is main's return value.
// SUBMIT cases run only when the grader sets BOOT_SUBMIT (the Submit button), like the C lessons.
// must_finish(seconds, hint) fails code that's correct but too slow; must_finish(0) cancels it.
#pragma once
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <unistd.h>
#include <vector>

template <typename T> std::ostream &operator<<(std::ostream &os, const std::vector<T> &v) {
    os << "{";
    for (size_t i = 0; i < v.size(); i++) os << (i ? ", " : "") << v[i];
    return os << "}";
}

// Unbuffered, so the checks that finished still show when the next one crashes.
inline const bool check_unbuffered = (std::cout << std::unitbuf << std::boolalpha, true);

inline int &check_fails() { static int n = 0; return n; }
inline bool submitting() { return std::getenv("BOOT_SUBMIT") != nullptr; }

#define CHECK_EQ(actual, expected) do {                                                    \
    auto _a = (actual); auto _e = (expected);                                              \
    if (_a == _e) std::cout << "✔ Pass  " << #actual << " == " << _e << "\n";               \
    else { ++check_fails();                                                                 \
        std::cout << "✘ Fail  " << #actual << "\n    expected: [" << _e << "]"              \
                  << "\n    actual:   [" << _a << "]\n"; }                                  \
} while (0)

#define CHECK(...) do {                                                                    \
    if (__VA_ARGS__) std::cout << "✔ Pass  " << #__VA_ARGS__ << "\n";                       \
    else { ++check_fails(); std::cout << "✘ Fail  " << #__VA_ARGS__ << "\n"; }              \
} while (0)

inline const char *&check_hint() { static const char *hint = ""; return hint; }

inline void check_too_slow(int) {  // a signal handler: only write() and _exit() are safe here
    const char *head = "\n✘ Fail  too slow: ", *hint = check_hint();
    if (write(1, head, std::strlen(head)) < 0 || write(1, hint, std::strlen(hint)) < 0 || write(1, "\n", 1) < 0) _exit(1);
    _exit(1);
}

inline void must_finish(unsigned seconds, const char *hint = "") {
    check_hint() = hint;
    std::signal(SIGALRM, check_too_slow);
    alarm(seconds);
}

inline int check_done() {
    std::cout << (check_fails() ? "\nSome checks failed.\n" : "\nAll checks passed.\n");
    return check_fails() ? 1 : 0;
}
