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

        # Window configuration / Konfiguracja okna aplikacji
        self.title("Invoice Processor")
        self.geometry("750x650")

        self.selected_fields = []
        self.files = []
        self.supplier_name = ctk.StringVar(value="Wybierz dostawcę")

        # Section for selecting PDF files / Sekcja wyboru plików PDF
        ctk.CTkLabel(self, text="Select PDF files:", font=("Arial", 18, "bold")).pack(pady=10)
        ctk.CTkButton(self, text="Add files", command=self.select_files).pack(pady=5)
        self.file_listbox = ctk.CTkTextbox(self, height=80, width=600)
        self.file_listbox.pack(pady=5, fill="both", expand=True)

        # Section for selecting the supplier / Sekcja wyboru dostawcy
        ctk.CTkLabel(self, text="Select supplier:").pack(pady=5)
        self.supplier_dropdown = ctk.CTkComboBox(
            self, variable=self.supplier_name,
            values=["Wybierz dostawcę"] + list(SUPPLIER_PATTERNS.keys()),
            command=self.update_fields
        )
        self.supplier_dropdown.pack()

        # Section for dynamic field selection / Sekcja dynamicznych pól wyboru
        self.frame_checkboxes = ctk.CTkFrame(self)
        self.frame_checkboxes.pack(pady=5, fill="both", expand=True)
        self.field_vars = {}

        # Output file format selection / Sekcja wyboru formatu pliku wyjściowego
        self.output_format = ctk.StringVar(value="Excel")
        ctk.CTkLabel(self, text="Select file format:").pack(pady=5)
        ctk.CTkRadioButton(self, text="Excel (.xlsx)", variable=self.output_format, value="Excel").pack()
        ctk.CTkRadioButton(self, text="CSV (.csv)", variable=self.output_format, value="CSV").pack()

        # Progress bar / Pasek postępu
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # Start button / Przycisk uruchamiający przetwarzanie
        self.button_start = ctk.CTkButton(self, text="Start", command=self.start_processing)
        self.button_start.pack_forget()

    def select_files(self):
        """ Opens a file dialog to select PDF files. / Otwiera okno dialogowe do wyboru plików PDF. """
        self.files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        self.file_listbox.delete("1.0", "end")
        for file in self.files:
            self.file_listbox.insert("end", f"{Path(file).name}\n")

    def update_fields(self, selected_supplier):
        """ Updates the available fields for analysis based on the selected supplier. / Aktualizuje dostępne pola do analizy na podstawie wybranego dostawcy. """
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

    def start_processing(self):
        """ Starts processing selected invoices. / Rozpoczyna przetwarzanie wybranych faktur. """
        if not self.files:
            messagebox.showerror("Error", "No files selected!")
            return

        selected_fields = [field for field, var in self.field_vars.items() if var.get()]
        if not selected_fields:
            messagebox.showerror("Error", "No fields selected for analysis!")
            return

        supplier = self.supplier_name.get()
        file_extension = ".xlsx" if self.output_format.get() == "Excel" else ".csv"
        output_file = filedialog.asksaveasfilename(
            defaultextension=file_extension,
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
        )

        if not output_file:
            messagebox.showerror("Error", "No output file selected!")
            return

        start_time = time.perf_counter()

        # Disable the start button while processing / Wyłącza przycisk start podczas przetwarzania
        self.button_start.configure(state="disabled")
        self.progress_bar.set(0)

        invoices_data = []
        total_files = len(self.files)

        # Multi-threaded invoice processing / Wielowątkowe przetwarzanie faktur
        with ProcessPoolExecutor() as executor:
            process_func = partial(InvoiceParser.process_single_file, supplier=supplier, selected_fields=selected_fields)
            futures = {executor.submit(process_func, file): file for file in self.files}

            for i, future in enumerate(as_completed(futures), start=1):
                invoices_data.append(future.result())
                self.progress_bar.set(i / total_files)
                self.update_idletasks()

        InvoiceParser.save_to_file(invoices_data, output_file, self.output_format.get())

        # Processing completed / Zakończenie przetwarzania
        self.progress_bar.set(1)
        self.button_start.configure(state="normal")

        elapsed_time = time.perf_counter() - start_time
        formatted_time = f"{elapsed_time:.2f} seconds"
        messagebox.showinfo("Success", f"Data saved to: {output_file}\nProcessing time: {formatted_time}")


if __name__ == "__main__":
    app = InvoiceProcessorGUI()
    app.mainloop()
