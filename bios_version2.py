import tkinter as tk
import time
from tkinter import simpledialog, messagebox
import os
from datetime import datetime

# ================= GLOBAL EXIT =================
def full_exit(event=None):
    root.destroy()

# ================= BIOS SIMULATOR =================
BIOS_VERSION_FILE = "bios_version.txt"
BIOS_CODE_FILE = "BIOS_code.txt"
BACKUP_FILE = "bios_backup.txt"

# ---------- Version Functions ----------
def ensure_version_file():
    if not os.path.exists(BIOS_VERSION_FILE):
        with open(BIOS_VERSION_FILE, "w") as f:
            f.write("1.9")  # نسخه اولیه
    if not os.path.exists(BIOS_CODE_FILE):
        with open(BIOS_CODE_FILE, "w") as f:
            f.write("2.8")  # نسخه آپدیت برای تست

def get_current_version():
    ensure_version_file()
    with open(BIOS_VERSION_FILE, "r") as f:
        return f.read().strip()

def get_update_code():
    if not os.path.exists(BIOS_CODE_FILE):
        return None
    with open(BIOS_CODE_FILE, "r") as f:
        return f.read().strip()

def set_new_version(v):
    with open(BIOS_VERSION_FILE, "w") as f:
        f.write(v)

def backup_version():
    with open(BACKUP_FILE, "w") as f:
        f.write(get_current_version())

def restore_backup():
    if os.path.exists(BACKUP_FILE):
        with open(BACKUP_FILE, "r") as f:
            set_new_version(f.read().strip())

# ---------- BIOS Manager ----------
class BIOSManager:
    def __init__(self):
        self.logs = []

    def log(self, message):
        self.logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")

    def show_logs(self):
        manager_window = tk.Toplevel(root)
        manager_window.title("BIOS Manager")
        manager_window.geometry("500x300")
        manager_window.configure(bg="black")
        tk.Label(manager_window, text="BIOS Manager Log", fg="white", bg="black", font=("Courier", 18)).pack()
        log_text = tk.Text(manager_window, fg="white", bg="black", font=("Courier", 12))
        log_text.pack(expand=True, fill="both")
        log_text.insert("end", "\n".join(self.logs))
        log_text.see("end")
        tk.Button(manager_window, text="Close", command=manager_window.destroy).pack(pady=5)

manager = BIOSManager()

