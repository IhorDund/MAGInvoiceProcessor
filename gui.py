import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from parser import InvoiceParser
from config import SUPPLIER_PATTERNS


class InvoiceProcessorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Konfiguracja okna aplikacji
        self.title("Przetwarzanie Faktur PDF")
        self.geometry("750x650")

        self.selected_fields = []
        self.files = []
        self.supplier_name = ctk.StringVar(value="Wybierz dostawcę")

        # Sekcja wyboru plików PDF
        ctk.CTkLabel(self, text="📂 Wybierz pliki PDF:", font=("Arial", 18, "bold")).pack(pady=10)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=5)

        ctk.CTkButton(button_frame, text="➕ Dodaj pliki", command=self.select_files).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="🗑️ Wyczyść listę", command=self.clear_files).pack(side="left", padx=5)

        self.file_listbox = ctk.CTkTextbox(self, height=80, width=600, state="disabled")
        self.file_listbox.pack(pady=5, fill="both", expand=True)

        # Sekcja wyboru dostawcy
        ctk.CTkLabel(self, text="🏢 Wybierz dostawcę:").pack(pady=5)
        self.supplier_dropdown = ctk.CTkComboBox(
            self, variable=self.supplier_name,
            values=["Wybierz dostawcę"] + list(SUPPLIER_PATTERNS.keys()),
            command=self.update_fields
        )
        self.supplier_dropdown.pack()

        # Sekcja dynamicznych pól wyboru
        self.frame_checkboxes = ctk.CTkFrame(self)
        self.frame_checkboxes.pack(pady=5, fill="both", expand=True)
        self.field_vars = {}

        # Sekcja wyboru formatu pliku wyjściowego
        self.output_format = ctk.StringVar(value="Excel")
        ctk.CTkLabel(self, text="📜 Wybierz format pliku:").pack(pady=5)
        ctk.CTkRadioButton(self, text="Excel (.xlsx)", variable=self.output_format, value="Excel").pack()
        ctk.CTkRadioButton(self, text="CSV (.csv)", variable=self.output_format, value="CSV").pack()

        # Pasek postępu
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # Przycisk uruchamiający przetwarzanie (na start ukryty)
        self.button_start = ctk.CTkButton(self, text="🚀 Rozpocznij przetwarzanie", command=self.start_processing)
        self.button_start.pack_forget()

    def select_files(self):
        """ Pozwala użytkownikowi wybrać pliki PDF, ale blokuje edycję listy. """
        new_files = filedialog.askopenfilenames(filetypes=[("Pliki PDF", "*.pdf")])

        if new_files:
            self.files.extend(new_files)  # Dodaje pliki do listy zamiast nadpisywać
            self.file_listbox.configure(state="normal")  # Odblokowuje pole do edycji
            self.file_listbox.delete("1.0", "end")  # Czyści stare wpisy
            for file in self.files:
                self.file_listbox.insert("end", f"{Path(file).name}\n")
            self.file_listbox.configure(state="disabled")  # Blokuje edycję

    def clear_files(self):
        """ Czyści listę plików i blokuje edycję pola tekstowego. """
        self.files = []
        self.file_listbox.configure(state="normal")  # Odblokowuje pole do edycji
        self.file_listbox.delete("1.0", "end")
        self.file_listbox.configure(state="disabled")  # Blokuje edycję

    def update_file_listbox(self):
        """ Aktualizuje widok listy plików. """
        self.file_listbox.delete("1.0", "end")
        for file in self.files:
            self.file_listbox.insert("end", f"{Path(file).name}\n")

    def update_fields(self, selected_supplier):
        """ Aktualizuje listę pól do wyboru na podstawie dostawcy. """
        # Usuwamy stare checkboxy
        for widget in self.frame_checkboxes.winfo_children():
            widget.destroy()

        if selected_supplier == "Wybierz dostawcę":
            self.button_start.pack_forget()
            return

        self.field_vars.clear()

        patterns = SUPPLIER_PATTERNS.get(selected_supplier, {})

        # 📌 Liczba kolumn (4 równe kolumny)
        cols = 4
        row = 0
        col = 0

        # Ustawienie szerokości kolumn na równą
        for i in range(cols):
            self.frame_checkboxes.grid_columnconfigure(i, weight=1)

        for field in patterns.keys():
            var = ctk.BooleanVar(value=True)  # 🔹 Domyślnie zaznaczone ✅
            cb = ctk.CTkCheckBox(self.frame_checkboxes, text=field, variable=var)

            # Ustawienie w siatce (grid layout zamiast pack)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=5)

            self.field_vars[field] = var

            # 🔹 Przechodzimy do nowej kolumny / nowego wiersza
            col += 1
            if col >= cols:  # Przejście do nowego rzędu po określonej liczbie kolumn
                col = 0
                row += 1

        # 📌 Centrowanie zawartości w poziomie
        self.frame_checkboxes.grid_columnconfigure(0, weight=1)
        self.frame_checkboxes.grid_columnconfigure(cols - 1, weight=1)

        self.button_start.pack(pady=10)  # Pokaż przycisk START

    def start_processing(self):
        """ Rozpoczyna przetwarzanie wybranych faktur. """
        if not self.files:
            messagebox.showerror("Błąd", "Nie wybrano żadnych plików!")
            return

        selected_fields = [field for field, var in self.field_vars.items() if var.get()]
        if not selected_fields:
            messagebox.showerror("Błąd", "Nie wybrano żadnych pól do analizy!")
            return

        supplier = self.supplier_name.get()
        file_extension = ".xlsx" if self.output_format.get() == "Excel" else ".csv"
        output_file = filedialog.asksaveasfilename(
            defaultextension=file_extension,
            filetypes=[("Pliki Excel", "*.xlsx"), ("Pliki CSV", "*.csv")]
        )

        if not output_file:
            messagebox.showerror("Błąd", "Nie wybrano pliku do zapisania!")
            return

        start_time = time.perf_counter()
        self.progress_bar.set(0)

        invoices_data = []
        total_files = len(self.files)

        with ProcessPoolExecutor() as executor:
            process_func = partial(InvoiceParser.process_single_file, supplier=supplier,
                                   selected_fields=selected_fields)
            futures = {executor.submit(process_func, file): file for file in self.files}

            for i, future in enumerate(as_completed(futures), start=1):
                invoices_data.append(future.result())
                self.progress_bar.set(i / total_files)
                self.update_idletasks()

        InvoiceParser.save_to_file(invoices_data, output_file, self.output_format.get())

        # Resetowanie paska postępu po zakończeniu przetwarzania
        self.progress_bar.set(1)
        time.sleep(0.5)  # Krótkie opóźnienie, aby użytkownik zobaczył pełny pasek
        self.progress_bar.set(0)

        self.button_start.configure(state="normal")

        elapsed_time = time.perf_counter() - start_time
        formatted_time = f"{elapsed_time:.2f} sekund"
        messagebox.showinfo("Sukces", f"Dane zapisane do: {output_file}\nCzas przetwarzania: {formatted_time}")


if __name__ == "__main__":
    app = InvoiceProcessorGUI()
    app.mainloop()
