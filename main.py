import os
import re
import time
import pdfplumber
import pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from itertools import islice


class InvoiceParser:
    """
    Uniwersalny parser faktur wykrywający dostawcę i ekstrahujący dane na podstawie wzorców regex.
    Universal Invoice Parser that detects the supplier and extracts relevant invoice data based on predefined regex patterns.
    """

    SUPPLIER_PATTERNS = {
        "MAG Dystrybucja": {
            "invoice_number": re.compile(r"nr\s*\(S\)FS-([A-Z0-9/_]+)"),
            "issue_date": re.compile(r"Data wystawienia:\s*(\d{4}-\d{2}-\d{2})"),
            "sale_date": re.compile(r"Data sprzedaży:\s*(\d{4}-\d{2}-\d{2})"),
            "order_number": re.compile(r"Zamówienia:.*?(\d{8})"),
            "payment_due": re.compile(r"Forma płatności.*?\s+(\d{4}-\d{2}-\d{2})", re.DOTALL),
            "net_5%": re.compile(r"W tym:\s*5%\s*([\d\s,]+)"),
            "net_23%": re.compile(r"23% \s*([\d\s,]+)")
        },
        "AN-BA": {
            "invoice_number": re.compile(r"Faktura VAT\s+([\w/-]+)"),
            "issue_date": re.compile(r"www\.facebook\.com/people/AN-BA\s*\n?(\d{4}-\d{2}-\d{2})"),
            "sale_date": re.compile(r"NIP:\s*957-095-88-16,\s*biuro@an-ba\.pl\s*\n?(\d{4}-\d{2}-\d{2})"),
            "order_number": re.compile(r"Uwagi\s*do\s*dokumentu:\s*(?:zam\.?\s*)?(\d+)"),
            "payment_due": re.compile(r"W\s*terminie:\s*\d+\s*dni\s*=\s*(\d{4}-\d{2}-\d{2})"),
            "net_23%": re.compile(r"Podstawowy\s*podatek\s*VAT\s*23%\s*([\d\s,]+)\s*([\d\s,]+)\s*([\d\s,]+)"),
            "total_due": re.compile(r"Razem do zapłaty:\s*([\d\s,]+)"),
            "store_id": re.compile(r"ID[:\s]+(\d{3,4})")
        }
    }

    @classmethod
    def detect_supplier(cls, text: str) -> str | None:
        """
        Wykrywa dostawcę na podstawie znanych wzorców w tekście faktury.
        Detects the supplier based on known patterns in the invoice text.
        """
        for supplier in cls.SUPPLIER_PATTERNS:
            if supplier in text:
                return supplier
        return None

    @classmethod
    def extract_data(cls, text: str, supplier_override: str = None) -> dict:
        """
        Ekstrahuje dane faktury na podstawie wykrytego lub podanego dostawcy.
        Extracts invoice data based on detected or specified supplier.
        """
        supplier = supplier_override or cls.detect_supplier(text)
        patterns = cls.SUPPLIER_PATTERNS.get(supplier, {})

        data = {key: None for key in patterns}
        for key, pattern in patterns.items():
            match = pattern.search(text)
            if match:
                data[key] = cls.clean_number(match.group(1)) if "net" in key else match.group(1).strip()

        data["supplier"] = supplier or "unknown"
        return data

    @staticmethod
    def clean_number(value: str) -> float | None:
        """
        Konwertuje sformatowaną liczbę na typ float.
        Converts formatted number string to float.
        """
        if not value:
            return None
        match = re.search(r"\d{1,3}(?: \d{3})*,\d+", value)
        return round(float(match.group(0).replace(" ", "").replace(",", ".")), 2) if match else None


class InvoiceProcessor:
    """
    Przetwarza faktury PDF z podanego folderu i eksportuje dane do CSV/Excel.
    Processes invoice PDFs from a given folder and exports extracted data to CSV/Excel.
    """

    def __init__(self, folder_path: str, output_file: str, batch_size: int = 10, supplier_name: str = None):
        self.folder_path = Path(folder_path)
        self.output_file = Path(output_file)
        self.batch_size = batch_size
        self.supplier_name = supplier_name

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Ekstrahuje tekst z podanego pliku PDF.
        Extracts text from a given PDF file.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return "\n".join(filter(None, (page.extract_text() for page in pdf.pages)))
        except Exception as e:
            print(f"❌ Błąd przetwarzania {pdf_path}: {e}")
            return ""

    def process_single_invoice(self, file: Path) -> dict:
        """
        Przetwarza pojedynczą fakturę i ekstrahuje jej dane.
        Processes a single invoice file and extracts its data.
        """
        text = self.extract_text_from_pdf(file)
        invoice_data = InvoiceParser.extract_data(text, self.supplier_name)
        invoice_data["file_name"] = file.name
        return invoice_data

    def batch_iterator(self, iterable):
        """
        Tworzy partie elementów do przetwarzania.
        Creates batches of items for processing.
        """
        iterator = iter(iterable)
        while batch := list(islice(iterator, self.batch_size)):
            yield batch

    def process_invoices(self):
        """
        Przetwarza wszystkie faktury w określonym folderze, wykorzystując multiprocessing.
        Processes all invoices in the specified folder using multiprocessing.
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


# ============================== URUCHOMIENIE SKRYPTU ====================================
if __name__ == "__main__":
    FOLDER_PATH = "pdf"
    OUTPUT_FILE = "pdf/invoices_data.xlsx"
    SUPPLIER_NAME = input("Podaj nazwę dostawcy (lub zostaw puste dla automatycznego wykrycia): ").strip()

    print("🚀 Rozpoczynam przetwarzanie faktur PDF...")
    start_time = time.perf_counter()

    processor = InvoiceProcessor(FOLDER_PATH, OUTPUT_FILE, supplier_name=SUPPLIER_NAME or None)
    processor.process_invoices()

    elapsed_time = time.perf_counter() - start_time
    print(f"✅ Przetwarzanie zakończone w {elapsed_time:.2f} sekund. Dane zapisano do: {OUTPUT_FILE}")
