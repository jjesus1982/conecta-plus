"""
Conecta Plus - Cliente de Email (SMTP)
Permite envio de emails via SMTP

Dependências:
    pip install aiosmtplib jinja2

Uso:
    from email_client import EmailClient

    client = EmailClient(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="seu@email.com",
        password="sua_senha"
    )

    # Enviar email simples
    await client.send_email(
        to="destino@email.com",
        subject="Assunto",
        body="Corpo do email"
    )

    # Enviar com template HTML
    await client.send_template_email(
        to="destino@email.com",
        subject="Bem-vindo!",
        template="welcome.html",
        context={"nome": "João"}
    )
"""

import logging
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Configuração do servidor SMTP"""
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_email: str = None
    from_name: str = "Conecta Plus"
    timeout: int = 30


@dataclass
class EmailAttachment:
    """Anexo de email"""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class EmailClient:
    """
    Cliente SMTP para envio de emails

    Funcionalidades:
    - Envio de emails texto e HTML
    - Suporte a templates Jinja2
    - Anexos
    - CC e BCC
    - Envio assíncrono
    - Fila de emails
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: str = None,
        password: str = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        from_email: str = None,
        from_name: str = "Conecta Plus",
        template_dir: str = None
    ):
        """
        Inicializa o cliente de email

        Args:
            smtp_host: Servidor SMTP
            smtp_port: Porta SMTP
            username: Usuário para autenticação
            password: Senha para autenticação
            use_tls: Usar STARTTLS
            use_ssl: Usar SSL direto
            from_email: Email de origem
            from_name: Nome de exibição
            template_dir: Diretório de templates
        """
        self.config = EmailConfig(
            host=smtp_host,
            port=smtp_port,
            username=username,
            password=password,
            use_tls=use_tls,
            use_ssl=use_ssl,
            from_email=from_email or username,
            from_name=from_name
        )

        self.template_dir = template_dir or "/opt/conecta-plus/templates/email"
        self._jinja_env = None

    def _get_jinja_env(self):
        """Obtém ambiente Jinja2 para templates"""
        if self._jinja_env is None:
            try:
                from jinja2 import Environment, FileSystemLoader

                if os.path.exists(self.template_dir):
                    self._jinja_env = Environment(
                        loader=FileSystemLoader(self.template_dir),
                        autoescape=True
                    )
                else:
                    logger.warning(f"Diretório de templates não existe: {self.template_dir}")

            except ImportError:
                logger.warning("Jinja2 não instalado. Templates HTML não disponíveis.")

        return self._jinja_env

    def _create_message(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: str = None,
        cc: Union[str, List[str]] = None,
        bcc: Union[str, List[str]] = None,
        attachments: List[EmailAttachment] = None,
        reply_to: str = None
    ) -> MIMEMultipart:
        """
        Cria mensagem de email

        Args:
            to: Destinatário(s)
            subject: Assunto
            body: Corpo texto
            html_body: Corpo HTML
            cc: Cópia
            bcc: Cópia oculta
            attachments: Anexos
            reply_to: Responder para

        Returns:
            Mensagem formatada
        """
        msg = MIMEMultipart("alternative")

        # Headers
        msg["Subject"] = subject
        msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"

        if isinstance(to, list):
            msg["To"] = ", ".join(to)
        else:
            msg["To"] = to

        if cc:
            if isinstance(cc, list):
                msg["Cc"] = ", ".join(cc)
            else:
                msg["Cc"] = cc

        if reply_to:
            msg["Reply-To"] = reply_to

        # Corpo texto
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Corpo HTML
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Anexos
        if attachments:
            for attachment in attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment.filename}"
                )
                msg.attach(part)

        return msg

    def _get_all_recipients(
        self,
        to: Union[str, List[str]],
        cc: Union[str, List[str]] = None,
        bcc: Union[str, List[str]] = None
    ) -> List[str]:
        """Obtém lista de todos os destinatários"""
        recipients = []

        if isinstance(to, str):
            recipients.append(to)
        else:
            recipients.extend(to)

        if cc:
            if isinstance(cc, str):
                recipients.append(cc)
            else:
                recipients.extend(cc)

        if bcc:
            if isinstance(bcc, str):
                recipients.append(bcc)
            else:
                recipients.extend(bcc)

        return recipients

    def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: str = None,
        cc: Union[str, List[str]] = None,
        bcc: Union[str, List[str]] = None,
        attachments: List[EmailAttachment] = None,
        reply_to: str = None
    ) -> bool:
        """
        Envia email (síncrono)

        Args:
            to: Destinatário(s)
            subject: Assunto
            body: Corpo texto
            html_body: Corpo HTML
            cc: Cópia
            bcc: Cópia oculta
            attachments: Anexos
            reply_to: Responder para

        Returns:
            True se enviado com sucesso
        """
        try:
            msg = self._create_message(
                to=to,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                reply_to=reply_to
            )

            recipients = self._get_all_recipients(to, cc, bcc)

            # Conectar ao servidor
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout
                )
            else:
                server = smtplib.SMTP(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout
                )

            try:
                if self.config.use_tls and not self.config.use_ssl:
                    server.starttls()

                if self.config.username and self.config.password:
                    server.login(self.config.username, self.config.password)

                server.sendmail(
                    self.config.from_email,
                    recipients,
                    msg.as_string()
                )

                logger.info(f"Email enviado para {recipients}: {subject}")
                return True

            finally:
                server.quit()

        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False

    async def send_email_async(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: str = None,
        cc: Union[str, List[str]] = None,
        bcc: Union[str, List[str]] = None,
        attachments: List[EmailAttachment] = None,
        reply_to: str = None
    ) -> bool:
        """
        Envia email (assíncrono)

        Args:
            to: Destinatário(s)
            subject: Assunto
            body: Corpo texto
            html_body: Corpo HTML
            cc: Cópia
            bcc: Cópia oculta
            attachments: Anexos
            reply_to: Responder para

        Returns:
            True se enviado com sucesso
        """
        try:
            import aiosmtplib

            msg = self._create_message(
                to=to,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                reply_to=reply_to
            )

            recipients = self._get_all_recipients(to, cc, bcc)

            await aiosmtplib.send(
                msg,
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                start_tls=self.config.use_tls,
                use_tls=self.config.use_ssl,
                timeout=self.config.timeout
            )

            logger.info(f"Email enviado (async) para {recipients}: {subject}")
            return True

        except ImportError:
            logger.warning("aiosmtplib não instalado. Usando envio síncrono.")
            return self.send_email(to, subject, body, html_body, cc, bcc, attachments, reply_to)

        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False

    def send_template_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        template: str,
        context: Dict[str, Any] = None,
        cc: Union[str, List[str]] = None,
        bcc: Union[str, List[str]] = None,
        attachments: List[EmailAttachment] = None,
        reply_to: str = None
    ) -> bool:
        """
        Envia email usando template HTML

        Args:
            to: Destinatário(s)
            subject: Assunto
            template: Nome do arquivo de template
            context: Variáveis para o template
            cc: Cópia
            bcc: Cópia oculta
            attachments: Anexos
            reply_to: Responder para

        Returns:
            True se enviado com sucesso
        """
        jinja = self._get_jinja_env()
        if not jinja:
            logger.error("Templates não disponíveis")
            return False

        try:
            tmpl = jinja.get_template(template)
            html_body = tmpl.render(**(context or {}))

            # Gerar versão texto do HTML
            text_body = self._html_to_text(html_body)

            return self.send_email(
                to=to,
                subject=subject,
                body=text_body,
                html_body=html_body,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                reply_to=reply_to
            )

        except Exception as e:
            logger.error(f"Erro ao renderizar template: {e}")
            return False

    def _html_to_text(self, html: str) -> str:
        """Converte HTML para texto simples"""
        import re

        # Remover tags
        text = re.sub(r'<[^>]+>', '', html)
        # Decodificar entidades
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        # Limpar espaços extras
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def send_file(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        file_path: str,
        filename: str = None
    ) -> bool:
        """
        Envia email com arquivo anexo

        Args:
            to: Destinatário(s)
            subject: Assunto
            body: Corpo do email
            file_path: Caminho do arquivo
            filename: Nome do arquivo no email

        Returns:
            True se enviado com sucesso
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Arquivo não encontrado: {file_path}")
                return False

            with open(path, "rb") as f:
                content = f.read()

            attachment = EmailAttachment(
                filename=filename or path.name,
                content=content
            )

            return self.send_email(
                to=to,
                subject=subject,
                body=body,
                attachments=[attachment]
            )

        except Exception as e:
            logger.error(f"Erro ao enviar arquivo: {e}")
            return False


class EmailTemplates:
    """Templates de email pré-definidos"""

    @staticmethod
    def welcome_email(nome: str, email: str) -> Dict[str, str]:
        """Template de boas-vindas"""
        return {
            "subject": "Bem-vindo ao Conecta Plus!",
            "body": f"""
