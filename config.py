import re

# ✅ Konfiguracja dostawców faktur oraz ich wzorców regex
SUPPLIER_PATTERNS = {
    "MAG Dystrybucja": {
        "Numer faktóry": re.compile(r"nr\s*\(S\)FS-([A-Z0-9/_]+)"),
        "Data wystawienia": re.compile(r"Data wystawienia:\s*(\d{4}-\d{2}-\d{2})"),
        "Data sprzedaży": re.compile(r"Data sprzedaży:\s*(\d{4}-\d{2}-\d{2})"),
        "Sklep": re.compile(r"SKL(?:EP)?[.\s]+(\d{3,4})"),
        "Numer zamówienia": re.compile(r"(?:Zamówienia:.*?|zam\s*)(\d{8})", re.IGNORECASE),
        "Termin płatności": re.compile(r"Forma płatności.*?\s+(\d{4}-\d{2}-\d{2})", re.DOTALL),
        "VAT 5%": re.compile(r"W tym:\s*5%\s*([\d\s,]+)"),
        "VAT 23%": re.compile(r"23% \s*([\d\s,]+)"),
        "Brutto": re.compile(r"Razem do zapłaty:\s*([\d\s,]+)"),
    },
    "AN-BA": {
        "Numer faktóry": re.compile(r"Faktura VAT\s+([\w/-]+)"),
        "Data wystawienia": re.compile(r"www\.facebook\.com/people/AN-BA\s*\n?(\d{4}-\d{2}-\d{2})"),
        "Data sprzedaży": re.compile(r"NIP:\s*957-095-88-16,\s*biuro@an-ba\.pl\s*\n?(\d{4}-\d{2}-\d{2})"),
        "Numer zamówienia": re.compile(r"Uwagi\s*do\s*dokumentu:\s*(?:zam\.?\s*)?(\d+)"),
        "Termin płatności": re.compile(r"W\s*terminie:\s*\d+\s*dni\s*=\s*(\d{4}-\d{2}-\d{2})"),
        "VAT 23%": re.compile(r"Podstawowy\s*podatek\s*VAT\s*23%\s*([\d\s,]+)\s*([\d\s,]+)\s*([\d\s,]+)"),
        "Brutto": re.compile(r"Razem do zapłaty:\s*([\d\s,]+)"),
        "Sklep": re.compile(r"ID[:\s]+(\d{3,4})"),
    }
}

# ✅ Alternatywne wzorce regex do użycia, jeśli podstawowe nie znajdą wartości
ALTERNATIVE_PATTERNS = {
    "MAG Dystrybucja": {
        "order_number": re.compile(r"zam\s*(\d{8})", re.IGNORECASE),
    },
    "AN-BA": {
        "order_number": re.compile(r"Numer\s*zamówienia\s*:\s*(\d+)", re.IGNORECASE),
    }
}
STORE_EMAILS_FILE = "Baza_01_01_2025.xlsx"
