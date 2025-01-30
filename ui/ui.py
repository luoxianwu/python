import tkinter as tk
from tkinter import Menu, messagebox, filedialog
import os  # Import os to list files in the directory

# Function to list all .sds files and update the Edit menu
def update_edit_menu():
    edit_menu.delete(0, tk.END)  # Clear previous entries
    current_directory = os.getcwd()
    sds_files = [f for f in os.listdir(current_directory) if f.endswith(".sds")]

    if not sds_files:
        edit_menu.add_command(label="No .sds files found", state=tk.DISABLED)
    else:
        for file in sds_files:
            edit_menu.add_command(label=file, command=lambda f=file: open_edit_window(f))

# Function to open an edit window for the selected file
def open_edit_window(filename):
    def save_file():
        """Save the current file (overwrite the existing file)."""
        try:
            with open(filename, "w") as file:
                file.write(edit_text.get("1.0", tk.END))
            #messagebox.showinfo("Save File", f"File '{filename}' saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def save_as_file():
        """Save the content as a new file (Save As)."""
        new_file_path = filedialog.asksaveasfilename(
            initialdir=os.getcwd(),
            title="Save As",
            defaultextension=".sds",
            filetypes=[("CCSDS Files", "*.sds"), ("All Files", "*.*")]
        )
        if new_file_path:
            try:
                with open(new_file_path, "w") as file:
                    file.write(edit_text.get("1.0", tk.END))
                #messagebox.showinfo("Save As", f"File saved as '{new_file_path}'")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def send_file():
        """Simulate sending the file."""
        messagebox.showinfo("Send File", f"File '{filename}' is being sent...")

    # Create a new window for editing
    edit_window = tk.Toplevel(root)
    edit_window.title(f"Editing: {filename}")
    edit_window.geometry("500x400")

    # Create a menu bar in the edit window
    menu_bar = Menu(edit_window)
    edit_window.config(menu=menu_bar)

    # Add "Save", "Save As", and "Send" menus
    menu_bar.add_command(label="Save", command=save_file)
    menu_bar.add_command(label="Save As", command=save_as_file)
    menu_bar.add_command(label="Send", command=send_file)

    # Create a text area for editing
    edit_text = tk.Text(edit_window, wrap="word")
    edit_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Load the file content into the text area
    try:
        with open(filename, "r") as file:
            content = file.read()
        edit_text.insert(tk.END, content)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open file: {str(e)}")
    edit_window.focus_force()  # Add this line at the end


# Function to handle file selection and display contents in Panel 1
def select_ccsds_file():
    current_directory = os.getcwd()
    file_path = filedialog.askopenfilename(
        initialdir=current_directory,  
        title="Select CCSDS File",
        filetypes=[("CCSDS Files", "*.sds"), ("All Files", "*.*")]
    )

    if file_path:
        try:
            with open(file_path, "r") as file:
                content = file.read()

            # Update the text widget in Panel 1 to display file content
            panel1_text.config(state=tk.NORMAL)
            panel1_text.delete("1.0", tk.END)
            panel1_text.insert(tk.END, content)
            panel1_text.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")

# Function to handle menu actions for Panel 2 (Telemetry)
def panel2_action(action):
    messagebox.showinfo("Telemetry", f"Panel 2: {action} selected!")

# Function to handle menu actions for Panel 2 (View)
def panel2_view_action(action):
    messagebox.showinfo("View", f"View Menu: {action} selected!")

# Create the main window
root = tk.Tk()
root.title("CCSDS Simulator")
root.geometry("800x500")

# Create a PanedWindow (resizable container) with HORIZONTAL orientation
paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL)
paned_window.pack(fill=tk.BOTH, expand=True)

### === PANEL 1 (TeleCommand) === ###
panel1 = tk.Frame(paned_window, bg="lightblue")
paned_window.add(panel1, stretch="always")

# Create a frame to hold menu buttons
panel1_menu_frame = tk.Frame(panel1, bg="gray")
panel1_menu_frame.pack(fill=tk.X)

# Create a menu button for "TeleCommand"
panel1_menu_button = tk.Menubutton(panel1_menu_frame, text="TeleCommand", font=("Arial", 12, "bold"), relief=tk.RAISED, bg="gray", fg="white")
panel1_menu_button.pack(side=tk.LEFT, padx=5, pady=2)

# Create a dropdown menu for "TeleCommand"
panel1_menu = Menu(panel1_menu_button, tearoff=0)
panel1_menu.add_command(label="Send a CCSDS file", command=select_ccsds_file)
panel1_menu.add_command(label="Send a CCSDS file periodically", command=lambda: messagebox.showinfo("TeleCommand", "Periodic file sending started."))

# Attach the menu to the button
panel1_menu_button["menu"] = panel1_menu

# Create another menu button for "Edit"
panel1_edit_button = tk.Menubutton(panel1_menu_frame, text="Edit", font=("Arial", 12, "bold"), relief=tk.RAISED, bg="gray", fg="white", direction=tk.RIGHT)
panel1_edit_button.pack(side=tk.LEFT, padx=5, pady=2)

# Create a dropdown menu for "Edit"
edit_menu = Menu(panel1_edit_button, tearoff=0)
panel1_edit_button["menu"] = edit_menu

# Update the file list when clicking "Edit"
panel1_edit_button.bind("<ButtonPress>", lambda e: update_edit_menu())

# Create a Text widget to display the selected file content
panel1_text = tk.Text(panel1, wrap="word", state=tk.DISABLED, height=15, width=40)
panel1_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

### === PANEL 2 (Telemetry) === ###
panel2 = tk.Frame(paned_window, bg="lightgreen")
paned_window.add(panel2, stretch="always")

# Create a frame to hold menu buttons
panel2_menu_frame = tk.Frame(panel2, bg="gray")
panel2_menu_frame.pack(fill=tk.X)

# Create a menu button for "Telemetry"
panel2_menu_button = tk.Menubutton(panel2_menu_frame, text="Telemetry", font=("Arial", 12, "bold"), relief=tk.RAISED, bg="gray", fg="white")
panel2_menu_button.pack(side=tk.LEFT, padx=5, pady=2)

# Create a dropdown menu for "Telemetry"
panel2_menu = Menu(panel2_menu_button, tearoff=0)
panel2_menu.add_command(label="View Logs", command=lambda: panel2_action("View Logs"))
panel2_menu.add_command(label="Clear Logs", command=lambda: panel2_action("Clear Logs"))

# Attach the menu to the button
panel2_menu_button["menu"] = panel2_menu

# Create another menu button for "View"
panel2_view_button = tk.Menubutton(panel2_menu_frame, text="View", font=("Arial", 12, "bold"), relief=tk.RAISED, bg="gray", fg="white")
panel2_view_button.pack(side=tk.LEFT, padx=5, pady=2)

# Run the application
root.mainloop()
