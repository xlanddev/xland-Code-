[BITS 16]
[ORG 0x7C00]

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    sti

    mov ah, 0x0E
    mov al, 'B'
    int 0x10

    mov [BOOT_DRIVE], dl

    ; لود کرنل به 0x8000
    mov ah, 0x02
    mov al, 4
    mov ch, 0
    mov cl, 2
    mov dh, 0
    mov dl, [BOOT_DRIVE]

    mov bx, 0x8000
    int 0x13
    jc disk_error

    jmp 0x8000

disk_error:
    mov ah, 0x0E
    mov al, 'E'
    int 0x10
    jmp $

BOOT_DRIVE db 0

times 510-($-$$) db 0
dw 0xAA55