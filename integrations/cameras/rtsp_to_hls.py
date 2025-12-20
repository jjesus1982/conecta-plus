"""
Conecta Plus - Conversor RTSP para HLS
Converte streams RTSP de câmeras para HLS para exibição em navegadores

Dependências:
    - FFmpeg instalado no sistema
    - pip install aiofiles

Uso:
    from rtsp_to_hls import RTSPtoHLS

    # Iniciar conversão
    converter = RTSPtoHLS('rtsp://camera/stream', 'camera_01')
    await converter.start()

    # HLS disponível em: /opt/conecta-plus/integrations/cameras/hls/camera_01/stream.m3u8
"""

import asyncio
import logging
import os
import signal
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diretório base para streams HLS
HLS_BASE_DIR = "/opt/conecta-plus/integrations/cameras/hls"


@dataclass
class StreamConfig:
    """Configuração do stream"""
    # Vídeo
    video_codec: str = "libx264"
    video_preset: str = "ultrafast"
    video_tune: str = "zerolatency"
    video_bitrate: str = "1500k"
    resolution: str = "1280x720"
    fps: int = 15

    # HLS
    hls_time: int = 2  # Duração de cada segmento em segundos
    hls_list_size: int = 5  # Número de segmentos no playlist
    hls_flags: str = "delete_segments+append_list"

    # Áudio
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    audio_enabled: bool = False


