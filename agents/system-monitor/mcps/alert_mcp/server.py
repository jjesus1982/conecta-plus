#!/usr/bin/env python3
"""
MCP Server: Alert System
Envia alertas por múltiplos canais (email, telegram, slack, webhook)
"""

import os
import json
import asyncio
from typing import Any, Dict
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# Importar MCP SDK
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP SDK not available - install with: pip install mcp")
    exit(1)


class AlertMCP:
    """MCP para sistema de alertas"""

    def __init__(self):
        self.server = Server("alert-mcp")
        self.alert_history = []

        # Configurações de email
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.alert_email = os.getenv('ALERT_EMAIL', '')

        # Telegram
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

        # Slack
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')

        self._register_tools()

    def _register_tools(self):
        """Registra tools do MCP"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="send_email_alert",
                    description="Envia alerta por email",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "message": {"type": "string"},
                            "severity": {"type": "string", "enum": ["critical", "high", "warning", "info"]}
                        },
                        "required": ["subject", "message"]
                    }
                ),
                Tool(
                    name="send_telegram_alert",
                    description="Envia alerta pelo Telegram",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "severity": {"type": "string", "enum": ["critical", "high", "warning", "info"]}
                        },
                        "required": ["message"]
                    }
                ),
                Tool(
                    name="send_slack_alert",
                    description="Envia alerta pelo Slack",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "severity": {"type": "string", "enum": ["critical", "high", "warning", "info"]}
                        },
                        "required": ["message"]
                    }
                ),
                Tool(
                    name="send_multi_channel_alert",
                    description="Envia alerta por múltiplos canais simultaneamente",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "message": {"type": "string"},
                            "severity": {"type": "string", "enum": ["critical", "high", "warning", "info"]},
                            "channels": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["message", "severity"]
                    }
                ),
                Tool(
                    name="get_alert_history",
                    description="Retorna histórico de alertas enviados",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "number"}
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            if name == "send_email_alert":
                result = await self.send_email_alert(
                    arguments.get("subject"),
                    arguments.get("message"),
                    arguments.get("severity", "info")
                )
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "send_telegram_alert":
                result = await self.send_telegram_alert(
                    arguments.get("message"),
                    arguments.get("severity", "info")
                )
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "send_slack_alert":
                result = await self.send_slack_alert(
                    arguments.get("message"),
                    arguments.get("severity", "info")
                )
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "send_multi_channel_alert":
                result = await self.send_multi_channel_alert(
                    arguments.get("subject", ""),
                    arguments.get("message"),
                    arguments.get("severity", "info"),
                    arguments.get("channels", ["email"])
                )
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "get_alert_history":
                limit = arguments.get("limit", 10)
                history = self.alert_history[-limit:]
                return [TextContent(type="text", text=json.dumps(history))]

            raise ValueError(f"Unknown tool: {name}")

    async def send_email_alert(self, subject: str, message: str, severity: str) -> Dict[str, Any]:
        """Envia alerta por email"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'channel': 'email',
            'severity': severity,
            'success': False
        }

        if not self.smtp_user or not self.smtp_password or not self.alert_email:
            result['error'] = 'Email não configurado (SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL)'
            self._log_alert(result)
            return result

        try:
            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{severity.upper()}] {subject}"
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email

            # Corpo HTML
            html = f"""
            <html>
                <body>
                    <h2 style="color: {'#dc2626' if severity == 'critical' else '#ea580c' if severity == 'high' else '#f59e0b' if severity == 'warning' else '#3b82f6'};">
                        {severity.upper()} Alert
                    </h2>
                    <p><strong>Subject:</strong> {subject}</p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <hr>
                    <pre>{message}</pre>
                    <hr>
                    <p><small>Sent by Conecta Plus System Monitor</small></p>
                </body>
            </html>
            """

            msg.attach(MIMEText(message, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            # Enviar
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            result['success'] = True
            result['to'] = self.alert_email

        except Exception as e:
            result['error'] = str(e)

        self._log_alert(result)
        return result

    async def send_telegram_alert(self, message: str, severity: str) -> Dict[str, Any]:
        """Envia alerta pelo Telegram"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'channel': 'telegram',
            'severity': severity,
            'success': False
        }

        if not self.telegram_token or not self.telegram_chat_id:
            result['error'] = 'Telegram não configurado (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)'
            self._log_alert(result)
            return result

        try:
            # Emoji por severidade
            emoji = {
                'critical': '🔴',
                'high': '🟠',
                'warning': '🟡',
                'info': '🔵'
            }.get(severity, '⚪')

            formatted_message = f"{emoji} *{severity.upper()} Alert*\n\n{message}\n\n_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                result['success'] = True
            else:
                result['error'] = f'Telegram API error: {response.status_code}'

        except Exception as e:
            result['error'] = str(e)

        self._log_alert(result)
        return result

    async def send_slack_alert(self, message: str, severity: str) -> Dict[str, Any]:
        """Envia alerta pelo Slack"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'channel': 'slack',
            'severity': severity,
            'success': False
        }

        if not self.slack_webhook:
            result['error'] = 'Slack não configurado (SLACK_WEBHOOK_URL)'
            self._log_alert(result)
            return result

        try:
            # Cor por severidade
            color = {
                'critical': '#dc2626',
                'high': '#ea580c',
                'warning': '#f59e0b',
                'info': '#3b82f6'
            }.get(severity, '#6b7280')

            payload = {
                'attachments': [{
                    'color': color,
                    'title': f'{severity.upper()} Alert',
                    'text': message,
                    'footer': 'Conecta Plus System Monitor',
                    'ts': int(datetime.now().timestamp())
                }]
            }

            response = requests.post(self.slack_webhook, json=payload, timeout=10)

            if response.status_code == 200:
                result['success'] = True
            else:
                result['error'] = f'Slack error: {response.status_code}'

        except Exception as e:
            result['error'] = str(e)

        self._log_alert(result)
        return result

    async def send_multi_channel_alert(self, subject: str, message: str, severity: str, channels: list) -> Dict[str, Any]:
        """Envia alerta por múltiplos canais"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'channels': {}
        }

        tasks = []

        if 'email' in channels:
            tasks.append(self.send_email_alert(subject, message, severity))

        if 'telegram' in channels:
            tasks.append(self.send_telegram_alert(message, severity))

        if 'slack' in channels:
            tasks.append(self.send_slack_alert(message, severity))

        if tasks:
            channel_results = await asyncio.gather(*tasks)

            for channel_result in channel_results:
                channel = channel_result['channel']
                results['channels'][channel] = channel_result

        return results

    def _log_alert(self, alert: Dict[str, Any]):
        """Registra alerta no histórico"""
        self.alert_history.append(alert)

        # Limitar histórico a 100 itens
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]

    async def run(self):
        """Executa servidor MCP"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Entry point"""
    mcp = AlertMCP()
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
