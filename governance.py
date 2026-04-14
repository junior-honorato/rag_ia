import re

# Padrões de PII Brasileiros
REGEX_PATTERNS = {
    "EMAIL": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    "PHONE": r"(?:\b|\()(?:\d{2}\)?\s?9\d{4}-?\d{4}\b|\d{2}\)?\s?\d{4}-?\d{4}\b)",
    "CNPJ": r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b",
    "CPF": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b",
}

def redact_text(text: str) -> str:
    """
    Substitui padrões de PII (CPF, CNPJ, Email, Telefone) por placeholders.
    """
    if not text:
        return text
        
    redacted_text = text
    
    # Ordem de aplicação: Email -> CNPJ -> CPF -> PHONE
    # Isso ajuda a capturar números longos (14 ou 11 dígitos) antes de tentar padrões de telefone.
    order = ["EMAIL", "CNPJ", "CPF", "PHONE"]
    
    for pii_type in order:
        pattern = REGEX_PATTERNS[pii_type]
        placeholder = f"[{pii_type}_REDACTED]"
        redacted_text = re.sub(pattern, placeholder, redacted_text)
        
    return redacted_text

if __name__ == "__main__":
    # Teste rápido
    test_str = "Meu CPF é 123.456.789-00 e meu email é teste@gmail.com. Ligue para (11) 98888-7777."
    print(f"Original: {test_str}")
    print(f"Redacted: {redact_text(test_str)}")
