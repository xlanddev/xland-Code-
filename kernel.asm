[BITS 16]
[ORG 0x8000]

start:

    ; فعال کردن گرافیک 320x200x256
    mov ax, 0x0013
    int 0x10

    ; اشاره به حافظه ویدیو
    mov ax, 0xA000
    mov es, ax
    xor di, di

    ; ==================
    ; پس‌زمینه آبی
    ; ==================
    mov cx, 64000
    mov al, 1
fill_bg:
    stosb
    loop fill_bg

    ; ==================
    ; تسکبار مشکی پایین
    ; ==================
    mov di, 320*180
    mov cx, 320*20
    mov al, 0
fill_taskbar:
    stosb
    loop fill_taskbar

    ; ==================
    ; دکمه Start سبز (50x10)
    ; ==================
    mov di, 320*185 + 10   ; موقعیت شروع
    mov bx, 50             ; عرض
    mov dx, 10             ; ارتفاع

draw_row:
    push dx
    mov cx, bx
    mov al, 2              ; رنگ سبز

draw_pixel:
    stosb
    loop draw_pixel

    ; رفتن به ابتدای ردیف بعدی (320 - عرض)
    add di, 320-50

    pop dx
    dec dx
    jnz draw_row

hang:
    jmp hang

times 2048-($-$$) db 0