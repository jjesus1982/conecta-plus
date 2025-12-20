"""
Conecta Plus - Testes dos Validadores
"""

import pytest
from pydantic_core import PydanticCustomError
from ..schemas.validators import (
    PasswordValidator,
    CPFValidator,
    CNPJValidator,
    PhoneValidator,
    PlacaVeiculoValidator,
    SanitizeString,
)


class TestPasswordValidator:
    """Testes do validador de senha."""

    def test_senha_valida(self):
        """Testa senha que atende todos os requisitos."""
        senha = "SenhaForte@123"
        resultado = PasswordValidator.validate(senha)
        assert resultado == senha

    def test_senha_curta(self):
        """Testa senha muito curta."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PasswordValidator.validate("Abc@1")
        assert "pelo menos 8 caracteres" in str(exc_info.value)

    def test_senha_sem_maiuscula(self):
        """Testa senha sem letra maiuscula."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PasswordValidator.validate("senhaforte@123")
        assert "maiuscula" in str(exc_info.value)

    def test_senha_sem_minuscula(self):
        """Testa senha sem letra minuscula."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PasswordValidator.validate("SENHAFORTE@123")
        assert "minuscula" in str(exc_info.value)

    def test_senha_sem_numero(self):
        """Testa senha sem numero."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PasswordValidator.validate("SenhaForte@abc")
        assert "numero" in str(exc_info.value)

    def test_senha_sem_especial(self):
        """Testa senha sem caractere especial."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PasswordValidator.validate("SenhaForte123")
        assert "especial" in str(exc_info.value)

    def test_senha_com_espaco(self):
        """Testa senha com espaco."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PasswordValidator.validate("Senha Forte@123")
        assert "espacos" in str(exc_info.value)

    def test_senha_comum(self):
        """Testa senha muito comum."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PasswordValidator.validate("password")
        assert "comum" in str(exc_info.value)


class TestCPFValidator:
    """Testes do validador de CPF."""

    def test_cpf_valido(self):
        """Testa CPF valido."""
        # CPF valido gerado para teste
        cpf = "52998224725"
        resultado = CPFValidator.validate(cpf)
        assert resultado == cpf

    def test_cpf_com_formatacao(self):
        """Testa CPF com formatacao (pontos e traco)."""
        cpf = "529.982.247-25"
        resultado = CPFValidator.validate(cpf)
        assert resultado == "52998224725"

    def test_cpf_tamanho_invalido(self):
        """Testa CPF com tamanho errado."""
        with pytest.raises(PydanticCustomError) as exc_info:
            CPFValidator.validate("1234567890")
        assert "11 digitos" in str(exc_info.value)

    def test_cpf_digitos_iguais(self):
        """Testa CPF com todos digitos iguais."""
        with pytest.raises(PydanticCustomError) as exc_info:
            CPFValidator.validate("11111111111")
        assert "invalido" in str(exc_info.value)

    def test_cpf_digito_verificador_errado(self):
        """Testa CPF com digito verificador errado."""
        with pytest.raises(PydanticCustomError) as exc_info:
            CPFValidator.validate("52998224720")  # Ultimo digito errado
        assert "invalido" in str(exc_info.value)


class TestCNPJValidator:
    """Testes do validador de CNPJ."""

    def test_cnpj_valido(self):
        """Testa CNPJ valido."""
        cnpj = "11222333000181"
        resultado = CNPJValidator.validate(cnpj)
        assert resultado == cnpj

    def test_cnpj_com_formatacao(self):
        """Testa CNPJ com formatacao."""
        cnpj = "11.222.333/0001-81"
        resultado = CNPJValidator.validate(cnpj)
        assert resultado == "11222333000181"

    def test_cnpj_tamanho_invalido(self):
        """Testa CNPJ com tamanho errado."""
        with pytest.raises(PydanticCustomError) as exc_info:
            CNPJValidator.validate("1234567890123")
        assert "14 digitos" in str(exc_info.value)

    def test_cnpj_digitos_iguais(self):
        """Testa CNPJ com todos digitos iguais."""
        with pytest.raises(PydanticCustomError) as exc_info:
            CNPJValidator.validate("11111111111111")
        assert "invalido" in str(exc_info.value)


class TestPhoneValidator:
    """Testes do validador de telefone."""

    def test_celular_valido(self):
        """Testa celular valido."""
        phone = "11999999999"
        resultado = PhoneValidator.validate(phone)
        assert resultado == phone

    def test_telefone_fixo_valido(self):
        """Testa telefone fixo valido."""
        phone = "1133334444"
        resultado = PhoneValidator.validate(phone)
        assert resultado == phone

    def test_telefone_com_formatacao(self):
        """Testa telefone com formatacao."""
        phone = "(11) 99999-9999"
        resultado = PhoneValidator.validate(phone)
        assert resultado == "11999999999"

    def test_telefone_com_codigo_pais(self):
        """Testa telefone com codigo de pais."""
        phone = "5511999999999"
        resultado = PhoneValidator.validate(phone)
        assert resultado == "11999999999"

    def test_telefone_curto(self):
        """Testa telefone muito curto."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PhoneValidator.validate("999999999")
        assert "10 ou 11 digitos" in str(exc_info.value)


class TestPlacaVeiculoValidator:
    """Testes do validador de placa de veiculo."""

    def test_placa_formato_antigo(self):
        """Testa placa formato antigo (ABC-1234)."""
        placa = "ABC1234"
        resultado = PlacaVeiculoValidator.validate(placa)
        assert resultado == "ABC1234"

    def test_placa_formato_antigo_com_hifen(self):
        """Testa placa formato antigo com hifen."""
        placa = "ABC-1234"
        resultado = PlacaVeiculoValidator.validate(placa)
        assert resultado == "ABC1234"

    def test_placa_formato_mercosul(self):
        """Testa placa formato Mercosul (ABC1D23)."""
        placa = "ABC1D23"
        resultado = PlacaVeiculoValidator.validate(placa)
        assert resultado == "ABC1D23"

    def test_placa_minuscula(self):
        """Testa placa em minusculas."""
        placa = "abc1234"
        resultado = PlacaVeiculoValidator.validate(placa)
        assert resultado == "ABC1234"

    def test_placa_invalida(self):
        """Testa placa invalida."""
        with pytest.raises(PydanticCustomError) as exc_info:
            PlacaVeiculoValidator.validate("12345678")
        assert "invalida" in str(exc_info.value)


class TestSanitizeString:
    """Testes do sanitizador de strings."""

    def test_remove_caracteres_perigosos(self):
        """Testa remocao de caracteres perigosos."""
        texto = "<script>alert('xss')</script>"
        resultado = SanitizeString.sanitize(texto)
        assert "<" not in resultado
        assert ">" not in resultado

    def test_remove_sql_injection(self):
        """Testa remocao de padroes SQL injection."""
        texto = "1; DROP TABLE users; --"
        resultado = SanitizeString.sanitize(texto)
        assert "DROP" not in resultado
        assert ";" not in resultado
        assert "--" not in resultado

    def test_limita_tamanho(self):
        """Testa limitacao de tamanho."""
        texto = "a" * 1000
        resultado = SanitizeString.sanitize(texto, max_length=100)
        assert len(resultado) == 100

    def test_remove_espacos_extras(self):
        """Testa remocao de espacos extras."""
        texto = "  texto   com   espacos   "
        resultado = SanitizeString.sanitize(texto)
        assert resultado == "texto com espacos"
