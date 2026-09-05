# -*- coding: utf-8 -*-
"""
Fluent Photo Viewer — PyQt5 + PyQt-Fluent-Widgets
简体中文版（无导航栏，关于为无标题栏独立弹窗）
"""

import os
import sys
import subprocess
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QTransform, QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QFileDialog, QScrollArea, QFrame,
    QGridLayout, QDialog, QGraphicsDropShadowEffect
)
from qfluentwidgets import (
    PrimaryPushButton, PushButton, TransparentToolButton,
    CaptionLabel, InfoBar, InfoBarPosition, isDarkTheme,
    setTheme, Theme, HyperlinkLabel, SubtitleLabel, BodyLabel,
    TitleLabel, FluentIcon
)

# ── 可选依赖检测 ──────────────────────────────────────────────────────

try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import rawpy
    HAS_RAWPY = True
except ImportError:
    HAS_RAWPY = False

# ── 格式定义 ──────────────────────────────────────────────────────────

QT_EXTS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif',
    '.webp', '.tiff', '.tif', '.ico', '.svg',
    '.icns', '.wbmp', '.xpm', '.pbm', '.pgm',
    '.ppm', '.pnm',
}

PIL_EXTS = {
    '.pcx', '.tga', '.j2k', '.jp2', '.dds',
    '.sgi', '.psd', '.heic', '.heif', '.avif',
    '.jxl', '.apng', '.blp', '.dcx', '.fit',
    '.fits', '.fli', '.flc', '.ftc', '.ftu',
    '.gbr', '.gd', '.im', '.mic', '.mpo',
    '.msp', '.pcd', '.pxr', '.sun', '.wal',
    '.xbm',
}

RAW_EXTS = {
    '.raw', '.cr2', '.nef', '.arw', '.dng',
    '.orf', '.rw2', '.pef', '.sr2', '.raf',
    '.mrw', '.kdc', '.dcr', '.erf', '.mos',
    '.nrw', '.3fr', '.mef', '.iiq', '.rwl',
    '.srf', '.srw',
}

IMAGE_EXTS = set(QT_EXTS)

if HAS_PIL:
    IMAGE_EXTS |= PIL_EXTS

if HAS_RAWPY:
    IMAGE_EXTS |= RAW_EXTS

_ALL_EXTS = sorted(IMAGE_EXTS)
_wildcards = " ".join(f"*{ext}" for ext in _ALL_EXTS)
IMAGE_FILTER = f"图片文件 ({_wildcards});;所有文件 (*)"

THUMB_SIZE = 150
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))


# ── 统一图片加载 ──────────────────────────────────────────────────────

def _load_pixmap(path):
    pm = QPixmap(path)
    if not pm.isNull():
        return pm

    ext = os.path.splitext(path)[1].lower()

    if HAS_PIL and ext in PIL_EXTS:
        try:
            img = Image.open(path)
            if img.mode == 'RGBA':
                data = img.tobytes("raw", "RGBA")
                qimg = QImage(data, img.width, img.height,
                              QImage.Format_RGBA8888).copy()
            elif img.mode == 'P':
                img = img.convert('RGBA')
                data = img.tobytes("raw", "RGBA")
                qimg = QImage(data, img.width, img.height,
                              QImage.Format_RGBA8888).copy()
            elif img.mode == 'L':
                data = img.tobytes("raw", "L")
                qimg = QImage(data, img.width, img.height,
                              QImage.Format_Grayscale8).copy()
            else:
                img = img.convert('RGB')
                data = img.tobytes("raw", "RGB")
                qimg = QImage(data, img.width, img.height,
                              QImage.Format_RGB888).copy()
            return QPixmap.fromImage(qimg)
        except Exception:
            pass

    if HAS_RAWPY and ext in RAW_EXTS:
        try:
            with rawpy.imread(path) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True, half_size=True,
                    no_auto_bright=False, output_bps=8)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line,
                          QImage.Format_RGB888).copy()
            return QPixmap.fromImage(qimg)
        except Exception:
            pass

    return QPixmap()