# ---------- BIOS Simulator ----------
def launch_bios(computer_name="WINLAND-PC"):
    global root
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="#24058A")
    root.config(cursor="none")

    root.bind("<Escape>", full_exit)

    # ===== POST Screen =====
    post = tk.Label(root, text="Press DEL to enter setup...", fg="white", bg="#060697", font=("Courier", 24))
    post.pack(expand=True)
    root.update()
    time.sleep(2)
    post.config(text="Loading Winland BIOS version 2...")
    root.update()
    time.sleep(1)
    post.pack_forget()
    manager.log("POST Screen displayed")

    # ===== BIOS Menu =====
    menus = {
        "Main": ["System Time", "System Date", "System Info", "Advanced", "Boot", "BIOS Update", "Reset BIOS", "BIOS Manager", "Exit"],
        "Advanced": ["CPU Settings", "Memory Settings", "Peripheral Configuration", "Back"],
        "Boot": ["Hard Drive", "CD-ROM", "USB Device", "Back"],
        "System Info": ["Back"],
        "BIOS Update": ["Back"],
        "Reset BIOS": ["Back"],
        "BIOS Manager": ["Back"]

    }

    current_menu = "Main"
    selected_index = 0

    top_label = tk.Label(root, text="   Main    Advanced  winland  Boot    Exit   ", fg="white", bg="#4B0082", font=("Courier", 18, "bold"))
    top_label.pack(fill="x")

    label = tk.Label(root, text="", fg="white", bg="#490080", font=("Courier", 20), justify="left", anchor="nw")
    label.pack(padx=50, pady=50, anchor="nw")

    # نسخه پایین صفحه
    version_label = tk.Label(root, text=f"BIOS Version: {get_current_version()}", fg="white", bg="#4F0080", font=("Courier", 16))
    version_label.pack(side="bottom", pady=5)





    # ساعت پایین صفحه
    clock_label = tk.Label(root, fg="white", bg="#4D0080", font=("Courier", 16))
    clock_label.pack(side="bottom", pady=2)

    def update_clock():
        clock_label.config(text=f"Time: {datetime.now().strftime('%H:%M:%S')}")
        root.after(1000, update_clock)

    update_clock()

    help_label = tk.Label(root, text="↑ ↓ Move  Enter Select  F10 Save & Exit  ESC Exit", fg="white", bg="#000080", font=("Courier", 16))
    help_label.pack(side="bottom", pady=10)

    # System Info فیک
    system_info = {
        "CPU": "Intel Core i9-9900K",
        "RAM": "32 GB DDR4",
        "Motherboard": "Winland Prime X99",
        "BIOS Version": get_current_version(),
        "GPU": "NVIDIA RTX 3090",
        "Storage": "1 TB SSD + 2 TB HDD"
    }

    # ---------- Error & Boot ----------
    def show_black_error(error_code):
        root.destroy()
        error = tk.Tk()
        error.attributes("-fullscreen", True)
        error.configure(bg="black")
        error.bind("<Escape>", lambda e: error.destroy())
        tk.Label(error, text=f"CRITICAL ERROR!\nCode: {error_code}", fg="red", bg="black", font=("Courier", 30)).pack(expand=True)
        manager.log(f"CRITICAL ERROR triggered: {error_code}")
        error.mainloop()

    def boot_priority_prompt(device):
        choice = tk.Tk()
        choice.title(f"Set {device} Priority")
        choice.geometry("300x150")
        tk.Label(choice, text=f"Do you want to set {device} as first boot device?").pack(pady=20)
        def yes():
            manager.log(f"{device} set as first boot device ")
            choice.destroy()
        def no():
            choice.destroy()
        tk.Button(choice, text="Yes", command=yes).pack(side="left", padx=20)
        tk.Button(choice, text="No", command=no).pack(side="right", padx=20)
        choice.mainloop()

    # ---------- Reset BIOS ----------
    def reset_bios():
        restore_backup()
        root.destroy()
        error = tk.Tk()
        error.attributes("-fullscreen", True)
        error.configure(bg="black")
        error.bind("<Escape>", lambda e: error.destroy())
        tk.Label(error, text="000x0000 jamp kernel error pc no boot\nCODE: 000x00100" \
        "", fg="red", bg="black", font=("Courier", 28)).pack(expand=True)
        error.update()
        time.sleep(3)
        error.destroy()
        manager.log("BIOS reset performed")
        computer_name_new = simpledialog.askstring("Reset BIOS", "Enter computer name:", initialvalue=computer_name)
        launch_bios(computer_name_new)

    # ---------- BIOS Update ----------
    def update_bios():
        backup_version()  # ذخیره نسخه قبل از آپدیت
        current = get_current_version()
        new_code = get_update_code()
        if not new_code:
            messagebox.showinfo("BIOS Update", "No update available.")
            manager.log("BIOS update check: No update available")
            return

        # چک اینکه نسخه جدیدتر باشه
        if tuple(map(int,new_code.split("."))) <= tuple(map(int,current.split("."))):
            messagebox.showinfo("BIOS Update", "Your BIOS is already up to date.")
            manager.log("BIOS update check: Already up to date")
            return

        # -------- لودینگ نصب ابدیت --------
        loader = tk.Toplevel(root)
        loader.attributes("-fullscreen", True)
        loader.configure(bg="black")
        loader.bind("<Escape>", lambda e: loader.destroy())
        tk.Label(loader, text=f"Installing BIOS Update for pc {new_code}...", fg="white", bg="black", font=("Courier", 28)).pack(pady=50)
        progress_label = tk.Label(loader, text="0%", fg="white", bg="black", font=("Courier", 24))
        progress_label.pack()
        for i in range(101):
            progress_label.config(text=f"{i}%")
            loader.update()
            time.sleep(0.05)

        # -------- اعمال تغییرات از BIOS_code.txt --------
        try:
            exec(new_code)
            manager.log(f"Applied update code: {new_code}")
        except Exception as e:
            print("Error in update code:", e)
            manager.log(f"Error in update code: {e}")

        # اعمال نسخه جدید
        set_new_version(new_code)
        system_info["BIOS Version"] = new_code
        version_label.config(text=f"BIOS Version: {new_code}")
        loader.destroy()

        # ریستارت شبیه‌سازی بعد از آپدیت
        root.destroy()
        messagebox.showinfo("Update Complete", f"BIOS Updated to {new_code}")
        manager.log(f"BIOS successfully updated to {new_code}")
        launch_bios(computer_name)

    # ---------- Draw Menu ----------
    def draw_menu():
        text = f"\nCurrent Menu: {current_menu}\n\n"
        if current_menu == "System Info":
            for k, v in system_info.items():
                text += f"{k}: {v}\n"
            text += "\n   Back\n"
        elif current_menu == "BIOS Update":
            current = get_current_version()
            text += f"Current Version: {current}\n"
            new_code = get_update_code()
            if new_code and tuple(map(int,new_code.split("."))) > tuple(map(int,current.split("."))):
                text += f"New Update Available: {new_code}\n"
                if selected_index == 0:
                    text += ">> Install Update\n"
                else:
                    text += "   Install Update\n"
              
            else:
                text += "No update available\n"
            text += "\n   Back\n"
        elif current_menu == "BIOS Manager":
            text += "View BIOS Activity Logs\n\n"
            if selected_index == 0:
                text += ">> Show Logs\n"
            else:
                text += "   Show Logs\n"
            text += "\n   Back\n"
        elif current_menu == "Reset BIOS":
            text += "Warning: Use Reset BIOS only if needed\n\n   Back\n"
        else:
            for i, option in enumerate(menus[current_menu]):
                prefix = ">> " if i == selected_index else "   "
                text += f"{prefix}{option}\n"
        label.config(text=text)

    # ---------- Navigation ----------
    def move_up(event):
        nonlocal selected_index
        selected_index = (selected_index - 1) % len(menus.get(current_menu, []))
        draw_menu()

    def move_down(event):
        nonlocal selected_index
        selected_index = (selected_index + 1) % len(menus.get(current_menu, []))
        draw_menu()

    def select_option(event):
        nonlocal current_menu, selected_index
        if current_menu in ["System Info", "BIOS Update", "Reset BIOS", "BIOS Manager"]:
            if current_menu == "BIOS Update":
                new_code = get_update_code()
                current = get_current_version()
                if new_code and tuple(map(int,new_code.split("."))) > tuple(map(int,current.split("."))):
                    if selected_index == 0:  # Install Update
                        update_bios()
                        return
                current_menu = "Main"
                selected_index = 0
            elif current_menu == "Reset BIOS":
                reset_bios()
                return
            elif current_menu == "BIOS Manager":
                if selected_index == 0:  # Show Logs
                    manager.show_logs()
                    return
                current_menu = "Main"
                selected_index = 0
            else:
                current_menu = "Main"
                selected_index = 0
        else:
            choice = menus[current_menu][selected_index]
            if choice == "Back":
                current_menu = "Main"
                selected_index = 0
            elif choice in menus:
                current_menu = choice
                selected_index = 0
            elif current_menu == "Boot":
                if choice == "Hard Drive":
                    show_black_error("00000x000000")
                elif choice in ["CD-ROM", "USB Device"]:
                    boot_priority_prompt(choice)
        draw_menu()

    root.bind("<Up>", move_up)
    root.bind("<Down>", move_down)
    root.bind("<Return>", select_option)
    root.bind("<F10>", full_exit)

    draw_menu()
    root.mainloop()

# ================= START =================
launch_bios()