# -*- coding: utf-8 -*-
"""
Fluent Photo Viewer — PyQt5 + PyQt-Fluent-Widgets
Supports: python photo_viewer.py image.jpg
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QTransform
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QFileDialog, QScrollArea, QFrame, QLabel,
    QGridLayout
)
from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition,
    PrimaryPushButton, PushButton, TransparentToolButton,
    CaptionLabel, TitleLabel, BodyLabel,
    InfoBar, InfoBarPosition, isDarkTheme,
    setTheme, Theme, HyperlinkLabel, SubtitleLabel,
    SwitchSettingCard, SettingCardGroup
)

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
THUMB_SIZE = 150


def _format_size(size_bytes):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


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
        pm = QPixmap(path)
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
            QTransform().rotate(self._rot), Qt.SmoothTransformation
        )

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
            pm = QPixmap(p)
            if not pm.isNull():
                if p.lower().endswith('.gif'):
                    pm = pm.copy(0, 0, pm.width(), pm.height())
                pm = pm.scaled(THUMB_SIZE, THUMB_SIZE,
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.loaded.emit(p, pm)

    def stop(self):
        self._stop = True


# ═══════════════════════════════════════════════════════════════════════
#  Gallery Page ("图片浏览")
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

        # ── Toolbar ────────────────────────────────────────────────────
        self.btnOpen = PrimaryPushButton("添加文件")
        self.btnOpenFolder = PushButton("添加文件夹")
        self.btnClear = PushButton("清空")
        self.btnFill = PushButton("填充")
        self.btnRotate = PushButton("旋转")
        self.btnZoomIn = PushButton("放大")
        self.btnZoomOut = PushButton("缩小")
        self.btnFit = PushButton("适配屏幕")

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(14, 10, 14, 6)
        toolbar.setSpacing(8)
        for b in (self.btnOpen, self.btnOpenFolder, self.btnClear,
                  self.btnFill, self.btnRotate, self.btnZoomIn,
                  self.btnZoomOut, self.btnFit):
            toolbar.addWidget(b)
        toolbar.addStretch()
        self.lblCount = CaptionLabel("共 0 张图片")
        toolbar.addWidget(self.lblCount)

        # ── Thumbnail Grid ─────────────────────────────────────────────
        self.gridWidget = QWidget()
        self.gridWidget.setStyleSheet("background: transparent;")
        self.gridLayout = QGridLayout(self.gridWidget)
        self.gridLayout.setContentsMargins(14, 14, 14, 14)
        self.gridLayout.setSpacing(8)

        gridScroll = QScrollArea()
        gridScroll.setWidgetResizable(True)
        gridScroll.setFrameShape(QFrame.NoFrame)
        gridScroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)
        gridScroll.setWidget(self.gridWidget)

        # ── Image Viewer ───────────────────────────────────────────────
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

        viewerBarWidget = QWidget()
        viewerBarWidget.setFixedHeight(32)
        viewerBar = QHBoxLayout(viewerBarWidget)
        viewerBar.setContentsMargins(6, 0, 6, 0)
        viewerBar.setSpacing(3)
        viewerBar.addWidget(self.btnBack)
        viewerBar.addWidget(self.btnPrev)
        viewerBar.addWidget(self.btnNext)
        viewerBar.addWidget(self.btnFull)
        viewerBar.addSpacing(8)
        viewerBar.addWidget(self.lblZoom)
        viewerBar.addWidget(self.lblPhotoInfo)
        viewerBar.addStretch()
        viewerBar.addWidget(self.lblInfo)

        viewerWrap = QWidget()
        vwLayout = QVBoxLayout(viewerWrap)
        vwLayout.setContentsMargins(0, 0, 0, 0)
        vwLayout.setSpacing(0)
        vwLayout.addWidget(self.viewer, 1)
        vwLayout.addWidget(viewerBarWidget, 0)

        # ── Stacked ────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.stack.addWidget(gridScroll)
        self.stack.addWidget(viewerWrap)
        self.stack.setCurrentIndex(0)

        # ── Main layout ────────────────────────────────────────────────
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addLayout(toolbar)
        mainLayout.addWidget(self.stack)

        # ── Connect ────────────────────────────────────────────────────
        self.btnBack.clicked.connect(self._backToGrid)
        self.btnPrev.clicked.connect(self._prev)
        self.btnNext.clicked.connect(self._next)
        self.btnFull.clicked.connect(self._toggleFull)
        self.viewer.zoomChanged.connect(
            lambda v: self.lblZoom.setText(f"{v}%")
        )

    # ── Public ─────────────────────────────────────────────────────────

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
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS
        )
        self.lblCount.setText(f"共 {len(self._paths)} 张图片")

        if not self._paths:
            InfoBar.warning("空文件夹", "未找到图片")
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

    def fillGallery(self):
        self._stopLoader()
        self._paths.clear()
        self._clearGrid()
        self.stack.setCurrentIndex(0)

        colors = [
            QColor(220, 80, 80), QColor(80, 180, 80),
            QColor(80, 120, 220), QColor(220, 180, 40),
            QColor(160, 80, 200), QColor(40, 180, 180),
        ]
        n = 16
        colCount = max(1, (self.gridWidget.width() - 28) // (THUMB_SIZE + 28))
        for i in range(n):
            pm = QPixmap(THUMB_SIZE, THUMB_SIZE)
            pm.fill(colors[i % len(colors)])
            qp = QPainter(pm)
            qp.setPen(QColor(255, 255, 255))
            qp.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
            qp.drawText(pm.rect(), Qt.AlignCenter, f"图片 {i + 1}")
            qp.end()
            card = ThumbCard(f"sample_{i + 1}.jpg", pm)
            card.clicked.connect(self._viewImage)
            r, c = divmod(i, colCount)
            self.gridLayout.addWidget(card, r, c)

        self.lblCount.setText(f"共 {n} 张图片")

    # ── Internal ───────────────────────────────────────────────────────

    def _clearGrid(self):
        """Properly clear all widgets from QGridLayout."""
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
        avail = self.gridWidget.width() - 28
        cardW = THUMB_SIZE + 20
        colCount = max(1, avail // cardW)
        for i, path in enumerate(self._paths):
            pm = QPixmap(path)
            if pm.isNull():
                continue
            if path.lower().endswith('.gif'):
                pm = pm.copy(0, 0, pm.width(), pm.height())
            pm = pm.scaled(THUMB_SIZE, THUMB_SIZE,
                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
            card = ThumbCard(path, pm)
            card.clicked.connect(self._viewImage)
            r, c = divmod(i, colCount)
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

        # photo info
        name = os.path.basename(path)
        self.lblInfo.setText(name)
        if self.viewer._orig:
            w, h = self.viewer._orig.width(), self.viewer._orig.height()
            fsize = os.path.getsize(path) if os.path.isfile(path) else 0
            self.lblPhotoInfo.setText(
                f"{w} x {h} px  |  {_format_size(fsize)}"
            )
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

    def getCurrentImage(self):
        if self._current and self.viewer._orig:
            return self._current, self.viewer.getRotatedPixmap()
        return None, None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._paths and self.stack.currentIndex() == 0:
            self._rebuildGrid()


# ═══════════════════════════════════════════════════════════════════════
#  Export Page ("导出")
# ═══════════════════════════════════════════════════════════════════════

class ExportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("exportPage")
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(TitleLabel("导出图片"))
        layout.addWidget(BodyLabel("在\"图片浏览\"中选择一张图片，然后在此保存到其他位置"))

        self.preview = QLabel("请先选择一张图片")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(300)
        self.preview.setFrameShape(QFrame.StyledPanel)
        self.preview.setStyleSheet(
            "QLabel { border: 2px dashed rgba(150,150,150,0.5); "
            "border-radius: 8px; color: rgba(150,150,150,0.8); "
            "font-size: 14px; background: transparent; }"
        )
        layout.addWidget(self.preview)

        self.lblFile = CaptionLabel("")
        layout.addWidget(self.lblFile)

        btnRow = QHBoxLayout()
        self.btnRefresh = PushButton("刷新预览")
        self.btnExport = PrimaryPushButton("选择位置并保存")
        btnRow.addWidget(self.btnRefresh)
        btnRow.addWidget(self.btnExport)
        btnRow.addStretch()
        layout.addLayout(btnRow)
        layout.addStretch()

        self._previewPixmap = None
        self._sourcePath = ""

        self.btnRefresh.clicked.connect(self._refreshPreview)
        self.btnExport.clicked.connect(self._doExport)

    def setSource(self, path, pixmap):
        self._sourcePath = path
        self._previewPixmap = pixmap
        self._refreshPreview()

    def _refreshPreview(self):
        if self._previewPixmap and not self._previewPixmap.isNull():
            scaled = self._previewPixmap.scaled(
                self.preview.width() - 20, self.preview.height() - 20,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview.setPixmap(scaled)
            self.lblFile.setText(os.path.basename(self._sourcePath))
        else:
            self.preview.setText("请先选择一张图片")
            self.lblFile.setText("")

    def _doExport(self):
        if not self._sourcePath or not self._previewPixmap:
            InfoBar.warning("无图片", "请先选择图片")
            return
        name = os.path.basename(self._sourcePath)
        dest, _ = QFileDialog.getSaveFileName(
            self, "保存图片",
            os.path.join(os.path.expanduser("~"), "Desktop", name),
            "图片文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*)"
        )
        if dest:
            if self._previewPixmap.save(dest):
                InfoBar.success("导出成功",
                                f"已保存到: {dest}",
                                position=InfoBarPosition.TOP)
            else:
                InfoBar.error("导出失败", "无法保存图片",
                              position=InfoBarPosition.TOP)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refreshPreview()


# ═══════════════════════════════════════════════════════════════════════
#  Settings Page ("设置")
# ═══════════════════════════════════════════════════════════════════════

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel("设置"))

        # ── Theme card ─────────────────────────────────────────────────
        self.themeCard = SwitchSettingCard(
            FluentIcon.BRIGHTNESS,
            "深色模式",
            "切换浅色/深色主题"
        )
        self.themeCard.setChecked(isDarkTheme())
        self.themeCard.checkedChanged.connect(self._onThemeChanged)

        group = SettingCardGroup("外观")
        group.addSettingCard(self.themeCard)
        layout.addWidget(group)

        layout.addStretch()

    def _onThemeChanged(self, checked):
        setTheme(Theme.DARK if checked else Theme.LIGHT)


# ═══════════════════════════════════════════════════════════════════════
#  About Page ("关于")
# ═══════════════════════════════════════════════════════════════════════

class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutPage")
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(TitleLabel("关于"))
        layout.addWidget(BodyLabel("Fluent Photo Viewer — 基于 PyQt5 + PyQt-Fluent-Widgets"))

        layout.addSpacing(10)
        layout.addWidget(SubtitleLabel("作者"))

        authors = [
            ("SYSTEM-WINOS-RE", ""),
            ("4795_Tester", ""),
            ("Xiaomi MiMo AI", ""),
        ]
        for name, url in authors:
            if url:
                label = HyperlinkLabel(url, name)
            else:
                label = BodyLabel(name)
                label.setStyleSheet("font-size: 14px;")
            layout.addWidget(label)

        layout.addStretch()


# ═══════════════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════════════

class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("照片查看器")
        self.resize(1280, 720)
        self.setMinimumSize(960, 640)

        # center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        self.galleryPage = GalleryPage()
        self.exportPage = ExportPage()
        self.settingsPage = SettingsPage()
        self.aboutPage = AboutPage()

        self.addSubInterface(self.galleryPage, FluentIcon.PHOTO, "图片浏览",
                             position=NavigationItemPosition.TOP)
        self.addSubInterface(self.exportPage, FluentIcon.SAVE, "导出",
                             position=NavigationItemPosition.TOP)

        self.navigationInterface.addSeparator(NavigationItemPosition.BOTTOM)

        self.addSubInterface(self.settingsPage, FluentIcon.SETTING, "设置",
                             position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.aboutPage, FluentIcon.INFO, "关于",
                             position=NavigationItemPosition.BOTTOM)

        gp = self.galleryPage
        gp.btnOpen.clicked.connect(self._openFiles)
        gp.btnOpenFolder.clicked.connect(self._openFolder)
        gp.btnClear.clicked.connect(self._clearGallery)
        gp.btnFill.clicked.connect(self._fillGallery)
        gp.btnRotate.clicked.connect(lambda: gp.viewer.rotateCW())
        gp.btnZoomIn.clicked.connect(lambda: gp.viewer.zoomIn())
        gp.btnZoomOut.clicked.connect(lambda: gp.viewer.zoomOut())
        gp.btnFit.clicked.connect(lambda: gp.viewer.fitToWindow())
        gp.btnFull.clicked.connect(self._toggleFull)
        gp._fullCallback = self._toggleFull

        gp.viewer.zoomChanged.connect(self._syncExport)

    def openFiles(self, paths):
        self.galleryPage.addFiles(paths)
        if paths:
            self.switchTo(self.galleryPage)

    def _openFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif);;所有文件 (*)"
        )
        if files:
            self.galleryPage.addFiles(files)

    def _openFolder(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if d:
            self.galleryPage.loadFolder(d)

    def _clearGallery(self):
        self.galleryPage.clearGallery()
        InfoBar.success("已清空", "已清空所有图片")

    def _fillGallery(self):
        self.galleryPage.fillGallery()

    def _toggleFull(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _syncExport(self):
        path, pix = self.galleryPage.getCurrentImage()
        if path:
            self.exportPage.setSource(path, pix)

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
