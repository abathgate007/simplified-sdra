import json
import os
from pathlib import Path
from tkinter import filedialog
import tkinter as tk

def select_file():
    """Open a file dialog to select a file and return its path."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    file_path = filedialog.askopenfilename(
        title="Select a file to read",
        filetypes=[
            ("All files", "*.*"),
            ("JSON files", "*.json"),
            ("Text files", "*.txt"),
            ("Python files", "*.py")
        ]
    )
    
    root.destroy()
    return file_path

def read_file_raw(file_path):
    """Read raw content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def main():
    """Main function to demonstrate file selection and reading."""
    print("File Selection and Reading Utility")
    
    # Select a file
    selected_file = select_file()
    
    if not selected_file:
        print("No file selected. Exiting.")
        return
    
    print(f"Selected file: {selected_file}")
    
    # Read raw content
    raw_content = read_file_raw(selected_file)
    
    if raw_content is None:
        print("Failed to read file content.")
        return
    
    print(f"\nFile content ({len(raw_content)} characters):")
    print("-" * 40)
    
    # If it looks like JSON, try to parse it
    if selected_file.lower().endswith('.json') or raw_content.strip().startswith(('{', '[')):
        try:
            # Try to parse as JSON
            parsed_data = json.loads(raw_content)
            print(f"\nParsed JSON data:")
            print(json.dumps(parsed_data, indent=2))
            
            # Save parsed JSON to file
            with open('parsedjson.txt', 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2)
            print(f"\nParsed JSON saved to: parsedjson.txt")
            
        except json.JSONDecodeError as e:
            print(f"\nCould not parse as JSON: {e}")
    
    return raw_content


if __name__ == "__main__":
    print("Starting parsing utility...")
    main()
        
    print("Finished processing.")