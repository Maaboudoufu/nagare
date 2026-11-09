/* Stand-in for the munit.h the C lessons' test runner expects (not part of the scraped lessons).
 * Tests are declared with munit_case(RUN|SUBMIT, name, { ... }); SUBMIT cases only run when the
 * BOOT_SUBMIT environment variable is set. Assertions take an optional message as the last argument. */
#ifndef BOOT_MUNIT_H
#define BOOT_MUNIT_H

#include <setjmp.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { RUN = 0, SUBMIT = 1 };

typedef int (*MunitTestFn)(void);
typedef struct { const char *name; MunitTestFn fn; int mode; } MunitTest;
typedef struct { const char *name; MunitTest *tests; } MunitSuite;

static jmp_buf munit__jmp;
static char munit__msg[2048];

static void munit__fail(const char *file, int line, const char *msg, const char *fmt, ...) {
  char detail[1024];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(detail, sizeof detail, fmt, ap);
  va_end(ap);
  snprintf(munit__msg, sizeof munit__msg, "%s%s%s (%s:%d)", msg, *msg ? ": " : "", detail, file, line);
  longjmp(munit__jmp, 1);
}

#define munit_case(mode, name, ...)    \
  static const int name##_mode = mode; \
  static int name(void) { __VA_ARGS__ return 0; }
#define munit_test(path, fn) {path, fn, fn##_mode}
#define munit_null_test {NULL, NULL, 0}
#define munit_suite(name, tests) {name, tests}

static int munit_suite_main(const MunitSuite *suite, void *user, int argc, char **argv) {
  (void)user, (void)argc, (void)argv;
  int submit = getenv("BOOT_SUBMIT") != NULL, passed = 0, failed = 0, skipped = 0;
  printf("Running suite: %s\n---------------------------------\n", suite->name);
  for (MunitTest *t = suite->tests; t->name; t++) {
    if (t->mode == SUBMIT && !submit) { skipped++; continue; }
    fflush(stdout);
    if (setjmp(munit__jmp) == 0) {
      t->fn();
      printf("✓ Pass: %s\n", t->name);
      passed++;
    } else {
      printf("✘ Fail: %s\n  %s\n", t->name, munit__msg);
      failed++;
    }
  }
  printf("\n%d passed, %d failed", passed, failed);
  if (skipped) printf(", %d skipped (submit only)", skipped);
  printf("\n");
  return failed ? 1 : 0;
}

/* a <op> b for one type; the trailing "" __VA_ARGS__ turns an optional message literal into a string. */
#define munit__cmp(T, fmt, a, op, b, ...)                                                       \
  do {                                                                                          \
    T munit__a = (T)(a), munit__b = (T)(b);                                                     \
    if (!(munit__a op munit__b))                                                                \
      munit__fail(__FILE__, __LINE__, "" __VA_ARGS__, "%s %s %s (" fmt " vs " fmt ")", #a, #op, \
                  #b, munit__a, munit__b);                                                      \
  } while (0)
#define munit__check(cond, what, ...) \
  do { if (!(cond)) munit__fail(__FILE__, __LINE__, "" __VA_ARGS__, "%s", what); } while (0)

#define munit_assert_int(a, op, b, ...) munit__cmp(long long, "%lld", a, op, b, __VA_ARGS__)
#define munit_assert_uint8(a, op, b, ...) munit__cmp(unsigned long long, "%llu", a, op, b, __VA_ARGS__)
#define munit_assert_uint16(a, op, b, ...) munit__cmp(unsigned long long, "%llu", a, op, b, __VA_ARGS__)
#define munit_assert_uint32(a, op, b, ...) munit__cmp(unsigned long long, "%llu", a, op, b, __VA_ARGS__)
#define munit_assert_ulong(a, op, b, ...) munit__cmp(unsigned long long, "%llu", a, op, b, __VA_ARGS__)
#define munit_assert_size(a, op, b, ...) munit__cmp(unsigned long long, "%llu", a, op, b, __VA_ARGS__)
#define munit_assert_float(a, op, b, ...) munit__cmp(float, "%g", a, op, b, __VA_ARGS__)
#define munit_assert_ptr(a, op, b, ...) munit__cmp(const void *, "%p", a, op, b, __VA_ARGS__)
#define munit_assert_int_equal(a, b, ...) munit_assert_int(a, ==, b, __VA_ARGS__)
#define munit_assert_ptr_equal(a, b, ...) munit_assert_ptr(a, ==, b, __VA_ARGS__)
#define munit_assert_ptr_not_equal(a, b, ...) munit_assert_ptr(a, !=, b, __VA_ARGS__)
#define munit_assert_true(x, ...) munit__check((x), #x " should be true", __VA_ARGS__)
#define munit_assert_false(x, ...) munit__check(!(x), #x " should be false", __VA_ARGS__)
#define munit_assert_null(p, ...) munit__check((p) == NULL, #p " should be NULL", __VA_ARGS__)
#define munit_assert_not_null(p, ...) munit__check((p) != NULL, #p " should not be NULL", __VA_ARGS__)
#define munit_assert_ptr_null munit_assert_null
#define munit_assert_ptr_not_null munit_assert_not_null
#define munit_assert_double_equal(a, b, ...)                                                    \
  do {                                                                                          \
    double munit__a = (a), munit__b = (b), munit__d = munit__a - munit__b;                      \
    double munit__m = munit__a < 0 ? -munit__a : munit__a;                                      \
    if (munit__m < 1) munit__m = 1;                                                             \
    if ((munit__d < 0 ? -munit__d : munit__d) > 1e-5 * munit__m)                               \
      munit__fail(__FILE__, __LINE__, "" __VA_ARGS__, "%s == %s (%g vs %g)", #a, #b, munit__a, \
                  munit__b);                                                                    \
  } while (0)
#define munit_assert_string_equal(a, b, ...)                                                     \
  do {                                                                                           \
    const char *munit__a = (a), *munit__b = (b);                                                 \
    if (!munit__a || !munit__b || strcmp(munit__a, munit__b) != 0)                               \
      munit__fail(__FILE__, __LINE__, "" __VA_ARGS__, "%s == %s (\"%s\" vs \"%s\")", #a, #b,    \
                  munit__a ? munit__a : "(null)", munit__b ? munit__b : "(null)");              \
  } while (0)

/* The lessons use both spellings. */
#define assert_int munit_assert_int
#define assert_uint8 munit_assert_uint8
#define assert_uint16 munit_assert_uint16
#define assert_uint32 munit_assert_uint32
#define assert_ulong munit_assert_ulong
#define assert_size munit_assert_size
#define assert_float munit_assert_float
#define assert_ptr munit_assert_ptr
#define assert_int_equal munit_assert_int_equal
#define assert_ptr_equal munit_assert_ptr_equal
#define assert_ptr_not_equal munit_assert_ptr_not_equal
#define assert_true munit_assert_true
#define assert_false munit_assert_false
#define assert_null munit_assert_null
#define assert_not_null munit_assert_not_null
#define assert_ptr_null munit_assert_null
#define assert_ptr_not_null munit_assert_not_null
#define assert_double_equal munit_assert_double_equal
#define assert_string_equal munit_assert_string_equal

#endif
