import tkinter as tk
from tkinter import Menu, messagebox

# Function to handle menu actions for Panel 1 (TeleCommand)
def panel1_action(action):
    messagebox.showinfo("TeleCommand", f"Panel 1: {action} selected!")

# Function to handle menu actions for Panel 1 (Edit)
def panel1_edit_action(action):
    messagebox.showinfo("Edit", f"Edit Menu: {action} selected!")

# Function to handle menu actions for Panel 2 (Telemetry)
def panel2_action(action):
    messagebox.showinfo("Telemetry", f"Panel 2: {action} selected!")

# Function to handle menu actions for Panel 2 (View)
def panel2_view_action(action):
    messagebox.showinfo("View", f"View Menu: {action} selected!")

# Create the main window
root = tk.Tk()
root.title("CCSDS simulator")
root.geometry("600x400")  # Set initial size

# Create a PanedWindow (resizable container) with HORIZONTAL orientation
paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL)
paned_window.pack(fill=tk.BOTH, expand=True)  # Fill the entire window

### === PANEL 1 (TeleCommand) === ###
panel1 = tk.Frame(paned_window, bg="lightblue")
paned_window.add(panel1, stretch="always")  # Add to PanedWindow with equal resizing

# Create a frame to hold menu buttons
panel1_menu_frame = tk.Frame(panel1, bg="gray")
panel1_menu_frame.pack(fill=tk.X)

# Create a menu button for "TeleCommand"
panel1_menu_button = tk.Menubutton(panel1_menu_frame, text="TeleCommand", font=("Arial", 12, "bold"), relief=tk.RAISED, bg="gray", fg="white")
panel1_menu_button.pack(side=tk.LEFT, padx=5, pady=2)

# Create a dropdown menu for "TeleCommand"
panel1_menu = Menu(panel1_menu_button, tearoff=0)
panel1_menu.add_command(label="Send a ccsds file", command=lambda: panel1_action("Send a ccsds file"))
panel1_menu.add_command(label="Send a ccsds file periodicly", command=lambda: panel1_action("Send a ccsds file periodicly"))

# Attach the menu to the button
panel1_menu_button["menu"] = panel1_menu

# Create another menu button for "Edit"
panel1_edit_button = tk.Menubutton(panel1_menu_frame, text="Edit", font=("Arial", 12, "bold"), relief=tk.RAISED, bg="gray", fg="white")
panel1_edit_button.pack(side=tk.LEFT, padx=5, pady=2)

# Create a dropdown menu for "Edit"
panel1_edit_menu = Menu(panel1_edit_button, tearoff=0)
panel1_edit_menu.add_command(label="Edit Settings", command=lambda: panel1_edit_action("Edit Settings"))
panel1_edit_menu.add_command(label="Preferences", command=lambda: panel1_edit_action("Preferences"))

# Attach the menu to the button
panel1_edit_button["menu"] = panel1_edit_menu

# Content inside Panel 1
label1 = tk.Label(panel1, text="This is Panel 1", font=("Arial", 12), bg="lightblue")
label1.pack(expand=True)

### === PANEL 2 (Telemetry) === ###
panel2 = tk.Frame(paned_window, bg="lightgreen")
paned_window.add(panel2, stretch="always")  # Add to PanedWindow with equal resizing

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

# Attach the menu to the menu button
panel2_menu_button["menu"] = panel2_menu

# Create another menu button for "View"
panel2_view_button = tk.Menubutton(panel2_menu_frame, text="View", font=("Arial", 12, "bold"), relief=tk.RAISED, bg="gray", fg="white")
panel2_view_button.pack(side=tk.LEFT, padx=5, pady=2)

# Create a dropdown menu for "View"
panel2_view_menu = Menu(panel2_view_button, tearoff=0)
panel2_view_menu.add_command(label="Real-Time Data", command=lambda: panel2_view_action("Real-Time Data"))
panel2_view_menu.add_command(label="Historical Data", command=lambda: panel2_view_action("Historical Data"))

# Attach the menu to the button
panel2_view_button["menu"] = panel2_view_menu

# Content inside Panel 2
label2 = tk.Label(panel2, text="This is Panel 2", font=("Arial", 12), bg="lightgreen")
label2.pack(expand=True)

# Run the application
root.mainloop()