def _format_size(size_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ═══════════════════════════════════════════════════════════════════════
#  About Dialog（无标题栏浮动卡片）
# ═══════════════════════════════════════════════════════════════════════

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 420)
        self._dragPos = None

        dark = isDarkTheme()
        bg      = '#1e1e1e' if dark else '#ffffff'
        border  = '#333333' if dark else '#e0e0e0'
        txt     = '#e0e0e0' if dark else '#1a1a1a'
        muted   = '#888888' if dark else '#666666'

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 120 if dark else 60))

        card = QWidget()
        card.setObjectName("aboutCard")
        card.setStyleSheet(f"""
            #aboutCard {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 16, 28, 24)
        cl.setSpacing(12)

        titleRow = QHBoxLayout()
        titleRow.setContentsMargins(0, 0, 0, 0)

        lblTitle = SubtitleLabel("关于")
        lblTitle.setStyleSheet(f"color: {txt};")
        titleRow.addWidget(lblTitle)
        titleRow.addStretch()

        btnClose = TransparentToolButton(FluentIcon.CLOSE)
        btnClose.setFixedSize(28, 28)
        btnClose.setToolTip("关闭")
        btnClose.clicked.connect(self.accept)
        titleRow.addWidget(btnClose)

        cl.addLayout(titleRow)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {border}; max-height: 1px;")
        cl.addWidget(sep)

        appTitle = TitleLabel("Fluent Photo Viewer")
        appTitle.setAlignment(Qt.AlignCenter)
        appTitle.setStyleSheet(f"color: {txt};")
        cl.addWidget(appTitle)

        desc = BodyLabel(
            "基于 PyQt5 + PyQt-Fluent-Widgets 构建，"
            "一款简洁优雅的本地图片浏览器。"
            "支持多种常见图片格式的浏览、旋转、缩放等操作。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {muted}; font-size: 13px;")
        cl.addWidget(desc)

        cl.addSpacing(4)

        lblAuthor = SubtitleLabel("作者")
        lblAuthor.setStyleSheet(f"color: {txt};")
        cl.addWidget(lblAuthor)

        for name in ["SYSTEM-WINOS-RE", "4795_Tester", "Xiaomi MiMo AI"]:
            label = BodyLabel(name)
            label.setStyleSheet(f"color: {txt}; font-size: 14px;")
            cl.addWidget(label)

        cl.addSpacing(4)

        githubLink = HyperlinkLabel(
            "https://github.com/minecraft-os/FluentView",
            "从 Github 查看源码")
        cl.addWidget(githubLink)

        cl.addStretch()

        btnBottom = PushButton("关闭")
        btnBottom.setFixedWidth(100)
        btnBottom.clicked.connect(self.accept)
        btnRow = QHBoxLayout()
        btnRow.addStretch()
        btnRow.addWidget(btnBottom)
        cl.addLayout(btnRow)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragPos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._dragPos and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPos() - self._dragPos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._dragPos = None


# ═══════════════════════════════════════════════════════════════════════
#  Thumbnail Card
# ═══════════════════════════════════════════════════════════════════════

class ThumbCard(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, path, pixmap, parent=None):
        super().__init__(parent)
        self.path = path
        self.pix = pixmap
        self._hover = False
        self.setFixedSize(THUMB_SIZE + 20, THUMB_SIZE + 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(os.path.basename(path))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self._hover:
            p.setBrush(QColor(0, 0, 0, 18))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, w, h, 8, 8)
        ix = (w - self.pix.width()) // 2
        p.drawPixmap(ix, 2, self.pix)
        name = os.path.basename(self.path)
        if len(name) > 22:
            name = name[:19] + "..."
        fg = QColor(60, 60, 60) if not isDarkTheme() else QColor(200, 200, 200)
        p.setPen(fg)
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(QRect(0, THUMB_SIZE + 4, w, 28),
                   Qt.AlignHCenter | Qt.AlignTop, name)
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.path)


# ═══════════════════════════════════════════════════════════════════════
#  Image Viewer
# ═══════════════════════════════════════════════════════════════════════

class ImageViewer(QWidget):
    zoomChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._orig = None
        self._path = ""
        self._zoom = 1.0
        self._rot = 0
        self._off = QPoint(0, 0)
        self._drag = False
        self._dragStart = QPoint()
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def loadImage(self, path):
        pm = _load_pixmap(path)
        if pm.isNull():
            return
        self._path = path
        self._orig = pm
        self._rot = 0
        self.fitToWindow()

    def zoomIn(self):
        self._zoom = min(self._zoom * 1.25, 10.0)
        self.zoomChanged.emit(int(self._zoom * 100))
        self.update()

    def zoomOut(self):
        self._zoom = max(self._zoom / 1.25, 0.05)
        self.zoomChanged.emit(int(self._zoom * 100))
        self.update()

    def fitToWindow(self):
        if not self._orig:
            return
        vw, vh = self.width(), self.height()
        iw, ih = self._orig.width(), self._orig.height()
        if iw == 0 or ih == 0:
            return
        self._zoom = min(vw / iw, vh / ih) * 0.96
        self._off = QPoint(0, 0)
        self.zoomChanged.emit(int(self._zoom * 100))
        self.update()

    def rotateCW(self):
        self._rot = (self._rot + 90) % 360
        self.update()

    def getRotatedPixmap(self):
        if not self._orig:
            return QPixmap()
        return self._orig.transformed(
            QTransform().rotate(self._rot), Qt.SmoothTransformation)

    def getCurrentPath(self):
        return self._path

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        dark = isDarkTheme()
        p.fillRect(self.rect(),
                   QColor(30, 30, 30) if dark else QColor(245, 245, 245))
        if not self._orig:
            fg = QColor(120, 120, 120) if dark else QColor(180, 180, 180)
            p.setPen(fg)
            p.setFont(QFont("Microsoft YaHei", 13))
            p.drawText(self.rect(), Qt.AlignCenter, "选择一张图片以查看")
            p.end()
            return
        pm = self.getRotatedPixmap()
        dw = int(pm.width() * self._zoom)
        dh = int(pm.height() * self._zoom)
        dx = (self.width() - dw) // 2 + self._off.x()
        dy = (self.height() - dh) // 2 + self._off.y()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 18))
        p.drawRoundedRect(dx + 3, dy + 3, dw, dh, 4, 4)
        p.drawPixmap(dx, dy, dw, dh, pm)
        p.end()

    def wheelEvent(self, e):
        if e.angleDelta().y() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = True
            self._dragStart = e.pos()

    def mouseMoveEvent(self, e):
        if self._drag:
            self._off += e.pos() - self._dragStart
            self._dragStart = e.pos()
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = False

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._orig:
            self.fitToWindow()


# ═══════════════════════════════════════════════════════════════════════
#  Background Thumbnail Loader
# ═══════════════════════════════════════════════════════════════════════

class ThumbLoader(QThread):
    loaded = pyqtSignal(str, object)

    def __init__(self, paths):
        super().__init__()
        self.paths = paths
        self._stop = False

    def run(self):
        for p in self.paths:
            if self._stop:
                break
            pm = _load_pixmap(p)
            if not pm.isNull():
                ext = os.path.splitext(p)[1].lower()
                if ext == '.gif':
                    pm = pm.copy(0, 0, pm.width(), pm.height())
                pm = pm.scaled(THUMB_SIZE, THUMB_SIZE,
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.loaded.emit(p, pm)

    def stop(self):
        self._stop = True


# ═══════════════════════════════════════════════════════════════════════
#  Gallery Page
# ═══════════════════════════════════════════════════════════════════════

class GalleryPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("galleryPage")
        self.setStyleSheet("background: transparent;")
        self._paths = []
        self._current = ""
        self._loader = None
        self._fullCallback = None
        self._aboutCallback = None
        self._editCallback = None

        # ── Toolbar ──
        self.btnOpen       = PrimaryPushButton("添加文件")
        self.btnOpenFolder = PushButton("添加文件夹")
        self.btnClear      = PushButton("清空")
        self.btnRotate     = PushButton("旋转")
        self.btnZoomIn     = PushButton("放大")
        self.btnZoomOut    = PushButton("缩小")
        self.btnFit        = PushButton("适配屏幕")
        self.btnEdit       = PushButton("编辑")
        self.btnAbout      = PushButton("关于")

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(14, 10, 14, 6)
        toolbar.setSpacing(8)
        for b in (self.btnOpen, self.btnOpenFolder, self.btnClear,
                  self.btnRotate, self.btnZoomIn,
                  self.btnZoomOut, self.btnFit, self.btnEdit):
            toolbar.addWidget(b)
        toolbar.addStretch()
        self.lblCount = CaptionLabel("共 0 张图片")
        toolbar.addWidget(self.lblCount)
        toolbar.addSpacing(8)
        toolbar.addWidget(self.btnAbout)

        # ── Thumbnail Grid ──
        self.gridWidget = QWidget()
        self.gridWidget.setStyleSheet("background: transparent;")
        self.gridLayout = QGridLayout(self.gridWidget)
        self.gridLayout.setContentsMargins(14, 14, 14, 14)
        self.gridLayout.setSpacing(8)

        gridScroll = QScrollArea()
        gridScroll.setWidgetResizable(True)
        gridScroll.setFrameShape(QFrame.NoFrame)
        gridScroll.setStyleSheet(
            "QScrollArea { background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }")
        gridScroll.setWidget(self.gridWidget)

        # ── Image Viewer ──
        self.viewer = ImageViewer()

        self.btnBack = TransparentToolButton(FluentIcon.RETURN)
        self.btnBack.setToolTip("返回缩略图")
        self.btnPrev = TransparentToolButton(FluentIcon.LEFT_ARROW)
        self.btnPrev.setToolTip("上一张 (←)")
        self.btnNext = TransparentToolButton(FluentIcon.CHEVRON_RIGHT)
        self.btnNext.setToolTip("下一张 (→)")
        self.btnFull = TransparentToolButton(FluentIcon.FULL_SCREEN)
        self.btnFull.setToolTip("全屏 (F)")

        self.lblZoom = CaptionLabel("100%")
        self.lblZoom.setFixedWidth(50)
        self.lblInfo = CaptionLabel("")
        self.lblPhotoInfo = CaptionLabel("")
        self.lblPhotoInfo.setContentsMargins(10, 0, 0, 0)

        bar = QWidget()
        bar.setFixedHeight(32)
        vb = QHBoxLayout(bar)
        vb.setContentsMargins(6, 0, 6, 0)
        vb.setSpacing(3)
        for w in (self.btnBack, self.btnPrev, self.btnNext, self.btnFull):
            vb.addWidget(w)
        vb.addSpacing(8)
        vb.addWidget(self.lblZoom)
        vb.addWidget(self.lblPhotoInfo)
        vb.addStretch()
        vb.addWidget(self.lblInfo)

        viewerWrap = QWidget()
        vl = QVBoxLayout(viewerWrap)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)
        vl.addWidget(self.viewer, 1)
        vl.addWidget(bar, 0)

        # ── Stacked ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.stack.addWidget(gridScroll)
        self.stack.addWidget(viewerWrap)
        self.stack.setCurrentIndex(0)

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addLayout(toolbar)
        mainLayout.addWidget(self.stack)

        self.btnBack.clicked.connect(self._backToGrid)
        self.btnPrev.clicked.connect(self._prev)
        self.btnNext.clicked.connect(self._next)
        self.btnFull.clicked.connect(self._toggleFull)
        self.btnEdit.clicked.connect(self._openEdit)
        self.btnAbout.clicked.connect(self._openAbout)
        self.viewer.zoomChanged.connect(
            lambda v: self.lblZoom.setText(f"{v}%"))

    # ── Public ──

    def addFiles(self, paths):
        added = 0
        for p in paths:
            if os.path.isfile(p) and os.path.splitext(p)[1].lower() in IMAGE_EXTS:
                if p not in self._paths:
                    self._paths.append(p)
                    added += 1
        self._rebuildGrid()
        self.lblCount.setText(f"共 {len(self._paths)} 张图片")
        if added:
            self._loadThumbs()

    def loadFolder(self, folder):
        self._stopLoader()
        self._clearGrid()
        self._paths = []
        self._current = ""
        self.stack.setCurrentIndex(0)
        self._paths = sorted(
            os.path.join(folder, f) for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS)
        self.lblCount.setText(f"共 {len(self._paths)} 张图片")
        if not self._paths:
            InfoBar.warning("空文件夹", "未找到图片", parent=self)
            return
        self._rebuildGrid()
        self._loadThumbs()

    def clearGallery(self):
        self._stopLoader()
        self._paths.clear()
        self._current = ""
        self._clearGrid()
        self.viewer._orig = None
        self.viewer.update()
        self.stack.setCurrentIndex(0)
        self.lblCount.setText("共 0 张图片")

    # ── Internal ──

    def _clearGrid(self):
        while self.gridLayout.count():
            item = self.gridLayout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _rebuildGrid(self):
        self._clearGrid()
        if not self._paths:
            return
        cols = max(1, (self.gridWidget.width() - 28) // (THUMB_SIZE + 28))
        for i, path in enumerate(self._paths):
            pm = _load_pixmap(path)
            if pm.isNull():
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext == '.gif':
                pm = pm.copy(0, 0, pm.width(), pm.height())
            pm = pm.scaled(THUMB_SIZE, THUMB_SIZE,
                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
            card = ThumbCard(path, pm)
            card.clicked.connect(self._viewImage)
            r, c = divmod(i, cols)
            self.gridLayout.addWidget(card, r, c)

    def _loadThumbs(self):
        self._stopLoader()
        self._loader = ThumbLoader(self._paths)
        self._loader.loaded.connect(self._onThumbLoaded)
        self._loader.start()

    def _onThumbLoaded(self, path, pix):
        for i in range(self.gridLayout.count()):
            item = self.gridLayout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ThumbCard):
                card = item.widget()
                if card.path == path:
                    card.pix = pix
                    card.update()
                    break

    def _stopLoader(self):
        if self._loader and self._loader.isRunning():
            self._loader.stop()
            self._loader.wait(2000)
            self._loader = None

    def _backToGrid(self):
        self.stack.setCurrentIndex(0)

    def _viewImage(self, path):
        if path not in self._paths:
            return
        self._current = path
        self.viewer.loadImage(path)
        self.stack.setCurrentIndex(1)
        self.lblInfo.setText(os.path.basename(path))
        if self.viewer._orig:
            w, h = self.viewer._orig.width(), self.viewer._orig.height()
            fs = os.path.getsize(path) if os.path.isfile(path) else 0
            self.lblPhotoInfo.setText(
                f"{w} x {h} px  |  {_format_size(fs)}")
        else:
            self.lblPhotoInfo.setText("")

    def _prev(self):
        if not self._current or not self._paths:
            return
        idx = self._paths.index(self._current) - 1
        if idx >= 0:
            self._viewImage(self._paths[idx])

    def _next(self):
        if not self._current or not self._paths:
            return
        idx = self._paths.index(self._current) + 1
        if idx < len(self._paths):
            self._viewImage(self._paths[idx])

    def _toggleFull(self):
        if self._fullCallback:
            self._fullCallback()

    def _openEdit(self):
        if self._editCallback:
            self._editCallback()

    def _openAbout(self):
        if self._aboutCallback:
            self._aboutCallback()

    def getCurrentImage(self):
        if self._current and self.viewer._orig:
            return self._current, self.viewer.getRotatedPixmap()
        return None, None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._paths and self.stack.currentIndex() == 0:
            self._rebuildGrid()


# ═══════════════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════════════

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("照片查看器")

        icon_path = os.path.join(BASE_DIR, "favicon.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            QApplication.instance().setWindowIcon(QIcon(icon_path))

        self.resize(1280, 720)
        self.setMinimumSize(960, 640)

        dark = isDarkTheme()
        self.setStyleSheet(f"""
            QWidget {{
                background: {"#1a1a1a" if dark else "#f5f5f5"};
                color: {"#e0e0e0" if dark else "#1a1a1a"};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 16px;
                background: {"#3a3a3a" if dark else "#e8e8e8"};
                border: 1px solid {"#4a4a4a" if dark else "#d0d0d0"};
            }}
            QPushButton:hover {{
                background: {"#4a4a4a" if dark else "#d8d8d8"};
            }}
        """)

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2,
                  (screen.height() - self.height()) // 2)

        self.galleryPage = GalleryPage()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.galleryPage)

        gp = self.galleryPage
        gp.btnOpen.clicked.connect(self._openFiles)
        gp.btnOpenFolder.clicked.connect(self._openFolder)
        gp.btnClear.clicked.connect(self._clearGallery)
        gp.btnRotate.clicked.connect(lambda: gp.viewer.rotateCW())
        gp.btnZoomIn.clicked.connect(lambda: gp.viewer.zoomIn())
        gp.btnZoomOut.clicked.connect(lambda: gp.viewer.zoomOut())
        gp.btnFit.clicked.connect(lambda: gp.viewer.fitToWindow())
        gp.btnEdit.clicked.connect(self._editImage)
        gp.btnFull.clicked.connect(self._toggleFull)
        gp._fullCallback = self._toggleFull
        gp._aboutCallback = self._showAbout
        gp._editCallback = self._editImage

    def openFiles(self, paths):
        self.galleryPage.addFiles(paths)

    def _openFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", "", IMAGE_FILTER)
        if files:
            self.galleryPage.addFiles(files)

    def _openFolder(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if d:
            self.galleryPage.loadFolder(d)

    def _clearGallery(self):
        self.galleryPage.clearGallery()
        InfoBar.success("已清空", "已清空所有图片",
                        orient=Qt.Horizontal, isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000, parent=self)

    def _toggleFull(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _editImage(self):
        path, _ = self.galleryPage.getCurrentImage()
        if not path:
            InfoBar.warning("无图片", "请先选择一张图片再进行编辑",
                            orient=Qt.Horizontal, isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000, parent=self)
            return

        win_dir = os.environ.get("SystemRoot", r"C:\Windows")

        mspaint = os.path.join(win_dir, "System32", "mspaint.exe")
        try:
            subprocess.Popen([mspaint, path])
            return
        except Exception:
            pass

        mspaint = os.path.join(win_dir, "SysWOW64", "mspaint.exe")
        try:
            subprocess.Popen([mspaint, path])
            return
        except Exception:
            pass

        InfoBar.error("打开失败",
                      "无法启动画图程序，请确认系统中存在 mspaint.exe",
                      orient=Qt.Horizontal, isClosable=True,
                      position=InfoBarPosition.TOP,
                      duration=3000, parent=self)

    def _showAbout(self):
        dlg = AboutDialog(self)
        dlg.exec_()

    def closeEvent(self, e):
        self.galleryPage._stopLoader()
        super().closeEvent(e)


# ═══════════════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)

    window = MainWindow()
    imageArgs = [
        a for a in sys.argv[1:]
        if os.path.isfile(a) and os.path.splitext(a)[1].lower() in IMAGE_EXTS
    ]
    if imageArgs:
        window.openFiles(imageArgs)

    window.show()
    sys.exit(app.exec_())
