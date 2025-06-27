import os
import shutil
from datetime import datetime
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


# === Organizer Logic ===
class FileOrganizer:
    def __init__(self):
        self.last_moves = []

    def get_file_size_category(self, file_path):
        size_bytes = os.path.getsize(file_path)
        mb = size_bytes / (1024 * 1024)
        if mb <= 10:
            return "Small"
        elif mb <= 100:
            return "Medium"
        elif mb <= 1000:
            return "Large"
        else:
            return "Very_Large"

    def organize(self, folder_path, log_output, sort_by_size, progress):
        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", "Invalid folder path")
            return

        log_output.insert(tk.END, f"\nOrganizing: {folder_path}\n")
        log_output.see(tk.END)
        self.last_moves.clear()

        total_files = sum(len(files) for _, _, files in os.walk(folder_path))
        progress["maximum"] = total_files
        progress["value"] = 0

        duplicate_counter = defaultdict(int)

        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(root, filename)

                if root != folder_path and os.path.commonpath([folder_path]) == os.path.commonpath([folder_path, root]):
                    continue

                _, extension = os.path.splitext(filename)
                extension = extension.lower() or 'no_extension'

                try:
                    timestamp = os.path.getmtime(file_path)
                    file_date = datetime.fromtimestamp(timestamp)
                    year = str(file_date.year)
                    month = file_date.strftime('%B')
                except Exception:
                    year = "Unknown_Year"
                    month = "Unknown_Month"

                folder_name = extension.replace('.', '') if extension != 'no_extension' else 'no_extension'
                target_folder = os.path.join(folder_path, folder_name, year, month)

                if sort_by_size:
                    size_folder = self.get_file_size_category(file_path)
                    target_folder = os.path.join(target_folder, size_folder)

                os.makedirs(target_folder, exist_ok=True)

                destination_file = os.path.join(target_folder, filename)

                if os.path.exists(destination_file):
                    name, ext = os.path.splitext(filename)
                    duplicate_counter[filename] += 1
                    new_filename = f"{name}_{duplicate_counter[filename]}{ext}"
                    destination_file = os.path.join(target_folder, new_filename)

                try:
                    shutil.move(file_path, destination_file)
                    self.last_moves.append((destination_file, file_path))
                    log_output.insert(tk.END, f"✅ Moved: {filename} --> {target_folder}\n")
                    log_output.see(tk.END)
                    log_output.update()
                except Exception as e:
                    log_output.insert(tk.END, f"❌ Failed: {filename} | Error: {e}\n")
                    log_output.see(tk.END)

                progress["value"] += 1
                progress.update()

        messagebox.showinfo("Complete", "Organization complete!")
        log_output.insert(tk.END, "\n🎉 Organization Complete!\n")
        log_output.see(tk.END)
        progress["value"] = 0

    def undo(self, log_output):
        if not self.last_moves:
            messagebox.showinfo("Undo", "Nothing to undo!")
            return

        for src, dest in reversed(self.last_moves):
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(src, dest)
                log_output.insert(tk.END, f"↩️ Restored: {os.path.basename(src)}\n")
                log_output.see(tk.END)
                log_output.update()
            except Exception as e:
                log_output.insert(tk.END, f"❌ Failed to restore {os.path.basename(src)}: {e}\n")
                log_output.see(tk.END)

        self.last_moves.clear()
        messagebox.showinfo("Undo", "Undo complete!")


# === Email Report ===
def send_email_report(subject, body, sender_email, sender_password, receiver_email):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()

        messagebox.showinfo("Email", "Email sent successfully!")
    except Exception as e:
        messagebox.showerror("Email Error", f"Failed to send email: {e}")


# === Google Drive Backup ===
def upload_to_drive(folder_path, log_output):
    try:
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()

        drive = GoogleDrive(gauth)

        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                gfile = drive.CreateFile({'title': file})
                gfile.SetContentFile(file_path)
                gfile.Upload()
                log_output.insert(tk.END, f"☁️ Uploaded {file} to Google Drive\n")
                log_output.see(tk.END)

        messagebox.showinfo("Cloud", "Upload to Google Drive complete.")
    except Exception as e:
        messagebox.showerror("Cloud Error", f"Google Drive upload failed: {e}")


