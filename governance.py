import re

# Níveis de risco e seus padrões associados
# Cada nível herda ou complementa o anterior se desejado,
# mas aqui definimos as categorias para controle granular.
RISK_PATTERNS = {
    "LEVEL_1": {  # Identidade e Contato
        "EMAIL": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "CNPJ": r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b",
        "CPF": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b",
        "PHONE": r"(?:\b|\()(?:\d{2}\)?\s?9\d{4}-?\d{4}\b|\d{2}\)?\s?\d{4}-?\d{4}\b)",
    },
    "LEVEL_2": {  # Dados Bancários (Sigilo Bancário)
        "CREDIT_CARD": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|2(?:2(?:2[1-9]|[3-9][0-9])|[3-6][0-9][0-9]|7(?:[01][0-9]|20))[0-9]{12}|3[47][0-9]{13})\b",
        "BANK_ACCOUNT": r"\b\d{1,5}-?\d{1,12}\b", # Agência ou Conta
    },
    "LEVEL_3": {  # Dados de Seguradora e Patrimônio
        "POLICY_CLAIM": r"\b\d{10,20}\b", # Números longos de apólices ou sinistros
        "VEHICLE_PLATE": r"\b[A-Z]{3}-\d{4}\b|\b[A-Z]{3}\d[A-Z]\d{2}\b", # Comum e Mercosul
    },
    "LEVEL_4": {  # Dados Sensíveis de Saúde
        "DISEASE_CID": r"\b[A-Z]\d{2}(?:\.\d{1,2})?\b", # Código CID-10
    }
}

def redact_text(text: str, max_level: int = 4) -> str:
    """
    Substitui padrões de PII e dados sensíveis por placeholders, filtrando até o nível de risco desejado.
    
    Args:
        text: O texto original a ser processado.
        max_level: O nível máximo de risco a ser aplicado (1 a 4). Padrão é 4 (Segurança Máxima).
    """
    if not text:
        return text
        
    redacted_text = text
    
    # Coletamos todos os padrões dos níveis selecionados
    active_patterns = {}
    for level in range(1, max_level + 1):
        level_key = f"LEVEL_{level}"
        if level_key in RISK_PATTERNS:
            active_patterns.update(RISK_PATTERNS[level_key])
            
    # Ordem de aplicação recomendada para evitar colisões
    # Prioridade para padrões mais longos ou específicos
    priority_order = [
        "EMAIL", "CREDIT_CARD", "CNPJ", "VEHICLE_PLATE", 
        "CPF", "POLICY_CLAIM", "BANK_ACCOUNT", "PHONE", "DISEASE_CID"
    ]
    
    for pii_type in priority_order:
        if pii_type in active_patterns:
            pattern = active_patterns[pii_type]
            placeholder = f"[{pii_type}_REDACTED]"
            redacted_text = re.sub(pattern, placeholder, redacted_text)
            
    return redacted_text

if __name__ == "__main__":
    # Teste de demonstração dos níveis
    sample = "O cliente CPF 123.456.789-00 com cartão 4111222233334444 e placa ABC-1234 tem CID J45."
    print(f"Original: {sample}")
    print(f"Nível 1: {redact_text(sample, max_level=1)}")
    print(f"Nível 2: {redact_text(sample, max_level=2)}")
    print(f"Nível 3: {redact_text(sample, max_level=3)}")
    print(f"Nível 4: {redact_text(sample, max_level=4)}")
