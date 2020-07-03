.global emulator_main
.global emulator_exit

.cpu cortex-m3
.syntax unified
.thumb

@ r0 - dst addr (assuming that it's aligned)
@ r1 - src addr (assuming that it's aligned)
@ r2 - number of bytes to copy
.thumb_func
.align	2
.type	_emulator_memcpy, %function
_emulator_memcpy:
	movs.n	r3, #4
	movs.n	r5, #0
.align	2
_emulator_memcpy_loop_begin:
	cbz.n	r2, _emulator_memcpy_loop_end
	subs.n	r2, r3
	ldr.n	r4, [r1, r5]
	str.n	r4, [r0, r5]
	adds.n	r5, r3
	b.n	_emulator_memcpy_loop_begin
.align	2
_emulator_memcpy_loop_end:
	bx.n	lr

@ r0: dst addr (assuming that it's aligned)
@ r1: memset value
@ r2: number of bytes to set
@ values in registers r0-r3,r5 are destroyed
.thumb_func
.align	2
.type	_emulator_memset, %function
_emulator_memset:
	movs.n	r3, #4
	movs.n	r5, #0
.align	2
_emulator_memset_loop_begin:
	cbz.n	r2, _emulator_memset_loop_end
	subs.n	r2, r3
	str.n	r1, [r0, r5]
	adds.n	r0, r3
	b.n	_emulator_memset_loop_begin
.align	2
_emulator_memset_loop_end:
	bx.n	lr

@ Init routine for emulator, replacing TI routine
.thumb_func
.align	2
.type	emulator_main, %function
emulator_main:
	@ Copy .data section from flash to SRAM
	ldr.n	r0, _data_val       @ .data section start on SRAM
	ldr.n	r1, _ldata_val      @ SRAM content start on flash
	ldr.n	r2, _edata_val      @ .data section end on SRAM
	subs.n	r2, r0              @ calculate number of bytes for memcpy
	bl.w	_emulator_memcpy

	@ Copy .gpram section from flash to GPRAM
	ldr.n   r0, _gpram_val      @ .gpram section start on GPRAM
	ldr.n   r1, _lgpram_val     @ GPRAM content start on flash
	ldr.n   r2, _egpram_val     @ .gpram section end on GPRAM
	subs.n  r2, r0              @ calculate number of bytes for memcpy
	bl.w    _emulator_memcpy

	@ Zero .bss section in SRAM
	@ these ldr have wide encodings
	@ narrow encodings throw a bunch of misalign errors for some reason
	ldr.n   r0, _bss_val        @ .bss section start on SRAM
	movs.n  r1, #0              @ value for memset
	ldr.n   r2, _ebss_val       @ .bss section end on SRAM
	subs.n  r2, r0              @ calculate number of bytes for memset
	bl.w    _emulator_memset

	b.w	_run_mocked_ti_funcs

.align	4
emulator_cdl_start:
	@ Jump to benchmarkCode
	bl.w    benchmarkCode

@ Exit routine for emulator, executed automatically
@ when benchmarkCode returns
.thumb_func
.align	2
.type	emulator_exit, %function
emulator_exit:
	@ Loop like there's no tomorrow
	b.n	emulator_exit
.size	emulator_main, .-emulator_main
.size	emulator_cdl_start, .-emulator_cdl_start
.size	emulator_exit, .-emulator_exit

.align	4
_data_val:	.word	_data
_ldata_val:	.word	_ldata
_edata_val:	.word	_edata

_gpram_val:	.word	_gpram
_lgpram_val:	.word	_lgpram
_egpram_val:	.word	_egpram

_bss_val:	.word	_bss
_ebss_val:	.word	_ebss


@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@                                      @
@     Mocks of symbols from TI lib     @
@                                      @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

.align	4
_run_mocked_ti_funcs:
    @ contents of this function are rendered based on test configuration
    @ might be empty, if nothing used
    {% if not write_buffer_enabled %}
    bl.w	_CPU_WriteBufferDisable
    {% endif %}
    {% if not line_buffer_enabled %}
    bl.w	_VIMSLineBufDisable
    {% endif %}
    b.w    emulator_cdl_start

@ References to TI code (root dir in `whip6-pub/nesc/whip6`):
@
@
@ `platforms/parts/mcu/cc26xx/native/cc26xxware/inc/hw_types.h`:
@ * (lines 71-120) definitions of macros HWREG*
@
@ `platforms/parts/mcu/cc26xx/native/cc26xxware/inc/hw_memmap.h`:
@ * (line 65) `VIMS_BASE`
@ * (line 152) `CPU_SCS_BASE`
@
@ `platforms/parts/mcu/cc26xx/native/cc26xxware/inc/hw_cpu_scs.h`:
@ * (line 50) `CPU_SCS_O_ACTLR`
@ * (line 267) `CPU_SCS_ACTLR_DISDEFWBUF_BITN`
@
@ `platforms/parts/mcu/cc26xx/native/cc26xxware/inc/hw_vims.h`:
@ * (line 50) `VIMS_O_CTL`
@ * (line 151) `VIMS_CTL_IDCODE_LB_DIS_M`
@ * (line 162) `VIMS_CTL_SYSBUS_LB_DIS_M`
@
@ `platforms/parts/mcu/cc26xx/native/cc26xxware/driverlib/vims.h`:
@ * (lines 298-306) `VIMSLineBufDisable`
@
@ `platforms/parts/mcu/cc26xx/native/cc26xxware/driverlib/cpu.h`:
@ * (lines 382-386) `CPU_WriteBufferDisable`
@
@
@ For easier overview, pasting source of mocked functions
@ along with needed defines (TI comments stripped):
@
@ #define HWREG(x)                                                              \
@         (*((volatile unsigned long *)(x)))
@
@ #define HWREGH(x)                                                             \
@         (*((volatile unsigned short *)(x)))
@
@ #define HWREGB(x)                                                             \
@         (*((volatile unsigned char *)(x)))
@
@ #define HWREGBITW(x, b)                                                       \
@         HWREG(((unsigned long)(x) & 0xF0000000) | 0x02000000 |                \
@              (((unsigned long)(x) & 0x000FFFFF) << 5) | ((b) << 2))
@
@ #define HWREGBITH(x, b)                                                       \
@         HWREGH(((unsigned long)(x) & 0xF0000000) | 0x02000000 |               \
@                (((unsigned long)(x) & 0x000FFFFF) << 5) | ((b) << 2))
@
@ #define HWREGBITB(x, b)                                                       \
@         HWREGB(((unsigned long)(x) & 0xF0000000) | 0x02000000 |               \
@                (((unsigned long)(x) & 0x000FFFFF) << 5) | ((b) << 2))
@
@ #define CPU_SCS_BASE                    0xE000E000 // CPU_SCS
@
@ #define CPU_SCS_O_ACTLR                 0x00000008
@ #define CPU_SCS_ACTLR_DISDEFWBUF_BITN   1
@
@ #define VIMS_BASE                       0x40034000 // VIMS
@
@ #define VIMS_O_CTL                      0x00000004
@ #define VIMS_CTL_IDCODE_LB_DIS_M        0x00000020
@ #define VIMS_CTL_SYSBUS_LB_DIS_M        0x00000010
@
@ __STATIC_INLINE void
@ CPU_WriteBufferDisable()
@ {
@     HWREGBITW( CPU_SCS_BASE + CPU_SCS_O_ACTLR, CPU_SCS_ACTLR_DISDEFWBUF_BITN ) = 1;
@ }
@
@ __STATIC_INLINE void
@ VIMSLineBufDisable()
@ {
@     HWREG(VIMS_BASE + VIMS_O_CTL) |= VIMS_CTL_IDCODE_LB_DIS_M |
@                                      VIMS_CTL_SYSBUS_LB_DIS_M;
@ }


.thumb_func
.align	2
.type	_CPU_WriteBufferDisable, %function
_CPU_WriteBufferDisable:
	ldr.n	r0, _CPU_WB_BIT_BAND_2
	movs.n	r1, #1
	movs.n	r2, #0
	str.n	r1, [r0, r2]
	bx.n	lr


.thumb_func
.align	2
.type	_VIMSLineBufDisable, %function
_VIMSLineBufDisable:
	ldr.n	r0, _VIMS_0_CTL
	ldr.n	r1, _VIMS_LB_DIS_M
	movs.n	r2, #0
	ldr.n	r3, [r0, r2]
	orrs.n	r3, r3, r1
	str.n	r3, [r0, r2]
	bx.n	lr

.align	4
@ [TI-TRM] 3.2.8 Cortex-M3 Memory Map
@ [TI-TRM] 7.9.2.2 CTL Register
_VIMS_0_CTL:		.word	0x40034004
_VIMS_LB_DIS_M:		.word	0x00000030
_CPU_WB_BIT_BAND_2:	.word	0xE21C0104
