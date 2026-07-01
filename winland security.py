import sys
import os
import ctypes
import psutil
import subprocess
import platform
import traceback
import webbrowser
import urllib.parse
import time
import hashlib
import shutil
import re
import json
from collections import defaultdict

try:
    import wmi
except Exception:
    wmi = None

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QStackedWidget,
    QMessageBox, QFileDialog, QLineEdit, QProgressBar,
    QListWidgetItem, QDialog, QDialogButtonBox, QStatusBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QTreeWidget, QTreeWidgetItem, QMenu, QTabWidget, QTextEdit
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QPoint

# =========================
# Constants
# =========================
APP_NAME = "Winland Security"
QUARANTINE_FOLDER = "Quarantine"

VIRUS_HASHES = {
    "eicar_test_file": "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f",
    "sample_malware_1": "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890",
    "suspicious_script_01": "f0e1d2c3b4a59687f0e1d2c3b4a59687f0e1d2c3b4a59687f0e1d2c3b4a59687",
}

SIMPLE_SIGNATURES = [
    "X5O!P%@AP[4\\PZX54(P^^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
]

# =========================
# Admin Utilities
# =========================
def is_windows():
    return platform.system().lower() == "windows"

def is_admin():
    if not is_windows():
        return True
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def build_admin_params():
    script = os.path.abspath(sys.argv[0])
    params = f'"{script}"'
    if len(sys.argv) > 1:
        extra = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        params += " " + extra
    return sys.executable, params

def relaunch_as_admin():
    if not is_windows():
        return True
    if is_admin():
        return True
    try:
        executable, params = build_admin_params()
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
        return rc > 32
    except Exception as e:
        print(f"Error relaunching as admin: {e}")
        return False

# =========================
# Utility Functions
# =========================
def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None

def create_quarantine_folder():
    if not os.path.exists(QUARANTINE_FOLDER):
        try:
            os.makedirs(QUARANTINE_FOLDER)
        except Exception:
            pass

def safe_text(value):
    try:
        return "" if value is None else str(value)
    except Exception:
        return ""

def extract_version_from_text(text):
    if not text:
        return ""
    m = re.search(r"(\d+\.\d+(?:\.\d+)*(?:\.\d+)?)", str(text))
    return m.group(1) if m else ""

def classify_device(class_name="", name="", caption=""):
    blob = f"{class_name} {name} {caption}".lower()
    if any(k in blob for k in ["net", "wifi", "wireless", "ethernet", "lan", "wan", "adapter"]):
        return "Network"
    if any(k in blob for k in ["audio", "sound", "speaker", "microphone", "mic", "realtek", "hd audio"]):
        return "Audio"
    if any(k in blob for k in ["gpu", "graphics", "nvidia", "amd", "radeon", "intel(r) uhd", "display"]):
        return "GPU"
    return "Other"

def format_bytes(n):
    try:
        n = float(n)
    except Exception:
        return ""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

# =========================
# Sidebar
# =========================
class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.drive_btn = QPushButton("Drive Manager")
        self.network_btn = QPushButton("Network Control")
        self.files_btn = QPushButton("File Operations")
        self.system_btn = QPushButton("System Control")
        self.antivirus_btn = QPushButton("Antivirus")
        self.google_search_btn = QPushButton("Google Search")
        self.drivers_btn = QPushButton("Driver Status")
        self.task_manager_btn = QPushButton("Task Manager")
        self.system_info_btn = QPushButton("System Info")

        for b in [
            self.drive_btn, self.network_btn, self.files_btn, self.system_btn,
            self.antivirus_btn, self.google_search_btn, self.drivers_btn,
            self.task_manager_btn, self.system_info_btn
        ]:
            self.layout.addWidget(b)

        self.layout.addStretch()

