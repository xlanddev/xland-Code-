import tkinter as tk
import winsound
import threading
import time
import sys

def play_crash_sound():
    winsound.Beep(900, 200)
    winsound.Beep(700, 200)
    winsound.Beep(500, 400)

def close_app(event=None):
    root.destroy()
    sys.exit()

def update_dump():
    percent = 0
    while percent <= 100:
        dump_label.config(text=f"Dumping physical memory to disk: {percent}%")
        root.update()
        time.sleep(0.04)
        percent += 1

    dump_label.config(text="Physical memory dump complete.")
    status_label.config(text="System halted. Press ESC to restart.")

root = tk.Tk()
root.attributes("-fullscreen", True)
root.configure(bg="#0000AA")
root.bind("<Escape>", close_app)

# مخفی کردن موس (نمایشی)
root.config(cursor="none")

main_text = """
A problem has been detected and Windows has been shut down
to prevent damage to your computer.

The problem seems to be caused by the following file:
WINLAND_KERNEL.SYS

PAGE_FAULT_IN_NONPAGED_AREA

If this is the first time you've seen this Stop error screen,
restart your computer. If this screen appears again, follow
these steps:

Check to make sure any new hardware or software is properly installed.
If problems continue, disable or remove any newly installed hardware
or software. Disable BIOS memory options such as caching or shadowing.

Technical information:

*** STOP: 0x0000008E (0xC0000005,0xBF8A9A20,0xF78D2524,0x00000000)

Beginning dump of physical memory
"""

label = tk.Label(
    root,
    text=main_text,
    fg="white",
    bg="#0000AA",
    font=("Courier", 20),
    justify="left"
)
label.pack(pady=80)

dump_label = tk.Label(
    root,
    text="",
    fg="white",
    bg="#0000AA",
    font=("Courier", 20),
    justify="left"
)
dump_label.pack()

status_label = tk.Label(
    root,
    text="",
    fg="white",
    bg="#0000AA",
    font=("Courier", 20),
    justify="left"
)
status_label.pack(pady=20)

threading.Thread(target=play_crash_sound).start()
threading.Thread(target=update_dump).start()

root.mainloop()