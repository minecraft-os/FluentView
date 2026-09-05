# -*- coding: utf-8 -*-
"""
Fluent Photo Viewer — PyQt5 + PyQt-Fluent-Widgets
Supports: python photo_viewer.py image.jpg
Multi-language: lang/zh_CN, lang/en_US
"""

import os
import sys
import warnings
import io
import json
import configparser
import subprocess
warnings.filterwarnings("ignore", category=DeprecationWarning)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QRect, QPoint, QSize,
                           QBuffer, QIODevice, QPropertyAnimation,
                           QEasingCurve, pyqtProperty, QTimer, QUrl)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QTransform, QImage, QDesktopServices
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QFileDialog, QScrollArea, QFrame, QLabel,
    QGridLayout, QComboBox as _QComboBox
)
from PIL import Image
import requests
from bs4 import BeautifulSoup
from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition,
    PrimaryPushButton, PushButton, TransparentToolButton,
    CaptionLabel, TitleLabel, BodyLabel,
    InfoBar, InfoBarPosition, isDarkTheme,
    setTheme, Theme, HyperlinkLabel, SubtitleLabel,
    SwitchSettingCard, SettingCardGroup, StrongBodyLabel
)

try:
    from qfluentwidgets import ComboBox
except ImportError:
    ComboBox = _QComboBox

IMAGE_EXTS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.ico',
    '.webp', '.heic', '.heif', '.avif',
    '.tiff', '.tif', '.svg',
    '.raw', '.cr2', '.nef', '.arw', '.dng',
    '.orf', '.rw2', '.pef', '.srw', '.raf',
    '.mrw', '.mdc', '.dcr', '.erf', '.mef',
}
THUMB_SIZE = 150

ALL_FORMATS = " ".join(f"*{e}" for e in sorted(IMAGE_EXTS))

# ═══════════════════════════════════════════════════════════════════════
#  Config persistence
# ═══════════════════════════════════════════════════════════════════════

CONFIG_DIR  = os.path.join(os.environ.get('APPDATA', '.'), 'FluentView')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
IMAGES_FILE = os.path.join(CONFIG_DIR, 'images.json')

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
LANG_DIR = os.path.join(BASE_DIR, 'lang')


def _load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_image_paths():
    try:
        with open(IMAGES_FILE, 'r', encoding='utf-8') as f:
            paths = json.load(f)
    except Exception:
        return []
    valid = [p for p in paths if os.path.isfile(p)]
    valid.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    if len(valid) != len(paths):
        _save_image_paths(valid)
    return valid