# =========================
# Existing widgets
# =========================
class DriveManager(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.drives_list = QListWidget()
        self.drives_list.setFixedHeight(150)
        self.drives_list.itemDoubleClicked.connect(self.open_drive)
        layout.addWidget(self.drives_list)
        self.contents_list = QListWidget()
        layout.addWidget(self.contents_list)
        refresh_btn = QPushButton("Refresh Drives")
        refresh_btn.clicked.connect(self.load_drives)
        layout.addWidget(refresh_btn)
        self.load_drives()

    def load_drives(self):
        self.drives_list.clear()
        self.contents_list.clear()
        try:
            partitions = psutil.disk_partitions(all=False)
            seen = set()
            for p in partitions:
                drive_path = p.device
                if drive_path and drive_path not in seen:
                    seen.add(drive_path)
                    self.drives_list.addItem(QListWidgetItem(drive_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load drives:\n{e}")

    def open_drive(self, item):
        drive = item.text()
        self.contents_list.clear()
        try:
            if not os.path.exists(drive):
                QMessageBox.warning(self, "Warning", f"Drive not accessible:\n{drive}")
                return
            entries = os.listdir(drive)
            for entry in entries:
                full_path = os.path.join(drive, entry)
                self.contents_list.addItem(f"[DIR] {entry}" if os.path.isdir(full_path) else entry)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class NetworkControl(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.input = QLineEdit()
        self.input.setPlaceholderText("example: google.com")
        layout.addWidget(self.input)
        btn = QPushButton("Ping")
        btn.clicked.connect(self.ping)
        layout.addWidget(btn)
        self.result = QLabel("Result here...")
        self.result.setWordWrap(True)
        layout.addWidget(self.result)

    def ping(self):
        host = self.input.text().strip()
        if not host:
            self.result.setText("Please enter a host.")
            return
        cmd = ["ping", "-n", "4", host] if platform.system() == "Windows" else ["ping", "-c", "4", host]
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, encoding="utf-8", errors="ignore")
            self.result.setText(out)
        except Exception as e:
            self.result.setText(str(e))

class FileOperations(QWidget):
    def __init__(self):
        super().__init__()
        self.current_dir = os.getcwd()
        layout = QVBoxLayout(self)
        self.path_label = QLabel(self.current_dir)
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse)
        layout.addWidget(browse_btn)
        self.input = QLineEdit()
        self.input.setPlaceholderText("File/Folder name")
        layout.addWidget(self.input)
        create_file_btn = QPushButton("Create File")
        create_folder_btn = QPushButton("Create Folder")
        create_file_btn.clicked.connect(self.create_file)
        create_folder_btn.clicked.connect(self.create_folder)
        layout.addWidget(create_file_btn)
        layout.addWidget(create_folder_btn)

    def browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.current_dir = folder
            self.path_label.setText(folder)

    def create_file(self):
        name = self.input.text().strip()
        if not name:
            return
        try:
            path = os.path.join(self.current_dir, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write("Created by Winland Security")
            QMessageBox.information(self, "Success", f"File created:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def create_folder(self):
        name = self.input.text().strip()
        if not name:
            return
        try:
            path = os.path.join(self.current_dir, name)
            os.makedirs(path, exist_ok=True)
            QMessageBox.information(self, "Success", f"Folder created:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class SystemControl(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        shutdown_btn = QPushButton("Shutdown")
        restart_btn = QPushButton("Restart")
        shutdown_btn.clicked.connect(self.shutdown)
        restart_btn.clicked.connect(self.restart)
        layout.addWidget(shutdown_btn)
        layout.addWidget(restart_btn)
        layout.addStretch()

    def shutdown(self):
        if QMessageBox.question(self, "Confirm Shutdown", "Are you sure?") == QMessageBox.StandardButton.Yes:
            subprocess.run(["shutdown", "/s", "/t", "1"], shell=False)

    def restart(self):
        if QMessageBox.question(self, "Confirm Restart", "Are you sure?") == QMessageBox.StandardButton.Yes:
            subprocess.run(["shutdown", "/r", "/t", "1"], shell=False)

class GoogleSearchWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter your search query...")
        self.search_input.returnPressed.connect(self.perform_search)
        layout.addWidget(self.search_input)
        search_button = QPushButton("Search Google")
        search_button.clicked.connect(self.perform_search)
        layout.addWidget(search_button)

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
        self.search_input.clear()

# =========================
# Driver Status Widget
# =========================
class DriverStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Network", "Audio", "GPU", "Other"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_drivers)
        top_bar.addWidget(QLabel("Category:"))
        top_bar.addWidget(self.filter_combo)
        top_bar.addWidget(refresh_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Driver Name", "Version", "Status", "Manufacturer", "Device/Class", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.info_label = QLabel("Ready.")
        layout.addWidget(self.info_label)
        self._all_rows = []
        self.load_drivers()

    def load_drivers(self):
        self._all_rows = []
        self.table.setRowCount(0)
        self.info_label.setText("Loading drivers...")
        QApplication.processEvents() # Update UI
        try:
            if platform.system().lower() == "windows" and wmi is not None:
                c = wmi.WMI()
                for d in c.Win32_SystemDriver():
                    name = safe_text(d.DisplayName or d.Name)
                    version = safe_text(getattr(d, "Version", ""))
                    status = safe_text(d.State or d.Status or "")
                    manufacturer = safe_text(d.ServiceType or d.StartMode) # Corrected attribute
                    device_class = safe_text(d.PathName or d.Name or "")
                    dtype = classify_device(device_class, name, "")
                    self._all_rows.append([name, version, status, manufacturer, device_class, dtype])
            else:
                self.info_label.setText("Windows + WMI recommended for full driver info.")
                return
            self.apply_filter()
            self.info_label.setText(f"Loaded {len(self._all_rows)} drivers.")
        except Exception as e:
            self.info_label.setText(str(e))

    def apply_filter(self):
        selected = self.filter_combo.currentText()
        rows = self._all_rows if selected == "All" else [r for r in self._all_rows if r[5] == selected]
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(value))

# =========================
# System Info Tab
# =========================
class SystemInfoWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_info)
        layout.addWidget(refresh_btn)

        self.refresh_info()

    def refresh_info(self):
        try:
            # Use interval=None for immediate, non-blocking reads
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            boot = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.boot_time()))
            text = f"""System Information

OS: {platform.system()} {platform.release()} {platform.version()}
Machine: {platform.machine()}
Processor: {platform.processor()}

CPU Usage: {cpu:.1f}%
RAM Usage: {ram.percent:.1f}% ({format_bytes(ram.used)} / {format_bytes(ram.total)})
Disk Usage: {disk.percent:.1f}% ({format_bytes(disk.used)} / {format_bytes(disk.total)})

Boot Time: {boot}
Python: {platform.python_version()}
"""
            self.text.setPlainText(text)
        except Exception as e:
            self.text.setPlainText(str(e))

# =========================
# Task Manager Widget
# =========================
class TaskManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter processes...")
        self.search.textChanged.connect(self.filter_tree)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.rebuild_tree) # Rebuilds the full tree

        top.addWidget(QLabel("Filter:"))
        top.addWidget(self.search)
        top.addWidget(refresh_btn)
        top.addStretch()
        layout.addLayout(top)

        self.cpu_label = QLabel("CPU: 0%")
        self.ram_label = QLabel("RAM: 0%")
        stats = QHBoxLayout()
        stats.addWidget(self.cpu_label)
        stats.addWidget(self.ram_label)
        stats.addStretch()
        layout.addLayout(stats)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(8)
        self.tree.setHeaderLabels(["Name", "PID", "CPU %", "RAM %", "Threads", "Handles", "Status", "Path"])
        self.tree.setSortingEnabled(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tree)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_live_stats) # Only updates CPU/RAM labels
        self.timer.start(2000) # Update labels every 2 seconds

        self.all_processes_data = {} # Stores detailed info for filtering/sorting
        self.process_tree_cache = {} # Cache for parent-child relationships to prevent cycles
        self.rebuild_tree() # Initial full load

    def update_live_stats(self):
        """Updates only the CPU and RAM labels with live data."""
        try:
            self.cpu_label.setText(f"CPU: {psutil.cpu_percent(interval=None):.1f}%")
            self.ram_label.setText(f"RAM: {psutil.virtual_memory().percent:.1f}%")
        except Exception:
            pass # Ignore errors during rapid updates

    def rebuild_tree(self):
        """Clears and rebuilds the entire process tree with fresh data. Call this for a full refresh."""
        self.tree.clear()
        self.all_processes_data.clear()
        self.process_tree_cache.clear() # Clear cache on rebuild
        self.load_all_process_data()
        self.populate_tree()
        self.tree.expandToDepth(1)
        # After rebuild, apply current filter if any
        self.filter_tree()

    def load_all_process_data(self):
        """Loads all process information into a dictionary for efficient access."""
        self.all_processes_data.clear() # Ensure it's clear before repopulating
        for p in psutil.process_iter(['pid', 'name', 'status', 'exe', 'num_threads', 'memory_percent', 'cpu_percent']):
            try:
                # Accessing ppid() and num_handles() can be slow or raise exceptions
                # so we fetch them carefully.
                ppid = p.ppid() if hasattr(p, 'ppid') else 0
                try:
                    handles = p.num_handles() if hasattr(p, "num_handles") else 0
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    handles = 0
                
                proc_info = {
                    'pid': p.pid,
                    'ppid': ppid,
                    'name': safe_text(p.name()),
                    'status': safe_text(p.status()),
                    'exe': safe_text(p.exe() if p.pid != 0 else ""), # Avoid error for PID 0
                    'num_threads': p.num_threads(),
                    'memory_percent': p.memory_percent(),
                    # Use interval=None for immediate, non-blocking read
                    'cpu_percent': p.cpu_percent(interval=None),
                    'handles': handles
                }
                self.all_processes_data[p.pid] = proc_info
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass # Process might have ended or access denied, just skip it.

    def populate_tree(self):
        """Populates the QTreeWidget using the data from all_processes_data, handling cycles."""
        children_map = defaultdict(list)
        for pid, data in self.all_processes_data.items():
            children_map[data['ppid']].append(pid)

        # Keep track of visited nodes during tree construction to detect cycles
        visited_in_path = set()

        def add_node(pid, parent_item=None):
            if pid in visited_in_path:
                # Cycle detected! Mark this item and stop recursion down this path
                if parent_item:
                    # Try to indicate the cycle, e.g., by changing text or color,
                    # but for simplicity, we'll just stop adding children.
                    # A more robust solution might involve special node types or logging.
                    pass # Do not add children if a cycle is detected
                return False # Indicate failure to add node

            data = self.all_processes_data.get(pid)
            if not data:
                return False # Process data not found

            # Add PID to the current path
            visited_in_path.add(pid)
            
            item = QTreeWidgetItem([
                data['name'], str(data['pid']), f"{data['cpu_percent']:.1f}",
                f"{data['memory_percent']:.1f}", str(data['num_threads']),
                str(data['handles']), data['status'], data['exe']
            ])

            # Store pid with the item for context menu access
            item.setData(0, Qt.ItemDataRole.UserRole, pid)

            if parent_item is None:
                self.tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)

            # Recursively add children, but only if no cycle detected for this path
            if pid in self.all_processes_data: # Check if data exists before accessing children_map
                for child_pid in sorted(children_map.get(pid, [])):
                    # Pass a copy of visited_in_path to children to maintain path context
                    # This is incorrect for cycle detection; visited_in_path should be managed per-path
                    # The current `visited_in_path` logic correctly tracks the *current* path.
                    add_node(child_pid, item)
            
            # Remove PID from the current path as we backtrack
            visited_in_path.remove(pid)
            return True

        # Find root processes (those whose PPID is not in our data or is 0)
        root_pids = []
        for pid, data in self.all_processes_data.items():
            # A process is a root if its parent is not in our list or is 0
            if data['ppid'] == 0 or data['ppid'] not in self.all_processes_data:
                root_pids.append(pid)
        
        for pid in sorted(root_pids):
            add_node(pid, None)

    def filter_tree(self):
        """Filters the displayed items based on the search input.
           This version hides/shows items instead of rebuilding the tree."""
        filter_text = self.search.text().lower().strip()
        
        if not filter_text:
            # If filter is cleared, show all top-level items and expand
            for i in range(self.tree.topLevelItemCount()):
                self.tree.topLevelItem(i).setHidden(False)
            self.tree.expandToDepth(1) # Expand again after showing
            return

        # Build a set of all PIDs that should be visible (match + their ancestors)
        visible_pids = set()
        for pid, data in self.all_processes_data.items():
            searchable_fields = f"{data['name']} {data['pid']} {data['status']} {data['exe']}".lower()
            if filter_text in searchable_fields:
                visible_pids.add(pid)
                # Add ancestors to the visible set
                current_pid = pid
                # Limit ancestor traversal to prevent issues if structure is very deep or corrupted
                for _ in range(100): # Max 100 levels up
                    parent_pid = self.all_processes_data.get(current_pid, {}).get('ppid')
                    if parent_pid is None or parent_pid == 0 or parent_pid not in self.all_processes_data:
                        break # Reached the top or parent is unknown
                    if parent_pid in visible_pids:
                        break # Parent already marked visible
                    visible_pids.add(parent_pid)
                    current_pid = parent_pid
        
        # Iterate through all items in the tree and hide/show them
        for i in range(self.tree.topLevelItemCount()):
            self.update_item_visibility(self.tree.topLevelItem(i), visible_pids)

    def update_item_visibility(self, item, visible_pids):
        """Recursively hides or shows tree items based on visible_pids."""
        pid = item.data(0, Qt.ItemDataRole.UserRole)
        if pid is None: return # Should not happen if populated correctly

        is_visible = pid in visible_pids
        item.setHidden(not is_visible)

        # If an item is hidden, its children might still be visible if they are ancestors of a match
        # So we need to check children regardless of parent's visibility in the filter context
        # but only if the item itself is not hidden.
        if is_visible:
            for i in range(item.childCount()):
                self.update_item_visibility(item.child(i), visible_pids)


    def selected_pid(self):
        item = self.tree.currentItem()
        if not item:
            return None, None
        try:
            pid = item.data(0, Qt.ItemDataRole.UserRole)
            return pid, item.text(0)
        except Exception:
            return None, None

    def open_context_menu(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        refresh_action = menu.addAction("Refresh Tree")
        kill_action = menu.addAction("End task")
        kill_tree_action = menu.addAction("End process tree")
        menu.addSeparator()
        properties_action = menu.addAction("Copy PID")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == refresh_action:
            self.rebuild_tree()
        elif action == kill_action:
            self.kill_process(tree=False)
        elif action == kill_tree_action:
            self.kill_process(tree=True)
        elif action == properties_action:
            pid, _ = self.selected_pid()
            if pid is not None:
                QApplication.clipboard().setText(str(pid))

    def kill_process(self, tree=False):
        pid, name = self.selected_pid()
        if pid is None:
            return
        try:
            proc = psutil.Process(pid)
            if tree:
                # Kill children first
                for child in proc.children(recursive=True):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass # Already gone
                proc.kill()
            else:
                proc.kill()
            # Delay refresh slightly to allow process to terminate gracefully
            QTimer.singleShot(500, self.rebuild_tree)
        except psutil.NoSuchProcess:
             QMessageBox.warning(self, "Info", f"Process {pid} ({name}) not found. It may have already terminated.")
             self.rebuild_tree() # Refresh to clean up any potentially stale items
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

# =========================
# Antivirus Scanner Thread
# =========================
class AntivirusScannerThread(QThread):
    update_progress = pyqtSignal(int)
    scan_finished = pyqtSignal(list)
    log_message = pyqtSignal(str)
    scan_status_update = pyqtSignal(str)

    def __init__(self, target_path):
        super().__init__()
        self.target_path = target_path
        self.running = True
        self.infected_files = []
        self.files_to_scan_count = 0
        self.scanned_count = 0

    def run(self):
        self.scan_status_update.emit("Preparing scan...")
        create_quarantine_folder()
        
        files_to_process = []
        try:
            if os.path.isdir(self.target_path):
                for root, dirs, files in os.walk(self.target_path):
                    # Skip quarantine folder if it's inside the scan path
                    if QUARANTINE_FOLDER in dirs:
                        dirs.remove(QUARANTINE_FOLDER)
                    if not self.running: break
                    for file in files:
                        files_to_process.append(os.path.join(root, file))
            elif os.path.isfile(self.target_path):
                files_to_process.append(self.target_path)
            else:
                self.update_progress.emit(100)
                self.scan_finished.emit([])
                self.scan_status_update.emit("Scan complete (No files found)")
                return
        except Exception as e:
            self.log_message.emit(f"Error during file enumeration: {e}")
            self.update_progress.emit(100)
            self.scan_finished.emit([])
            self.scan_status_update.emit("Scan failed")
            return

        self.files_to_scan_count = len(files_to_process)
        if self.files_to_scan_count == 0:
            self.update_progress.emit(100)
            self.scan_finished.emit([])
            self.scan_status_update.emit("Scan complete (No files to scan)")
            return

        self.scan_status_update.emit(f"Scanning {self.files_to_scan_count} items...")
        
        for idx, file_path in enumerate(files_to_process):
            if not self.running:
                self.scan_status_update.emit("Scan stopped by user")
                return
            
            self.scanned_count = idx + 1
            progress = int((self.scanned_count / self.files_to_scan_count) * 100)
            self.update_progress.emit(progress)
            
            if self.check_file_for_threats(file_path):
                self.infected_files.append(file_path)

        self.scan_finished.emit(self.infected_files)
        if self.running: # Only set to complete if not stopped
            self.scan_status_update.emit("Scan complete")

    def check_file_for_threats(self, file_path):
        if not self.running: return False # Check running flag frequently
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
        try:
            # Check signatures first (faster for known simple threats)
            # Read only a small part for signature checking to be faster
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content_start = f.read(512) # Read first 512 bytes
                if any(sig in content_start for sig in SIMPLE_SIGNATURES):
                    self.log_message.emit(f"Signature match: {os.path.basename(file_path)}")
                    return True
        except Exception as e:
            self.log_message.emit(f"Error reading {os.path.basename(file_path)} for signature: {e}")
            # Continue to hash check if signature read fails

        # Hash check for known malware
        file_hash = calculate_sha256(file_path)
        if file_hash and file_hash in VIRUS_HASHES.values():
            self.log_message.emit(f"Hash match: {os.path.basename(file_path)}")
            return True
        return False

    def quarantine_file(self, file_path):
        if not os.path.exists(file_path):
            return False
        try:
            filename = os.path.basename(file_path)
            destination_folder = QUARANTINE_FOLDER
            # Ensure quarantine folder exists
            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder)

            destination = os.path.join(destination_folder, filename)
            counter = 1
            base, ext = os.path.splitext(filename)
            # Handle potential naming conflicts in quarantine folder
            while os.path.exists(destination):
                destination = os.path.join(destination_folder, f"{base}_{counter}{ext}")
                counter += 1
            
            shutil.move(file_path, destination)
            self.log_message.emit(f"Quarantined: {file_path} -> {destination}")
            return True
        except Exception as e:
            self.log_message.emit(f"Failed to quarantine {file_path}: {e}")
            return False

    def stop(self):
        self.running = False
        self.scan_status_update.emit("Stopping scan...")

