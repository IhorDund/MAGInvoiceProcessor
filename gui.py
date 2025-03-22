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
        """
        Inicjalizacja głównego okna aplikacji GUI.
        - Ustawia tytuł i rozmiar okna.
        - Inicjalizuje zmienne dla wyboru plików, dostawców i pól formularza.
        - Tworzy interfejs użytkownika z odpowiednimi kontrolkami.

        Initializes the main application window.
        - Sets the title and window size.
        - Initializes variables for file selection, suppliers, and form fields.
        - Creates the user interface with necessary controls.
        """
        super().__init__()

        # Konfiguracja głównego okna GUI
        # Configure the main application window
        self.title("Przetwarzanie Faktur PDF")  # Tytuł okna / Window title
        self.geometry("750x650")  # Rozmiar okna / Window size

        # Zmienne przechowujące wybrane pliki, dostawcę i pola
        # Variables for storing selected files, supplier, and fields
        self.selected_fields = []  # Lista wybranych pól / List of selected fields
        self.files = []  # Lista wybranych plików PDF / List of selected PDF files
        self.supplier_name = ctk.StringVar(value="Wybierz dostawcę")  # Zmienna do wyboru dostawcy / Supplier selection variable

        #  Sekcja wyboru plików PDF
        #  File selection section
        ctk.CTkLabel(self, text="📂 Wybierz pliki PDF:", font=("Arial", 18, "bold")).pack(pady=10)

        button_frame = ctk.CTkFrame(self)  # Ramka dla przycisków wyboru plików / Frame for file selection buttons
        button_frame.pack(pady=5)

        # Przycisk do dodawania plików PDF / Button to add PDF files
        ctk.CTkButton(button_frame, text="➕ Dodaj pliki", command=self.select_files).pack(side="left", padx=5)

        # Przycisk do usuwania wszystkich wybranych plików / Button to clear the file list
        ctk.CTkButton(button_frame, text="🗑️ Wyczyść listę", command=self.clear_files).pack(side="left", padx=5)

        # Pole tekstowe do wyświetlania listy plików / Textbox for displaying selected files
        self.file_listbox = ctk.CTkTextbox(self, height=80, width=600, state="disabled")
        self.file_listbox.pack(pady=5, fill="both", expand=True)

        #  Sekcja wyboru dostawcy
        #  Supplier selection section
        ctk.CTkLabel(self, text="🏢 Wybierz dostawcę:").pack(pady=5)

        # Lista rozwijana z dostawcami / Dropdown list for selecting a supplier
        self.supplier_dropdown = ctk.CTkComboBox(
            self, variable=self.supplier_name,
            values=["Wybierz dostawcę"] + list(SUPPLIER_PATTERNS.keys()),
            command=self.update_fields  # Aktualizacja dostępnych pól po wyborze dostawcy / Update available fields after selecting a supplier
        )
        self.supplier_dropdown.pack()

        #  Sekcja dynamicznych pól wyboru (checkboxy)
        #  Dynamic field selection section (checkboxes)
        self.frame_checkboxes = ctk.CTkFrame(self)
        self.frame_checkboxes.pack(pady=5, fill="both", expand=True)
        self.field_vars = {}  # Słownik przechowujący zmienne checkboxów / Dictionary storing checkbox variables

        #  Sekcja wyboru formatu pliku wyjściowego
        #  Output file format selection section
        self.output_format = ctk.StringVar(value="Excel")  # Domyślny format pliku wyjściowego / Default output file format

        ctk.CTkLabel(self, text="📜 Wybierz format pliku:").pack(pady=5)

        # Przycisk do wyboru formatu Excel (.xlsx) / Button to select Excel (.xlsx) format
        ctk.CTkRadioButton(self, text="Excel (.xlsx)", variable=self.output_format, value="Excel").pack()

        # Przycisk do wyboru formatu CSV (.csv) / Button to select CSV (.csv) format
        ctk.CTkRadioButton(self, text="CSV (.csv)", variable=self.output_format, value="CSV").pack()

        #  Pasek postępu
        #  Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)  # Ustawienie początkowej wartości na 0 / Set initial progress to 0

        #  Przycisk uruchamiający przetwarzanie (na start ukryty)
        #  Start processing button (initially hidden)
        self.button_start = ctk.CTkButton(self, text="🚀 Rozpocznij przetwarzanie", command=self.start_processing)
        self.button_start.pack_forget()  # Ukrycie przycisku do momentu, gdy użytkownik wybierze pliki i dostawcę / Hide the button until files and supplier are selected

        #  Checkbox do porównania wyników z GOLD
        #  Checkbox for comparing results with GOLD
        self.compare_gold_var = ctk.BooleanVar(value=False)

        self.compare_gold_checkbox = ctk.CTkCheckBox(
            self, text="📊 Porównanie z GOLD",
            variable=self.compare_gold_var,
            command=self.select_gold_file  # Po kliknięciu od razu wybiera plik GOLD / Clicking triggers GOLD file selection
        )
        self.compare_gold_checkbox.pack(pady=5)

        #  Ścieżka do pliku GOLD (na start brak)
        #  Path to the GOLD file (initially None)
        self.gold_file_path = None

    def select_files(self):
        """
        Otwiera okno dialogowe, umożliwiające użytkownikowi wybór plików PDF.
        - Dodaje nowe pliki do listy, zamiast nadpisywać poprzednie.
        - Aktualizuje listę wybranych plików w interfejsie graficznym.
        - Blokuje edycję pola tekstowego po aktualizacji.

        Opens a file dialog allowing the user to select PDF files.
        - Appends new files to the list instead of overwriting it.
        - Updates the displayed list of selected files in the UI.
        - Disables text field editing after the update.
        """
        new_files = filedialog.askopenfilenames(
            filetypes=[("Pliki PDF", "*.pdf")])  # Otwórz okno wyboru plików / Open file selection dialog

        if new_files:
            self.files.extend(
                new_files)  # Dodaj nowe pliki do istniejącej listy / Append new files to the existing list
            self.file_listbox.configure(
                state="normal")  # Odblokuj pole tekstowe do edycji / Unlock text field for editing
            self.file_listbox.delete("1.0", "end")  # Usuń poprzednie wpisy / Clear previous entries

            for file in self.files:
                self.file_listbox.insert("end",
                                         f"{Path(file).name}\n")  # Dodaj nazwę pliku do pola tekstowego / Insert file name into text field

            self.file_listbox.configure(state="disabled")  # Zablokuj edycję pola tekstowego / Lock text field editing

    def clear_files(self):
        """
        Usuwa wszystkie wybrane pliki i czyści pole tekstowe listy plików.
        - Resetuje listę plików do pustej wartości.
        - Odblokowuje i ponownie blokuje pole tekstowe, aby usunąć stare wpisy.

        Clears all selected files and resets the file list display.
        - Resets the file list to an empty state.
        - Unlocks and re-locks the text field to remove previous entries.
        """
        self.files = []  # Wyczyść listę plików / Clear the file list
        self.file_listbox.configure(state="normal")  # Odblokuj edycję pola tekstowego / Unlock text field editing
        self.file_listbox.delete("1.0", "end")  # Usuń wszystkie wpisy / Remove all entries
        self.file_listbox.configure(state="disabled")  # Zablokuj edycję pola tekstowego / Lock text field editing

    def update_file_listbox(self):
        """
        Odświeża widok listy plików w interfejsie użytkownika.
        - Usuwa wszystkie wpisy z pola tekstowego.
        - Ponownie dodaje wszystkie aktualnie wybrane pliki.

        Refreshes the file list view in the user interface.
        - Removes all entries from the text field.
        - Re-adds all currently selected files.
        """
        self.file_listbox.configure(state="normal")  # Odblokuj edycję pola tekstowego / Unlock text field editing
        self.file_listbox.delete("1.0", "end")  # Usuń wszystkie wpisy / Remove all entries

        for file in self.files:
            self.file_listbox.insert("end", f"{Path(file).name}\n")  # Dodaj nazwę pliku / Insert file name

        self.file_listbox.configure(state="disabled")  # Zablokuj edycję pola tekstowego / Lock text field editing

    def update_fields(self, selected_supplier):
        """
        Aktualizuje listę pól do wyboru na podstawie wybranego dostawcy.
        - Usuwa poprzednie checkboxy.
        - Jeśli nie wybrano dostawcy, ukrywa przycisk START.
        - Tworzy nową siatkę checkboxów na podstawie wzorców danego dostawcy.

        Updates the selectable fields based on the selected supplier.
        - Removes old checkboxes.
        - Hides the START button if no supplier is selected.
        - Creates a new grid of checkboxes based on the supplier's patterns.
        """
        # Usuń stare checkboxy z kontenera
        # Remove old checkboxes from the container
        for widget in self.frame_checkboxes.winfo_children():
            widget.destroy()

        # Jeśli wybrano opcję domyślną, ukryj przycisk i zakończ działanie
        # If the default option is selected, hide the button and exit
        if selected_supplier == "Wybierz dostawcę":
            self.button_start.pack_forget()
            return

        # Wyczyść poprzednio zapisane zmienne pól
        # Clear previously stored field variables
        self.field_vars.clear()

        # Pobierz wzorce pól dla wybranego dostawcy
        # Retrieve field patterns for the selected supplier
        patterns = SUPPLIER_PATTERNS.get(selected_supplier, {})

        #  Ustal liczbę kolumn dla checkboxów (np. 4 równe kolumny)
        #  Set the number of columns for checkboxes (e.g., 4 equal columns)
        cols = 4
        row = 0
        col = 0

        # Skonfiguruj siatkę: ustaw równy podział kolumn
        # Configure the grid: set equal column weights
        for i in range(cols):
            self.frame_checkboxes.grid_columnconfigure(i, weight=1)

        # Dla każdego pola w wzorcach, utwórz checkbox
        # For each field in the patterns, create a checkbox
        for field in patterns.keys():
            var = ctk.BooleanVar(value=True)  # 🔹 Domyślnie checkbox zaznaczony / Checkbox is checked by default
            cb = ctk.CTkCheckBox(self.frame_checkboxes, text=field, variable=var)

            # Dodaj checkbox do siatki (grid layout) z określonymi marginesami
            # Place the checkbox in the grid with specified padding
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=5)

            # Zapisz zmienną pola w słowniku
            # Save the field variable in a dictionary
            self.field_vars[field] = var

            # Przejdź do kolejnej kolumny, a po osiągnięciu limitu przejdź do nowego wiersza
            # Move to the next column; if reached the column limit, reset column and increment row
            col += 1
            if col >= cols:
                col = 0
                row += 1

        #  Opcjonalnie: Centrowanie zawartości poprzez konfigurację pierwszej i ostatniej kolumny
        #  Optionally: Center content by configuring the first and last columns
        self.frame_checkboxes.grid_columnconfigure(0, weight=1)
        self.frame_checkboxes.grid_columnconfigure(cols - 1, weight=1)

        # Pokaż przycisk START, gdy pola są gotowe
        # Show the START button once fields are ready
        self.button_start.pack(pady=10)

    def select_gold_file(self):
        """
        Wymusza wybór pliku GOLD po zaznaczeniu checkboxa.
        - Otwiera okno dialogowe do wyboru pliku Excel.
        - Jeśli użytkownik nie wybierze pliku, wyświetla komunikat o błędzie i odznacza checkbox.

        Forces the user to select a GOLD file when the checkbox is checked.
        - Opens a file dialog for selecting an Excel file.
        - If no file is selected, displays an error message and unchecks the checkbox.
        """
        if self.compare_gold_var.get():  # Sprawdza, czy checkbox został zaznaczony / Checks if the checkbox is checked
            self.gold_file_path = filedialog.askopenfilename(
                title="Wybierz plik GOLD",  # Tytuł okna dialogowego / Dialog window title
                filetypes=[("Excel files", "*.xlsx")]
                # Ograniczenie wyboru do plików Excel / Restrict selection to Excel files
            )

            # Jeśli użytkownik nie wybrał pliku, pokaż błąd i odznacz checkbox
            # If the user didn't select a file, show an error and uncheck the checkbox
            if not self.gold_file_path:
                messagebox.showerror("Błąd", "Nie wybrano pliku GOLD!")  # Komunikat błędu / Error message
                self.compare_gold_var.set(False)  # Odznacz checkbox / Uncheck the checkbox

    def start_processing(self):
        """
        Rozpoczyna przetwarzanie wybranych faktur.
        - Sprawdza, czy użytkownik wybrał pliki oraz pola do analizy.
        - Otwiera okno dialogowe do wyboru pliku wyjściowego.
        - Uruchamia wielowątkowe przetwarzanie plików faktur.
        - Jeśli wybrano opcję porównania z GOLD, ładuje dane referencyjne i dokonuje porównania.
        - Dopasowuje e-maile sklepów do danych.
        - Zapisuje przetworzone dane do pliku (Excel/CSV).
        - Aktualizuje pasek postępu i wyświetla komunikat o zakończeniu.

        Starts processing the selected invoices.
        - Checks if the user selected files and fields for analysis.
        - Opens a save dialog for selecting the output file.
        - Runs multi-threaded processing for invoice files.
        - Loads and compares data with GOLD if the option is selected.
        - Matches store emails to the data.
        - Saves processed data to a file (Excel/CSV).
        - Updates the progress bar and displays a completion message.
        """
        # Sprawdzenie, czy wybrano pliki
        # Check if any files were selected
        if not self.files:
            messagebox.showerror("Błąd", "Nie wybrano żadnych plików!")  # Komunikat błędu / Error message
            return

        # Pobranie listy wybranych pól do analizy
        # Get the list of selected fields for analysis
        selected_fields = [field for field, var in self.field_vars.items() if var.get()]
        if not selected_fields:
            messagebox.showerror("Błąd", "Nie wybrano żadnych pól do analizy!")  # Komunikat błędu / Error message
            return

        # Pobranie nazwy dostawcy
        # Get supplier name
        supplier = self.supplier_name.get()

        # Określenie rozszerzenia pliku wyjściowego na podstawie wybranego formatu
        # Determine output file extension based on selected format
        file_extension = ".xlsx" if self.output_format.get() == "Excel" else ".csv"

        # Okno dialogowe do wyboru pliku wyjściowego
        # Save dialog for selecting the output file
        output_file = filedialog.asksaveasfilename(
            defaultextension=file_extension,
            filetypes=[("Pliki Excel", "*.xlsx"), ("Pliki CSV", "*.csv")]
        )

        # Sprawdzenie, czy użytkownik wybrał plik wyjściowy
        # Check if the user selected an output file
        if not output_file:
            messagebox.showerror("Błąd", "Nie wybrano pliku do zapisania!")  # Komunikat błędu / Error message
            return

        start_time = time.perf_counter()  # Pomiar czasu rozpoczęcia / Start time measurement
        self.progress_bar.set(0)  # Reset paska postępu / Reset progress bar

        invoices_data = []  # Lista przechowująca przetworzone dane / List to store processed data
        total_files = len(self.files)  # Liczba plików do przetworzenia / Number of files to process

        # Przetwarzanie plików faktur w wielu wątkach
        # Processing invoice files using multiple threads
        with ProcessPoolExecutor() as executor:
            process_func = partial(InvoiceParser.process_single_file, supplier=supplier,
                                   selected_fields=selected_fields)
            futures = {executor.submit(process_func, file): file for file in self.files}

            for i, future in enumerate(as_completed(futures), start=1):
                invoices_data.append(future.result())  # Pobranie wyniku przetwarzania / Get processing result
                self.progress_bar.set(i / total_files)  # Aktualizacja paska postępu / Update progress bar
                self.update_idletasks()  # Odświeżenie interfejsu / Refresh UI

        # Jeśli zaznaczono porównanie z GOLD, wczytaj dane referencyjne
        # If GOLD comparison is selected, load reference data
        if self.compare_gold_var.get():
            if not self.gold_file_path:
                messagebox.showerror("Błąd", "Nie wybrano pliku GOLD!")  # Komunikat błędu / Error message
                return

            try:
                gold_data = InvoiceParser.load_gold_data(self.gold_file_path)  # Wczytanie danych GOLD / Load GOLD data
            except Exception as e:
                messagebox.showerror("Błąd wczytywania GOLD", str(e))  # Obsługa błędu ładowania / Handle loading error
                return

            # Porównanie danych faktur z GOLD
            # Compare invoice data with GOLD
            invoices_data = InvoiceParser.compare_with_gold(invoices_data, gold_data)

        # Dopasowanie e-maili sklepów do przetworzonych danych
        # Match store emails to processed data
        invoices_data = InvoiceParser.match_store_email(invoices_data)
        # Zapisanie danych do pliku
        # Save processed data to a file
        InvoiceParser.save_to_file(invoices_data, output_file, self.output_format.get())

        # Resetowanie paska postępu po zakończeniu przetwarzania
        # Reset progress bar after processing is complete
        self.progress_bar.set(1)
        time.sleep(0.5)  # Krótkie opóźnienie dla wizualnego efektu / Short delay for visual effect
        self.progress_bar.set(0)

        self.button_start.configure(state="normal")  # Ponowne włączenie przycisku START / Re-enable START button

        # Obliczenie czasu wykonania i wyświetlenie komunikatu o sukcesie
        # Calculate elapsed time and show success message
        elapsed_time = time.perf_counter() - start_time
        formatted_time = f"{elapsed_time:.2f} sekund"  # Formatowanie czasu / Format elapsed time
        messagebox.showinfo("Sukces", f"Dane zapisane do: {output_file}\nCzas przetwarzania: {formatted_time}")
