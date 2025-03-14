import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import concurrent.futures  # Multi-threading
from parser import InvoiceParser
from config import SUPPLIER_PATTERNS


class InvoiceProcessorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 📌 Konfiguracja okna
        self.title("📄 Invoice Processor")
        self.geometry("750x650")

        self.selected_fields = []
        self.files = []
        self.supplier_name = ctk.StringVar(value="Wybierz dostawcę")

        # 📂 Wybór plików
        ctk.CTkLabel(self, text="📂 Wybierz pliki PDF:", font=("Arial", 18, "bold")).pack(pady=10)
        ctk.CTkButton(self, text="➕ Dodaj pliki", command=self.select_files).pack(pady=5)
        self.file_listbox = ctk.CTkTextbox(self, height=80, width=600)
        self.file_listbox.pack(pady=5, fill="both", expand=True)

        # 🏢 Wybór dostawcy
        ctk.CTkLabel(self, text="🏢 Wybierz dostawcę:").pack(pady=5)
        self.supplier_dropdown = ctk.CTkComboBox(self, variable=self.supplier_name,
            values=["Wybierz dostawcę"] + list(SUPPLIER_PATTERNS.keys()),
            command=self.update_fields)
        self.supplier_dropdown.pack()

        # 🔹 Kontener na dynamiczne pola wyboru
        self.frame_checkboxes = ctk.CTkFrame(self)
        self.frame_checkboxes.pack(pady=5, fill="both", expand=True)
        self.field_vars = {}

        # 📜 Wybór formatu pliku
        self.output_format = ctk.StringVar(value="Excel")
        ctk.CTkLabel(self, text="📜 Wybierz format pliku:").pack(pady=5)
        ctk.CTkRadioButton(self, text="Excel (.xlsx)", variable=self.output_format, value="Excel").pack()
        ctk.CTkRadioButton(self, text="CSV (.csv)", variable=self.output_format, value="CSV").pack()

        # 🔹 Pasek postępu
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # 🔹 Przycisk START
        self.button_start = ctk.CTkButton(self, text="🚀 Start", command=self.start_processing)
        self.button_start.pack_forget()

    def select_files(self):
        """ 📌 Pozwala użytkownikowi wybrać pliki PDF. """
        self.files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        self.file_listbox.delete("1.0", "end")
        for file in self.files:
            self.file_listbox.insert("end", f"{Path(file).name}\n")

    def update_fields(self, selected_supplier):
        """ 📌 Aktualizuje listę pól do wyboru na podstawie dostawcy. """
        for widget in self.frame_checkboxes.winfo_children():
            widget.destroy()
        if selected_supplier == "Wybierz dostawcę":
            self.button_start.pack_forget()
            return
        self.field_vars.clear()
        patterns = SUPPLIER_PATTERNS.get(selected_supplier, {})
        for field in patterns.keys():
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(self.frame_checkboxes, text=field, variable=var)
            cb.pack(anchor="w", padx=10)
            self.field_vars[field] = var
        self.button_start.pack(pady=10)

    def process_single_file(self, file, supplier, selected_fields):
        """ 📌 Przetwarza pojedynczy plik PDF i zwraca dane """
        text = InvoiceParser.extract_text_from_pdf(file)
        data = InvoiceParser.extract_data(text, supplier, selected_fields)
        data["file_name"] = Path(file).name
        return data

    def start_processing(self):
        """ 📌 Przetwarza faktury równolegle i zapisuje wyniki do pliku. """
        if not self.files:
            messagebox.showerror("❌ Błąd", "Nie wybrano żadnych plików!")
            return

        selected_fields = [field for field, var in self.field_vars.items() if var.get()]
        if not selected_fields:
            messagebox.showerror("❌ Błąd", "Nie wybrano żadnych pól do analizy!")
            return

        supplier = self.supplier_name.get()
        file_extension = ".xlsx" if self.output_format.get() == "Excel" else ".csv"
        output_file = filedialog.asksaveasfilename(defaultextension=file_extension, filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")])

        if not output_file:
            messagebox.showerror("❌ Błąd", "Nie wybrano pliku do zapisania!")
            return

        # ✅ WYŁĄCZ PRZYCISK START W TRAKCIE PRZETWARZANIA
        self.button_start.configure(state="disabled")
        self.progress_bar.set(0)

        invoices_data = []
        total_files = len(self.files)

        # ✅ Wykorzystujemy wielowątkowość do przetwarzania plików szybciej!
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.process_single_file, file, supplier, selected_fields): file for file in self.files}

            for i, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                invoices_data.append(future.result())

                # ✅ AKTUALIZACJA PASKA POSTĘPU
                self.progress_bar.set(i / total_files)
                self.update_idletasks()  # Odświeżenie GUI

        InvoiceParser.save_to_file(invoices_data, output_file, self.output_format.get())

        # ✅ PASEK POSTĘPU NA 100% I PRZYCISK ZNÓW WŁĄCZONY
        self.progress_bar.set(1)
        self.button_start.configure(state="normal")

        messagebox.showinfo("✅ Sukces", f"Dane zapisane do: {output_file}")


if __name__ == "__main__":
    app = InvoiceProcessorGUI()
    app.mainloop()
