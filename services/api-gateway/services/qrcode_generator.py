"""
Conecta Plus - Gerador de QR Code PIX
Gera QR Codes visuais para pagamento PIX
"""

import io
import base64
from typing import Optional
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from PIL import Image


class GeradorQRCodePIX:
    """Gera QR Codes para pagamento PIX"""

    def __init__(
        self,
        box_size: int = 10,
        border: int = 4,
        fill_color: str = "black",
        back_color: str = "white"
    ):
        self.box_size = box_size
        self.border = border
        self.fill_color = fill_color
        self.back_color = back_color

    def gerar_qrcode(
        self,
        pix_copia_cola: str,
        logo_path: Optional[str] = None,
        tamanho: int = 300
    ) -> bytes:
        """
        Gera imagem do QR Code PIX

        Args:
            pix_copia_cola: Código PIX EMV (Copia e Cola)
            logo_path: Caminho para logo central (opcional)
            tamanho: Tamanho final da imagem em pixels

        Returns:
            bytes: Imagem PNG do QR Code
        """
        qr = qrcode.QRCode(
            version=None,  # Auto-determina versão
            error_correction=ERROR_CORRECT_M,
            box_size=self.box_size,
            border=self.border,
        )

        qr.add_data(pix_copia_cola)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color=self.fill_color,
            back_color=self.back_color
        ).convert('RGB')

        # Redimensiona para tamanho desejado
        img = img.resize((tamanho, tamanho), Image.Resampling.LANCZOS)

        # Adiciona logo central se fornecido
        if logo_path:
            try:
                logo = Image.open(logo_path)
                logo_size = tamanho // 4
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

                # Posição central
                pos = ((tamanho - logo_size) // 2, (tamanho - logo_size) // 2)

                # Cria fundo branco para logo
                logo_bg = Image.new('RGB', (logo_size + 10, logo_size + 10), 'white')
                img.paste(logo_bg, (pos[0] - 5, pos[1] - 5))
                img.paste(logo, pos)
            except Exception:
                pass  # Ignora se não conseguir adicionar logo

        # Converte para bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95)
        buffer.seek(0)

        return buffer.getvalue()

    def gerar_qrcode_base64(
        self,
        pix_copia_cola: str,
        logo_path: Optional[str] = None,
        tamanho: int = 300
    ) -> str:
        """
        Gera QR Code como string Base64

        Returns:
            str: QR Code em formato data:image/png;base64,...
        """
        img_bytes = self.gerar_qrcode(pix_copia_cola, logo_path, tamanho)
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/png;base64,{b64}"

    def gerar_qrcode_svg(self, pix_copia_cola: str) -> str:
        """
        Gera QR Code em formato SVG (vetorial)

        Returns:
            str: SVG do QR Code
        """
        import qrcode.image.svg

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(pix_copia_cola)
        qr.make(fit=True)

        factory = qrcode.image.svg.SvgPathImage
        img = qr.make_image(image_factory=factory)

        buffer = io.BytesIO()
        img.save(buffer)
        buffer.seek(0)

        return buffer.getvalue().decode('utf-8')


# Instância global
qrcode_generator = GeradorQRCodePIX()


def gerar_qrcode_pix(pix_copia_cola: str, formato: str = "base64") -> str:
    """
    Função utilitária para gerar QR Code PIX

    Args:
        pix_copia_cola: Código PIX
        formato: "base64", "svg" ou "bytes"

    Returns:
        QR Code no formato especificado
    """
    if formato == "base64":
        return qrcode_generator.gerar_qrcode_base64(pix_copia_cola)
    elif formato == "svg":
        return qrcode_generator.gerar_qrcode_svg(pix_copia_cola)
    else:
        return qrcode_generator.gerar_qrcode(pix_copia_cola)
