import tkinter as tk
from tkinter import messagebox
import subprocess
import sys

def launch_virtual_keyboard():
    # This function will run the virtual keyboard code in a separate process
    messagebox.showinfo("AI Virtual Keyboard", "Launching AI Virtual Keyboard...")
    subprocess.Popen([sys.executable, "Keyboard.py"])  # Run virtual_keyboard.py as a separate process

def launch_volume_adjust():
    # This function will run the volume adjust code in a separate process
    messagebox.showinfo("Volume Adjust", "Launching Volume Adjust...")
    subprocess.Popen([sys.executable, "Volume.py"])  # Run volume_adjust.py as a separate process

# Main screen setup
def main_screen():
    root = tk.Tk()
    root.title("AI Project Options")
    root.geometry("400x300")

    label = tk.Label(root, text="Select an option:", font=("Arial", 16))
    label.pack(pady=20)

    # Button for AI Virtual Keyboard
    button1 = tk.Button(root, text="AI Virtual Keyboard", width=25, height=2, command=launch_virtual_keyboard)
    button1.pack(pady=10)

    # Button for Volume Adjust
    button2 = tk.Button(root, text="Volume Adjust", width=25, height=2, command=launch_volume_adjust)
    button2.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main_screen()