# =========================
# Infected Files Dialog
# =========================
class InfectedFilesDialog(QDialog):
    quarantine_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Threats Found!")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Found {len(files)} potential threat(s):"))
        self.file_list = QListWidget()
        for file_path in files:
            self.file_list.addItem(file_path)
        layout.addWidget(self.file_list)
        
        btns = QHBoxLayout()
        q_btn = QPushButton("Quarantine Selected")
        d_btn = QPushButton("Delete Selected")
        q_btn.clicked.connect(self.request_quarantine)
        d_btn.clicked.connect(self.request_delete)
        btns.addWidget(q_btn)
        btns.addWidget(d_btn)
        layout.addLayout(btns)
        
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def request_quarantine(self):
        for item in self.file_list.selectedItems():
            self.quarantine_requested.emit(item.text())

    def request_delete(self):
        if QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to permanently delete the selected files? This action cannot be undone.") == QMessageBox.StandardButton.Yes:
            for item in self.file_list.selectedItems():
                self.delete_requested.emit(item.text())

# =========================
# Antivirus Widget
# =========================
class Antivirus(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.log_list = QListWidget()
        layout.addWidget(self.log_list)
        buttons = QHBoxLayout()
        self.scan_btn = QPushButton("Start Scan")
        self.stop_btn = QPushButton("Stop Scan")
        self.scan_btn.clicked.connect(self.start_scan)
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        buttons.addWidget(self.scan_btn)
        buttons.addWidget(self.stop_btn)
        layout.addLayout(buttons)
        self.scanner_thread = None
        self.infected_files_found = []

    def start_scan(self):
        target_path = QFileDialog.getExistingDirectory(self, "Select Folder or Drive to Scan")
        if not target_path:
            return
        self.log_list.clear()
        self.progress.setValue(0)
        self.status_label.setText(f"Scanning: {target_path}")
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.scanner_thread = AntivirusScannerThread(target_path)
        self.scanner_thread.update_progress.connect(self.progress.setValue)
        self.scanner_thread.scan_finished.connect(self.on_scan_finished)
        self.scanner_thread.log_message.connect(self.add_log)
        self.scanner_thread.scan_status_update.connect(self.status_label.setText)
        self.scanner_thread.start()

    def stop_scan(self):
        if self.scanner_thread:
            self.scanner_thread.stop()
            self.stop_btn.setEnabled(False)
            # Status update happens within the thread

    def on_scan_finished(self, infected_files):
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        # Ensure progress bar shows 100% if scan finished normally
        if self.scanner_thread and self.scanner_thread.running:
            self.progress.setValue(100)
        
        self.infected_files_found = infected_files
        if infected_files:
            dlg = InfectedFilesDialog(infected_files, self)
            dlg.quarantine_requested.connect(self.handle_quarantine_request)
            dlg.delete_requested.connect(self.handle_delete_request)
            dlg.exec()
        elif self.scanner_thread and self.scanner_thread.running: # Only show this if scan completed normally and found no threats
            self.add_log("No threats found.")
            
        if self.scanner_thread: # Ensure thread is cleaned up
            self.scanner_thread.quit()
            self.scanner_thread.wait() # Wait for thread to finish
        self.scanner_thread = None


    def handle_quarantine_request(self, file_path):
        if self.scanner_thread: # Make sure thread is still valid
            self.scanner_thread.quarantine_file(file_path)
            # Log message is handled inside quarantine_file

    def handle_delete_request(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.add_log(f"Deleted: {file_path}")
                # Remove from found list if it was there
                if file_path in self.infected_files_found:
                    self.infected_files_found.remove(file_path)
        except Exception as e:
            self.add_log(f"Delete error: {e}")

    def add_log(self, message):
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()

# =========================
# Main Window
# =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1300, 800)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(180)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.drive = DriveManager()
        self.network = NetworkControl()
        self.files = FileOperations()
        self.system = SystemControl()
        self.antivirus = Antivirus()
        self.google_search_widget = GoogleSearchWidget()
        self.driver_status = DriverStatusWidget()
        self.task_manager = TaskManagerWidget()
        self.system_info = SystemInfoWidget()

        self.widgets = {
            self.sidebar.drive_btn: self.drive,
            self.sidebar.network_btn: self.network,
            self.sidebar.files_btn: self.files,
            self.sidebar.system_btn: self.system,
            self.sidebar.antivirus_btn: self.antivirus,
            self.sidebar.google_search_btn: self.google_search_widget,
            self.sidebar.drivers_btn: self.driver_status,
            self.sidebar.task_manager_btn: self.task_manager,
            self.sidebar.system_info_btn: self.system_info
        }

        for widget in self.widgets.values():
            self.stack.addWidget(widget)

        for button, widget in self.widgets.items():
            button.clicked.connect(lambda checked, w=widget: self.stack.setCurrentWidget(w))

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

# =========================
# Main Execution
# =========================
def main():
    if is_windows() and not is_admin():
        if not relaunch_as_admin():
            QMessageBox.critical(None, "Permission Error", "Administrator privileges are required.")
            return
        sys.exit()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        app = QApplication.instance()
        temp_app = None
        if app is None:
            temp_app = QApplication(sys.argv)
        QMessageBox.critical(None, "Fatal Error", f"An unexpected error occurred:\n\n{err}")
        if temp_app is not None:
            temp_app.quit()
