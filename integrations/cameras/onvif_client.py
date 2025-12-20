"""
Conecta Plus - Cliente ONVIF para Câmeras IP
Permite descoberta, configuração e controle de câmeras via protocolo ONVIF

Dependências:
    pip install onvif-zeep python-nmap

Uso:
    from onvif_client import ONVIFCamera

    # Conectar à câmera
    camera = ONVIFCamera('192.168.1.100', 'admin', 'senha')
    camera.connect()

    # Obter stream RTSP
    rtsp_url = camera.get_stream_uri()

    # Controle PTZ
    camera.ptz_move(pan=0.5, tilt=0.3)
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CameraInfo:
    """Informações da câmera"""
    manufacturer: str
    model: str
    firmware: str
    serial_number: str
    hardware_id: str


@dataclass
class StreamProfile:
    """Perfil de streaming"""
    name: str
    token: str
    encoding: str
    resolution: tuple
    fps: int
    bitrate: int


class ONVIFCamera:
    """
    Cliente ONVIF para controle de câmeras IP

    Suporta:
    - Descoberta de câmeras na rede
    - Autenticação
    - Obtenção de streams RTSP
    - Controle PTZ (Pan-Tilt-Zoom)
    - Configuração de perfis de mídia
    - Snapshots
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 80,
        wsdl_dir: str = None
    ):
        """
        Inicializa o cliente ONVIF

        Args:
            host: IP ou hostname da câmera
            username: Usuário para autenticação
            password: Senha para autenticação
            port: Porta HTTP da câmera (padrão: 80)
            wsdl_dir: Diretório com arquivos WSDL (opcional)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.wsdl_dir = wsdl_dir

        # Serviços ONVIF
        self._camera = None
        self._media_service = None
        self._ptz_service = None
        self._device_service = None
        self._imaging_service = None

        # Cache
        self._profiles = []
        self._info = None

    def connect(self) -> bool:
        """
        Conecta à câmera ONVIF

        Returns:
            True se conectou com sucesso

        Raises:
            ConnectionError: Se não conseguir conectar
        """
        try:
            # Importar apenas quando necessário
            from onvif import ONVIFCamera as ONVIFCam

            logger.info(f"Conectando à câmera ONVIF {self.host}:{self.port}...")

            self._camera = ONVIFCam(
                self.host,
                self.port,
                self.username,
                self.password,
                self.wsdl_dir
            )

            # Inicializar serviços
            self._device_service = self._camera.create_devicemgmt_service()
            self._media_service = self._camera.create_media_service()

            # PTZ pode não estar disponível em todas as câmeras
            try:
                self._ptz_service = self._camera.create_ptz_service()
            except Exception:
                logger.warning("Serviço PTZ não disponível nesta câmera")
                self._ptz_service = None

            logger.info(f"Conectado com sucesso à câmera {self.host}")
            return True

        except ImportError:
            logger.error("Biblioteca onvif-zeep não instalada. Execute: pip install onvif-zeep")
            raise
        except Exception as e:
            logger.error(f"Erro ao conectar: {e}")
            raise ConnectionError(f"Não foi possível conectar à câmera: {e}")

    def get_device_info(self) -> CameraInfo:
        """
        Obtém informações do dispositivo

        Returns:
            CameraInfo com dados da câmera
        """
        if not self._device_service:
            raise RuntimeError("Não conectado. Execute connect() primeiro")

        if self._info:
            return self._info

        info = self._device_service.GetDeviceInformation()

        self._info = CameraInfo(
            manufacturer=info.Manufacturer,
            model=info.Model,
            firmware=info.FirmwareVersion,
            serial_number=info.SerialNumber,
            hardware_id=info.HardwareId
        )

        return self._info

    def get_profiles(self) -> List[StreamProfile]:
        """
        Obtém perfis de mídia disponíveis

        Returns:
            Lista de StreamProfile
        """
        if not self._media_service:
            raise RuntimeError("Não conectado. Execute connect() primeiro")

        if self._profiles:
            return self._profiles

        profiles = self._media_service.GetProfiles()

        self._profiles = []
        for p in profiles:
            try:
                video_config = p.VideoEncoderConfiguration
                profile = StreamProfile(
                    name=p.Name,
                    token=p.token,
                    encoding=video_config.Encoding if video_config else "Unknown",
                    resolution=(
                        video_config.Resolution.Width if video_config else 0,
                        video_config.Resolution.Height if video_config else 0
                    ),
                    fps=video_config.RateControl.FrameRateLimit if video_config else 0,
                    bitrate=video_config.RateControl.BitrateLimit if video_config else 0
                )
                self._profiles.append(profile)
            except Exception as e:
                logger.warning(f"Erro ao processar perfil {p.Name}: {e}")

        return self._profiles

    def get_stream_uri(
        self,
        profile_token: str = None,
        stream_type: str = "RTP-Unicast",
        protocol: str = "RTSP"
    ) -> str:
        """
        Obtém URI do stream RTSP

        Args:
            profile_token: Token do perfil (usa primeiro se não especificado)
            stream_type: Tipo de stream (RTP-Unicast, RTP-Multicast)
            protocol: Protocolo (RTSP, HTTP)

        Returns:
            URI do stream RTSP
        """
        if not self._media_service:
            raise RuntimeError("Não conectado. Execute connect() primeiro")

        # Usar primeiro perfil se não especificado
        if not profile_token:
            profiles = self.get_profiles()
            if not profiles:
                raise RuntimeError("Nenhum perfil de mídia disponível")
            profile_token = profiles[0].token

        # Configurar request
        stream_setup = {
            'Stream': stream_type,
            'Transport': {'Protocol': protocol}
        }

        uri_response = self._media_service.GetStreamUri(
            StreamSetup=stream_setup,
            ProfileToken=profile_token
        )

        return uri_response.Uri

    def get_snapshot_uri(self, profile_token: str = None) -> str:
        """
        Obtém URI para snapshot

        Args:
            profile_token: Token do perfil

        Returns:
            URI para obter snapshot
        """
        if not self._media_service:
            raise RuntimeError("Não conectado. Execute connect() primeiro")

        if not profile_token:
            profiles = self.get_profiles()
            if profiles:
                profile_token = profiles[0].token

        uri_response = self._media_service.GetSnapshotUri(
            ProfileToken=profile_token
        )

        return uri_response.Uri

    def ptz_move(
        self,
        pan: float = 0,
        tilt: float = 0,
        zoom: float = 0,
        profile_token: str = None
    ) -> bool:
        """
        Move a câmera PTZ

        Args:
            pan: Velocidade horizontal (-1 a 1)
            tilt: Velocidade vertical (-1 a 1)
            zoom: Velocidade de zoom (-1 a 1)
            profile_token: Token do perfil

        Returns:
            True se movimento executado
        """
        if not self._ptz_service:
            logger.warning("PTZ não disponível nesta câmera")
            return False

        if not profile_token:
            profiles = self.get_profiles()
            if profiles:
                profile_token = profiles[0].token

        # Criar request de movimento
        request = self._ptz_service.create_type('ContinuousMove')
        request.ProfileToken = profile_token
        request.Velocity = {
            'PanTilt': {'x': pan, 'y': tilt},
            'Zoom': {'x': zoom}
        }

        self._ptz_service.ContinuousMove(request)
        return True

    def ptz_stop(self, profile_token: str = None) -> bool:
        """
        Para movimento PTZ

        Args:
            profile_token: Token do perfil

        Returns:
            True se parado com sucesso
        """
        if not self._ptz_service:
            return False

        if not profile_token:
            profiles = self.get_profiles()
            if profiles:
                profile_token = profiles[0].token

        self._ptz_service.Stop({'ProfileToken': profile_token})
        return True

    def ptz_goto_preset(self, preset: int, profile_token: str = None) -> bool:
        """
        Vai para preset PTZ

        Args:
            preset: Número do preset
            profile_token: Token do perfil

        Returns:
            True se executado com sucesso
        """
        if not self._ptz_service:
            return False

        if not profile_token:
            profiles = self.get_profiles()
            if profiles:
                profile_token = profiles[0].token

        request = self._ptz_service.create_type('GotoPreset')
        request.ProfileToken = profile_token
        request.PresetToken = str(preset)

        self._ptz_service.GotoPreset(request)
        return True


def discover_cameras(timeout: int = 5) -> List[Dict[str, Any]]:
    """
    Descobre câmeras ONVIF na rede local

    Args:
        timeout: Timeout em segundos

    Returns:
        Lista de dicionários com informações das câmeras encontradas
    """
    try:
        from wsdiscovery import WSDiscovery

        logger.info("Iniciando descoberta de câmeras ONVIF...")

        wsd = WSDiscovery()
        wsd.start()

        # Procurar dispositivos ONVIF
        services = wsd.searchServices(
            types=['dn:NetworkVideoTransmitter'],
            timeout=timeout
        )

        cameras = []
        for service in services:
            camera = {
                'addresses': service.getXAddrs(),
                'scopes': [str(s) for s in service.getScopes()],
                'types': [str(t) for t in service.getTypes()]
            }
            cameras.append(camera)
            logger.info(f"Câmera encontrada: {camera['addresses']}")

        wsd.stop()

        logger.info(f"Descoberta concluída. {len(cameras)} câmera(s) encontrada(s)")
        return cameras

    except ImportError:
        logger.error("Biblioteca wsdiscovery não instalada. Execute: pip install wsdiscovery")
        return []
    except Exception as e:
        logger.error(f"Erro na descoberta: {e}")
        return []


# Exemplo de uso
if __name__ == "__main__":
    # Descobrir câmeras na rede
    print("Buscando câmeras ONVIF na rede...")
    cameras = discover_cameras()

    for cam in cameras:
        print(f"  - {cam['addresses']}")

    # Exemplo de conexão
    # camera = ONVIFCamera('192.168.1.100', 'admin', 'admin123')
    # camera.connect()
    # print(f"Stream URL: {camera.get_stream_uri()}")