Olá {nome}!

Seja bem-vindo ao Conecta Plus!

Sua conta foi criada com sucesso usando o email: {email}

Para começar, acesse o sistema em: https://conectaplus.com.br

Atenciosamente,
Equipe Conecta Plus
            """.strip(),
            "html_body": f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #2563eb;">Bem-vindo ao Conecta Plus!</h2>

    <p>Olá <strong>{nome}</strong>!</p>

    <p>Sua conta foi criada com sucesso usando o email: <strong>{email}</strong></p>

    <p>Para começar, acesse o sistema:</p>

    <a href="https://conectaplus.com.br" style="
        display: inline-block;
        background-color: #2563eb;
        color: white;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 20px 0;
    ">Acessar Sistema</a>

    <p>Atenciosamente,<br>Equipe Conecta Plus</p>
</body>
</html>
            """
        }

    @staticmethod
    def password_reset(nome: str, reset_link: str) -> Dict[str, str]:
        """Template de redefinição de senha"""
        return {
            "subject": "Redefinição de Senha - Conecta Plus",
            "body": f"""
Olá {nome},

Recebemos uma solicitação para redefinir sua senha.

Clique no link abaixo para criar uma nova senha:
{reset_link}

Este link expira em 1 hora.

Se você não solicitou esta alteração, ignore este email.

Atenciosamente,
Equipe Conecta Plus
            """.strip(),
            "html_body": f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #2563eb;">Redefinição de Senha</h2>

    <p>Olá <strong>{nome}</strong>,</p>

    <p>Recebemos uma solicitação para redefinir sua senha.</p>

    <p>Clique no botão abaixo para criar uma nova senha:</p>

    <a href="{reset_link}" style="
        display: inline-block;
        background-color: #dc2626;
        color: white;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 20px 0;
    ">Redefinir Senha</a>

    <p style="color: #666; font-size: 14px;">Este link expira em 1 hora.</p>

    <p style="color: #666; font-size: 14px;">
        Se você não solicitou esta alteração, ignore este email.
    </p>

    <p>Atenciosamente,<br>Equipe Conecta Plus</p>
</body>
</html>
            """
        }

    @staticmethod
    def alert_notification(
        title: str,
        message: str,
        level: str = "info"
    ) -> Dict[str, str]:
        """Template de alerta/notificação"""
        colors = {
            "info": "#3b82f6",
            "success": "#22c55e",
            "warning": "#f59e0b",
            "error": "#ef4444"
        }
        color = colors.get(level, colors["info"])

        return {
            "subject": f"[{level.upper()}] {title}",
            "body": f"""
{title}

{message}

---
Conecta Plus - Sistema de Alertas
            """.strip(),
            "html_body": f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <div style="
        border-left: 4px solid {color};
        padding-left: 16px;
        margin-bottom: 20px;
    ">
        <h2 style="color: {color}; margin: 0 0 10px 0;">{title}</h2>
        <p style="margin: 0; white-space: pre-wrap;">{message}</p>
    </div>

    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

    <p style="color: #666; font-size: 12px;">
        Conecta Plus - Sistema de Alertas
    </p>
</body>
</html>
            """
        }


# Exemplo de uso
if __name__ == "__main__":
    print("Cliente de Email SMTP")
    print("Uso:")
    print("  client = EmailClient('smtp.gmail.com', 587, 'user@gmail.com', 'senha')")
    print("  client.send_email('destino@email.com', 'Assunto', 'Corpo')")
