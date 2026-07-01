import os
import shutil
import socket
import subprocess
import threading
import tempfile
import calendar
import datetime as dt
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# Optional dependency
try:
    import psutil
except ImportError:
    psutil = None

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None


APP_NAME = "Winlandhex"
REMINDERS_FILE = Path.home() / ".winlandhex_reminders.txt"
NOTES_FILE = Path.home() / ".winlandhex_notes.txt"
KEY_FILE = Path.home() / ".winlandhex_key.key"


# ----------------------------
# Helpers
# ----------------------------
def human_size(size):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def get_ip_info():
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "Unknown"
    return hostname, ip


def ping_host(host):
    param = "-n" if os.name == "nt" else "-c"
    cmd = ["ping", param, "4", host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Ping failed: {e}"


def scan_port(host, port, timeout=1.0):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def get_disk_usage():
    drives = []
    if os.name == "nt":
        if psutil:
            parts = psutil.disk_partitions(all=False)
            for p in parts:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    drives.append((p.device, p.mountpoint, usage.total, usage.used, usage.free, usage.percent))
                except Exception:
                    pass
        else:
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    total, used, free = shutil.disk_usage(drive)
                    percent = used / total * 100 if total else 0
                    drives.append((drive, drive, total, used, free, percent))
    else:
        total, used, free = shutil.disk_usage("/")
        percent = used / total * 100 if total else 0
        drives.append(("/", "/", total, used, free, percent))
    return drives


def list_processes():
    procs = []
    if psutil:
        for p in psutil.process_iter(["pid", "name", "status"]):
            try:
                info = p.info
                procs.append((info["pid"], info["name"], info.get("status", "")))
            except Exception:
                pass
    else:
        if os.name == "nt":
            out = subprocess.check_output(["tasklist"], text=True, errors="ignore")
            procs.append((0, out[:200], ""))
        else:
            out = subprocess.check_output(["ps", "-e"], text=True, errors="ignore")
            procs.append((0, out[:200], ""))
    return procs


def kill_process(pid):
    if psutil:
        p = psutil.Process(pid)
        p.terminate()
        try:
            p.wait(3)
        except Exception:
            p.kill()
    else:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"])
        else:
            subprocess.run(["kill", "-9", str(pid)])


def ensure_key():
    if not Fernet:
        return None
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return key


def encrypt_file(path):
    if not Fernet:
        raise RuntimeError("cryptography نصب نیست")
    key = ensure_key()
    f = Fernet(key)
    data = Path(path).read_bytes()
    enc = f.encrypt(data)
    out = str(path) + ".enc"
    Path(out).write_bytes(enc)
    return out


def decrypt_file(path):
    if not Fernet:
        raise RuntimeError("cryptography نصب نیست")
    key = ensure_key()
    f = Fernet(key)
    data = Path(path).read_bytes()
    dec = f.decrypt(data)
    out = str(path).removesuffix(".enc") if str(path).endswith(".enc") else str(path) + ".dec"
    Path(out).write_bytes(dec)
    return out


def search_files(root, keyword):
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            if keyword.lower() in name.lower():
                matches.append(os.path.join(dirpath, name))
    return matches


def load_notes():
    if NOTES_FILE.exists():
        return NOTES_FILE.read_text(encoding="utf-8", errors="ignore")
    return ""


def save_notes(text):
    NOTES_FILE.write_text(text, encoding="utf-8")


def load_reminders():
    if REMINDERS_FILE.exists():
        return REMINDERS_FILE.read_text(encoding="utf-8", errors="ignore")
    return ""


def save_reminders(text):
    REMINDERS_FILE.write_text(text, encoding="utf-8")


# ----------------------------
# Main App
# ----------------------------
class WinlandhexApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1100x700")
        self.minsize(1000, 650)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.create_widgets()
        self.refresh_status()

    def create_widgets(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self.title_label = ttk.Label(top, text=APP_NAME, font=("Segoe UI", 18, "bold"))
        self.title_label.pack(side="left")

        self.status_label = ttk.Label(top, text="", anchor="e")
        self.status_label.pack(side="right")

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(main, width=220)
        main.add(left, weight=1)

        right = ttk.Frame(main)
        main.add(right, weight=4)

        self.sections = tk.StringVar(value="file")

        buttons = [
            ("File Manager", "file"),
            ("Network Tools", "network"),
            ("Disk Utilities", "disk"),
            ("Process Manager", "process"),
            ("Notepad", "notes"),
            ("Calendar", "calendar"),
            ("Reminders", "reminders"),
            ("Security", "security"),
        ]

        for text, value in buttons:
            ttk.Radiobutton(left, text=text, variable=self.sections, value=value, command=self.show_section).pack(
                anchor="w", fill="x", pady=4
            )

        self.right = right
        self.section_frames = {}
        self.build_sections()
        self.show_section()

    def build_sections(self):
        self.section_frames["file"] = self.build_file_manager(self.right)
        self.section_frames["network"] = self.build_network_tools(self.right)
        self.section_frames["disk"] = self.build_disk_tools(self.right)
        self.section_frames["process"] = self.build_process_manager(self.right)
        self.section_frames["notes"] = self.build_notepad(self.right)
        self.section_frames["calendar"] = self.build_calendar(self.right)
        self.section_frames["reminders"] = self.build_reminders(self.right)
        self.section_frames["security"] = self.build_security(self.right)

    def clear_right(self):
        for child in self.right.winfo_children():
            child.pack_forget()

    def show_section(self):
        self.clear_right()
        frame = self.section_frames.get(self.sections.get())
        if frame:
            frame.pack(fill="both", expand=True)

    def refresh_status(self):
        host, ip = get_ip_info()
        self.status_label.config(text=f"{host} | {ip}")
        self.after(5000, self.refresh_status)

    # ---------------- File Manager ----------------
    def build_file_manager(self, parent):
        frame = ttk.Frame(parent, padding=10)

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x", pady=5)

        ttk.Label(path_frame, text="Path:").pack(side="left")
        self.file_path_var = tk.StringVar(value=str(Path.home()))
        ttk.Entry(path_frame, textvariable=self.file_path_var).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(path_frame, text="Browse", command=self.browse_file_path).pack(side="left")
        ttk.Button(path_frame, text="Load", command=self.load_file_list).pack(side="left", padx=5)

        action = ttk.Frame(frame)
        action.pack(fill="x", pady=5)

        ttk.Button(action, text="New Folder", command=self.create_folder).pack(side="left", padx=3)
        ttk.Button(action, text="Copy", command=self.copy_selected).pack(side="left", padx=3)
        ttk.Button(action, text="Move", command=self.move_selected).pack(side="left", padx=3)
        ttk.Button(action, text="Delete", command=self.delete_selected).pack(side="left", padx=3)
        ttk.Button(action, text="Search", command=self.search_files_ui).pack(side="left", padx=3)

        self.file_list = tk.Listbox(frame)
        self.file_list.pack(fill="both", expand=True, pady=10)

        self.load_file_list()
        return frame

    def browse_file_path(self):
        p = filedialog.askdirectory()
        if p:
            self.file_path_var.set(p)
            self.load_file_list()

    def load_file_list(self):
        self.file_list.delete(0, tk.END)
        p = Path(self.file_path_var.get())
        if not p.exists():
            messagebox.showerror("Error", "Path does not exist")
            return
        try:
            for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                suffix = "/" if item.is_dir() else ""
                self.file_list.insert(tk.END, item.name + suffix)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def selected_file_item(self):
        sel = self.file_list.curselection()
        if not sel:
            return None
        name = self.file_list.get(sel[0]).rstrip("/")
        return Path(self.file_path_var.get()) / name

    def create_folder(self):
        name = simpledialog.askstring("New Folder", "Folder name:")
        if not name:
            return
        try:
            (Path(self.file_path_var.get()) / name).mkdir(parents=True, exist_ok=True)
            self.load_file_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def copy_selected(self):
        src = self.selected_file_item()
        if not src:
            return
        dst = filedialog.askdirectory(title="Select destination")
        if not dst:
            return
        try:
            target = Path(dst) / src.name
            if src.is_dir():
                shutil.copytree(src, target)
            else:
                shutil.copy2(src, target)
            messagebox.showinfo("Done", "Copied successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def move_selected(self):
        src = self.selected_file_item()
        if not src:
            return
        dst = filedialog.askdirectory(title="Select destination")
        if not dst:
            return
        try:
            shutil.move(str(src), str(Path(dst) / src.name))
            self.load_file_list()
            messagebox.showinfo("Done", "Moved successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_selected(self):
        src = self.selected_file_item()
        if not src:
            return
        if not messagebox.askyesno("Confirm", f"Delete {src.name}?"):
            return
        try:
            if src.is_dir():
                shutil.rmtree(src)
            else:
                src.unlink()
            self.load_file_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_files_ui(self):
        root = filedialog.askdirectory(title="Search root")
        if not root:
            return
        keyword = simpledialog.askstring("Search", "Filename keyword:")
        if not keyword:
            return
        try:
            matches = search_files(root, keyword)
            win = tk.Toplevel(self)
            win.title("Search Results")
            txt = tk.Text(win, wrap="word")
            txt.pack(fill="both", expand=True)
            txt.insert("end", "\n".join(matches) if matches else "No matches found")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Network Tools ----------------
    def build_network_tools(self, parent):
        frame = ttk.Frame(parent, padding=10)

        ip_frame = ttk.LabelFrame(frame, text="IP Info", padding=10)
        ip_frame.pack(fill="x", pady=5)

        self.net_info = tk.Text(ip_frame, height=5)
        self.net_info.pack(fill="x")
        ttk.Button(ip_frame, text="Refresh IP Info", command=self.refresh_ip_info).pack(pady=5)

        ping_frame = ttk.LabelFrame(frame, text="Ping", padding=10)
        ping_frame.pack(fill="both", expand=True, pady=5)

        row = ttk.Frame(ping_frame)
        row.pack(fill="x")
        ttk.Label(row, text="Host:").pack(side="left")
        self.ping_var = tk.StringVar(value="8.8.8.8")
        ttk.Entry(row, textvariable=self.ping_var).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(row, text="Ping", command=self.do_ping).pack(side="left")

        self.ping_output = tk.Text(ping_frame, height=15)
        self.ping_output.pack(fill="both", expand=True, pady=5)

        self.refresh_ip_info()
        return frame

    def refresh_ip_info(self):
        host, ip = get_ip_info()
        self.net_info.delete("1.0", tk.END)
        self.net_info.insert(tk.END, f"Hostname: {host}\nLocal IP: {ip}\n")

    def do_ping(self):
        host = self.ping_var.get().strip()
        if not host:
            return
        self.ping_output.delete("1.0", tk.END)

        def worker():
            result = ping_host(host)
            self.ping_output.insert(tk.END, result)

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- Disk Utilities ----------------
    def build_disk_tools(self, parent):
        frame = ttk.Frame(parent, padding=10)
        ttk.Button(frame, text="Refresh Drives", command=self.refresh_drives).pack(anchor="w")

        self.disk_tree = ttk.Treeview(frame, columns=("mount", "total", "used", "free", "percent"), show="headings")
        for col, text, width in [
            ("mount", "Mount", 120),
            ("total", "Total", 120),
            ("used", "Used", 120),
            ("free", "Free", 120),
            ("percent", "Usage %", 80),
        ]:
            self.disk_tree.heading(col, text=text)
            self.disk_tree.column(col, width=width)
        self.disk_tree.pack(fill="both", expand=True, pady=10)

        ttk.Button(frame, text="Clean Temp Files", command=self.clean_temp_files).pack(anchor="w")
        self.refresh_drives()
        return frame

    def refresh_drives(self):
        for row in self.disk_tree.get_children():
            self.disk_tree.delete(row)
        for drive in get_disk_usage():
            device, mount, total, used, free, percent = drive
            self.disk_tree.insert("", "end", values=(mount, human_size(total), human_size(used), human_size(free), f"{percent:.1f}%"))

    def clean_temp_files(self):
        temp_dir = Path(tempfile.gettempdir())
        if not messagebox.askyesno("Confirm", f"Delete temp files in {temp_dir}?"):
            return
        deleted = 0
        errors = 0
        for item in temp_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                deleted += 1
            except Exception:
                errors += 1
        messagebox.showinfo("Temp Clean", f"Deleted: {deleted}\nErrors: {errors}")
        self.refresh_drives()

    # ---------------- Process Manager ----------------
    def build_process_manager(self, parent):
        frame = ttk.Frame(parent, padding=10)
        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Button(top, text="Refresh", command=self.refresh_processes).pack(side="left")
        ttk.Button(top, text="Kill Selected", command=self.kill_selected_process).pack(side="left", padx=5)

        self.proc_tree = ttk.Treeview(frame, columns=("pid", "name", "status"), show="headings")
        for col, text, width in [("pid", "PID", 80), ("name", "Name", 350), ("status", "Status", 120)]:
            self.proc_tree.heading(col, text=text)
            self.proc_tree.column(col, width=width)
        self.proc_tree.pack(fill="both", expand=True, pady=10)
        self.refresh_processes()
        return frame

    def refresh_processes(self):
        for row in self.proc_tree.get_children():
            self.proc_tree.delete(row)
        if not psutil:
            self.proc_tree.insert("", "end", values=("", "psutil not installed", ""))
            return
        for pid, name, status in list_processes():
            self.proc_tree.insert("", "end", values=(pid, name, status))

    def kill_selected_process(self):
        if not psutil:
            messagebox.showerror("Error", "psutil not installed")
            return
        sel = self.proc_tree.selection()
        if not sel:
            return
        pid = int(self.proc_tree.item(sel[0], "values")[0])
        if not messagebox.askyesno("Confirm", f"Kill PID {pid}?"):
            return
        try:
            kill_process(pid)
            self.refresh_processes()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Notepad ----------------
    def build_notepad(self, parent):
        frame = ttk.Frame(parent, padding=10)
        btns = ttk.Frame(frame)
        btns.pack(fill="x")
        ttk.Button(btns, text="Load", command=self.load_note).pack(side="left")
        ttk.Button(btns, text="Save", command=self.save_note).pack(side="left", padx=5)

        self.note_text = tk.Text(frame, wrap="word")
        self.note_text.pack(fill="both", expand=True, pady=10)
        self.note_text.insert("end", load_notes())
        return frame

    def load_note(self):
        self.note_text.delete("1.0", tk.END)
        self.note_text.insert("end", load_notes())

    def save_note(self):
        save_notes(self.note_text.get("1.0", tk.END))
        messagebox.showinfo("Saved", "Note saved")

    # ---------------- Calendar ----------------
    def build_calendar(self, parent):
        frame = ttk.Frame(parent, padding=10)
        now = dt.date.today()
        self.cal_year = tk.IntVar(value=now.year)
        self.cal_month = tk.IntVar(value=now.month)

        top = ttk.Frame(frame)
        top.pack(fill="x")

        ttk.Spinbox(top, from_=1970, to=2100, textvariable=self.cal_year, width=8, command=self.update_calendar_text).pack(side="left")
        ttk.Spinbox(top, from_=1, to=12, textvariable=self.cal_month, width=5, command=self.update_calendar_text).pack(side="left", padx=5)
        ttk.Button(top, text="Show", command=self.update_calendar_text).pack(side="left")

        self.cal_text = tk.Text(frame, height=20)
        self.cal_text.pack(fill="both", expand=True, pady=10)
        self.update_calendar_text()
        return frame

    def update_calendar_text(self):
        y = self.cal_year.get()
        m = self.cal_month.get()
        self.cal_text.delete("1.0", tk.END)
        self.cal_text.insert(tk.END, calendar.month(y, m))

    # ---------------- Reminders ----------------
    def build_reminders(self, parent):
        frame = ttk.Frame(parent, padding=10)

        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Button(top, text="Add Reminder", command=self.add_reminder).pack(side="left")
        ttk.Button(top, text="Reload", command=self.load_reminder_text).pack(side="left", padx=5)
        ttk.Button(top, text="Save", command=self.save_reminder_text).pack(side="left", padx=5)

        self.reminder_text = tk.Text(frame, wrap="word")
        self.reminder_text.pack(fill="both", expand=True, pady=10)
        self.reminder_text.insert("end", load_reminders())
        return frame

    def add_reminder(self):
        text = simpledialog.askstring("Reminder", "Reminder text:")
        if not text:
            return
        when = simpledialog.askstring("Reminder", "Date/time (free text):")
        if not when:
            return
        current = self.reminder_text.get("1.0", tk.END)
        self.reminder_text.delete("1.0", tk.END)
        self.reminder_text.insert("end", current.rstrip() + f"\n[{when}] {text}\n")

    def load_reminder_text(self):
        self.reminder_text.delete("1.0", tk.END)
        self.reminder_text.insert("end", load_reminders())

    def save_reminder_text(self):
        save_reminders(self.reminder_text.get("1.0", tk.END))
        messagebox.showinfo("Saved", "Reminders saved")

    # ---------------- Security ----------------
    def build_security(self, parent):
        frame = ttk.Frame(parent, padding=10)
        ttk.Label(frame, text="File Encryption / Decryption").pack(anchor="w", pady=5)

        ttk.Button(frame, text="Encrypt File", command=self.encrypt_ui).pack(anchor="w", pady=3)
        ttk.Button(frame, text="Decrypt File", command=self.decrypt_ui).pack(anchor="w", pady=3)

        self.security_log = tk.Text(frame, height=18)
        self.security_log.pack(fill="both", expand=True, pady=10)
        self.log_security("Ready.")
        if not Fernet:
            self.log_security("cryptography not installed. Encryption disabled.")
        return frame

    def log_security(self, msg):
        self.security_log.insert(tk.END, msg + "\n")
        self.security_log.see(tk.END)

    def encrypt_ui(self):
        try:
            path = filedialog.askopenfilename()
            if not path:
                return
            out = encrypt_file(path)
            self.log_security(f"Encrypted: {out}")
            messagebox.showinfo("Success", out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def decrypt_ui(self):
        try:
            path = filedialog.askopenfilename(filetypes=[("Encrypted files", "*.enc"), ("All files", "*.*")])
            if not path:
                return
            out = decrypt_file(path)
            self.log_security(f"Decrypted: {out}")
            messagebox.showinfo("Success", out)
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = WinlandhexApp()
    app.mainloop()
