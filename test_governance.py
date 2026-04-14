from governance import redact_text

def test_redaction():
    cases = [
        ("CPF formatado: 123.456.789-00", "CPF formatado: [CPF_REDACTED]"),
        ("CPF limpo: 12345678901", "CPF limpo: [CPF_REDACTED]"),
        ("CNPJ formatado: 12.345.678/0001-99", "CNPJ formatado: [CNPJ_REDACTED]"),
        ("CNPJ limpo: 12345678000199", "CNPJ limpo: [CNPJ_REDACTED]"),
        ("Email: joao.silva@exemplo.com.br", "Email: [EMAIL_REDACTED]"),
        ("Telefone 1: (11) 99999-8888", "Telefone 1: [PHONE_REDACTED]"),
        ("Telefone 2: 21988887777", "Telefone 2: [PHONE_REDACTED]"),
        ("Telefone 3: 1133334444", "Telefone 3: [PHONE_REDACTED]"),
        ("Texto misto: O e-mail do cliente 123.456.789-00 é cliente@site.com", "Texto misto: O e-mail do cliente [CPF_REDACTED] é [EMAIL_REDACTED]"),
    ]
    
    for original, expected in cases:
        result = redact_text(original)
        assert result == expected, f"Falha no caso: {original}\nEsperado: {expected}\nRecebido: {result}"
        print(f"PASS: {original} -> {result}")

if __name__ == "__main__":
    try:
        test_redaction()
        print("\nTodos os testes passaram!")
    except AssertionError as e:
        print(f"\nERRO NO TESTE: {e}")