# === GUI ===
def start_gui():
    organizer = FileOrganizer()

    window = tk.Tk()
    window.title("File Organizer Pro")
    window.geometry("850x650")
    window.resizable(False, False)

    is_dark_mode = tk.BooleanVar(value=False)
    sort_by_size = tk.BooleanVar(value=False)

    # === Header ===
    header = tk.Label(window, text="📂 File Organizer Pro", font=("Arial", 20, "bold"))
    header.pack(pady=10)

    # === Folder Selection ===
    folder_frame = tk.Frame(window)
    folder_frame.pack(pady=5)

    folder_label = tk.Label(folder_frame, text="Folder Path:", font=("Arial", 11))
    folder_label.grid(row=0, column=0, padx=5)

    folder_path_var = tk.StringVar()

    folder_entry = tk.Entry(folder_frame, textvariable=folder_path_var, width=60)
    folder_entry.grid(row=0, column=1, padx=5)

    def browse_folder():
        selected_folder = filedialog.askdirectory()
        if selected_folder:
            folder_path_var.set(selected_folder)

    browse_button = tk.Button(folder_frame, text="Browse", command=browse_folder)
    browse_button.grid(row=0, column=2, padx=5)

    # === Options ===
    option_frame = tk.Frame(window)
    option_frame.pack()

    sort_checkbox = tk.Checkbutton(option_frame, text="Sort by File Size", variable=sort_by_size)
    sort_checkbox.grid(row=0, column=0, padx=10)

    dark_mode_checkbox = tk.Checkbutton(option_frame, text="Dark Mode", variable=is_dark_mode, command=lambda: apply_theme())
    dark_mode_checkbox.grid(row=0, column=1, padx=10)

    # === Progress Bar ===
    progress = ttk.Progressbar(window, orient="horizontal", length=600, mode="determinate")
    progress.pack(pady=5)

    # === Action Buttons ===
    button_frame = tk.Frame(window)
    button_frame.pack(pady=10)

    def apply_theme():
        bg = "#222222" if is_dark_mode.get() else "#f5f5f5"
        fg = "#eeeeee" if is_dark_mode.get() else "#000000"
        text_bg = "#333333" if is_dark_mode.get() else "#ffffff"

        window.config(bg=bg)
        header.config(bg=bg, fg=fg)
        folder_frame.config(bg=bg)
        folder_label.config(bg=bg, fg=fg)
        option_frame.config(bg=bg)
        sort_checkbox.config(bg=bg, fg=fg, selectcolor=bg)
        dark_mode_checkbox.config(bg=bg, fg=fg, selectcolor=bg)
        footer.config(bg=bg, fg=fg)
        log_output.config(bg=text_bg, fg=fg, insertbackground=fg)

    organize_button = tk.Button(button_frame, text="Organize Files", font=("Arial", 12, "bold"),
                                bg="#4CAF50", fg="white",
                                command=lambda: organizer.organize(folder_path_var.get(), log_output, sort_by_size.get(), progress))
    organize_button.grid(row=0, column=0, padx=10)

    undo_button = tk.Button(button_frame, text="Undo", font=("Arial", 12, "bold"),
                            bg="#FF5722", fg="white",
                            command=lambda: organizer.undo(log_output))
    undo_button.grid(row=0, column=1, padx=10)

    save_log_button = tk.Button(button_frame, text="Save Log", font=("Arial", 12, "bold"),
                                bg="#2196F3", fg="white",
                                command=lambda: save_log(log_output))
    save_log_button.grid(row=0, column=2, padx=10)

    email_button = tk.Button(button_frame, text="Send Email", font=("Arial", 12, "bold"),
                             bg="#9C27B0", fg="white",
                             command=lambda: send_email_report(
                                 subject="File Organization Report",
                                 body=log_output.get(1.0, tk.END),
                                 sender_email="your_email@gmail.com",
                                 sender_password="your_app_password",  # Use app password
                                 receiver_email="receiver_email@gmail.com"
                             ))
    email_button.grid(row=0, column=3, padx=10)

    cloud_button = tk.Button(button_frame, text="Cloud Backup", font=("Arial", 12, "bold"),
                             bg="#009688", fg="white",
                             command=lambda: upload_to_drive(folder_path_var.get(), log_output))
    cloud_button.grid(row=0, column=4, padx=10)

    def batch_process():
        folders = filedialog.askdirectory(title="Select Main Folder with Subfolders")
        if folders:
            subfolders = [os.path.join(folders, f) for f in os.listdir(folders)
                          if os.path.isdir(os.path.join(folders, f))]
            if subfolders:
                for folder in subfolders:
                    organizer.organize(folder, log_output, sort_by_size.get(), progress)
            else:
                messagebox.showinfo("Batch", "No subfolders found.")

    batch_button = tk.Button(button_frame, text="Batch Organize",
                             bg="#673AB7", fg="white", font=("Arial", 12, "bold"),
                             command=batch_process)
    batch_button.grid(row=0, column=5, padx=10)

    # === Log Area ===
    log_output = scrolledtext.ScrolledText(window, width=100, height=25, wrap=tk.WORD, font=("Consolas", 10))
    log_output.pack(padx=10, pady=10)

    # === Footer ===
    footer = tk.Label(window, text="Developed by Martin • Powered by Python", font=("Arial", 9))
    footer.pack(pady=5)

    apply_theme()
    window.mainloop()


# === Save Log ===
def save_log(log_output):
    log_content = log_output.get(1.0, tk.END)
    if not log_content.strip():
        messagebox.showinfo("Save Log", "Log is empty.")
        return

    file = filedialog.asksaveasfile(defaultextension=".txt",
                                     filetypes=[("Text File", "*.txt")],
                                     title="Save Log As")
    if file:
        file.write(log_content)
        file.close()
        messagebox.showinfo("Save Log", "Log saved successfully.")


# === Run App ===
if __name__ == "__main__":
    start_gui()
