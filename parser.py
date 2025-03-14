import os
import re
import pdfplumber
import pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from itertools import islice
from config import SUPPLIER_PATTERNS, ALTERNATIVE_PATTERNS


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
            data[key] = cls._search_patterns(text, primary_patterns.get(key), alternative_patterns.get(key))

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
                    return InvoiceParser.clean_number(match.group(1)) if "net" in pattern.pattern or "total" in pattern.pattern else match.group(1).strip()
        return None

    @staticmethod
    def clean_number(value: str) -> float | None:
        """
        Converts formatted number string to float.
        Konwertuje sformatowaną liczbę na typ float.
        """
        if not value:
            return None
        match = re.search(r"\d{1,3}(?: \d{3})*,\d+", value)
        return round(float(match.group(0).replace(" ", "").replace(",", ".")), 2) if match else None

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
                future_results = executor.map(lambda f: InvoiceParser.process_single_file(f, supplier, selected_fields), batch)
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
