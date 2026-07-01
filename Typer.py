import pyautogui
import time
import tkinter as tk

# Function to type text with delays
def type_with_delay():
    text = text_box.get("1.0", "end-1c")  # Get text from the text box
    delay = float(delay_box.get())        # Get overall delay from input
    char_delay = float(char_delay_box.get())  # Get per-character delay from input
    
    time.sleep(delay)  # Initial delay before typing starts

    # Type each character with the specified interval
    pyautogui.typewrite(text, interval=char_delay)

# Create GUI window
root = tk.Tk()
root.title("Text Typer with Delay")

# Frame for layout
frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

# Text input box
text_box_label = tk.Label(frame, text="Enter Text:")
text_box_label.pack()
text_box = tk.Text(frame, height=10, width=40)
text_box.pack(pady=5)

# Overall delay input
delay_box_label = tk.Label(frame, text="Enter Overall Delay (seconds):")
delay_box_label.pack()
delay_box = tk.Entry(frame)
delay_box.pack(pady=5)

# Character delay input
char_delay_box_label = tk.Label(frame, text="Enter Character Delay (seconds):")
char_delay_box_label.pack()
char_delay_box = tk.Entry(frame)
char_delay_box.pack(pady=5)

# Start typing button
type_button = tk.Button(frame, text="Start Typing", command=type_with_delay)
type_button.pack(pady=10)

# Run the GUI
root.mainloop()