def _save_image_paths(paths):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(IMAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(paths, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════════
#  内嵌语言模板
# ═══════════════════════════════════════════════════════════════════════

_ZH_TEMPLATE = """\
[lang]
code = zh_CN
name = 简体中文

[app]
title = 照片查看器

[navigation]
gallery = 图片浏览
wallpaper = 壁纸库
export_nav = 导出
settings = 设置
about = 关于

[gallery]
btn_add_files = 添加文件
btn_add_folder = 添加文件夹
btn_clear = 清空
btn_rotate = 旋转
btn_zoom_in = 放大
btn_zoom_out = 缩小
btn_fit_screen = 适配屏幕
count = 共 {n} 张图片
tooltip_back = 返回缩略图
tooltip_prev = 上一张 (←)
tooltip_next = 下一张 (→)
tooltip_fullscreen = 全屏 (F)
zoom_default = 100%%
select_image_hint = 选择一张图片以查看
empty_folder = 空文件夹
no_images_found = 未找到图片
photo_info = {w} x {h} px  |  {size}
cleared_title = 已清空
cleared_msg = 已清空所有图片

[wallpaper]
title = 壁纸库
desc = 高品质设计师壁纸，让您的设备格调优雅
source_label = 来源: {url}
btn_open = 打开壁纸库
opening = 正在打开壁纸库...
window_title = 壁纸库 — zhutix.com
install_hint = 提示: 安装 pywebview 可获得内置浏览器体验 (pip install pywebview)
opened_in_browser = 已在默认浏览器中打开
btn_refresh = 刷新
load_failed = 加载失败
load_failed_msg = 无法连接到壁纸网站，请检查网络连接
btn_load_more = 加载更多
loading_page = 正在加载第 {page} 页…
loaded_count = 共 {n} 张壁纸 · {info}
load_page = 第 {page} 页
load_all = 已加载全部
error_prefix = 加载失败: {msg}
getting_original = 正在获取原图…
downloading = 正在下载原图…
save_success = 保存成功
save_success_msg = 已保存到: {path}
save_failed = 保存失败
save_failed_msg = 下载图片出错
add_success = 已添加
add_success_msg = 已添加到图片库
get_failed = 获取失败
get_failed_msg = 无法获取原图地址
save_dialog = 保存壁纸
tooltip_browser = 在浏览器打开
tooltip_save_as = 另存为
tooltip_add_gallery = 添加到图片库
download_complete = 保存完成
download_failed = 下载失败
status_added = 已添加到图片库

[export]
title = 导出图片
desc = 在"图片浏览"中选择一张图片，然后在此保存到其他位置
no_image_hint = 请先选择一张图片
btn_refresh = 刷新预览
btn_save = 选择位置并保存
no_image_title = 无图片
no_image_msg = 请先选择图片
save_dialog = 保存图片
success_title = 导出成功
success_msg = 已保存到: {dest}
error_title = 导出失败
error_msg = 无法保存图片

[settings]
title = 设置
appearance = 外观
dark_mode = 深色模式
dark_mode_desc = 切换浅色/深色主题
language = 语言
language_desc = 切换界面语言（切换后将重启应用）
language_card_title = 界面语言

[about]
title = 关于
description = Fluent Photo Viewer — 基于 PyQt5 + PyQt-Fluent-Widgets
author_title = 作者
github_link = 从 Github 查看源码

[file_dialog]
select_images = 选择图片文件
select_folder = 选择图片文件夹
image_filter = 图片文件 ({formats});;所有文件 (*)
image_filter_export = 图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.ico *.webp *.heic *.heif *.avif *.tiff *.tif *.svg *.raw *.cr2 *.nef *.arw *.dng);;所有文件 (*)

[format]
byte = B
kilobyte = KB
megabyte = MB
gigabyte = GB
terabyte = TB
"""

_EN_TEMPLATE = """\
[lang]
code = en_US
name = English

[app]
title = Photo Viewer

[navigation]
gallery = Gallery
wallpaper = Wallpapers
export_nav = Export
settings = Settings
about = About

[gallery]
btn_add_files = Add Files
btn_add_folder = Add Folder
btn_clear = Clear
btn_rotate = Rotate
btn_zoom_in = Zoom In
btn_zoom_out = Zoom Out
btn_fit_screen = Fit Screen
count = {n} images
tooltip_back = Back to Thumbnails
tooltip_prev = Previous (←)
tooltip_next = Next (→)
tooltip_fullscreen = Fullscreen (F)
zoom_default = 100%%
select_image_hint = Select an image to view
empty_folder = Empty Folder
no_images_found = No images found
photo_info = {w} x {h} px  |  {size}
cleared_title = Cleared
cleared_msg = All images have been cleared

[wallpaper]
title = Wallpapers
desc = High-quality designer wallpapers to make your device elegant
source_label = Source: {url}
btn_open = Open Wallpapers
opening = Opening wallpapers...
window_title = Wallpapers — zhutix.com
install_hint = Tip: Install pywebview for built-in browser (pip install pywebview)
opened_in_browser = Opened in default browser
load_failed = Load Failed
load_failed_msg = Cannot connect to wallpaper site. Check your network.
btn_refresh = Refresh
btn_load_more = Load More
loading_page = Loading page {page}…
loaded_count = {n} wallpapers · {info}
load_page = Page {page}
load_all = All loaded
error_prefix = Load failed: {msg}
getting_original = Fetching original image…
downloading = Downloading…
save_success = Saved
save_success_msg = Saved to: {path}
save_failed = Save Failed
save_failed_msg = Download error
add_success = Added
add_success_msg = Added to gallery
get_failed = Failed
get_failed_msg = Cannot get original image URL
save_dialog = Save Wallpaper
tooltip_browser = Open in Browser
tooltip_save_as = Save As
tooltip_add_gallery = Add to Gallery
download_complete = Download complete
download_failed = Download failed
status_added = Added to gallery

[export]
title = Export Image
desc = Select an image in Gallery, then save it to another location
no_image_hint = Please select an image first
btn_refresh = Refresh Preview
btn_save = Choose Location and Save
no_image_title = No Image
no_image_msg = Please select an image first
save_dialog = Save Image
success_title = Export Successful
success_msg = Saved to: {dest}
error_title = Export Failed
error_msg = Unable to save image

[settings]
title = Settings
appearance = Appearance
dark_mode = Dark Mode
dark_mode_desc = Switch between light and dark theme
language = Language
language_desc = Switch language (app will restart)
language_card_title = Interface Language

[about]
title = About
description = Fluent Photo Viewer — Built with PyQt5 + PyQt-Fluent-Widgets
author_title = Authors
github_link = View source on Github

[file_dialog]
select_images = Select Image Files
select_folder = Select Image Folder
image_filter = Image Files ({formats});;All Files (*)
image_filter_export = Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.ico *.webp *.heic *.heif *.avif *.tiff *.tif *.svg *.raw *.cr2 *.nef *.arw *.dng);;All Files (*)

[format]
byte = B
kilobyte = KB
megabyte = MB
gigabyte = GB
terabyte = TB
"""


# ═══════════════════════════════════════════════════════════════════════
#  Language Manager
# ═══════════════════════════════════════════════════════════════════════

class LanguageManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._translations = {}
            cls._instance._current_lang = "zh_CN"
        return cls._instance

    def init(self):
        self._ensureLangFiles()
        cfg = _load_config()
        saved = cfg.get('language', 'zh_CN')
        if self.load(saved):
            return
        if self.load("zh_CN"):
            return
        for lang in self.availableLangs():
            if self.load(lang):
                return

    def _ensureLangFiles(self):
        templates = {"zh_CN": _ZH_TEMPLATE, "en_US": _EN_TEMPLATE}
        for code, content in templates.items():
            lang_dir = os.path.join(LANG_DIR, code)
            ini_path = os.path.join(lang_dir, "settings.ini")
            if not os.path.isfile(ini_path):
                os.makedirs(lang_dir, exist_ok=True)
                with open(ini_path, "w", encoding="utf-8") as f:
                    f.write(content)

    def saveLang(self, lang_code):
        cfg = _load_config()
        cfg['language'] = lang_code
        _save_config(cfg)

    def load(self, lang_code):
        ini = os.path.join(LANG_DIR, lang_code, "settings.ini")
        if not os.path.isfile(ini):
            return False
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(ini, encoding="utf-8")
        self._translations = {}
        for section in cfg.sections():
            if section == "lang":
                continue
            for key, value in cfg.items(section):
                self._translations[f"{section}.{key}"] = value
        self._current_lang = lang_code
        return True

    def tr(self, key, **kwargs):
        text = self._translations.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass
        return text

    @property
    def current_lang(self):
        return self._current_lang

    def availableLangs(self):
        langs = []
        if os.path.isdir(LANG_DIR):
            for d in sorted(os.listdir(LANG_DIR)):
                ini = os.path.join(LANG_DIR, d, "settings.ini")
                if os.path.isdir(os.path.join(LANG_DIR, d)) and os.path.isfile(ini):
                    langs.append(d)
        return langs

    def langName(self, lang_code):
        ini = os.path.join(LANG_DIR, lang_code, "settings.ini")
        if os.path.isfile(ini):
            cfg = configparser.ConfigParser(interpolation=None)
            cfg.read(ini, encoding="utf-8")
            return cfg.get("lang", "name", fallback=lang_code)
        return lang_code


LM = LanguageManager()


def _restartApp():
    subprocess.Popen([sys.executable] + sys.argv)
    QApplication.instance().quit()


def _format_size(size_bytes):
    keys = ("format.byte", "format.kilobyte", "format.megabyte", "format.gigabyte")
    for k in keys:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {LM.tr(k)}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} {LM.tr('format.terabyte')}"


def IMAGE_FILTER_STR():
    return LM.tr("file_dialog.image_filter", formats=ALL_FORMATS)


# ═══════════════════════════════════════════════════════════════════════
#  load_pixmap
# ═══════════════════════════════════════════════════════════════════════

def load_pixmap(path, size=None):
    ext = os.path.splitext(path)[1].lower()

    if ext == '.svg':
        renderer = QSvgRenderer(path)
        if renderer.isValid():
            sz = renderer.defaultSize()
            if size:
                sz = sz.scaled(size, size, Qt.KeepAspectRatio)
            pm = QPixmap(sz)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            renderer.render(p)
            p.end()
            return pm
        return QPixmap()

    pm = QPixmap(path)
    if not pm.isNull():
        if ext == '.gif':
            pm = pm.copy(0, 0, pm.width(), pm.height())
        return pm

    try:
        img = Image.open(path)
        if img.mode == 'P':
            img = img.convert('RGBA')
        elif img.mode == 'CMYK':
            img = img.convert('RGB')
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        if size and img.width > size and img.height > size:
            img.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        fmt = 'PNG' if img.mode in ('RGBA', 'LA', 'PA') else 'JPEG'
        if fmt == 'JPEG' and img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(buf, format=fmt)
        buf.seek(0)
        qimg = QImage()
        qimg.loadFromData(buf.read())
        return QPixmap.fromImage(qimg)
    except Exception:
        return QPixmap()


# ═══════════════════════════════════════════════════════════════════════
#  ThumbCard
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
#  GIF Frame Loader
# ═══════════════════════════════════════════════════════════════════════

MAX_GIF_FRAMES = 200

class GifLoader(QThread):
    frameReady = pyqtSignal(int, object, int)
    allDone = pyqtSignal()

    def __init__(self, path, maxW, maxH):
        super().__init__()
        self.path = path
        self.maxW = maxW
        self.maxH = maxH
        self._stop = False

    def run(self):
        try:
            img = Image.open(self.path)
            n = min(getattr(img, 'n_frames', 1), MAX_GIF_FRAMES)
            for i in range(n):
                if self._stop:
                    break
                img.seek(i)
                frame = img.copy().convert('RGBA')
                fw, fh = frame.size
                if self.maxW > 0 and self.maxH > 0:
                    scale = min(self.maxW / fw, self.maxH / fh, 1.0)
                    if scale < 1:
                        frame = frame.resize(
                            (int(fw * scale), int(fh * scale)), Image.LANCZOS)
                buf = io.BytesIO()
                frame.save(buf, format='PNG')
                buf.seek(0)
                qimg = QImage()
                qimg.loadFromData(buf.read())
                pixmap = QPixmap.fromImage(qimg)
                duration = img.info.get('duration', 100)
                duration = max(duration, 20)
                self.frameReady.emit(i, pixmap, duration)
        except Exception:
            pass
        self.allDone.emit()

    def stop(self):
        self._stop = True


# ═══════════════════════════════════════════════════════════════════════
#  ImageViewer
# ═══════════════════════════════════════════════════════════════════════

class ImageViewer(QWidget):
    zoomChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._orig = None
        self._path = ""
        self._zoom = 1.0
        self._targetZoom = 1.0
        self._rot = 0
        self._off = QPoint(0, 0)
        self._drag = False
        self._dragStart = QPoint()
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.ArrowCursor)

        self._zoomAni = QPropertyAnimation(self, b"zoomLevel", self)
        self._zoomAni.setDuration(200)
        self._zoomAni.setEasingCurve(QEasingCurve.OutCubic)

        self._gifFrames = []
        self._gifDurations = []
        self._gifIndex = 0
        self._gifLoading = False
        self._gifTimer = QTimer(self)
        self._gifTimer.timeout.connect(self._nextGifFrame)

    def loadImage(self, path):
        self._stopGif()
        pm = load_pixmap(path)
        if pm.isNull():
            return
        self._path = path
        self._rot = 0
        if path.lower().endswith('.gif'):
            self._loadGifFrames(path)
        if self._gifFrames:
            self._orig = self._gifFrames[0]
        else:
            self._orig = pm
        self.fitToWindow()

    def _getZoomLevel(self):
        return self._zoom

    def _setZoomLevel(self, val):
        self._zoom = val
        self.zoomChanged.emit(int(self._zoom * 100))
        self.update()

    zoomLevel = pyqtProperty(float, _getZoomLevel, _setZoomLevel)

    def zoomIn(self):
        self._targetZoom = min(self._targetZoom * 1.25, 10.0)
        self._animateZoom()

    def zoomOut(self):
        self._targetZoom = max(self._targetZoom / 1.25, 0.05)
        self._animateZoom()

    def _animateZoom(self):
        self._zoomAni.stop()
        self._zoomAni.setStartValue(self._zoom)
        self._zoomAni.setEndValue(self._targetZoom)
        self._zoomAni.start()

    def fitToWindow(self):
        if not self._orig:
            return
        vw, vh = self.width(), self.height()
        iw, ih = self._orig.width(), self._orig.height()
        if iw == 0 or ih == 0:
            return
        self._zoom = min(vw / iw, vh / ih) * 0.96
        self._targetZoom = self._zoom
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

    def _loadGifFrames(self, path):
        self._stopGif()
        self._gifLoading = True
        self._gifLoader = GifLoader(path, self.width(), self.height())
        self._gifLoader.frameReady.connect(self._onGifFrame)
        self._gifLoader.allDone.connect(self._onGifDone)
        self._gifLoader.start()

    def _onGifFrame(self, index, pixmap, duration):
        if index == 0:
            self._orig = pixmap
            self.fitToWindow()
            self.update()
        self._gifFrames.append(pixmap)
        self._gifDurations.append(duration)
        if len(self._gifFrames) == 1 and not self._gifTimer.isActive():
            self._gifIndex = 0
            self._gifTimer.start(self._gifDurations[0])

    def _onGifDone(self):
        self._gifLoading = False

    def _nextGifFrame(self):
        if not self._gifFrames:
            return
        self._gifIndex = (self._gifIndex + 1) % len(self._gifFrames)
        self._orig = self._gifFrames[self._gifIndex]
        self.update()
        self._gifTimer.setInterval(self._gifDurations[self._gifIndex])

    def _stopGif(self):
        self._gifTimer.stop()
        if hasattr(self, '_gifLoader') and self._gifLoader.isRunning():
            self._gifLoader.stop()
            self._gifLoader.wait(1000)
        self._gifFrames.clear()
        self._gifDurations.clear()
        self._gifIndex = 0
        self._gifLoading = False

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
            p.drawText(self.rect(), Qt.AlignCenter, LM.tr("gallery.select_image_hint"))
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
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag:
            self._off += e.pos() - self._dragStart
            self._dragStart = e.pos()
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = False
        self.setCursor(Qt.ArrowCursor)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._orig:
            self.fitToWindow()


