/* Stand-in for the bootlib.h the C lessons include: tracks heap allocations so tests can check for leaks.
 * grader.py links with -Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free,--wrap=strdup whenever a
 * lesson file includes this header, so allocations in your own .c files are tracked too.
 * Include it from one file only (the lessons include it from main.c). */
#ifndef BOOTLIB_H
#define BOOTLIB_H

#include <stdbool.h>
#include <stddef.h>
#include <string.h>

void *__real_malloc(size_t size);
void *__real_calloc(size_t count, size_t size);
void *__real_realloc(void *ptr, size_t size);
void __real_free(void *ptr);

typedef struct { void *ptr; size_t size; bool freed; } boot_alloc_t;
/* ponytail: fixed table, allocations past 65536 go untracked; grow it if a lesson ever needs more */
static boot_alloc_t boot__allocs[65536];
static size_t boot__count, boot__realloc_count, boot__last_realloc_size;

static boot_alloc_t *boot__find(void *ptr) {
  for (size_t i = boot__count; i-- > 0;)  /* newest first: addresses get reused after free */
    if (boot__allocs[i].ptr == ptr) return &boot__allocs[i];
  return NULL;
}

static void boot__track(void *ptr, size_t size) {
  if (!ptr) return;
  boot_alloc_t *a = boot__find(ptr);
  if (!a && boot__count < sizeof boot__allocs / sizeof *boot__allocs) a = &boot__allocs[boot__count++];
  if (a) *a = (boot_alloc_t){ptr, size, false};
}

static void boot__untrack(void *ptr) {
  boot_alloc_t *a = ptr ? boot__find(ptr) : NULL;
  if (a) a->freed = true;
}

void *__wrap_malloc(size_t size) { void *p = __real_malloc(size); boot__track(p, size); return p; }
void *__wrap_calloc(size_t count, size_t size) { void *p = __real_calloc(count, size); boot__track(p, count * size); return p; }
void __wrap_free(void *ptr) { boot__untrack(ptr); __real_free(ptr); }
void *__wrap_realloc(void *ptr, size_t size) {
  boot__realloc_count++;
  boot__last_realloc_size = size;
  void *p = __real_realloc(ptr, size);
  if (p) { boot__untrack(ptr); boot__track(p, size); }
  return p;
}
char *__wrap_strdup(const char *s) {
  size_t n = strlen(s) + 1;
  char *p = (char *)__wrap_malloc(n);
  return p ? (char *)memcpy(p, s, n) : NULL;
}

static inline bool boot_all_freed(void) {
  for (size_t i = 0; i < boot__count; i++)
    if (!boot__allocs[i].freed) return false;
  return true;
}
static inline bool boot_is_freed(void *ptr) { boot_alloc_t *a = boot__find(ptr); return a && a->freed; }
static inline size_t boot_alloc_size(void) {
  size_t total = 0;
  for (size_t i = 0; i < boot__count; i++)
    if (!boot__allocs[i].freed) total += boot__allocs[i].size;
  return total;
}
static inline size_t boot_realloc_count(void) { return boot__realloc_count; }
static inline size_t boot_last_realloc_size(void) { return boot__last_realloc_size; }

#endif