class RTSPtoHLS:
    """
    Conversor de RTSP para HLS usando FFmpeg

    Converte streams RTSP em tempo real para formato HLS,
    permitindo visualização em navegadores web.
    """

    def __init__(
        self,
        rtsp_url: str,
        stream_id: str,
        config: StreamConfig = None,
        output_dir: str = None
    ):
        """
        Inicializa o conversor

        Args:
            rtsp_url: URL do stream RTSP
            stream_id: Identificador único do stream
            config: Configurações do stream
            output_dir: Diretório de saída (usa padrão se não especificado)
        """
        self.rtsp_url = rtsp_url
        self.stream_id = stream_id
        self.config = config or StreamConfig()
        self.output_dir = output_dir or os.path.join(HLS_BASE_DIR, stream_id)

        self._process: Optional[subprocess.Popen] = None
        self._running = False
        self._start_time: Optional[datetime] = None
        self._error_count = 0
        self._max_errors = 5

    @property
    def is_running(self) -> bool:
        """Verifica se o stream está ativo"""
        return self._running and self._process is not None

    @property
    def playlist_path(self) -> str:
        """Caminho do arquivo de playlist HLS"""
        return os.path.join(self.output_dir, "stream.m3u8")

    @property
    def uptime(self) -> Optional[float]:
        """Tempo de execução em segundos"""
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return None

    def _build_ffmpeg_command(self) -> list:
        """
        Constrói o comando FFmpeg

        Returns:
            Lista com argumentos do comando
        """
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",

            # Input
            "-rtsp_transport", "tcp",
            "-i", self.rtsp_url,

            # Reconexão automática
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",

            # Vídeo
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-tune", self.config.video_tune,
            "-b:v", self.config.video_bitrate,
            "-s", self.config.resolution,
            "-r", str(self.config.fps),

            # Keyframes para HLS
            "-g", str(self.config.fps * self.config.hls_time),
            "-keyint_min", str(self.config.fps * self.config.hls_time),
            "-sc_threshold", "0",
        ]

        # Áudio
        if self.config.audio_enabled:
            cmd.extend([
                "-c:a", self.config.audio_codec,
                "-b:a", self.config.audio_bitrate,
            ])
        else:
            cmd.extend(["-an"])  # Sem áudio

        # HLS output
        cmd.extend([
            "-f", "hls",
            "-hls_time", str(self.config.hls_time),
            "-hls_list_size", str(self.config.hls_list_size),
            "-hls_flags", self.config.hls_flags,
            "-hls_segment_filename", os.path.join(self.output_dir, "segment_%03d.ts"),
            self.playlist_path
        ])

        return cmd

    async def start(self) -> bool:
        """
        Inicia a conversão RTSP → HLS

        Returns:
            True se iniciou com sucesso
        """
        if self._running:
            logger.warning(f"Stream {self.stream_id} já está rodando")
            return False

        # Criar diretório de saída
        os.makedirs(self.output_dir, exist_ok=True)

        # Construir comando
        cmd = self._build_ffmpeg_command()
        logger.info(f"Iniciando stream {self.stream_id}: {self.rtsp_url}")
        logger.debug(f"Comando: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Criar novo grupo de processos
            )

            self._running = True
            self._start_time = datetime.now()
            self._error_count = 0

            # Iniciar monitoramento em background
            asyncio.create_task(self._monitor())

            logger.info(f"Stream {self.stream_id} iniciado (PID: {self._process.pid})")
            return True

        except Exception as e:
            logger.error(f"Erro ao iniciar stream {self.stream_id}: {e}")
            self._running = False
            return False

    async def stop(self) -> bool:
        """
        Para a conversão

        Returns:
            True se parou com sucesso
        """
        if not self._running or not self._process:
            return False

        logger.info(f"Parando stream {self.stream_id}...")

        try:
            # Enviar SIGTERM para o grupo de processos
            os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)

            # Aguardar término
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Forçar término
                os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                self._process.wait()

            self._running = False
            self._process = None
            self._start_time = None

            # Limpar arquivos temporários
            await self._cleanup()

            logger.info(f"Stream {self.stream_id} parado")
            return True

        except Exception as e:
            logger.error(f"Erro ao parar stream {self.stream_id}: {e}")
            return False

    async def restart(self) -> bool:
        """
        Reinicia a conversão

        Returns:
            True se reiniciou com sucesso
        """
        await self.stop()
        await asyncio.sleep(1)
        return await self.start()

    async def _monitor(self):
        """Monitora o processo FFmpeg"""
        while self._running and self._process:
            # Verificar se processo ainda está rodando
            poll = self._process.poll()

            if poll is not None:
                # Processo terminou
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""

                if poll != 0:
                    self._error_count += 1
                    logger.error(
                        f"Stream {self.stream_id} terminou com erro (código {poll}): {stderr[:500]}"
                    )

                    # Tentar reconectar
                    if self._error_count < self._max_errors:
                        logger.info(
                            f"Tentando reconectar stream {self.stream_id} "
                            f"({self._error_count}/{self._max_errors})"
                        )
                        await asyncio.sleep(5)
                        await self.start()
                    else:
                        logger.error(
                            f"Stream {self.stream_id} excedeu limite de erros. Desistindo."
                        )
                        self._running = False

                break

            await asyncio.sleep(5)

    async def _cleanup(self):
        """Limpa arquivos temporários"""
        try:
            # Remover segmentos antigos
            for f in Path(self.output_dir).glob("*.ts"):
                f.unlink()

            # Remover playlist
            playlist = Path(self.playlist_path)
            if playlist.exists():
                playlist.unlink()

        except Exception as e:
            logger.warning(f"Erro na limpeza: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Obtém status do stream

        Returns:
            Dicionário com informações do status
        """
        return {
            "stream_id": self.stream_id,
            "rtsp_url": self.rtsp_url,
            "running": self.is_running,
            "pid": self._process.pid if self._process else None,
            "uptime": self.uptime,
            "error_count": self._error_count,
            "playlist": self.playlist_path if self.is_running else None,
            "config": {
                "resolution": self.config.resolution,
                "fps": self.config.fps,
                "bitrate": self.config.video_bitrate
            }
        }


class StreamManager:
    """
    Gerenciador de múltiplos streams RTSP → HLS
    """

    def __init__(self):
        self._streams: Dict[str, RTSPtoHLS] = {}

    async def add_stream(
        self,
        stream_id: str,
        rtsp_url: str,
        config: StreamConfig = None,
        auto_start: bool = True
    ) -> RTSPtoHLS:
        """
        Adiciona um novo stream

        Args:
            stream_id: Identificador único
            rtsp_url: URL RTSP da câmera
            config: Configurações personalizadas
            auto_start: Iniciar automaticamente

        Returns:
            Instância do conversor
        """
        if stream_id in self._streams:
            raise ValueError(f"Stream {stream_id} já existe")

        stream = RTSPtoHLS(rtsp_url, stream_id, config)
        self._streams[stream_id] = stream

        if auto_start:
            await stream.start()

        return stream

    async def remove_stream(self, stream_id: str) -> bool:
        """
        Remove um stream

        Args:
            stream_id: Identificador do stream

        Returns:
            True se removido com sucesso
        """
        if stream_id not in self._streams:
            return False

        stream = self._streams[stream_id]
        await stream.stop()
        del self._streams[stream_id]

        return True

    def get_stream(self, stream_id: str) -> Optional[RTSPtoHLS]:
        """Obtém um stream pelo ID"""
        return self._streams.get(stream_id)

    def list_streams(self) -> Dict[str, Dict[str, Any]]:
        """Lista todos os streams e seus status"""
        return {
            stream_id: stream.get_status()
            for stream_id, stream in self._streams.items()
        }

    async def stop_all(self):
        """Para todos os streams"""
        for stream in self._streams.values():
            await stream.stop()


# Exemplo de uso
if __name__ == "__main__":
    async def main():
        # Criar gerenciador
        manager = StreamManager()

        # Adicionar stream de exemplo
        # await manager.add_stream(
        #     stream_id="camera_01",
        #     rtsp_url="rtsp://admin:admin@192.168.1.100:554/stream1"
        # )

        # Listar streams
        print("Streams ativos:", manager.list_streams())

        # Aguardar
        # await asyncio.sleep(60)

        # Parar todos
        # await manager.stop_all()

    asyncio.run(main())