# ═══════════════════════════════════════════════════════════════════════
#  ThumbLoader
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
            pm = load_pixmap(p, THUMB_SIZE)
            if not pm.isNull():
                pm = pm.scaled(THUMB_SIZE, THUMB_SIZE,
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.loaded.emit(p, pm)

    def stop(self):
        self._stop = True


# ═══════════════════════════════════════════════════════════════════════
#  GalleryPage
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

        self.btnOpen       = PrimaryPushButton(LM.tr("gallery.btn_add_files"))
        self.btnOpenFolder = PushButton(LM.tr("gallery.btn_add_folder"))
        self.btnClear      = PushButton(LM.tr("gallery.btn_clear"))
        self.btnRotate     = PushButton(LM.tr("gallery.btn_rotate"))
        self.btnZoomIn     = PushButton(LM.tr("gallery.btn_zoom_in"))
        self.btnZoomOut    = PushButton(LM.tr("gallery.btn_zoom_out"))
        self.btnFit        = PushButton(LM.tr("gallery.btn_fit_screen"))

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(14, 10, 14, 6)
        toolbar.setSpacing(8)
        for b in (self.btnOpen, self.btnOpenFolder, self.btnClear,
                  self.btnRotate, self.btnZoomIn, self.btnZoomOut, self.btnFit):
            toolbar.addWidget(b)
        toolbar.addStretch()
        self.lblCount = CaptionLabel(LM.tr("gallery.count", n=0))
        toolbar.addWidget(self.lblCount)

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

        self.viewer = ImageViewer()

        self.btnBack = TransparentToolButton(FluentIcon.RETURN)
        self.btnBack.setToolTip(LM.tr("gallery.tooltip_back"))
        self.btnPrev = TransparentToolButton(FluentIcon.LEFT_ARROW)
        self.btnPrev.setToolTip(LM.tr("gallery.tooltip_prev"))
        self.btnNext = TransparentToolButton(FluentIcon.CHEVRON_RIGHT)
        self.btnNext.setToolTip(LM.tr("gallery.tooltip_next"))
        self.btnFull = TransparentToolButton(FluentIcon.FULL_SCREEN)
        self.btnFull.setToolTip(LM.tr("gallery.tooltip_fullscreen"))

        self.lblZoom = CaptionLabel(LM.tr("gallery.zoom_default"))
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
        self.viewer.zoomChanged.connect(lambda v: self.lblZoom.setText(f"{v}%"))

    def addFiles(self, paths):
        added = 0
        for p in paths:
            if os.path.isfile(p) and os.path.splitext(p)[1].lower() in IMAGE_EXTS:
                if p not in self._paths:
                    self._paths.append(p)
                    added += 1
        self._paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        self._rebuildGrid()
        self.lblCount.setText(LM.tr("gallery.count", n=len(self._paths)))
        if added:
            self._loadThumbs()
            _save_image_paths(self._paths)

    def loadFolder(self, folder):
        self._stopLoader()
        self._clearGrid()
        self._paths = []
        self._current = ""
        self.stack.setCurrentIndex(0)
        self._paths = sorted(
            (os.path.join(folder, f) for f in os.listdir(folder)
             if os.path.splitext(f)[1].lower() in IMAGE_EXTS),
            key=lambda p: os.path.getmtime(p), reverse=True)
        self.lblCount.setText(LM.tr("gallery.count", n=len(self._paths)))
        if not self._paths:
            InfoBar.warning(LM.tr("gallery.empty_folder"),
                            LM.tr("gallery.no_images_found"))
            return
        self._rebuildGrid()
        self._loadThumbs()
        _save_image_paths(self._paths)

    def clearGallery(self):
        self._stopLoader()
        self._paths.clear()
        self._current = ""
        self._clearGrid()
        self.viewer._orig = None
        self.viewer.update()
        self.stack.setCurrentIndex(0)
        self.lblCount.setText(LM.tr("gallery.count", n=0))
        _save_image_paths([])

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
        avail = self.gridWidget.width() - 28
        cardW = THUMB_SIZE + 20
        colCount = max(1, avail // cardW)
        for i, path in enumerate(self._paths):
            pm = load_pixmap(path, THUMB_SIZE)
            if pm.isNull():
                continue
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
        self.lblInfo.setText(os.path.basename(path))
        if self.viewer._orig:
            w, h = self.viewer._orig.width(), self.viewer._orig.height()
            fsize = os.path.getsize(path) if os.path.isfile(path) else 0
            self.lblPhotoInfo.setText(
                LM.tr("gallery.photo_info", w=w, h=h, size=_format_size(fsize)))
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
#  ExportPage
# ═══════════════════════════════════════════════════════════════════════

class ExportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("exportPage")
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(TitleLabel(LM.tr("export.title")))
        layout.addWidget(BodyLabel(LM.tr("export.desc")))

        self.preview = QLabel(LM.tr("export.no_image_hint"))
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(300)
        self.preview.setFrameShape(QFrame.StyledPanel)
        self.preview.setStyleSheet(
            "QLabel { border: 2px dashed rgba(150,150,150,0.5); "
            "border-radius: 8px; color: rgba(150,150,150,0.8); "
            "font-size: 14px; background: transparent; }")
        layout.addWidget(self.preview)

        self.lblFile = CaptionLabel("")
        layout.addWidget(self.lblFile)

        btnRow = QHBoxLayout()
        self.btnRefresh = PushButton(LM.tr("export.btn_refresh"))
        self.btnExport  = PrimaryPushButton(LM.tr("export.btn_save"))
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
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview.setPixmap(scaled)
            self.lblFile.setText(os.path.basename(self._sourcePath))
        else:
            self.preview.setText(LM.tr("export.no_image_hint"))
            self.lblFile.setText("")

    def _doExport(self):
        if not self._sourcePath or not self._previewPixmap:
            InfoBar.warning(LM.tr("export.no_image_title"),
                            LM.tr("export.no_image_msg"))
            return
        name = os.path.basename(self._sourcePath)
        dest, _ = QFileDialog.getSaveFileName(
            self, LM.tr("export.save_dialog"),
            os.path.join(os.path.expanduser("~"), "Desktop", name),
            LM.tr("file_dialog.image_filter_export"))
        if dest:
            if self._previewPixmap.save(dest):
                InfoBar.success(LM.tr("export.success_title"),
                                LM.tr("export.success_msg", dest=dest),
                                position=InfoBarPosition.TOP)
            else:
                InfoBar.error(LM.tr("export.error_title"),
                              LM.tr("export.error_msg"),
                              position=InfoBarPosition.TOP)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refreshPreview()


# ═══════════════════════════════════════════════════════════════════════
#  SettingsPage
# ═══════════════════════════════════════════════════════════════════════

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel(LM.tr("settings.title")))

        # ── 外观卡片组 ──
        self.themeCard = SwitchSettingCard(
            FluentIcon.BRIGHTNESS,
            LM.tr("settings.dark_mode"),
            LM.tr("settings.dark_mode_desc"))
        cfg = _load_config()
        saved_dark = cfg.get('dark_mode', isDarkTheme())
        self.themeCard.setChecked(saved_dark)
        setTheme(Theme.DARK if saved_dark else Theme.LIGHT)
        self.themeCard.checkedChanged.connect(self._onThemeChanged)

        group1 = SettingCardGroup(LM.tr("settings.appearance"))
        group1.addSettingCard(self.themeCard)
        layout.addWidget(group1)

        # ── 语言卡片组（板块形状） ──
        lang_items = [(LM.langName(l), l) for l in LM.availableLangs()]

        langCardWidget = QWidget()
        langCardWidget.setFixedHeight(70)
        langCardWidget.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
            }
        """)
        lcLayout = QHBoxLayout(langCardWidget)
        lcLayout.setContentsMargins(18, 10, 18, 10)
        lcLayout.setSpacing(16)

        # 左侧图标
        iconLabel = QLabel("🌐")
        iconLabel.setFixedSize(32, 32)
        iconLabel.setAlignment(Qt.AlignCenter)
        iconLabel.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        lcLayout.addWidget(iconLabel)

        # 中间文字区
        textWrap = QWidget()
        textWrap.setStyleSheet("background: transparent; border: none;")
        twLayout = QVBoxLayout(textWrap)
        twLayout.setContentsMargins(0, 0, 0, 0)
        twLayout.setSpacing(2)

        lblTitle = StrongBodyLabel(LM.tr("settings.language_card_title"))
        lblTitle.setStyleSheet("background: transparent; border: none; font-weight: bold;")
        lblDesc = CaptionLabel(LM.tr("settings.language_desc"))
        lblDesc.setStyleSheet("background: transparent; border: none;")
        twLayout.addWidget(lblTitle)
        twLayout.addWidget(lblDesc)
        lcLayout.addWidget(textWrap, 1)

        # 右侧 ComboBox
        self.langCombo = ComboBox()
        for text, data in lang_items:
            self.langCombo.addItem(text, userData=data)
        idx = self.langCombo.findData(LM.current_lang)
        if idx >= 0:
            self.langCombo.setCurrentIndex(idx)
        self.langCombo.setFixedWidth(160)
        self.langCombo.currentIndexChanged.connect(self._onLanguageChanged)
        lcLayout.addWidget(self.langCombo)

        group2 = SettingCardGroup(LM.tr("settings.language"))
        group2.addSettingCard(langCardWidget)
        layout.addWidget(group2)

        layout.addStretch()

    def _onThemeChanged(self, checked):
        setTheme(Theme.DARK if checked else Theme.LIGHT)
        cfg = _load_config()
        cfg['dark_mode'] = checked
        _save_config(cfg)

    def _onLanguageChanged(self, index):
        lang_code = self.langCombo.currentData()
        if lang_code and lang_code != LM.current_lang:
            LM.saveLang(lang_code)
            _restartApp()


# ═══════════════════════════════════════════════════════════════════════
#  AboutPage
# ═══════════════════════════════════════════════════════════════════════

class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutPage")
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(TitleLabel(LM.tr("about.title")))
        layout.addWidget(BodyLabel(LM.tr("about.description")))

        layout.addSpacing(10)
        layout.addWidget(SubtitleLabel(LM.tr("about.author_title")))

        for name, url in [("SYSTEM-WINOS-RE", ""), ("4795_Tester", ""),
                          ("Xiaomi MiMo AI", "")]:
            if url:
                label = HyperlinkLabel(url, name)
            else:
                label = BodyLabel(name)
                label.setStyleSheet("font-size: 14px;")
            layout.addWidget(label)

        layout.addSpacing(10)
        githubBtn = PushButton(LM.tr("about.github_link"))
        githubBtn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/minecraft-os/FluentView")))
        layout.addWidget(githubBtn)
        layout.addStretch()


# ═══════════════════════════════════════════════════════════════════════
#  Wallpaper Loader (background thread)
# ═══════════════════════════════════════════════════════════════════════

WALLPAPER_BASE = "https://zhutix.com/wallpaper/"
WALLPAPER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class WallpaperLoader(QThread):
    itemLoaded = pyqtSignal(str, str, str, object)
    loadDone = pyqtSignal(bool)
    loadError = pyqtSignal(str)

    def __init__(self, page=1):
        super().__init__()
        self.page = page
        self._stop = False

    def run(self):
        try:
            url = WALLPAPER_BASE if self.page == 1 else f"{WALLPAPER_BASE}page/{self.page}/"
            r = requests.get(url, headers=WALLPAPER_HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.select('li.post-list-item')

            for item in items:
                if self._stop:
                    return
                img = item.select_one('img.post-thumb')
                link_el = item.select_one('a.thumb-link')
                title_el = item.select_one('.ycfm .imglist-char')
                if not img or not link_el:
                    continue
                thumb_url = img.get('src') or img.get('data-src', '')
                if not thumb_url:
                    continue
                detail_url = link_el.get('href', '')
                title = title_el.get_text(strip=True) if title_el else ''

                try:
                    tr = requests.get(thumb_url, headers=WALLPAPER_HEADERS, timeout=10)
                    qimg = QImage()
                    qimg.loadFromData(tr.content)
                    pixmap = QPixmap.fromImage(qimg)
                except Exception:
                    pixmap = QPixmap()

                self.itemLoaded.emit(title, detail_url, thumb_url, pixmap)

            next_link = soup.select_one('a.next.page-numbers')
            self.loadDone.emit(next_link is not None)
        except Exception as e:
            self.loadError.emit(str(e))

    def stop(self):
        self._stop = True


class _DownloadWorker(QThread):
    finished = pyqtSignal(bool)

    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            r = requests.get(self.url, headers=WALLPAPER_HEADERS,
                             timeout=30, stream=True)
            r.raise_for_status()
            with open(self.dest, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            self.finished.emit(True)
        except Exception:
            self.finished.emit(False)


class _DetailPageWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, detail_url):
        super().__init__()
        self.detail_url = detail_url

    def run(self):
        try:
            r = requests.get(self.detail_url, headers=WALLPAPER_HEADERS, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            urls = []
            for img in soup.select('img'):
                src = img.get('src', '')
                if 'b.zhutix.com' in src:
                    clean = src.split('?')[0]
                    if clean not in urls:
                        urls.append(clean)
            self.done.emit(urls)
        except Exception:
            self.done.emit([])


# ═══════════════════════════════════════════════════════════════════════
#  WallpaperCard
# ═══════════════════════════════════════════════════════════════════════

class WallpaperCard(QWidget):
    clicked = pyqtSignal(str, str, str)
    actionOpen = pyqtSignal(str)
    actionSave = pyqtSignal(str, str)
    actionAddToGallery = pyqtSignal(str, str)

    def __init__(self, title, thumb_url, pixmap, parent=None):
        super().__init__(parent)
        self._title = title
        self._detailUrl = ""
        self._thumbUrl = thumb_url
        self._pixmap = pixmap
        self._hover = False
        self.setFixedSize(THUMB_SIZE + 20, THUMB_SIZE + 80)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(title)

        self._btnBar = QWidget(self)
        self._btnBar.setFixedHeight(24)
        self._btnBar.setVisible(False)
        self._btnBar.move(0, THUMB_SIZE + 50)

        bl = QHBoxLayout(self._btnBar)
        bl.setContentsMargins(4, 0, 4, 0)
        bl.setSpacing(2)

        self._btnBrowser = TransparentToolButton(FluentIcon.GLOBE)
        self._btnBrowser.setFixedSize(24, 24)
        self._btnBrowser.setToolTip(LM.tr("wallpaper.tooltip_browser"))
        self._btnSave = TransparentToolButton(FluentIcon.SAVE)
        self._btnSave.setFixedSize(24, 24)
        self._btnSave.setToolTip(LM.tr("wallpaper.tooltip_save_as"))
        self._btnAdd = TransparentToolButton(FluentIcon.ADD)
        self._btnAdd.setFixedSize(24, 24)
        self._btnAdd.setToolTip(LM.tr("wallpaper.tooltip_add_gallery"))

        bl.addWidget(self._btnBrowser)
        bl.addWidget(self._btnSave)
        bl.addWidget(self._btnAdd)

        self._btnBrowser.clicked.connect(lambda: self.actionOpen.emit(self._detailUrl))
        self._btnSave.clicked.connect(lambda: self.actionSave.emit(self._title, self._detailUrl))
        self._btnAdd.clicked.connect(lambda: self.actionAddToGallery.emit(self._title, self._detailUrl))

    def setDetailUrl(self, url):
        self._detailUrl = url

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self._hover:
            p.setBrush(QColor(0, 0, 0, 18))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, w, h, 8, 8)
        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ix = (w - scaled.width()) // 2
            p.drawPixmap(ix, 2, scaled)
        name = self._title
        if len(name) > 22:
            name = name[:19] + "..."
        fg = QColor(60, 60, 60) if not isDarkTheme() else QColor(200, 200, 200)
        p.setPen(fg)
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(QRect(0, THUMB_SIZE + 4, w, 20),
                   Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, name)
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self._btnBar.setVisible(True)
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self._btnBar.setVisible(False)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._title, self._detailUrl, self._thumbUrl)


# ═══════════════════════════════════════════════════════════════════════
#  WallpaperPage
# ═══════════════════════════════════════════════════════════════════════

class WallpaperPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("wallpaperPage")
        self.setStyleSheet("background: transparent;")

        self._page = 1
        self._hasMore = True
        self._loading = False
        self._loader = None
        self._wallpapers = []

        self.btnRefresh = PushButton(LM.tr("wallpaper.btn_refresh"))
        self.btnLoadMore = PushButton(LM.tr("wallpaper.btn_load_more"))
        self.lblStatus = CaptionLabel(LM.tr("wallpaper.source_label", url="zhutix.com"))

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(14, 10, 14, 6)
        toolbar.setSpacing(8)
        toolbar.addWidget(self.btnRefresh)
        toolbar.addWidget(self.btnLoadMore)
        toolbar.addStretch()
        toolbar.addWidget(self.lblStatus)

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(toolbar)
        layout.addWidget(gridScroll)

        self.btnRefresh.clicked.connect(self._refresh)
        self.btnLoadMore.clicked.connect(self._loadMore)
        QTimer.singleShot(100, self._refresh)

    def _refresh(self):
        self._clearGrid()
        self._page = 1
        self._hasMore = True
        self._wallpapers.clear()
        self._startLoad()

    def _loadMore(self):
        if self._hasMore and not self._loading:
            self._startLoad()

    def _startLoad(self):
        self._loading = True
        self.btnLoadMore.setEnabled(False)
        self.lblStatus.setText(LM.tr("wallpaper.loading_page", page=self._page))
        self._loader = WallpaperLoader(self._page)
        self._loader.itemLoaded.connect(self._onItem)
        self._loader.loadDone.connect(self._onDone)
        self._loader.loadError.connect(self._onError)
        self._loader.start()

    def _onItem(self, title, detail_url, thumb_url, pixmap):
        self._wallpapers.append((title, detail_url, thumb_url, pixmap))
        self._addCard(title, detail_url, thumb_url, pixmap)

    def _onDone(self, has_more):
        self._hasMore = has_more
        self._loading = False
        self.btnLoadMore.setEnabled(has_more)
        n = len(self._wallpapers)
        info = LM.tr("wallpaper.load_page", page=self._page) if has_more else LM.tr("wallpaper.load_all")
        self.lblStatus.setText(LM.tr("wallpaper.loaded_count", n=n, info=info))
        if has_more:
            self._page += 1

    def _onError(self, msg):
        self._loading = False
        self.btnLoadMore.setEnabled(True)
        self.lblStatus.setText(LM.tr("wallpaper.error_prefix", msg=msg))

    def _addCard(self, title, detail_url, thumb_url, pixmap):
        avail = self.gridWidget.width() - 28
        cardW = THUMB_SIZE + 20
        colCount = max(1, avail // cardW)
        count = self.gridLayout.count()
        r, c = divmod(count, colCount)

        card = WallpaperCard(title, thumb_url, pixmap)
        card.setDetailUrl(detail_url)
        card.clicked.connect(self._onCardClicked)
        card.actionOpen.connect(self._openInBrowser)
        card.actionSave.connect(self._saveAs)
        card.actionAddToGallery.connect(self._addToGallery)
        self.gridLayout.addWidget(card, r, c)

    def _onCardClicked(self, title, detail_url, thumb_url):
        import webbrowser
        webbrowser.open(detail_url)

    def _openInBrowser(self, detail_url):
        import webbrowser
        webbrowser.open(detail_url)

    def _saveAs(self, title, detail_url):
        self.lblStatus.setText(LM.tr("wallpaper.getting_original"))
        self._detailWorker = _DetailPageWorker(detail_url)
        self._detailWorker.done.connect(lambda urls: self._doSaveAs(title, urls))
        self._detailWorker.start()

    def _doSaveAs(self, title, full_urls):
        if not full_urls:
            InfoBar.error(LM.tr("wallpaper.get_failed"),
                          LM.tr("wallpaper.get_failed_msg"),
                          position=InfoBarPosition.TOP)
            self.lblStatus.setText("")
            return
        url = full_urls[0]
        ext = os.path.splitext(url.split('?')[0])[1] or '.jpg'
        default_name = (title or "wallpaper").replace('/', '_').replace('\\', '_') + ext
        dest, _ = QFileDialog.getSaveFileName(
            self, LM.tr("wallpaper.save_dialog"),
            os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            f"图片文件 (*{ext});;所有文件 (*)")
        if not dest:
            self.lblStatus.setText("")
            return
        self.lblStatus.setText(LM.tr("wallpaper.downloading"))
        self._downloadThread = _DownloadWorker(url, dest)
        self._downloadThread.finished.connect(
            lambda ok, d=dest: self._onSaveDone(ok, d))
        self._downloadThread.start()

    def _onSaveDone(self, ok, path):
        if ok:
            InfoBar.success(LM.tr("wallpaper.save_success"),
                            LM.tr("wallpaper.save_success_msg", path=path),
                            position=InfoBarPosition.TOP)
            self.lblStatus.setText(LM.tr("wallpaper.download_complete"))
        else:
            InfoBar.error(LM.tr("wallpaper.save_failed"),
                          LM.tr("wallpaper.save_failed_msg"),
                          position=InfoBarPosition.TOP)
            self.lblStatus.setText(LM.tr("wallpaper.download_failed"))

    def _addToGallery(self, title, detail_url):
        self.lblStatus.setText(LM.tr("wallpaper.getting_original"))
        self._detailWorker2 = _DetailPageWorker(detail_url)
        self._detailWorker2.done.connect(lambda urls: self._doAddToGallery(title, urls))
        self._detailWorker2.start()

    def _doAddToGallery(self, title, full_urls):
        if not full_urls:
            InfoBar.error(LM.tr("wallpaper.get_failed"),
                          LM.tr("wallpaper.get_failed_msg"),
                          position=InfoBarPosition.TOP)
            self.lblStatus.setText("")
            return
        url = full_urls[0]
        save_dir = os.path.join(os.environ.get('APPDATA', '.'), 'FluentView', 'wallpapers')
        os.makedirs(save_dir, exist_ok=True)
        ext = os.path.splitext(url.split('?')[0])[1] or '.jpg'
        filename = (title or "wallpaper").replace('/', '_').replace('\\', '_') + ext
        dest = os.path.join(save_dir, filename)

        if os.path.exists(dest):
            self._addFileToGallery(dest)
            return

        self.lblStatus.setText(LM.tr("wallpaper.downloading"))
        self._downloadThread = _DownloadWorker(url, dest)
        self._downloadThread.finished.connect(
            lambda ok, d=dest: self._onAddDone(ok, d))
        self._downloadThread.start()

    def _onAddDone(self, ok, path):
        if ok:
            self._addFileToGallery(path)
        else:
            InfoBar.error(LM.tr("wallpaper.save_failed"),
                          LM.tr("wallpaper.save_failed_msg"),
                          position=InfoBarPosition.TOP)

    def _addFileToGallery(self, path):
        win = self.window()
        if hasattr(win, 'galleryPage'):
            win.galleryPage.addFiles([path])
            InfoBar.success(LM.tr("wallpaper.add_success"),
                            LM.tr("wallpaper.add_success_msg"),
                            position=InfoBarPosition.TOP)
            self.lblStatus.setText(LM.tr("wallpaper.status_added"))

    def _clearGrid(self):
        while self.gridLayout.count():
            item = self.gridLayout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._wallpapers:
            self._reflow()

    def _reflow(self):
        self._clearGrid()
        avail = self.gridWidget.width() - 28
        cardW = THUMB_SIZE + 20
        colCount = max(1, avail // cardW)
        for i, (title, detail_url, thumb_url, pixmap) in enumerate(self._wallpapers):
            card = WallpaperCard(title, thumb_url, pixmap)
            card.setDetailUrl(detail_url)
            card.clicked.connect(self._onCardClicked)
            card.actionOpen.connect(self._openInBrowser)
            card.actionSave.connect(self._saveAs)
            card.actionAddToGallery.connect(self._addToGallery)
            r, c = divmod(i, colCount)
            self.gridLayout.addWidget(card, r, c)


# ═══════════════════════════════════════════════════════════════════════
#  MainWindow
# ═══════════════════════════════════════════════════════════════════════

class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(LM.tr("app.title"))
        self.resize(1280, 720)
        self.setMinimumSize(960, 640)

        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        self.galleryPage   = GalleryPage()
        self.exportPage    = ExportPage()
        self.wallpaperPage = WallpaperPage()
        self.settingsPage  = SettingsPage()
        self.aboutPage     = AboutPage()

        self.addSubInterface(self.galleryPage, FluentIcon.PHOTO,
                             LM.tr("navigation.gallery"),
                             position=NavigationItemPosition.TOP)
        self.addSubInterface(self.wallpaperPage, FluentIcon.PALETTE,
                             LM.tr("navigation.wallpaper"),
                             position=NavigationItemPosition.TOP)
        self.addSubInterface(self.exportPage, FluentIcon.SAVE,
                             LM.tr("navigation.export_nav"),
                             position=NavigationItemPosition.TOP)

        self.navigationInterface.addSeparator(NavigationItemPosition.BOTTOM)

        self.addSubInterface(self.settingsPage, FluentIcon.SETTING,
                             LM.tr("navigation.settings"),
                             position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.aboutPage, FluentIcon.INFO,
                             LM.tr("navigation.about"),
                             position=NavigationItemPosition.BOTTOM)

        gp = self.galleryPage
        gp.btnOpen.clicked.connect(self._openFiles)
        gp.btnOpenFolder.clicked.connect(self._openFolder)
        gp.btnClear.clicked.connect(self._clearGallery)
        gp.btnRotate.clicked.connect(lambda: gp.viewer.rotateCW())
        gp.btnZoomIn.clicked.connect(lambda: gp.viewer.zoomIn())
        gp.btnZoomOut.clicked.connect(lambda: gp.viewer.zoomOut())
        gp.btnFit.clicked.connect(lambda: gp.viewer.fitToWindow())
        gp.btnFull.clicked.connect(self._toggleFull)
        gp._fullCallback = self._toggleFull
        gp.viewer.zoomChanged.connect(self._syncExport)

        saved = _load_image_paths()
        if saved:
            self.galleryPage.addFiles(saved)

    def openFiles(self, paths):
        self.galleryPage.addFiles(paths)
        if paths:
            self.switchTo(self.galleryPage)

    def _openFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, LM.tr("file_dialog.select_images"), "",
            IMAGE_FILTER_STR())
        if files:
            self.galleryPage.addFiles(files)

    def _openFolder(self):
        d = QFileDialog.getExistingDirectory(
            self, LM.tr("file_dialog.select_folder"))
        if d:
            self.galleryPage.loadFolder(d)

    def _clearGallery(self):
        self.galleryPage.clearGallery()
        _save_image_paths([])
        InfoBar.success(LM.tr("gallery.cleared_title"),
                        LM.tr("gallery.cleared_msg"))

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

    # 加载语言包
    LM.init()

    # 应用保存的主题
    cfg = _load_config()
    if cfg.get('dark_mode'):
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.LIGHT)

    window = MainWindow()
    imageArgs = [
        a for a in sys.argv[1:]
        if os.path.isfile(a) and os.path.splitext(a)[1].lower() in IMAGE_EXTS
    ]
    if imageArgs:
        window.openFiles(imageArgs)

    window.show()
    sys.exit(app.exec_())
