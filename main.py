import os
import pdfplumber
import re
import pandas as pd
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from itertools import islice


class InvoiceProcessor:
    """
    Class responsible for extracting invoice data from PDF files and exporting it to CSV and Excel.
    Klasa odpowiedzialna za ekstrakcję danych z faktur PDF i eksportowanie ich do plików CSV i Excel.
    """

    def __init__(self, folder_path: str, output_file: str, batch_size: int = 10):
        self.folder_path = Path(folder_path)
        self.output_file = Path(output_file)
        self.batch_size = batch_size

        # Precompiled regex patterns for data extraction
        # Wstępnie skompilowane wyrażenia regularne do ekstrakcji danych
        self.patterns = {
            "invoice_number": re.compile(r"nr\s*\(S\)FS-([A-Z0-9/_]+)"),
            "issue_date": re.compile(r"Data wystawienia:\s*(\d{4}-\d{2}-\d{2})"),
            "sale_date": re.compile(r"Data sprzedaży:\s*(\d{4}-\d{2}-\d{2})"),
            "order_number": re.compile(r"Zamówienia:.*?(\d{8})"),
            "payment_due": re.compile(r"Forma płatności.*?\s+(\d{4}-\d{2}-\d{2})", re.DOTALL),
            "net_5%": re.compile(r"W tym:\s*5%\s*([\d\s,]+)"),
            "net_23%": re.compile(r"23% \s*([\d\s,]+)"),
        }

        # Alternative order number regex
        # Alternatywne wyrażenie regularne dla numeru zamówienia
        self.alt_order_number = re.compile(r"zam\s*(\d{8})", re.IGNORECASE)

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from a given PDF file.
        Ekstrakcja tekstu z podanego pliku PDF.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return "\n".join(filter(None, (page.extract_text() for page in pdf.pages)))
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return ""

    def clean_number(self, value: str) -> float | None:
        """
        Convert a formatted string number to a float.
        Konwersja sformatowanej liczby na wartość zmiennoprzecinkową.
        """
        if not value:
            return None
        match = re.search(r"\d{1,3}(?: \d{3})*,\d+", value)
        if match:
            return round(float(match.group(0).replace(" ", "").replace(",", ".")), 2)
        return None

    def extract_invoice_data(self, text: str) -> dict:
        """
        Extract relevant invoice data using regex patterns.
        Ekstrakcja kluczowych danych z faktury przy użyciu wyrażeń regularnych.
        """
        data = {key: None for key in self.patterns.keys()}

        for key, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                data[key] = self.clean_number(matches[0]) if key in ["net_5%", "net_23%"] else matches[0].strip()

        # Fallback for order number
        # Alternatywna metoda pobierania numeru zamówienia
        if not data["order_number"]:
            match = self.alt_order_number.search(text)
            if match:
                data["order_number"] = match.group(1).strip()

        return data

    def process_single_invoice(self, file: Path) -> dict:
        """
        Process a single invoice file and extract its data.
        Przetwarza pojedynczy plik faktury i ekstrahuje dane.
        """
        text = self.extract_text_from_pdf(file)
        invoice_data = self.extract_invoice_data(text)
        invoice_data["file_name"] = file.name
        return invoice_data

    def batch_iterator(self, iterable):
        """
        Create batches of items for processing.
        Tworzy partie elementów do przetwarzania.
        """
        iterator = iter(iterable)
        while batch := list(islice(iterator, self.batch_size)):
            yield batch

    def process_invoices(self):
        """
        Process all invoices in the specified folder using multiprocessing.
        Przetwarza wszystkie faktury w podanym folderze, wykorzystując multiprocessing.
        """
        pdf_files = list(self.folder_path.glob("*.pdf"))
        invoices_data = []

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            for batch in self.batch_iterator(pdf_files):
                results = executor.map(self.process_single_invoice, batch)
                invoices_data.extend(results)

        df = pd.DataFrame(invoices_data)
        df.to_csv(self.output_file.with_suffix(".csv"), index=False)
        df.to_excel(self.output_file, index=False)


# ============================== RUN SCRIPT ====================================
if __name__ == "__main__":
    FOLDER_PATH = "pdf"
    OUTPUT_FILE = "pdf/invoices_data.xlsx"

    print("Starting PDF invoice processing...")
    start_time = time.perf_counter()

    processor = InvoiceProcessor(FOLDER_PATH, OUTPUT_FILE)
    processor.process_invoices()

    elapsed_time = time.perf_counter() - start_time
    print(f"Processing completed in {elapsed_time:.2f} seconds. Data saved to: {OUTPUT_FILE}")
