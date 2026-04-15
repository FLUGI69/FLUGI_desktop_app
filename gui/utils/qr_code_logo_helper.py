import io
from pathlib import Path
from typing import cast

from PIL import Image
from PIL.Image import Image as PILImage, Resampling
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, QSize, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

def load_qr_logo(logo_path: str | Path, max_size: tuple[int, int] | None = None) -> PILImage:

    path: Path = Path(logo_path)

    if path.exists() == False:

        raise FileNotFoundError("QR logo file was not found: %s" % path)

    if path.suffix.lower() != ".svg":

        raster_logo: PILImage = cast(PILImage, Image.open(path).convert("RGBA"))

        if max_size is not None:

            raster_logo.thumbnail(max_size, Resampling.LANCZOS)

        return raster_logo

    renderer: QSvgRenderer = QSvgRenderer(str(path))

    if renderer.isValid() == False:

        raise ValueError("QR logo SVG could not be rendered: %s" % path)

    source_size: QSize = renderer.defaultSize()

    if source_size.isEmpty():

        source_size = QSize(512, 512)

    min_render_px: int = 512

    render_width: int = source_size.width()
    render_height: int = source_size.height()

    if render_width < min_render_px and render_height < min_render_px:

        up_scale: float = float(min_render_px) / float(max(render_width, render_height))
        render_width = max(1, int(round(float(render_width) * up_scale)))
        render_height = max(1, int(round(float(render_height) * up_scale)))

    render_size: QSize = QSize(render_width, render_height)

    image: QImage = QImage(render_size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter: QPainter = QPainter(image)

    try:

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        render_rect: QRectF = QRectF(
            0.0,
            0.0,
            float(render_width),
            float(render_height)
        )

        renderer.render(painter, render_rect)

    finally:

        painter.end()

    byte_array: QByteArray = QByteArray()
    buffer: QBuffer = QBuffer(byte_array)

    if buffer.open(QIODevice.OpenModeFlag.WriteOnly) == False:

        raise OSError("QR logo buffer could not be opened for writing: %s" % path)

    try:

        if image.save(buffer, "PNG") == False:

            raise OSError("QR logo SVG could not be converted to PNG: %s" % path)

    finally:

        buffer.close()

    result: PILImage = cast(PILImage, Image.open(io.BytesIO(bytes(byte_array))).convert("RGBA"))

    if max_size is not None:

        result.thumbnail(max_size, Resampling.LANCZOS)

    return result