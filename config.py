import re

# ✅ Konfiguracja dostawców faktur oraz ich wzorców regex
SUPPLIER_PATTERNS = {
    "MAG Dystrybucja": {
        "invoice_number": re.compile(r"nr\s*\(S\)FS-([A-Z0-9/_]+)"),
        "issue_date": re.compile(r"Data wystawienia:\s*(\d{4}-\d{2}-\d{2})"),
        "sale_date": re.compile(r"Data sprzedaży:\s*(\d{4}-\d{2}-\d{2})"),
        "order_number": re.compile(r"Zamówienia:.*?(\d{8})"),
        "payment_due": re.compile(r"Forma płatności.*?\s+(\d{4}-\d{2}-\d{2})", re.DOTALL),
        "net_5%": re.compile(r"W tym:\s*5%\s*([\d\s,]+)"),
        "net_23%": re.compile(r"23% \s*([\d\s,]+)"),
    },
    "AN-BA": {
        "invoice_number": re.compile(r"Faktura VAT\s+([\w/-]+)"),
        "issue_date": re.compile(r"www\.facebook\.com/people/AN-BA\s*\n?(\d{4}-\d{2}-\d{2})"),
        "sale_date": re.compile(r"NIP:\s*957-095-88-16,\s*biuro@an-ba\.pl\s*\n?(\d{4}-\d{2}-\d{2})"),
        "order_number": re.compile(r"Uwagi\s*do\s*dokumentu:\s*(?:zam\.?\s*)?(\d+)"),
        "payment_due": re.compile(r"W\s*terminie:\s*\d+\s*dni\s*=\s*(\d{4}-\d{2}-\d{2})"),
        "net_23%": re.compile(r"Podstawowy\s*podatek\s*VAT\s*23%\s*([\d\s,]+)\s*([\d\s,]+)\s*([\d\s,]+)"),
        "total_due": re.compile(r"Razem do zapłaty:\s*([\d\s,]+)"),
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
