import os
import sys
import re
import pdfplumber
import pandas as pd
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from itertools import islice
from config import SUPPLIER_PATTERNS, ALTERNATIVE_PATTERNS, STORE_EMAILS_FILE


class InvoiceParser:
    """
    High-performance invoice parser using parallel processing.
    Wysokowydajny parser faktur wykorzystujący przetwarzanie równoległe.
    """

    @classmethod
    def extract_data(cls, text: str, supplier: str, selected_fields: list) -> dict:
        """
        Extracts invoice data using optimized regex matching.
        Ekstrahuje dane faktury przy użyciu zoptymalizowanego wyszukiwania regex.
        """
        primary_patterns = SUPPLIER_PATTERNS.get(supplier, {})
        alternative_patterns = ALTERNATIVE_PATTERNS.get(supplier, {})
        data = {key: None for key in selected_fields}

        # ✅ Przetwarzanie regex w jednym przebiegu
        for key in selected_fields:
            extracted_value = cls._search_patterns(text, primary_patterns.get(key), alternative_patterns.get(key))

            # ✅ Sprawdzamy, czy wartość to liczba (VAT, NET, TOTAL)
            if extracted_value and any(sub in key.lower() for sub in ["net", "vat", "total"]):
                extracted_value = cls.clean_number(extracted_value)

            data[key] = extracted_value

        data["supplier"] = supplier
        return data

    @staticmethod
    def _search_patterns(text: str, primary_pattern, alternative_pattern):
        """
        Searches for data using primary and alternative regex patterns.
        Wyszukuje dane przy użyciu głównego i alternatywnego wzorca regex.
        """
        for pattern in (primary_pattern, alternative_pattern):
            if pattern:
                match = pattern.search(text)
                if match:
                    return match.group(1).strip()
        return None

    @staticmethod
    def clean_number(value: str) -> float | None:
        """
        Converts formatted number string to float, handling VAT, net, and total amounts.
        Konwertuje sformatowaną liczbę na typ float, obsługując VAT, NET i TOTAL.
        """
        if not value:
            return None

        # ✅ Dopasowanie liczb z separatorami (np. "1 234,56" lub "1.234,56")
        match = re.search(r"\d{1,3}(?:[ \.]\d{3})*,\d+|\d+", value)
        if match:
            number = match.group(0).replace(" ", "").replace(".", "").replace(",", ".")  # Usuwamy spacje i formatowanie
            return round(float(number), 2)  # Zwracamy jako float z dwoma miejscami po przecinku

        return None

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Efficiently extracts text from a PDF file using optimized reading.
        Efektywnie ekstrahuje tekst z pliku PDF przy użyciu zoptymalizowanego odczytu.
        """
        with pdfplumber.open(pdf_path) as pdf:
            return " ".join(filter(None, (page.extract_text() for page in pdf.pages)))

    @staticmethod
    def batch_process(files, supplier, selected_fields, batch_size=5):
        """
        Processes PDF files in batches using multiple CPU cores.
        Przetwarza pliki PDF w partiach, używając wielu rdzeni CPU.
        """
        num_workers = os.cpu_count() or 2  # Użyj liczby rdzeni CPU lub minimum 2

        results = []
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            while files:
                batch = list(islice(files, batch_size))  # Pobiera kolejne batch_size plików
                future_results = executor.map(InvoiceParser.process_single_file, batch, [supplier] * len(batch),
                                              [selected_fields] * len(batch))
                results.extend(future_results)

        return results

    @staticmethod
    def process_single_file(pdf_path: str, supplier: str, selected_fields: list) -> dict:
        """
        Processes a single PDF file and extracts relevant data.
        Przetwarza pojedynczy plik PDF i ekstrahuje dane.
        """
        text = InvoiceParser.extract_text_from_pdf(pdf_path)
        data = InvoiceParser.extract_data(text, supplier, selected_fields)
        data["file_name"] = Path(pdf_path).name
        return data

    @staticmethod
    def save_to_file(data: list, output_file: str, file_format: str) -> None:
        """
        Saves extracted data to an Excel or CSV file.
        Zapisuje wyekstrahowane dane do pliku Excel lub CSV.
        """
        df = pd.DataFrame(data)
        if file_format == "Excel":
            df.to_excel(output_file, index=False, engine="openpyxl")
        else:
            df.to_csv(output_file, index=False)

    @staticmethod
    def resource_path(relative_path: str) -> str:
        """
        Returns absolute path to resource file, supporting PyInstaller environment.
        Zwraca bezwzględną ścieżkę do pliku zasobu, wspierając środowisko PyInstaller.
        """
        try:
            base_path = sys._MEIPASS  # Ścieżka tymczasowa tworzona przez PyInstaller
        except AttributeError:
            base_path = os.path.abspath(".")  # Ścieżka do katalogu bieżącego podczas uruchamiania lokalnie

        return os.path.join(base_path, relative_path)

    @staticmethod
    def match_store_email(data: list) -> list:
        """
        Matches store numbers from invoices with corresponding email addresses if the "Sklep" column exists.
        Dopasowuje numery sklepów do e-maili, jeśli kolumna "Sklep" istnieje.
        """
        excel_path = InvoiceParser.resource_path(STORE_EMAILS_FILE)

        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Plik bazy e-maili nie został znaleziony: {excel_path}")

        # Wczytanie bazy e-maili sklepów
        store_emails_df = pd.read_excel(excel_path, dtype={"GOLD": str})
        store_email_dict = dict(zip(store_emails_df["GOLD"].astype(str), store_emails_df["Adres e-mail sklepu"]))

        # Sprawdzenie, czy w danych faktur jest kolumna "Sklep"
        if not any("Sklep" in invoice for invoice in data):
            return data  # Jeśli brak kolumny "Sklep", zwracamy dane bez zmian

        # Dopasowanie e-maili do faktur
        for invoice in data:
            store_number = str(invoice.get("Sklep", ""))
            invoice["E-mail sklepu"] = store_email_dict.get(store_number, "Brak e-maila")

        return data

    @staticmethod
    def preprocess_gold_data(gold_df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans and processes GOLD data by aggregating duplicate order numbers and selecting the correct invoice number.
        Oczyszcza i przetwarza dane GOLD poprzez sumowanie duplikatów Nr Zamówienia i wybór poprawnego Nr faktury.

        :param gold_df: DataFrame containing raw GOLD data.
        :return: Processed DataFrame with aggregated values.
        """
        required_columns = ["Nr Zamówienia", "Nr faktury", "Brutto"]

        # ✅ Validation: Ensure required columns exist
        if not all(col in gold_df.columns for col in required_columns):
            raise ValueError(
                f"Błąd: brak wymaganych kolumn w pliku GOLD. Oczekiwano {required_columns}. Znalezione: {list(gold_df.columns)}"
            )

        # ✅ Convert empty invoice numbers to NaN for easier filtering
        gold_df["Nr faktury"] = gold_df["Nr faktury"].replace("", np.nan)

        # ✅ Aggregate duplicate orders by summing "Brutto" and selecting the first valid invoice number
        grouped = gold_df.groupby("Nr Zamówienia").agg(
            {
                "Brutto": "sum",  # Sum all "Brutto" values for the same order number
                "Nr faktury": lambda x: next((val for val in x if pd.notna(val)), x.iloc[-1])
                # Select the first non-null invoice number, or the last one if all are NaN
            }
        ).reset_index()

        return grouped

    @staticmethod
    def load_gold_data(file_path: str) -> pd.DataFrame:
        """
        Loads and preprocesses GOLD data from an Excel file.
        Wczytuje i przetwarza dane GOLD z pliku Excel.

        :param file_path: Path to the GOLD Excel file.
        :return: Processed DataFrame with cleaned GOLD data.
        """
        required_columns = ["Nr Zamówienia", "Nr faktury", "Brutto"]

        # ✅ Load the Excel file, skipping the first row, and enforce column data types
        gold_df = pd.read_excel(file_path, skiprows=1, dtype={"Nr Zamówienia": str, "Nr faktury": str, "Brutto": float})

        # ✅ Validation: Ensure required columns exist
        missing_columns = [col for col in required_columns if col not in gold_df.columns]
        if missing_columns:
            raise ValueError(
                f"Błąd: brak wymaganych kolumn w pliku GOLD. Oczekiwano {required_columns}. Znalezione: {list(gold_df.columns)}"
            )

        # ✅ Process duplicates (sum "Brutto", select correct "Nr faktury")
        return InvoiceParser.preprocess_gold_data(gold_df)

    @staticmethod
    def compare_with_gold(invoices: list, gold_df: pd.DataFrame) -> list:
        """
        Compares extracted invoices with GOLD data using order numbers.
        Porównuje wyekstrahowane faktury z danymi GOLD na podstawie numeru zamówienia.

        :param invoices: List of extracted invoice dictionaries.
        :param gold_df: Processed DataFrame with GOLD data.
        :return: Updated list of invoices with GOLD comparisons.
        """
        # ✅ Convert GOLD data to a dictionary for fast lookups
        gold_dict = gold_df.set_index("Nr Zamówienia").to_dict(orient="index")

        for invoice in invoices:
            order_number = str(invoice.get("Numer zamówienia", "")).strip()

            if order_number in gold_dict:
                gold_data = gold_dict[order_number]
                invoice["Brutto GOLD"] = gold_data.get("Brutto", "Brak danych")
                invoice["Nr faktury GOLD"] = gold_data.get("Nr faktury", "Brak danych")

                # ✅ Verify if the "Brutto" amount matches
                invoice["Brutto zgodne?"] = "TAK" if str(invoice.get("Brutto", "")) == str(
                    gold_data.get("Brutto", "")) else "NIE"
            else:
                invoice["Brutto GOLD"] = "Brak w GOLD"
                invoice["Nr faktury GOLD"] = "Brak w GOLD"
                invoice["Brutto zgodne?"] = "NIE"

        return invoices