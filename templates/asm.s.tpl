{% block before %}{% endblock %}

{% set saved_regs = ['r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11', 'r12', 'r14'] %}

{% block attributes %}
	.cpu cortex-m3
	.eabi_attribute 20, 1
	.eabi_attribute 21, 1
	.eabi_attribute 23, 3
	.eabi_attribute 24, 1
	.eabi_attribute 25, 1
	.eabi_attribute 26, 1
	.eabi_attribute 30, 4
	.eabi_attribute 34, 1
	.eabi_attribute 18, 4
	.align	1
	.global	benchmarkCode
	.syntax unified
	.thumb
	.thumb_func
	.fpu softvfp
	.type	benchmarkCode, %function
	{% block additionalAttributes %}{% endblock %}
{% endblock %}
benchmarkCode:
	{% block outerCode %}

	movs.n r2, #0
	@ save {r4 - r12, r14} to memory
	{% for reg in saved_regs %}
	ldr.w	r1, ={{reg}}_val
	str.w	{{reg}}, [r1, r2]
	{% endfor %}

	@ init counter for values saved to times and results array
	@ high 16 bits - times array
	@ low 16 bits - results array
	{{initCounter(r10)}}

	{% block code %}{% endblock %}
	
	{{saveCounterToResReg()}}

	movs.n r2, #0
	@ restore {r4 - r12, r14} from memory
	{% for reg in saved_regs %}
	ldr.w	r1, ={{reg}}_val
	ldr.w	{{reg}}, [r1, r2]
	{% endfor %}

	bx.n		lr

	{% endblock %}
.size	benchmarkCode, .-benchmarkCode

.align	4
results_mask:		.word 0x0000FFFF
dwt:			.word 0xe0001000

{% block after %}{% endblock %}

{{section('sram')}}

.align	4
{% for reg in saved_regs %}
{{reg}}_val:		.word 0x00000000
{% endfor %}
