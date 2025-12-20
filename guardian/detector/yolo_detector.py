"""
Conecta Plus - Guardian - Detector YOLO
Sistema de detecção de objetos usando YOLOv8

Dependências:
    pip install ultralytics opencv-python-headless numpy

Uso:
    from yolo_detector import YOLODetector

    detector = YOLODetector()

    # Detectar em imagem
    results = detector.detect_image("imagem.jpg")

    # Detectar em frame de vídeo
    results = detector.detect_frame(frame)

    # Processar stream
    async for detection in detector.process_stream("rtsp://camera/stream"):
        print(detection)
"""

import logging
import os
import asyncio
from typing import Optional, List, Dict, Any, Tuple, Generator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diretório de modelos
MODELS_DIR = "/opt/conecta-plus/models/yolo"


@dataclass
class Detection:
    """Resultado de uma detecção"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    timestamp: datetime = field(default_factory=datetime.now)
    frame_id: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": {
                "x1": self.bbox[0],
                "y1": self.bbox[1],
                "x2": self.bbox[2],
                "y2": self.bbox[3]
            },
            "timestamp": self.timestamp.isoformat(),
            "frame_id": self.frame_id,
            "metadata": self.metadata
        }

    @property
    def center(self) -> Tuple[int, int]:
        """Centro do bounding box"""
        return (
            (self.bbox[0] + self.bbox[2]) // 2,
            (self.bbox[1] + self.bbox[3]) // 2
        )

    @property
    def area(self) -> int:
        """Área do bounding box"""
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


@dataclass
class DetectionConfig:
    """Configurações do detector"""
    model_name: str = "yolov8n.pt"  # nano, small, medium, large, xlarge
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    max_detections: int = 100
    classes_filter: List[int] = None  # None = todas as classes
    device: str = "auto"  # auto, cpu, cuda, cuda:0
    half_precision: bool = False  # FP16 (requer GPU)
    img_size: int = 640


class YOLODetector:
    """
    Detector de objetos usando YOLOv8

    Funcionalidades:
    - Detecção em imagens e vídeos
    - Múltiplos modelos (nano a xlarge)
    - Filtragem por classes
    - Processamento de streams em tempo real
    - Suporte a GPU (CUDA) e CPU
    - Tracking de objetos
    """

    # Classes COCO (80 classes)
    COCO_CLASSES = {
        0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
        5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
        10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
        14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
        20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
        25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
        30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
        34: "baseball bat", 35: "baseball glove", 36: "skateboard",
        37: "surfboard", 38: "tennis racket", 39: "bottle", 40: "wine glass",
        41: "cup", 42: "fork", 43: "knife", 44: "spoon", 45: "bowl",
        46: "banana", 47: "apple", 48: "sandwich", 49: "orange", 50: "broccoli",
        51: "carrot", 52: "hot dog", 53: "pizza", 54: "donut", 55: "cake",
        56: "chair", 57: "couch", 58: "potted plant", 59: "bed",
        60: "dining table", 61: "toilet", 62: "tv", 63: "laptop", 64: "mouse",
        65: "remote", 66: "keyboard", 67: "cell phone", 68: "microwave",
        69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator", 73: "book",
        74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear",
        78: "hair drier", 79: "toothbrush"
    }

    def __init__(self, config: DetectionConfig = None):
        """
        Inicializa o detector

        Args:
            config: Configurações do detector
        """
        self.config = config or DetectionConfig()
        self._model = None
        self._device = None
        self._frame_count = 0

    def _load_model(self):
        """Carrega o modelo YOLO"""
        if self._model is not None:
            return

        try:
            from ultralytics import YOLO

            # Caminho do modelo
            model_path = os.path.join(MODELS_DIR, self.config.model_name)

            # Se não existir localmente, baixar
            if not os.path.exists(model_path):
                logger.info(f"Baixando modelo {self.config.model_name}...")
                model_path = self.config.model_name

            logger.info(f"Carregando modelo: {model_path}")
            self._model = YOLO(model_path)

            # Configurar device
            if self.config.device == "auto":
                import torch
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self._device = self.config.device

            logger.info(f"Modelo carregado. Device: {self._device}")

        except ImportError:
            logger.error(
                "Ultralytics não instalado. Execute: pip install ultralytics"
            )
            raise

    def detect_image(
        self,
        image_path: str,
        save_result: bool = False,
        output_path: str = None
    ) -> List[Detection]:
        """
        Detecta objetos em uma imagem

        Args:
            image_path: Caminho da imagem
            save_result: Salvar imagem com anotações
            output_path: Caminho para salvar resultado

        Returns:
            Lista de Detection
        """
        self._load_model()

        results = self._model(
            image_path,
            conf=self.config.confidence_threshold,
            iou=self.config.iou_threshold,
            max_det=self.config.max_detections,
            classes=self.config.classes_filter,
            device=self._device,
            half=self.config.half_precision,
            imgsz=self.config.img_size,
            verbose=False
        )

        detections = self._parse_results(results[0])

        if save_result:
            self._save_annotated_image(
                results[0],
                output_path or image_path.replace(".", "_detected.")
            )

        return detections

    def detect_frame(
        self,
        frame,
        return_annotated: bool = False
    ) -> Tuple[List[Detection], Any]:
        """
        Detecta objetos em um frame de vídeo (numpy array)

        Args:
            frame: Frame como numpy array (BGR)
            return_annotated: Retornar frame anotado

        Returns:
            Tupla (lista de Detection, frame anotado ou None)
        """
        self._load_model()
        self._frame_count += 1

        results = self._model(
            frame,
            conf=self.config.confidence_threshold,
            iou=self.config.iou_threshold,
            max_det=self.config.max_detections,
            classes=self.config.classes_filter,
            device=self._device,
            half=self.config.half_precision,
            imgsz=self.config.img_size,
            verbose=False
        )

        detections = self._parse_results(results[0], frame_id=self._frame_count)

        annotated = None
        if return_annotated:
            annotated = results[0].plot()

        return detections, annotated

    def _parse_results(
        self,
        result,
        frame_id: int = 0
    ) -> List[Detection]:
        """Converte resultados YOLO para objetos Detection"""
        detections = []

        boxes = result.boxes
        if boxes is None:
            return detections

        for box in boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = tuple(map(int, box.xyxy[0].tolist()))

            detection = Detection(
                class_id=class_id,
                class_name=self.COCO_CLASSES.get(class_id, f"class_{class_id}"),
                confidence=confidence,
                bbox=bbox,
                frame_id=frame_id
            )

            detections.append(detection)

        return detections

    def _save_annotated_image(self, result, output_path: str):
        """Salva imagem com anotações"""
        try:
            import cv2
            annotated = result.plot()
            cv2.imwrite(output_path, annotated)
            logger.info(f"Imagem anotada salva: {output_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar imagem: {e}")

    async def process_stream(
        self,
        stream_url: str,
        callback=None,
        skip_frames: int = 0,
        max_frames: int = None
    ):
        """
        Processa stream de vídeo em tempo real

        Args:
            stream_url: URL do stream (RTSP, arquivo, webcam)
            callback: Função chamada a cada detecção
            skip_frames: Pular N frames entre detecções
            max_frames: Número máximo de frames a processar

        Yields:
            Detection para cada objeto detectado
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV não instalado. Execute: pip install opencv-python-headless")
            return

        self._load_model()

        cap = cv2.VideoCapture(stream_url)

        if not cap.isOpened():
            logger.error(f"Não foi possível abrir stream: {stream_url}")
            return

        logger.info(f"Processando stream: {stream_url}")

        frame_count = 0
        processed_count = 0

        try:
            while True:
                ret, frame = cap.read()

                if not ret:
                    logger.warning("Fim do stream ou erro de leitura")
                    break

                frame_count += 1

                # Pular frames conforme configurado
                if skip_frames > 0 and frame_count % (skip_frames + 1) != 0:
                    continue

                processed_count += 1

                # Detectar
                detections, _ = self.detect_frame(frame)

                for detection in detections:
                    if callback:
                        await callback(detection)
                    yield detection

                # Limite de frames
                if max_frames and processed_count >= max_frames:
                    break

                # Permitir outras tarefas async
                await asyncio.sleep(0)

        finally:
            cap.release()
            logger.info(
                f"Stream finalizado. Frames: {frame_count}, "
                f"Processados: {processed_count}"
            )

    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações do modelo"""
        self._load_model()

        return {
            "model_name": self.config.model_name,
            "device": self._device,
            "classes": len(self.COCO_CLASSES),
            "img_size": self.config.img_size,
            "confidence_threshold": self.config.confidence_threshold,
            "iou_threshold": self.config.iou_threshold
        }


class AlertManager:
    """
    Gerenciador de alertas baseado em detecções

    Permite configurar regras para disparar alertas quando
    determinados objetos são detectados.
    """

    def __init__(self):
        self._rules = []
        self._handlers = []
        self._detection_history = []
        self._max_history = 1000

    def add_rule(
        self,
        name: str,
        classes: List[str],
        min_confidence: float = 0.5,
        min_count: int = 1,
        cooldown_seconds: int = 60,
        zones: List[Dict] = None
    ):
        """
        Adiciona regra de alerta

        Args:
            name: Nome da regra
            classes: Classes que disparam alerta
            min_confidence: Confiança mínima
            min_count: Quantidade mínima de objetos
            cooldown_seconds: Tempo entre alertas
            zones: Zonas de detecção (opcional)
        """
        self._rules.append({
            "name": name,
            "classes": classes,
            "min_confidence": min_confidence,
            "min_count": min_count,
            "cooldown": cooldown_seconds,
            "zones": zones,
            "last_alert": None
        })

    def on_alert(self, handler):
        """Decorator para handlers de alerta"""
        self._handlers.append(handler)
        return handler

    async def process_detection(self, detection: Detection) -> List[Dict]:
        """
        Processa detecção e verifica regras

        Args:
            detection: Detecção a processar

        Returns:
            Lista de alertas disparados
        """
        # Adicionar ao histórico
        self._detection_history.append(detection)
        if len(self._detection_history) > self._max_history:
            self._detection_history = self._detection_history[-self._max_history:]

        alerts = []

        for rule in self._rules:
            if self._check_rule(detection, rule):
                alert = {
                    "rule": rule["name"],
                    "detection": detection.to_dict(),
                    "timestamp": datetime.now().isoformat()
                }

                alerts.append(alert)
                rule["last_alert"] = datetime.now()

                # Notificar handlers
                for handler in self._handlers:
                    try:
                        await handler(alert)
                    except Exception as e:
                        logger.error(f"Erro no handler de alerta: {e}")

        return alerts

    def _check_rule(self, detection: Detection, rule: Dict) -> bool:
        """Verifica se detecção dispara regra"""
        # Verificar classe
        if detection.class_name not in rule["classes"]:
            return False

        # Verificar confiança
        if detection.confidence < rule["min_confidence"]:
            return False

        # Verificar cooldown
        if rule["last_alert"]:
            elapsed = (datetime.now() - rule["last_alert"]).total_seconds()
            if elapsed < rule["cooldown"]:
                return False

        # Verificar zonas (se configuradas)
        if rule["zones"]:
            in_zone = False
            for zone in rule["zones"]:
                if self._point_in_zone(detection.center, zone):
                    in_zone = True
                    break
            if not in_zone:
                return False

        return True

    def _point_in_zone(
        self,
        point: Tuple[int, int],
        zone: Dict
    ) -> bool:
        """Verifica se ponto está dentro da zona"""
        x, y = point
        return (
            zone["x1"] <= x <= zone["x2"] and
            zone["y1"] <= y <= zone["y2"]
        )


# Exemplo de uso
if __name__ == "__main__":
    print("Guardian - Detector YOLO")
    print("Uso:")
    print("  detector = YOLODetector()")
    print("  results = detector.detect_image('imagem.jpg')")
    print("  for det in results:")
    print("      print(f'{det.class_name}: {det.confidence:.2f}')")
