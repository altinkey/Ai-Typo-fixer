import time
import logging
import httpx
import pyperclip
import json
import tkinter as tk
from tkinter import ttk
from pynput import keyboard
from pynput.keyboard import Key, Controller
import threading

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize keyboard controller
controller = Controller()

# Define LMstudio API endpoint and configuration
LMSTUDIO_ENDPOINT = "http://localhost:1234/v1/chat/completions"
LMSTUDIO_CONFIG = {
    "model": "LMstudiomodel",
    "temperature": 0.0,  # Lower randomness
    "max_tokens": -1,
    "stream": True  # Enable streaming
}

def create_payload(text, language=None):
    messages = [
        {"role": "system", "content": "Fix all typos, casing, and punctuation in this text, but preserve all new line characters,Return only the corrected text, don't include a preamble"},
        {"role": "user", "content": text}
    ]
    
    if language:
        messages.append({"role": "system", "content": f"Translate the text to {language}."})
    
    return {
        "model": LMSTUDIO_CONFIG["model"],
        "messages": messages,
        "temperature": LMSTUDIO_CONFIG["temperature"],
        "max_tokens": LMSTUDIO_CONFIG["max_tokens"],
        "stream": LMSTUDIO_CONFIG["stream"]
    }

def fix_text(text, language=None):
    url = LMSTUDIO_ENDPOINT
    payload = create_payload(text, language)

    try:
        with httpx.stream("POST", url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10) as response:
            response.raise_for_status()  # Raise an exception for HTTP errors
            fixed_text = ""

            # Handle streaming response
            for line in response.iter_text():
                if line.startswith("data:"):
                    line_content = line[5:].strip()
                    if line_content and line_content != "[DONE]":
                        json_content = json.loads(line_content)  # Use json.loads to parse JSON
                        if "choices" in json_content:
                            fixed_text += json_content["choices"][0]["delta"].get("content", "")

            return fixed_text.strip()
    
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP status error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    return None

def paste_fixed_text():
    logger.debug("Pasting fixed text.")
    controller.press(Key.ctrl)
    controller.tap('v')
    controller.release(Key.ctrl)
    logger.debug("Fixed text pasted.")

def fix_selection(translate_to=None):
    logger.debug("Fixing selected text.")

    # 1. Copy the selected text to the clipboard
    controller.press(Key.ctrl)
    controller.tap('c')
    controller.release(Key.ctrl)
    time.sleep(0.01)  # Delay to ensure clipboard update

    # 2. Get the clipboard content
    text = pyperclip.paste().strip()
    logger.debug(f"Clipboard text: {text}")

    # 3. Fix the text using LMstudio
    if not text:
        logger.debug("No text to fix.")
        return
    fixed_text = fix_text(text, translate_to)
    if not fixed_text:
        logger.debug("No fixed text returned.")
        return

    # 4. Copy the fixed text to clipboard
    pyperclip.copy(fixed_text)
    logger.debug(f"Fixed text copied to clipboard: {fixed_text}")
    time.sleep(0.01)

    # 5. Paste the fixed text back to replace the selected text
    paste_fixed_text()

    # Notify that the task is complete
    status_label.config(text="Ready to accept new command")

def on_f10():
    logger.debug("F10 key pressed.")
    # Determine the selected option
    option = option_var.get()
    language = language_var.get() if option in ["Translate", "Fix and Translate"] else None
    
    if option == "Fix Typos Only":
        threading.Thread(target=fix_selection).start()
    elif option == "Translate":
        # Get the text to translate and translate only
        text = pyperclip.paste().strip()
        if text:
            threading.Thread(target=lambda: fix_selection(translate_to=language)).start()
    elif option == "Fix and Translate":
        threading.Thread(target=lambda: fix_selection(translate_to=language)).start()

def on_closing():
    logger.debug("Window closing. Stopping hotkey listener.")
    h.stop()
    root.destroy()

# Create the main window
root = tk.Tk()
root.title("Typing Assistant")
root.configure(bg="#242124")  # Set background color to black

# Set a modern theme
style = ttk.Style(root)
style.theme_use("clam")

# Create and place widgets
frame = ttk.Frame(root, padding="10", style="Black.TFrame")
frame.pack(fill=tk.BOTH, expand=True)

option_var = tk.StringVar(value="Fix Typos Only")
ttk.Radiobutton(frame, text="Fix Typos Only", variable=option_var, value="Fix Typos Only", style="Black.TRadiobutton").grid(row=0, column=0, sticky="w", pady=5)
ttk.Radiobutton(frame, text="Translate", variable=option_var, value="Translate", style="Black.TRadiobutton").grid(row=1, column=0, sticky="w", pady=5)
ttk.Radiobutton(frame, text="Fix and Translate", variable=option_var, value="Fix and Translate", style="Black.TRadiobutton").grid(row=2, column=0, sticky="w", pady=5)

language_var = tk.StringVar(value="None")
language_menu = ttk.Combobox(frame, textvariable=language_var, values=["None", "Chinese", "Japanese", "German", "Spanish", "French", "Italian", "Portuguese", "Russian", "Korean", "Arabic", "Dutch", "Swedish"], style="Normal.TCombobox")
language_menu.grid(row=3, column=0, sticky="w", pady=5)
language_menu.config(state="readonly")  # Make dropdown menu readonly

def update_language_menu(*args):
    if option_var.get() == "Fix Typos Only":
        language_menu.set("None")
        language_menu.config(state="disabled", style="Disabled.TCombobox")
    else:
        language_menu.config(state="readonly", style="Normal.TCombobox")

option_var.trace_add("write", update_language_menu)

# Define styles for active and inactive states
style.configure("Disabled.TCombobox", fieldbackground="#ff0000", foreground="white")
style.configure("Normal.TCombobox", fieldbackground="#00ff00", foreground="white")
style.configure("Black.TFrame", background="#242124")
style.configure("Black.TRadiobutton", background="#242124", foreground="white")

status_label = ttk.Label(frame, text="Ready to accept new command", anchor="w", background="#242124", foreground="white")
status_label.grid(row=4, column=0, sticky="w", pady=10)

# Set up global hotkeys
h = keyboard.GlobalHotKeys({"<f10>": on_f10})
h.start()

# Set up window close handler
root.protocol("WM_DELETE_WINDOW", on_closing)

logger.debug("Hotkeys initialized.")
root.mainloop()