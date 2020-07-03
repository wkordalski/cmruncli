#define WAIT_LOOP_N     2000000
#define BULK_SIZE       50

#include <stdint.h>
#include <inttypes.h>

extern int printf(const char *, ...);
extern void emulator_main();
extern void emulator_exit();


__attribute__((optimize("-O0"))) static void wait_loop(int n) {
    int i = 0;
    for (i = 0; i < n; i++);
}

/* not optimized function with dead code
   using emulator_main and emulator_exit,
   so that they won't be optimized by linker
   and land in .elf */
static void dummy_for_linker_not_to_optimize() {
    volatile int i = 0;
    if (i) {
        emulator_main();
        emulator_exit();
    }
}

__attribute__((optimize("-O0"))) int mem_print(void *ptr, int size) {
    dummy_for_linker_not_to_optimize();
    int i = 0;
    uint8_t *p = (uint8_t*)ptr;
    for (i = 0; i < size; i++) {
        printf("%02x ", p[i]);
        if ((i + 1) % BULK_SIZE == 0) {
            // sleep for smaller throughput for UART
            wait_loop(WAIT_LOOP_N);
        }
    }

    return 0;
}

{% for (symbol, _) in dump_symbols %}
    {% if symbol in ['results', 'times'] %}
extern uint32_t volatile {{symbol}}[100];
    {% else %}
extern void *{{symbol}};
    {% endif %}
{% endfor %}

void dumpMem() {
    void *symbol;
	{% for (symbol, size) in dump_symbols %}
	symbol = (void*)&{{symbol}};
	printf("{{symbol}}: addr %" PRIu32 ", mem ", (uint32_t)&{{symbol}});
	mem_print(symbol, {{size}});
	printf("end\n");
	wait_loop(WAIT_LOOP_N);
	{% endfor %}
}
