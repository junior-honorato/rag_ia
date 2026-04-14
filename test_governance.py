from governance import redact_text

def test_advanced_redaction():
    print("--- INICIANDO TESTES DE GOVERNANÇA AVANÇADA ---\n")
    
    cases = [
        # LEVEL 1: Identidade
        ("CPF: 123.456.789-00", "[CPF_REDACTED]", 1),
        ("Email: suporte@banco.com", "[EMAIL_REDACTED]", 1),
        
        # LEVEL 2: Bancário
        ("Cartão: 4111222233334444", "[CREDIT_CARD_REDACTED]", 2),
        ("Agência 1234 Conta 56789-0", "Agência [BANK_ACCOUNT_REDACTED] Conta [BANK_ACCOUNT_REDACTED]", 2),
        
        # LEVEL 3: Seguro e Patrimônio
        ("Apólice: 100200300400500", "Apólice: [POLICY_CLAIM_REDACTED]", 3),
        ("Sinistro: 2024999888777", "Sinistro: [POLICY_CLAIM_REDACTED]", 3),
        ("Placa: ABC-1234", "Placa: [VEHICLE_PLATE_REDACTED]", 3),
        ("Placa: BRA2E19", "Placa: [VEHICLE_PLATE_REDACTED]", 3),
        
        # LEVEL 4: Saúde
        ("Diagnóstico CID: J45.0", "Diagnóstico CID: [DISEASE_CID_REDACTED]", 4),
    ]
    
    for original, expected_snippet, level in cases:
        result = redact_text(original, max_level=level)
        assert expected_snippet in result, f"Falha no Nível {level}: {original}\nEsperado conter: {expected_snippet}\nRecebido: {result}"
        print(f"PASS (Nível {level}): {original} -> {result}")

def test_level_isolation():
    print("\n--- TESTANDO ISOLAMENTO DE NÍVEIS ---")
    text = "CPF 123.456.789-00 e Cartão 4111222233334444"
    
    # Nível 1 não deve pegar cartão
    res_l1 = redact_text(text, max_level=1)
    assert "[CPF_REDACTED]" in res_l1
    assert "4111222233334444" in res_l1
    print("PASS: Nível 1 isolado (não pegou cartão)")
    
    # Nível 2 deve pegar ambos
    res_l2 = redact_text(text, max_level=2)
    assert "[CPF_REDACTED]" in res_l2
    assert "[CREDIT_CARD_REDACTED]" in res_l2
    print("PASS: Nível 2 capturou ambos")

if __name__ == "__main__":
    try:
        test_advanced_redaction()
        test_level_isolation()
        print("\nTodos os testes avançados passaram!")
    except AssertionError as e:
        print(f"\nERRO NO TESTE: {e}")
