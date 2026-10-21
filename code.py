# -*- coding: utf-8 -*-
"""
Fluent Photo Viewer — PyQt5 + PyQt-Fluent-Widgets
Multi-language · File Association · First-run Wizard
rawpy · pillow-heif
"""

import os, sys, warnings, io, json, configparser, subprocess, platform, re, time
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QRect, QPoint,
                           QPropertyAnimation, QEasingCurve, pyqtProperty,
                           QTimer, QUrl, QSize)
from PyQt5.QtGui import (QPixmap, QPainter, QColor, QFont, QTransform, QImage,
                         QDesktopServices, QIcon, QPen, QFontDatabase)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
    QStackedWidget, QFileDialog, QScrollArea, QFrame, QLabel,
    QGridLayout, QCheckBox, QDialog, QComboBox as _QComboBox, QButtonGroup,
    QPushButton, QLineEdit)
from PIL import Image
import requests
from bs4 import BeautifulSoup
from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition,
    PrimaryPushButton, PushButton, TransparentToolButton,
    CaptionLabel, TitleLabel, BodyLabel,
    isDarkTheme, setTheme, Theme, HyperlinkLabel, SubtitleLabel,
    SwitchSettingCard, SettingCardGroup, StrongBodyLabel,
    InfoBar, InfoBarPosition, MessageBox)
try:
    from qfluentwidgets import ComboBox
except ImportError:
    ComboBox = _QComboBox

# ── 格式 ──
RAW_EXTS = {
    '.raw','.cr2','.cr3','.crw','.nef','.arw','.dng','.orf','.rw2',
    '.pef','.srw','.raf','.mrw','.mdc','.dcr','.erf','.mef','.3fr',
    '.ari','.bay','.cap','.iiq','.fff','.mos','.nrw','.ptx','.r3d',
    '.rwl','.x3f','.gpr',
}
HEIF_EXTS = {'.heic','.heif','.avif','.hif'}
IMAGE_EXTS = {
    '.jpg','.jpeg','.png','.bmp','.gif','.ico','.webp','.tiff','.tif','.svg',
    '.heic','.heif','.avif','.hif',
    *RAW_EXTS,
}
THUMB_SIZE = 150
ALL_FORMATS = " ".join(f"*{e}" for e in sorted(IMAGE_EXTS))

APP_VERSION = "1.6.0"
GITHUB_REPO_URL = "https://github.com/minecraft-os/FluentView"
GITHUB_RELEASES_URL = GITHUB_REPO_URL + "/releases"
GITHUB_API_RELEASES = "https://api.github.com/repos/minecraft-os/FluentView/releases"

FORMAT_DISPLAY = {
    '.jpg':'JPEG','.jpeg':'JPEG','.png':'PNG','.bmp':'BMP','.gif':'GIF',
    '.ico':'ICO','.webp':'WebP','.tiff':'TIFF','.tif':'TIFF','.svg':'SVG',
    '.heic':'HEIC','.heif':'HEIF','.avif':'AVIF','.hif':'HIF',
    '.raw':'RAW','.cr2':'Canon CR2','.cr3':'Canon CR3','.crw':'Canon CRW',
    '.nef':'Nikon NEF','.arw':'Sony ARW','.dng':'Adobe DNG',
    '.orf':'Olympus ORF','.rw2':'Panasonic RW2','.pef':'Pentax PEF',
    '.srw':'Samsung SRW','.raf':'Fuji RAF','.mrw':'Minolta MRW',
    '.erf':'Epson ERF','.mef':'Mamiya MEF','.3fr':'Hasselblad 3FR',
    '.ari':'ARRI ARI','.bay':'Casio BAY','.cap':'Phase One CAP',
    '.iiq':'Phase One IIQ','.fff':'Imacon FFF','.mos':'Leaf MOS',
    '.nrw':'Nikon NRW','.ptx':'Pentax PTX','.r3d':'RED R3D',
    '.rwl':'Leica RWL','.x3f':'Sigma X3F','.gpr':'GoPro GPR',
    '.dcr':'Kodak DCR','.mdc':'Minolta MDC',
}

CONFIG_DIR = os.path.join(os.environ.get('APPDATA','.'), 'FluentView')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
IMAGES_FILE = os.path.join(CONFIG_DIR, 'images.json')
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
LANG_DIR = os.path.join(BASE_DIR, 'lang')

def _load_config():
    try:
        with open(CONFIG_FILE,'r',encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def _save_config(data):
    os.makedirs(CONFIG_DIR,exist_ok=True)
    with open(CONFIG_FILE,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def _load_image_paths():
    try:
        with open(IMAGES_FILE,'r',encoding='utf-8') as f:
            paths=json.load(f)
    except:
        return []
    valid=[p for p in paths if os.path.isfile(p)]
    valid.sort(key=lambda p:os.path.getmtime(p),reverse=True)
    if len(valid)!=len(paths):
        _save_image_paths(valid)
    return valid

def _save_image_paths(paths):
    os.makedirs(CONFIG_DIR,exist_ok=True)
    with open(IMAGES_FILE,'w',encoding='utf-8') as f:
        json.dump(paths,f,ensure_ascii=False,indent=2)

class FileAssocManager:
    PROG_ID="FluentView.PhotoViewer"
    @staticmethod
    def _get_app_command():
        if getattr(sys,'frozen',False):
            return f'"{sys.executable}" "%1"'
        return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" "%1"'
    @classmethod
    def associate(cls,ext_list):
        if platform.system()!="Windows":
            return False
        import winreg
        cmd=cls._get_app_command()
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,f"Software\\Classes\\{cls.PROG_ID}") as key:
                winreg.SetValue(key,"",winreg.REG_SZ,"FluentView Photo Viewer")
                with winreg.CreateKey(key,"DefaultIcon") as ik:
                    winreg.SetValue(ik,"",winreg.REG_SZ,f'"{sys.executable}",0')
                with winreg.CreateKey(key,r"shell\open\command") as ck:
                    winreg.SetValue(ck,"",winreg.REG_SZ,cmd)
        except OSError:
            return False
        for ext in ext_list:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,f"Software\\Classes\\{ext}") as key:
                    winreg.SetValue(key,"",winreg.REG_SZ,cls.PROG_ID)
            except OSError:
                continue
        cfg=_load_config()
        cfg['associated_formats']=sorted(ext_list)
        cfg['assoc_done']=True
        _save_config(cfg)
        cls._refresh_shell()
        return True
    @classmethod
    def remove_association(cls):
        if platform.system()!="Windows":
            return
        import winreg
        cfg=_load_config()
        for ext in cfg.get('associated_formats',[]):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,f"Software\\Classes\\{ext}",0,winreg.KEY_ALL_ACCESS) as key:
                    val,_=winreg.QueryValueEx(key,"")
                    if val==cls.PROG_ID:
                        winreg.DeleteValue(key,"")
            except OSError:
                continue
        for sub in (r"shell\open\command",r"shell\open",r"shell","DefaultIcon",""):
            try:
                p=f"Software\\Classes\\{cls.PROG_ID}"+(f"\\{sub}" if sub else "")
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER,p)
            except OSError:
                continue
        cfg['associated_formats']=[]
        cfg['assoc_done']=False
        _save_config(cfg)
        cls._refresh_shell()
    @staticmethod
    def _refresh_shell():
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000,0x1000,None,None)
        except:
            pass
    @staticmethod
    def get_associated():
        return _load_config().get('associated_formats',[])

_ZH_TEMPLATE="""\
[lang]
code = zh_CN
name = 简体中文
[app]
title = 照片查看器
[navigation]
gallery = 图片浏览
edit = 编辑图片
wallpaper = 壁纸库
export_nav = 导出
settings = 设置
about = 关于
[gallery]
btn_add_files = 添加文件
btn_add_folder = 添加文件夹
btn_clear = 清空
btn_edit = 编辑图片
tooltip_edit = 编辑当前图片 (裁剪 / 批注 / 移动 / 旋转)
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
btn_refresh = 刷新
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
list_title = 可导出图片
list_empty = 暂无可导出图片
[editor]
title = 编辑图片
tool_move = 移动
tool_crop = 裁剪
tool_pen = 批注
tool_text = 文字
tool_rotate = 旋转
tool_undo = 撤销
btn_apply_crop = 应用裁剪
btn_save = 保存
btn_reset = 重置
btn_cancel = 取消
btn_ok = 确定
pen_color = 颜色
pen_width = 粗细
text_label = 文字样式
text_font = 字体
text_size = 大小
text_bold = 加粗
text_underline = 下划线
hint = 移动: 拖动平移画布 · 裁剪: 拖出选区后点击“应用裁剪” · 批注: 按住左键在图上绘制 · 文字: 在图上点击后输入文字，回车确认（字体/大小/加粗/下划线可调） · 旋转: 每次顺时针旋转 90°
no_image_title = 无图片
no_image = 请先选择一张图片
save_ok_title = 修改成功
save_ok_msg = 修改成功，请在图片导出中导出图片
[settings]
title = 设置
appearance = 外观
dark_mode = 深色模式
dark_mode_desc = 切换浅色/深色主题
file_assoc = 文件关联
file_assoc_desc = 设置 FluentView 为默认图片查看器
select_all = 全选
btn_apply_assoc = 应用关联
btn_remove_assoc = 取消关联
assoc_success_title = 关联成功
assoc_success_msg = 已关联 {n} 种图片格式
assoc_remove_title = 已取消关联
assoc_remove_msg = 已取消所有文件关联
assoc_no_format_title = 未选择格式
assoc_no_format_msg = 请至少选择一种格式
assoc_not_windows = 文件关联仅支持 Windows 系统
language = 语言
language_desc = 切换界面语言（切换后将重启应用）
language_card_title = 界面语言
[first_run]
title = 欢迎使用 FluentView
subtitle = 首次启动设置
desc = 请选择要关联的图片格式，设置后双击图片即可用 FluentView 打开
select_all = 全选
confirm = 确认并关联
skip = 跳过
success_title = 设置完成
success_msg = 已关联 {n} 种格式，开始使用吧！
[about]
title = 关于
description = Fluent Photo Viewer — 基于 PyQt5 + PyQt-Fluent-Widgets
author_title = 作者
github_link = 前往 Github 查看源码
current_version = 当前版本: {ver}
btn_update = 自动更新
update_checking = 正在检查更新…
update_latest = 当前已是最新版本
update_latest_msg = 当前版本 {ver} 已是最新版本
update_found_title = 发现新版本
update_found_msg = 发现新版本 {tag}，是否前往下载？
btn_open_release = 前往下载
btn_cancel = 取消
update_error = 检查更新失败
update_error_msg = 无法连接 GitHub 检查更新，请检查网络后重试
[file_dialog]
select_images = 选择图片文件
select_folder = 选择图片文件夹
image_filter = 图片文件 ({formats});;所有文件 (*)
image_filter_export = 图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.ico *.webp *.heic *.heif *.avif *.hif *.tiff *.tif *.svg *.raw *.cr2 *.cr3 *.nef *.arw *.dng *.3fr *.ari *.bay *.cap *.iiq *.fff *.mos *.nrw *.ptx *.r3d *.rwl *.x3f *.gpr *.orf *.rw2 *.pef *.srw *.raf *.mrw *.dcr *.erf *.mef *.crw *.mdc);;所有文件 (*)
[format]
byte = B
kilobyte = KB
megabyte = MB
gigabyte = GB
terabyte = TB
"""
_EN_TEMPLATE="""\
[lang]
code = en_US
name = English
[app]
title = Photo Viewer
[navigation]
gallery = Gallery
edit = Edit Image
wallpaper = Wallpapers
export_nav = Export
settings = Settings
about = About
[gallery]
btn_add_files = Add Files
btn_add_folder = Add Folder
btn_clear = Clear
btn_edit = Edit Image
tooltip_edit = Edit current image (crop / annotate / move / rotate)
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
list_title = Images Ready to Export
list_empty = No images to export yet
[editor]
title = Edit Image
tool_move = Move
tool_crop = Crop
tool_pen = Annotate
tool_text = Text
tool_rotate = Rotate
tool_undo = Undo
btn_apply_crop = Apply Crop
btn_save = Save
btn_reset = Reset
btn_cancel = Cancel
btn_ok = OK
pen_color = Color
pen_width = Width
text_label = Text Style
text_font = Font
text_size = Size
text_bold = Bold
text_underline = Underline
hint = Move: drag to pan · Crop: drag a selection then click "Apply Crop" · Annotate: draw with left button · Text: click on the image and type, press Enter to confirm (font / size / bold / underline adjustable) · Rotate: 90° clockwise each time
no_image_title = No Image
no_image = Please select an image first
save_ok_title = Saved
save_ok_msg = Modified successfully, please export the image in Image Export
[settings]
title = Settings
appearance = Appearance
dark_mode = Dark Mode
dark_mode_desc = Switch between light and dark theme
file_assoc = File Association
file_assoc_desc = Set FluentView as default image viewer
select_all = Select All
btn_apply_assoc = Apply Association
btn_remove_assoc = Remove Association
assoc_success_title = Associated
assoc_success_msg = {n} image formats associated
assoc_remove_title = Removed
assoc_remove_msg = All file associations removed
assoc_no_format_title = No Format Selected
assoc_no_format_msg = Please select at least one format
assoc_not_windows = File association is only supported on Windows
language = Language
language_desc = Switch language (app will restart)
language_card_title = Interface Language
[first_run]
title = Welcome to FluentView
subtitle = First-time Setup
desc = Select image formats to associate — double-click will open with FluentView
select_all = Select All
confirm = Confirm and Associate
skip = Skip
success_title = Setup Complete
success_msg = {n} formats associated. Enjoy!
[about]
title = About
description = Fluent Photo Viewer — Built with PyQt5 + PyQt-Fluent-Widgets
author_title = Authors
github_link = View source on Github
current_version = Current version: {ver}
btn_update = Check for Updates
update_checking = Checking for updates…
update_latest = Already up to date
update_latest_msg = Current version {ver} is the latest one
update_found_title = New Version Found
update_found_msg = New version {tag} is available. Download it now?
btn_open_release = Download
btn_cancel = Cancel
update_error = Update check failed
update_error_msg = Cannot reach GitHub to check updates
[file_dialog]
select_images = Select Image Files
select_folder = Select Image Folder
image_filter = Image Files ({formats});;All Files (*)
image_filter_export = Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.ico *.webp *.heic *.heif *.avif *.hif *.tiff *.tif *.svg *.raw *.cr2 *.cr3 *.nef *.arw *.dng *.3fr *.ari *.bay *.cap *.iiq *.fff *.mos *.nrw *.ptx *.r3d *.rwl *.x3f *.gpr *.orf *.rw2 *.pef *.srw *.raf *.mrw *.dcr *.erf *.mef *.crw *.mdc);;All Files (*)
[format]
byte = B
kilobyte = KB
megabyte = MB
gigabyte = GB
terabyte = TB
"""

class LanguageManager:
    _instance=None
    def __new__(cls):
        if cls._instance is None:
            cls._instance=super().__new__(cls)
            cls._instance._translations={}
            cls._instance._current_lang="zh_CN"
        return cls._instance
    def init(self):
        self._ensureLangFiles()
        cfg=_load_config()
        saved=cfg.get('language','zh_CN')
        if self.load(saved):
            return
        if self.load("zh_CN"):
            return
        for lang in self.availableLangs():
            if self.load(lang):
                return
    def _ensureLangFiles(self):
        for code,content in {"zh_CN":_ZH_TEMPLATE,"en_US":_EN_TEMPLATE}.items():
            d=os.path.join(LANG_DIR,code)
            p=os.path.join(d,"settings.ini")
            os.makedirs(d,exist_ok=True)
            if not os.path.isfile(p):
                with open(p,"w",encoding="utf-8") as f:
                    f.write(content)
                continue
            # 升级兼容：合并模板中新增的键，保留已有翻译
            try:
                cur=configparser.ConfigParser(interpolation=None)
                cur.read(p,encoding="utf-8")
                tpl=configparser.ConfigParser(interpolation=None)
                tpl.read_string(content)
                changed=False
                for sec in tpl.sections():
                    if not cur.has_section(sec):
                        cur.add_section(sec)
                        for k,v in tpl.items(sec):
                            cur.set(sec,k,v)
                        changed=True
                        continue
                    for k,v in tpl.items(sec):
                        if not cur.has_option(sec,k):
                            cur.set(sec,k,v)
                            changed=True
                if changed:
                    with open(p,"w",encoding="utf-8") as f:
                        cur.write(f)
            except Exception:
                pass
    def saveLang(self,lang_code):
        cfg=_load_config()
        cfg['language']=lang_code
        _save_config(cfg)
    def load(self,lang_code):
        ini=os.path.join(LANG_DIR,lang_code,"settings.ini")
        if not os.path.isfile(ini):
            return False
        cfg=configparser.ConfigParser(interpolation=None)
        cfg.read(ini,encoding="utf-8")
        self._translations={}
        for section in cfg.sections():
            if section=="lang":
                continue
            for key,value in cfg.items(section):
                self._translations[f"{section}.{key}"]=value
        self._current_lang=lang_code
        return True
    def tr(self,key,**kwargs):
        text=self._translations.get(key,key)
        if kwargs:
            try:
                text=text.format(**kwargs)
            except:
                pass
        return text
    @property
    def current_lang(self):
        return self._current_lang
    def availableLangs(self):
        langs=[]
        if os.path.isdir(LANG_DIR):
            for d in sorted(os.listdir(LANG_DIR)):
                if os.path.isdir(os.path.join(LANG_DIR,d)) and os.path.isfile(os.path.join(LANG_DIR,d,"settings.ini")):
                    langs.append(d)
        return langs
    def langName(self,lang_code):
        ini=os.path.join(LANG_DIR,lang_code,"settings.ini")
        if os.path.isfile(ini):
            cfg=configparser.ConfigParser(interpolation=None)
            cfg.read(ini,encoding="utf-8")
            return cfg.get("lang","name",fallback=lang_code)
        return lang_code

LM=LanguageManager()

def _restartApp():
    subprocess.Popen([sys.executable]+sys.argv)
    QApplication.instance().quit()

def _format_size(size_bytes):
    for k in ("format.byte","format.kilobyte","format.megabyte","format.gigabyte"):
        if size_bytes<1024:
            return f"{size_bytes:.1f} {LM.tr(k)}"
        size_bytes/=1024
    return f"{size_bytes:.1f} {LM.tr('format.terabyte')}"

def IMAGE_FILTER_STR():
    return LM.tr("file_dialog.image_filter",formats=ALL_FORMATS)

def _notify_ok(parent, title, content=""):
    InfoBar.success(title=title, content=content, orient=Qt.Horizontal,
                    isClosable=True, duration=4000, position=InfoBarPosition.TOP, parent=parent)

def _notify_warn(parent, title, content=""):
    InfoBar.warning(title=title, content=content, orient=Qt.Horizontal,
                    isClosable=True, duration=5000, position=InfoBarPosition.TOP, parent=parent)

def _notify_err(parent, title, content=""):
    InfoBar.error(title=title, content=content, orient=Qt.Horizontal,
                  isClosable=True, duration=6000, position=InfoBarPosition.TOP, parent=parent)


# ═══════════════════════════════════════════
# 经典 WinUI3 风格矢量图标 (内嵌 SVG)
# ═══════════════════════════════════════════
_VECTOR_ICONS = {
    # 语言 / 地球
    "globe": (
        '<circle cx="12" cy="12" r="8.6"/>'
        '<ellipse cx="12" cy="12" rx="4.2" ry="8.6"/>'
        '<path d="M3.4 12h17.2M4.9 7.1h14.2M4.9 16.9h14.2"/>'
    ),
    # 铅笔 / 批注
    "edit": (
        '<path d="M4 20.2l1.1-4.4L15.4 5.5a1.9 1.9 0 0 1 2.7 0l1.4 1.4a1.9 1.9 0 0 1 0 2.7'
        'L9.2 20.2 4 20.2z"/>'
        '<path d="M14.2 6.8l3 3"/>'
    ),
    # 文字 / A
    "text": (
        '<path d="M5 7V4.8h14V7"/>'
        '<path d="M12 4.8v14.4"/>'
        '<path d="M8.6 19.2h6.8"/>'
    ),
    # 裁剪
    "crop": '<path d="M7 2.6v14.4h14.4"/><path d="M2.6 7h14.4v14.4"/>',
    # 移动
    "move": (
        '<path d="M12 2.8v18.4M2.8 12h18.4"/>'
        '<path d="M9 5.8L12 2.8l3 3M9 18.2l3 3 3-3M5.8 9l-3 3 3 3M18.2 9l3 3-3 3"/>'
    ),
    # 旋转
    "rotate": '<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20.4 3.2v4.8h-4.8"/>',
    # 撤销
    "undo": (
        '<path d="M8.6 7.2L4 11.8l4.6 4.6"/>'
        '<path d="M4 11.8h10a5.2 5.2 0 0 1 0 10.4h-2.4"/>'
    ),
    # 自动更新 / 同步
    "sync": (
        '<path d="M4.6 12a7.4 7.4 0 0 1 12.6-5.2l2.3 2.5"/>'
        '<path d="M20 4.2v5h-5"/>'
        '<path d="M19.4 12a7.4 7.4 0 0 1-12.6 5.2L4.5 14.7"/>'
        '<path d="M4 19.8v-5h5"/>'
    ),
    # 保存
    "save": (
        '<path d="M4.5 4.5h11.6l3.4 3.4v11.6h-15z"/>'
        '<path d="M8 4.5v5.2h7.2V4.5"/>'
        '<path d="M7.6 19.5v-5.6h8.8v5.6"/>'
    ),
}


def vector_pixmap(name, size=20, color=None):
    """渲染内嵌 SVG 矢量图标为 QPixmap（随主题取色）"""
    if color is None:
        color = "#e8e6e3" if isDarkTheme() else "#1a1a1a"
    body = _VECTOR_ICONS.get(name, "")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
           f'{body}</svg>')
    renderer = QSvgRenderer(svg.encode("utf-8"))
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    renderer.render(p)
    p.end()
    return pm


def vector_icon(name, size=20, color=None):
    return QIcon(vector_pixmap(name, size, color))


def _version_tuple(s):
    parts = [int(x) for x in re.findall(r'\d+', str(s))]
    return tuple(parts) if parts else (0,)


class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LM.tr("first_run.title"))
        self.setFixedSize(520, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dark = isDarkTheme()
        bg = "#1e1e28" if dark else "#f5f5f5"
        tm = "#e8e6e3" if dark else "#1a1a1a"
        muted = "#8a8a9a" if dark else "#666666"
        self.setStyleSheet(
            f"QDialog{{background:{bg};}}QLabel{{color:{tm};}}"
            f"QCheckBox{{color:{tm};font-size:12px;}}QCheckBox::indicator{{width:16px;height:16px;}}"
            f"QScrollArea{{background:transparent;border:none;}}")
        self._checkboxes = {}
        lo = QVBoxLayout(self)
        lo.setContentsMargins(28, 24, 28, 24)
        lo.setSpacing(10)
        t = TitleLabel(LM.tr("first_run.title"))
        t.setAlignment(Qt.AlignCenter)
        lo.addWidget(t)
        s = CaptionLabel(LM.tr("first_run.subtitle"))
        s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet(f"color:{muted};")
        lo.addWidget(s)
        lo.addSpacing(4)
        d = BodyLabel(LM.tr("first_run.desc"))
        d.setAlignment(Qt.AlignCenter)
        d.setWordWrap(True)
        d.setStyleSheet(f"color:{muted};")
        lo.addWidget(d)
        lo.addSpacing(4)
        self.chkSelectAll = QCheckBox(LM.tr("first_run.select_all"))
        self.chkSelectAll.setStyleSheet(f"font-weight:bold;font-size:13px;color:{tm};")
        self.chkSelectAll.stateChanged.connect(self._onSelectAll)
        lo.addWidget(self.chkSelectAll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        grid = QGridLayout(container)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(5)
        for i, ext in enumerate(sorted(FORMAT_DISPLAY.keys())):
            chk = QCheckBox(f"{ext}  ({FORMAT_DISPLAY[ext]})")
            chk.setStyleSheet(f"font-size:11px;color:{tm};")
            chk.stateChanged.connect(self._onChildChanged)
            self._checkboxes[ext] = chk
            grid.addWidget(chk, i // 3, i % 3)
        scroll.setWidget(container)
        lo.addWidget(scroll, 1)
        br = QHBoxLayout()
        br.setSpacing(12)
        self.btnSkip = PushButton(LM.tr("first_run.skip"))
        self.btnConfirm = PrimaryPushButton(LM.tr("first_run.confirm"))
        self.btnSkip.setFixedHeight(38)
        self.btnConfirm.setFixedHeight(38)
        br.addWidget(self.btnSkip)
        br.addWidget(self.btnConfirm)
        lo.addLayout(br)
        self.btnConfirm.clicked.connect(self._onConfirm)
        self.btnSkip.clicked.connect(self._onSkip)

    def _onSelectAll(self, state):
        for chk in self._checkboxes.values():
            chk.blockSignals(True)
            chk.setChecked(state == Qt.Checked)
            chk.blockSignals(False)

    def _onChildChanged(self):
        total = len(self._checkboxes)
        checked = sum(1 for c in self._checkboxes.values() if c.isChecked())
        self.chkSelectAll.blockSignals(True)
        self.chkSelectAll.setChecked(checked == total)
        self.chkSelectAll.blockSignals(False)

    def _onConfirm(self):
        selected = [e for e, c in self._checkboxes.items() if c.isChecked()]
        if not selected:
            _notify_warn(self, LM.tr("settings.assoc_no_format_title"), LM.tr("settings.assoc_no_format_msg"))
            return
        FileAssocManager.associate(selected)
        _notify_ok(self, LM.tr("first_run.success_title"), LM.tr("first_run.success_msg", n=len(selected)))
        cfg = _load_config()
        cfg['first_run_done'] = True
        _save_config(cfg)
        QTimer.singleShot(1000, self.accept)

    def _onSkip(self):
        cfg = _load_config()
        cfg['first_run_done'] = True
        _save_config(cfg)
        self.reject()


# ═══════════════════════════════════════════
# FormatSelectorCard — 格式全部显示，无滚动截断
# ═══════════════════════════════════════════
class FormatSelectorCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes = {}
        self._colCount = 4
        self._rowHeight = 24
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        dark = isDarkTheme()
        tc = "#e8e6e3" if dark else "#1a1a1a"
        sbg = "rgba(255,255,255,0.04)" if dark else "rgba(0,0,0,0.03)"
        sbd = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.08)"
        accent = "#00b894" if dark else "#00a884"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # ── 标题行 ──
        titleRow = QHBoxLayout()
        titleRow.setSpacing(8)
        iconLbl = QLabel()
        iconLbl.setFixedSize(28, 28)
        iconLbl.setAlignment(Qt.AlignCenter)
        iconLbl.setStyleSheet(f"font-size:18px;background:{sbg};border:1px solid {sbd};border-radius:6px;")
        try:
            iconLbl.setPixmap(FluentIcon.FOLDER.icon().pixmap(18, 18))
        except:
            iconLbl.setText("📂")
        titleRow.addWidget(iconLbl)
        tLbl = StrongBodyLabel(LM.tr("settings.file_assoc"))
        tLbl.setStyleSheet(f"font-size:13px;font-weight:bold;color:{tc};background:transparent;border:none;")
        titleRow.addWidget(tLbl)
        titleRow.addStretch()
        self._lblStatus = CaptionLabel("")
        self._lblStatus.setStyleSheet(f"font-size:10px;color:{accent};background:transparent;border:none;")
        titleRow.addWidget(self._lblStatus)
        root.addLayout(titleRow)

        # ── 操作行 ──
        actRow = QHBoxLayout()
        actRow.setSpacing(8)
        self.chkSelectAll = QCheckBox(LM.tr("settings.select_all"))
        self.chkSelectAll.setStyleSheet(
            f"font-size:11px;font-weight:bold;color:{tc};QCheckBox::indicator{{width:13px;height:13px;}}")
        self.chkSelectAll.stateChanged.connect(self._onSelectAll)
        actRow.addWidget(self.chkSelectAll)
        actRow.addStretch()
        self.btnRemove = PushButton(LM.tr("settings.btn_remove_assoc"))
        self.btnApply = PrimaryPushButton(LM.tr("settings.btn_apply_assoc"))
        self.btnRemove.setFixedHeight(28)
        self.btnApply.setFixedHeight(28)
        actRow.addWidget(self.btnRemove)
        actRow.addWidget(self.btnApply)
        root.addLayout(actRow)

        # ── 格式网格：直接放在布局中，不套 QScrollArea，全部显示 ──
        gridWrap = QWidget()
        gridWrap.setStyleSheet("background:transparent;border:none;")
        self._grid = QGridLayout(gridWrap)
        self._grid.setContentsMargins(0, 2, 0, 0)
        self._grid.setSpacing(0)
        self._grid.setHorizontalSpacing(10)

        sorted_exts = sorted(FORMAT_DISPLAY.keys())
        for i, ext in enumerate(sorted_exts):
            chk = QCheckBox(ext)
            chk.setFixedHeight(self._rowHeight)
            chk.setToolTip(f"{ext} — {FORMAT_DISPLAY[ext]}")
            chk.setStyleSheet(f"font-size:11px;color:{tc};QCheckBox::indicator{{width:13px;height:13px;}}")
            chk.stateChanged.connect(self._onChildChanged)
            self._checkboxes[ext] = chk
            self._grid.addWidget(chk, i // self._colCount, i % self._colCount)

        root.addWidget(gridWrap)

        self.btnApply.clicked.connect(self._onApply)
        self.btnRemove.clicked.connect(self._onRemove)
        self._loadState()

    def sizeHint(self):
        rc = (len(FORMAT_DISPLAY) + self._colCount - 1) // self._colCount
        h = 28 + 28 + 8 + rc * self._rowHeight + 8
        return QSize(300, h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def _loadState(self):
        assoc = FileAssocManager.get_associated()
        for ext, chk in self._checkboxes.items():
            chk.blockSignals(True)
            chk.setChecked(ext in assoc)
            chk.blockSignals(False)
        self._updateStatus()
        self._updateSelectAll()

    def _updateStatus(self):
        assoc = FileAssocManager.get_associated()
        self._lblStatus.setText(f"✓ {len(assoc)} formats" if assoc else "")

    def _updateSelectAll(self):
        total = len(self._checkboxes)
        checked = sum(1 for c in self._checkboxes.values() if c.isChecked())
        self.chkSelectAll.blockSignals(True)
        self.chkSelectAll.setChecked(checked == total and total > 0)
        self.chkSelectAll.blockSignals(False)

    def _onSelectAll(self, state):
        for chk in self._checkboxes.values():
            chk.blockSignals(True)
            chk.setChecked(state == Qt.Checked)
            chk.blockSignals(False)

    def _onChildChanged(self):
        self._updateSelectAll()

    def _onApply(self):
        if platform.system() != "Windows":
            _notify_warn(self, LM.tr("settings.assoc_no_format_title"), LM.tr("settings.assoc_not_windows"))
            return
        sel = [e for e, c in self._checkboxes.items() if c.isChecked()]
        if not sel:
            _notify_warn(self, LM.tr("settings.assoc_no_format_title"), LM.tr("settings.assoc_no_format_msg"))
            return
        FileAssocManager.associate(sel)
        self._updateStatus()
        _notify_ok(self, LM.tr("settings.assoc_success_title"), LM.tr("settings.assoc_success_msg", n=len(sel)))

    def _onRemove(self):
        if platform.system() != "Windows":
            return
        FileAssocManager.remove_association()
        self._loadState()
        _notify_ok(self, LM.tr("settings.assoc_remove_title"), LM.tr("settings.assoc_remove_msg"))


def load_pixmap(path, size=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.svg':
        r = QSvgRenderer(path)
        if r.isValid():
            sz = r.defaultSize()
            if size:
                sz = sz.scaled(size, size, Qt.KeepAspectRatio)
            pm = QPixmap(sz)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            r.render(p)
            p.end()
            return pm
        return QPixmap()
    if ext in RAW_EXTS:
        try:
            import rawpy
            with rawpy.imread(path) as raw:
                rgb = raw.postprocess(use_camera_wb=True, half_size=True, output_bps=8)
            h, w, _ = rgb.shape
            qi = QImage(rgb.data, w, 3 * w, 3 * w, QImage.Format_RGB888).copy()
            pm = QPixmap.fromImage(qi)
            if size and pm.width() > size and pm.height() > size:
                pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return pm
        except ImportError:
            pass
        except:
            pass
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
        except:
            pass
        if size and img.width > size and img.height > size:
            img.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        fmt = 'PNG' if img.mode in ('RGBA', 'LA', 'PA') else 'JPEG'
        if fmt == 'JPEG' and img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(buf, format=fmt)
        buf.seek(0)
        qi = QImage()
        qi.loadFromData(buf.read())
        return QPixmap.fromImage(qi)
    except:
        return QPixmap()


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
        p.drawPixmap((w - self.pix.width()) // 2, 2, self.pix)
        name = os.path.basename(self.path)
        if len(name) > 22:
            name = name[:19] + "..."
        p.setPen(QColor(60, 60, 60) if not isDarkTheme() else QColor(200, 200, 200))
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(QRect(0, THUMB_SIZE + 4, w, 28), Qt.AlignHCenter | Qt.AlignTop, name)
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
            for i in range(min(getattr(img, 'n_frames', 1), MAX_GIF_FRAMES)):
                if self._stop:
                    break
                img.seek(i)
                frame = img.copy().convert('RGBA')
                fw, fh = frame.size
                if self.maxW > 0 and self.maxH > 0:
                    s = min(self.maxW / fw, self.maxH / fh, 1.0)
                    if s < 1:
                        frame = frame.resize((int(fw * s), int(fh * s)), Image.LANCZOS)
                buf = io.BytesIO()
                frame.save(buf, format='PNG')
                buf.seek(0)
                qi = QImage()
                qi.loadFromData(buf.read())
                self.frameReady.emit(i, QPixmap.fromImage(qi), max(img.info.get('duration', 100), 20))
        except:
            pass
        self.allDone.emit()
    def stop(self):
        self._stop = True


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
        self._orig = self._gifFrames[0] if self._gifFrames else pm
        self.fitToWindow()

    def _getZoomLevel(self):
        return self._zoom

    def _setZoomLevel(self, v):
        self._zoom = v
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
        return self._orig.transformed(QTransform().rotate(self._rot), Qt.SmoothTransformation)

    def getCurrentPath(self):
        return self._path

    def _loadGifFrames(self, path):
        self._stopGif()
        self._gifLoader = GifLoader(path, self.width(), self.height())
        self._gifLoader.frameReady.connect(self._onGifFrame)
        self._gifLoader.allDone.connect(lambda: None)
        self._gifLoader.start()

    def _onGifFrame(self, idx, pm, dur):
        if idx == 0:
            self._orig = pm
            self.fitToWindow()
            self.update()
        self._gifFrames.append(pm)
        self._gifDurations.append(dur)
        if len(self._gifFrames) == 1 and not self._gifTimer.isActive():
            self._gifIndex = 0
            self._gifTimer.start(self._gifDurations[0])

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

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        dark = isDarkTheme()
        p.fillRect(self.rect(), QColor(30, 30, 30) if dark else QColor(245, 245, 245))
        if not self._orig:
            p.setPen(QColor(120, 120, 120) if dark else QColor(180, 180, 180))
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


# ═══════════════════════════════════════════
# 图片编辑器 — 裁剪 / 批注 / 移动 / 旋转
# ═══════════════════════════════════════════
# 图片编辑器 — 裁剪 / 批注 / 文字 / 移动 / 旋转
# ═══════════════════════════════════════════
class EditCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._img = None            # QImage 工作区
        self._zoom = 1.0
        self._off = QPoint(0, 0)
        self._tool = "move"          # move | crop | pen | text
        self._penColor = QColor(231, 72, 86)
        self._penWidth = 5
        self._textStyle = {"family": "Microsoft YaHei", "size": 24,
                           "bold": False, "underline": False}
        self._undo = []
        self._panning = False
        self._panStart = QPoint()
        self._offStart = QPoint(0, 0)
        self._stroke = []
        self._drawing = False
        self._cropStart = None
        self._cropRect = None        # 图片坐标系中的选区
        self._textEdit = None        # 浮动文字输入框
        self._textAnchor = QPoint()
        self.setMinimumSize(520, 380)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.OpenHandCursor)

    # ── 对外接口 ──
    def setImage(self, img):
        self._finishTextEntry(False)
        self._img = img.copy() if img is not None and not img.isNull() else None
        self._undo.clear()
        self._cropRect = None
        self._cropStart = None
        self._stroke = []
        self.fitView()

    def image(self):
        return self._img.copy() if self._img else None

    def setTool(self, tool):
        self._finishTextEntry(True)
        self._tool = tool
        self._stroke = []
        self._drawing = False
        if tool != "crop":
            self._cropRect = None
            self._cropStart = None
        if tool == "move":
            self.setCursor(Qt.OpenHandCursor)
        elif tool == "text":
            self.setCursor(Qt.IBeamCursor)
        else:
            self.setCursor(Qt.CrossCursor)
        self.update()

    def setPenColor(self, color):
        self._penColor = QColor(color)

    def setPenWidth(self, w):
        self._penWidth = max(1, int(w))

    def setTextStyle(self, family=None, size=None, bold=None, underline=None):
        if family:
            self._textStyle["family"] = family
        if size:
            self._textStyle["size"] = int(size)
        if bold is not None:
            self._textStyle["bold"] = bool(bold)
        if underline is not None:
            self._textStyle["underline"] = bool(underline)
        if self._textEdit is not None:
            self._textEdit.setFont(self._textFont())

    def textFont(self):
        f = QFont(self._textStyle.get("family") or "Microsoft YaHei",
                  max(6, int(self._textStyle.get("size", 24))))
        f.setBold(bool(self._textStyle.get("bold")))
        f.setUnderline(bool(self._textStyle.get("underline")))
        return f

    def fitView(self):
        if not self._img:
            self.update()
            return
        iw, ih = self._img.width(), self._img.height()
        if iw == 0 or ih == 0:
            return
        self._zoom = min(self.width() / iw, self.height() / ih) * 0.96
        self._off = QPoint(0, 0)
        self.update()

    def rotate90(self):
        if not self._img:
            return
        self._finishTextEntry(True)
        self._pushUndo()
        self._img = self._img.transformed(QTransform().rotate(90), Qt.SmoothTransformation)
        self._cropRect = None
        self.fitView()

    def undo(self):
        self._finishTextEntry(False)
        if self._undo:
            self._img = self._undo.pop()
            self._cropRect = None
            self._cropStart = None
            self.update()

    def hasUndo(self):
        return bool(self._undo)

    def applyCrop(self):
        self._finishTextEntry(True)
        if not self._img or not self._cropRect:
            return False
        r = self._cropRect.intersected(QRect(0, 0, self._img.width(), self._img.height()))
        if r.width() < 2 or r.height() < 2:
            return False
        self._pushUndo()
        self._img = self._img.copy(r)
        self._cropRect = None
        self._cropStart = None
        self.fitView()
        return True

    def _pushUndo(self):
        if self._img:
            self._undo.append(self._img.copy())
            if len(self._undo) > 20:
                self._undo.pop(0)

    # ── 文字批注 ──
    def _startTextEntry(self, widgetPos, imgPt):
        self._finishTextEntry(True)
        self._textAnchor = imgPt
        dark = isDarkTheme()
        le = QLineEdit(self)
        self._textEdit = le
        le.setFont(self.textFont())
        le.setStyleSheet(
            "QLineEdit{{background:{bg};color:{fg};border:2px solid #00b894;"
            "border-radius:4px;padding:2px 6px;selection-background-color:#00b894;}}".format(
                bg="rgba(28,28,32,0.96)" if dark else "rgba(255,255,255,0.96)",
                fg="#e8e6e3" if dark else "#1a1a1a"))
        le.setMinimumWidth(220)
        le.move(widgetPos)
        le.show()
        le.setFocus()
        le.returnPressed.connect(self._commitText)

    def _finishTextEntry(self, commit):
        if self._textEdit is None:
            return
        text = self._textEdit.text()
        te = self._textEdit
        self._textEdit = None
        te.deleteLater()
        if commit and text and self._img:
            self._pushUndo()
            p = QPainter(self._img)
            p.setRenderHint(QPainter.TextAntialiasing)
            p.setFont(self.textFont())
            p.setPen(self._penColor)
            p.drawText(self._textAnchor, text)
            p.end()
        self.update()

    def _commitText(self):
        self._finishTextEntry(True)

    # ── 坐标换算 ──
    def _imageRect(self):
        if not self._img:
            return QRect()
        w = max(1, int(self._img.width() * self._zoom))
        h = max(1, int(self._img.height() * self._zoom))
        return QRect((self.width() - w) // 2 + self._off.x(),
                     (self.height() - h) // 2 + self._off.y(), w, h)

    def _toImage(self, pos):
        if not self._img:
            return None
        r = self._imageRect()
        return QPoint(int(round((pos.x() - r.x()) / self._zoom)),
                      int(round((pos.y() - r.y()) / self._zoom)))

    def _toView(self, pt):
        r = self._imageRect()
        return QPoint(int(r.x() + pt.x() * self._zoom), int(r.y() + pt.y() * self._zoom))

    def _imgRectToView(self, imgRect):
        r = self._imageRect()
        return QRect(r.x() + int(imgRect.x() * self._zoom),
                     r.y() + int(imgRect.y() * self._zoom),
                     max(1, int(imgRect.width() * self._zoom)),
                     max(1, int(imgRect.height() * self._zoom)))

    # ── 绘制 ──
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        dark = isDarkTheme()
        p.fillRect(self.rect(), QColor(28, 28, 30) if dark else QColor(238, 238, 240))
        if not self._img:
            p.setPen(QColor(140, 140, 140))
            p.setFont(QFont("Microsoft YaHei", 12))
            p.drawText(self.rect(), Qt.AlignCenter, LM.tr("editor.no_image"))
            p.end()
            return
        r = self._imageRect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 45))
        p.drawRoundedRect(r.x() + 3, r.y() + 3, r.width(), r.height(), 4, 4)
        p.drawPixmap(r, QPixmap.fromImage(self._img))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(130, 130, 140), 1))
        p.drawRect(r)
        # 裁剪遮罩
        if self._tool == "crop" and self._cropRect and self._cropRect.width() > 0 and self._cropRect.height() > 0:
            sel = self._imgRectToView(self._cropRect)
            p.setBrush(QColor(0, 0, 0, 115))
            p.setPen(Qt.NoPen)
            p.drawRect(QRect(r.x(), r.y(), r.width(), max(0, sel.y() - r.y())))
            p.drawRect(QRect(r.x(), sel.y() + sel.height(), r.width(),
                             max(0, r.y() + r.height() - sel.y() - sel.height())))
            p.drawRect(QRect(r.x(), sel.y(), max(0, sel.x() - r.x()), sel.height()))
            p.drawRect(QRect(sel.x() + sel.width(), sel.y(),
                             max(0, r.x() + r.width() - sel.x() - sel.width()), sel.height()))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(0, 184, 255), 2))
            p.drawRect(sel)
        # 批注笔迹预览
        if self._tool == "pen" and self._drawing and self._stroke:
            pen = QPen(self._penColor, max(1.0, self._penWidth * self._zoom),
                       Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            pts = [self._toView(pt) for pt in self._stroke]
            if len(pts) == 1:
                p.drawPoint(pts[0])
            else:
                for a, b in zip(pts, pts[1:]):
                    p.drawLine(a, b)
        p.end()

    def _commitStroke(self):
        if not self._stroke or not self._img:
            self._stroke = []
            self.update()
            return
        self._pushUndo()
        p = QPainter(self._img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self._penColor, self._penWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if len(self._stroke) == 1:
            p.drawPoint(self._stroke[0])
        else:
            for a, b in zip(self._stroke, self._stroke[1:]):
                p.drawLine(a, b)
        p.end()
        self._stroke = []
        self.update()

    def wheelEvent(self, e):
        if not self._img:
            return
        factor = 1.25 if e.angleDelta().y() > 0 else 0.8
        self._zoom = max(0.05, min(self._zoom * factor, 16.0))
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or not self._img:
            return
        if self._tool == "move":
            self._panning = True
            self._panStart = e.pos()
            self._offStart = QPoint(self._off)
            self.setCursor(Qt.ClosedHandCursor)
        elif self._tool == "pen":
            pt = self._toImage(e.pos())
            if pt is not None:
                self._drawing = True
                self._stroke = [pt]
        elif self._tool == "text":
            pt = self._toImage(e.pos())
            if pt is not None:
                self._startTextEntry(e.pos(), pt)
        elif self._tool == "crop":
            pt = self._toImage(e.pos())
            if pt is not None:
                self._cropStart = pt
                self._cropRect = QRect(pt, pt)

    def mouseMoveEvent(self, e):
        if not self._img:
            return
        if self._tool == "move" and self._panning:
            self._off = self._offStart + (e.pos() - self._panStart)
            self.update()
        elif self._tool == "pen" and self._drawing:
            pt = self._toImage(e.pos())
            if pt is not None:
                self._stroke.append(pt)
                self.update()
        elif self._tool == "crop" and self._cropStart is not None:
            pt = self._toImage(e.pos())
            if pt is not None:
                self._cropRect = QRect(self._cropStart, pt).normalized().intersected(
                    QRect(0, 0, self._img.width(), self._img.height()))
                self.update()

    def mouseReleaseEvent(self, e):
        if self._tool == "move":
            self._panning = False
            self.setCursor(Qt.OpenHandCursor)
        elif self._tool == "pen" and self._drawing:
            self._drawing = False
            self._commitStroke()
        elif self._tool == "crop":
            self._cropStart = None
        self.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)


class EditPage(QWidget):
    """编辑图片分类页：裁剪 / 批注 / 文字 / 移动 / 旋转"""
    saved = pyqtSignal(str, object)   # (保存路径, QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editPage")
        self.setStyleSheet("background:transparent;")
        self._sourcePath = ""
        self._original = None        # QImage 原图（用于重置）

        dark = isDarkTheme()
        tm = "#e8e6e3" if dark else "#1a1a1a"
        muted = "#8a8a9a" if dark else "#666666"
        sbd = "rgba(255,255,255,0.10)" if dark else "rgba(0,0,0,0.10)"

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(10)

        # ── 标题行 ──
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(TitleLabel(LM.tr("editor.title")))
        head.addStretch()
        self.lblName = CaptionLabel(LM.tr("editor.no_image"))
        self.lblName.setStyleSheet(f"font-size:12px;color:{muted};")
        head.addWidget(self.lblName)
        root.addLayout(head)

        # ── 工具行 ──
        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.btnMove = PushButton(LM.tr("editor.tool_move"))
        self.btnCrop = PushButton(LM.tr("editor.tool_crop"))
        self.btnPen = PushButton(LM.tr("editor.tool_pen"))
        self.btnText = PushButton(LM.tr("editor.tool_text"))
        for btn, ico in ((self.btnMove, "move"), (self.btnCrop, "crop"),
                         (self.btnPen, "edit"), (self.btnText, "text")):
            btn.setIcon(vector_icon(ico, 16, tm))
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            tools.addWidget(btn)
        self._toolGroup = QButtonGroup(self)
        self._toolGroup.setExclusive(True)
        for btn in (self.btnMove, self.btnCrop, self.btnPen, self.btnText):
            self._toolGroup.addButton(btn)
        self.btnMove.setChecked(True)

        tools.addSpacing(6)
        self.btnRotate = PushButton(LM.tr("editor.tool_rotate"))
        self.btnRotate.setIcon(vector_icon("rotate", 16, tm))
        self.btnUndo = PushButton(LM.tr("editor.tool_undo"))
        self.btnUndo.setIcon(vector_icon("undo", 16, tm))
        self.btnApplyCrop = PushButton(LM.tr("editor.btn_apply_crop"))
        self.btnApplyCrop.setIcon(vector_icon("crop", 16, tm))
        for b in (self.btnRotate, self.btnUndo, self.btnApplyCrop):
            b.setFixedHeight(32)
            tools.addWidget(b)

        tools.addStretch()
        tools.addWidget(CaptionLabel(LM.tr("editor.pen_color")))
        self._colorButtons = []
        for c in ("#e74856", "#f7b32b", "#2ec4b6", "#3d5afe", "#ffffff", "#1a1a1a"):
            b = QPushButton()
            b.setFixedSize(26, 26)
            b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True)
            b.setStyleSheet(
                f"QPushButton{{background:{c};border-radius:13px;border:2px solid {sbd};}}"
                f"QPushButton:checked{{border:2px solid #00b894;}}")
            b.clicked.connect(lambda _=False, col=c: self._pickColor(col))
            tools.addWidget(b)
            self._colorButtons.append(b)
        self._colorButtons[0].setChecked(True)

        tools.addWidget(CaptionLabel(LM.tr("editor.pen_width")))
        self.widthCombo = ComboBox()
        for w in (3, 5, 8, 14, 24):
            self.widthCombo.addItem(f"{w} px", userData=w)
        self.widthCombo.setCurrentIndex(1)
        self.widthCombo.setFixedWidth(88)
        self.widthCombo.currentIndexChanged.connect(
            lambda i: self.canvas.setPenWidth(self.widthCombo.itemData(i)))
        tools.addWidget(self.widthCombo)
        root.addLayout(tools)

        # ── 文字批注样式行 ──
        textRow = QHBoxLayout()
        textRow.setSpacing(8)
        textRow.addWidget(CaptionLabel(LM.tr("editor.text_label")))
        self.fontCombo = ComboBox()
        common = ["Microsoft YaHei", "SimSun", "SimHei", "KaiTi", "FangSong",
                  "Segoe UI", "Arial", "Times New Roman", "Consolas", "Calibri"]
        try:
            families = list(QFontDatabase().families())
        except Exception:
            families = []
        seen = []
        for f in common + families:
            if f and f not in seen and (not families or f in families):
                seen.append(f)
        if not seen:
            seen = ["Microsoft YaHei"]
        for f in seen:
            self.fontCombo.addItem(f, userData=f)
        idx = self.fontCombo.findData("Microsoft YaHei")
        if idx >= 0:
            self.fontCombo.setCurrentIndex(idx)
        self.fontCombo.setFixedWidth(180)
        textRow.addWidget(self.fontCombo)

        textRow.addWidget(CaptionLabel(LM.tr("editor.text_size")))
        self.sizeCombo = ComboBox()
        for s in (8, 10, 12, 14, 16, 20, 24, 32, 48, 64, 96):
            self.sizeCombo.addItem(f"{s} px", userData=s)
        self.sizeCombo.setCurrentIndex(self.sizeCombo.findData(24))
        self.sizeCombo.setFixedWidth(96)
        textRow.addWidget(self.sizeCombo)

        self.btnBold = PushButton(LM.tr("editor.text_bold"))
        self.btnBold.setCheckable(True)
        self.btnBold.setFixedHeight(32)
        bf = self.btnBold.font()
        bf.setBold(True)
        self.btnBold.setFont(bf)
        self.btnUnderline = PushButton(LM.tr("editor.text_underline"))
        self.btnUnderline.setCheckable(True)
        self.btnUnderline.setFixedHeight(32)
        uf = self.btnUnderline.font()
        uf.setUnderline(True)
        self.btnUnderline.setFont(uf)
        textRow.addWidget(self.btnBold)
        textRow.addWidget(self.btnUnderline)
        textRow.addStretch()
        root.addLayout(textRow)

        # ── 画布 ──
        self.canvas = EditCanvas()
        root.addWidget(self.canvas, 1)

        hint = CaptionLabel(LM.tr("editor.hint"))
        hint.setStyleSheet(f"color:{muted};")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # ── 底部按钮 ──
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        bottom.addStretch()
        self.btnReset = PushButton(LM.tr("editor.btn_reset"))
        self.btnReset.setIcon(vector_icon("undo", 16, tm))
        self.btnSave = PrimaryPushButton(LM.tr("editor.btn_save"))
        self.btnSave.setIcon(vector_icon("save", 16, "#ffffff"))
        self.btnReset.setFixedHeight(36)
        self.btnSave.setFixedHeight(36)
        bottom.addWidget(self.btnReset)
        bottom.addWidget(self.btnSave)
        root.addLayout(bottom)

        # ── 信号 ──
        self.btnMove.clicked.connect(lambda: self.canvas.setTool("move"))
        self.btnCrop.clicked.connect(lambda: self.canvas.setTool("crop"))
        self.btnPen.clicked.connect(lambda: self.canvas.setTool("pen"))
        self.btnText.clicked.connect(lambda: self.canvas.setTool("text"))
        self.btnRotate.clicked.connect(self.canvas.rotate90)
        self.btnUndo.clicked.connect(self.canvas.undo)
        self.btnApplyCrop.clicked.connect(self._applyCrop)
        self.btnReset.clicked.connect(self._reset)
        self.btnSave.clicked.connect(self._save)
        self.fontCombo.currentIndexChanged.connect(self._syncTextStyle)
        self.sizeCombo.currentIndexChanged.connect(self._syncTextStyle)
        self.btnBold.toggled.connect(self._syncTextStyle)
        self.btnUnderline.toggled.connect(self._syncTextStyle)
        self._syncTextStyle()

    # ── 对外接口 ──
    def loadImage(self, pixmap, path=""):
        self._sourcePath = path
        self.lblName.setText(os.path.basename(path) if path else LM.tr("editor.no_image"))
        self._original = pixmap.toImage() if pixmap is not None and not pixmap.isNull() else None
        self.canvas.setImage(self._original)
        self.canvas.setTool("move")
        self.btnMove.setChecked(True)

    def _syncTextStyle(self, *args):
        self.canvas.setTextStyle(
            family=self.fontCombo.currentData(),
            size=self.sizeCombo.currentData(),
            bold=self.btnBold.isChecked(),
            underline=self.btnUnderline.isChecked())

    def _pickColor(self, color):
        self.canvas.setPenColor(color)
        if not self.btnPen.isChecked() and not self.btnText.isChecked():
            self.btnPen.setChecked(True)
            self.canvas.setTool("pen")

    def _applyCrop(self):
        if not self.canvas.applyCrop():
            _notify_warn(self, LM.tr("editor.title"), LM.tr("editor.no_image"))

    def _reset(self):
        if self._original is not None:
            self.canvas.setImage(self._original)
            self.canvas.setTool("move")
            self.btnMove.setChecked(True)

    def _save(self):
        self.canvas._finishTextEntry(True)
        img = self.canvas.image()
        if img is None:
            _notify_warn(self, LM.tr("editor.no_image_title"), LM.tr("editor.no_image"))
            return
        try:
            save_dir = os.path.join(os.environ.get('APPDATA', '.'), 'FluentView', 'edited')
            os.makedirs(save_dir, exist_ok=True)
            dest = os.path.join(save_dir, "edited_" + time.strftime("%Y%m%d_%H%M%S") + ".png")
            if not img.save(dest, "PNG"):
                raise IOError("save failed")
        except Exception:
            _notify_err(self, LM.tr("export.error_title"), LM.tr("export.error_msg"))
            return
        self.saved.emit(dest, QPixmap.fromImage(img))


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
                pm = pm.scaled(THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.loaded.emit(p, pm)
    def stop(self):
        self._stop = True


class GalleryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("galleryPage")
        self.setStyleSheet("background:transparent;")
        self._paths = []
        self._current = ""
        self._loader = None
        self._fullCallback = None
        self.btnOpen = PrimaryPushButton(LM.tr("gallery.btn_add_files"))
        self.btnOpenFolder = PushButton(LM.tr("gallery.btn_add_folder"))
        self.btnClear = PushButton(LM.tr("gallery.btn_clear"))
        self.btnEdit = PushButton(LM.tr("gallery.btn_edit"))
        self.btnEdit.setIcon(vector_icon("edit", 16))
        self.btnEdit.setToolTip(LM.tr("gallery.tooltip_edit"))
        self.btnRotate = PushButton(LM.tr("gallery.btn_rotate"))
        self.btnZoomIn = PushButton(LM.tr("gallery.btn_zoom_in"))
        self.btnZoomOut = PushButton(LM.tr("gallery.btn_zoom_out"))
        self.btnFit = PushButton(LM.tr("gallery.btn_fit_screen"))
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(14, 10, 14, 6)
        toolbar.setSpacing(8)
        for b in (self.btnOpen, self.btnOpenFolder, self.btnClear, self.btnEdit,
                  self.btnRotate, self.btnZoomIn, self.btnZoomOut, self.btnFit):
            toolbar.addWidget(b)
        toolbar.addStretch()
        self.lblCount = CaptionLabel(LM.tr("gallery.count", n=0))
        toolbar.addWidget(self.lblCount)
        self.gridWidget = QWidget()
        self.gridWidget.setStyleSheet("background:transparent;")
        self.gridLayout = QGridLayout(self.gridWidget)
        self.gridLayout.setContentsMargins(14, 14, 14, 14)
        self.gridLayout.setSpacing(8)
        gs = QScrollArea()
        gs.setWidgetResizable(True)
        gs.setFrameShape(QFrame.NoFrame)
        gs.setStyleSheet("QScrollArea{background:transparent;}QScrollArea>QWidget>QWidget{background:transparent;}")
        gs.setWidget(self.gridWidget)
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
        vw = QWidget()
        vl = QVBoxLayout(vw)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)
        vl.addWidget(self.viewer, 1)
        vl.addWidget(bar, 0)
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:transparent;")
        self.stack.addWidget(gs)
        self.stack.addWidget(vw)
        self.stack.setCurrentIndex(0)
        ml = QVBoxLayout(self)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)
        ml.addLayout(toolbar)
        ml.addWidget(self.stack)
        self.btnBack.clicked.connect(lambda: self.stack.setCurrentIndex(0))
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
            _notify_warn(self, LM.tr("gallery.empty_folder"), LM.tr("gallery.no_images_found"))
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
        cols = max(1, (self.gridWidget.width() - 28) // (THUMB_SIZE + 20))
        for i, path in enumerate(self._paths):
            pm = load_pixmap(path, THUMB_SIZE)
            if pm.isNull():
                continue
            pm = pm.scaled(THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
                c = item.widget()
                if c.path == path:
                    c.pix = pix
                    c.update()
                    break

    def _stopLoader(self):
        if self._loader and self._loader.isRunning():
            self._loader.stop()
            self._loader.wait(2000)
            self._loader = None

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
            self.lblPhotoInfo.setText(LM.tr("gallery.photo_info", w=w, h=h, size=_format_size(fs)))
        else:
            self.lblPhotoInfo.setText("")

    def _prev(self):
        if self._current and self._paths:
            idx = self._paths.index(self._current) - 1
            if idx >= 0:
                self._viewImage(self._paths[idx])

    def _next(self):
        if self._current and self._paths:
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


class ExportThumbCard(QWidget):
    """图片导出列表中的缩略图卡片"""
    clicked = pyqtSignal(int)

    def __init__(self, idx, pixmap, name, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.pix = pixmap
        self.name = name
        self.selected = False
        self.setFixedSize(72, 72)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(name)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self.selected:
            p.setBrush(QColor(0, 184, 148, 45))
            p.setPen(QPen(QColor(0, 184, 148), 2))
        else:
            p.setBrush(QColor(255, 255, 255, 16) if isDarkTheme() else QColor(0, 0, 0, 12))
            p.setPen(QPen(QColor(150, 150, 150, 90), 1))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)
        if self.pix and not self.pix.isNull():
            s = self.pix.scaled(w - 12, h - 12, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((w - s.width()) // 2, (h - s.height()) // 2, s)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.idx)


class ExportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("exportPage")
        self.setStyleSheet("background:transparent;")
        self._items = []          # [{'kind','path','pixmap','name'}]
        self._selected = -1
        self._previewPixmap = None
        self._sourcePath = ""
        l = QVBoxLayout(self)
        l.setContentsMargins(24, 24, 24, 24)
        l.setSpacing(12)
        l.addWidget(TitleLabel(LM.tr("export.title")))
        l.addWidget(BodyLabel(LM.tr("export.desc")))
        self.preview = QLabel(LM.tr("export.no_image_hint"))
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(300)
        self.preview.setFrameShape(QFrame.StyledPanel)
        self.preview.setStyleSheet(
            "QLabel{border:2px dashed rgba(150,150,150,0.5);border-radius:8px;"
            "color:rgba(150,150,150,0.8);font-size:14px;background:transparent;}")
        l.addWidget(self.preview)
        self.lblFile = CaptionLabel("")
        l.addWidget(self.lblFile)
        # ── 可导出图片（含编辑结果）──
        listTitle = StrongBodyLabel(LM.tr("export.list_title"))
        l.addWidget(listTitle)
        self.listWidget = QWidget()
        self.listWidget.setStyleSheet("background:transparent;")
        self.listLayout = QHBoxLayout(self.listWidget)
        self.listLayout.setContentsMargins(2, 2, 2, 2)
        self.listLayout.setSpacing(8)
        self.listLayout.addStretch()
        ls = QScrollArea()
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setFixedHeight(92)
        ls.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        ls.setWidget(self.listWidget)
        l.addWidget(ls)
        self.lblListEmpty = CaptionLabel(LM.tr("export.list_empty"))
        self.lblListEmpty.setStyleSheet("color:rgba(150,150,150,0.9);")
        l.addWidget(self.lblListEmpty)
        self.lblListEmpty.setVisible(True)
        br = QHBoxLayout()
        self.btnRefresh = PushButton(LM.tr("export.btn_refresh"))
        self.btnExport = PrimaryPushButton(LM.tr("export.btn_save"))
        br.addWidget(self.btnRefresh)
        br.addWidget(self.btnExport)
        br.addStretch()
        l.addLayout(br)
        l.addStretch()
        self.btnRefresh.clicked.connect(self._refreshPreview)
        self.btnExport.clicked.connect(self._doExport)

    # ── 数据接口 ──
    def setSource(self, path, pixmap):
        """来自图片浏览的当前图片（保持单项占位，不堆叠）"""
        if not path or pixmap is None or pixmap.isNull():
            return
        if self._items and self._items[0].get('kind') == 'current':
            self._items[0].update({'path': path, 'pixmap': pixmap, 'name': os.path.basename(path)})
            if self._selected <= 0:
                self._selected = 0
                self._sourcePath = path
                self._previewPixmap = pixmap
            self._refreshPreview()
            self._syncThumbs()
        else:
            self._items.insert(0, {'kind': 'current', 'path': path, 'pixmap': pixmap,
                                   'name': os.path.basename(path)})
            self._selected = 0
            self._sourcePath = path
            self._previewPixmap = pixmap
            self._rebuildList()
            self._refreshPreview()

    def addEditedImage(self, path, pixmap):
        """编辑器保存后，把成品加载进图片导出列表"""
        self._items.append({'kind': 'edited', 'path': path, 'pixmap': pixmap,
                            'name': os.path.basename(path)})
        self._selected = len(self._items) - 1
        self._sourcePath = path
        self._previewPixmap = pixmap
        self._rebuildList()
        self._refreshPreview()

    def _selectItem(self, idx):
        if 0 <= idx < len(self._items):
            it = self._items[idx]
            self._selected = idx
            self._sourcePath = it['path']
            self._previewPixmap = it['pixmap']
            self._refreshPreview()
            self._syncThumbs()

    def _rebuildList(self):
        while self.listLayout.count():
            item = self.listLayout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        for i, it in enumerate(self._items):
            card = ExportThumbCard(i, it['pixmap'], it['name'])
            card.selected = (i == self._selected)
            card.clicked.connect(self._selectItem)
            self.listLayout.addWidget(card)
        self.listLayout.addStretch()
        self.lblListEmpty.setVisible(not self._items)

    def _syncThumbs(self):
        for i in range(self.listLayout.count()):
            w = self.listLayout.itemAt(i).widget()
            if isinstance(w, ExportThumbCard):
                w.selected = (w.idx == self._selected)
                w.update()

    def _refreshPreview(self):
        if self._previewPixmap and not self._previewPixmap.isNull():
            s = self._previewPixmap.scaled(
                self.preview.width() - 20, self.preview.height() - 20,
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview.setPixmap(s)
            self.lblFile.setText(os.path.basename(self._sourcePath))
        else:
            self.preview.setText(LM.tr("export.no_image_hint"))
            self.lblFile.setText("")

    def _doExport(self):
        if not self._sourcePath or not self._previewPixmap:
            _notify_warn(self, LM.tr("export.no_image_title"), LM.tr("export.no_image_msg"))
            return
        name = os.path.basename(self._sourcePath)
        dest, _ = QFileDialog.getSaveFileName(
            self, LM.tr("export.save_dialog"),
            os.path.join(os.path.expanduser("~"), "Desktop", name),
            LM.tr("file_dialog.image_filter_export"))
        if dest:
            if self._previewPixmap.save(dest):
                _notify_ok(self, LM.tr("export.success_title"), LM.tr("export.success_msg", dest=dest))
            else:
                _notify_err(self, LM.tr("export.error_title"), LM.tr("export.error_msg"))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refreshPreview()


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.setStyleSheet("background:transparent;")
        dark = isDarkTheme()
        tm = "#e8e6e3" if dark else "#1a1a1a"
        muted = "#8a8a9a" if dark else "#666666"
        sbg = "rgba(255,255,255,0.04)" if dark else "rgba(0,0,0,0.03)"
        sbd = "rgba(255,255,255,0.06)" if dark else "rgba(0,0,0,0.06)"
        # SettingsPage 本身可滚动
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        layout.addWidget(TitleLabel(LM.tr("settings.title")))

        self.themeCard = SwitchSettingCard(FluentIcon.BRIGHTNESS, LM.tr("settings.dark_mode"), LM.tr("settings.dark_mode_desc"))
        cfg = _load_config()
        sd = cfg.get('dark_mode', isDarkTheme())
        self.themeCard.setChecked(sd)
        setTheme(Theme.DARK if sd else Theme.LIGHT)
        self.themeCard.checkedChanged.connect(self._onThemeChanged)
        g1 = SettingCardGroup(LM.tr("settings.appearance"))
        g1.addSettingCard(self.themeCard)
        layout.addWidget(g1)

        self.formatCard = FormatSelectorCard()
        g2 = SettingCardGroup(LM.tr("settings.file_assoc"))
        g2.addSettingCard(self.formatCard)
        layout.addWidget(g2)

        lang_items = [(LM.langName(l), l) for l in LM.availableLangs()]
        lcw = QWidget()
        lcw.setFixedHeight(60)
        lcw.setStyleSheet(f"QWidget{{background:{sbg};border:1px solid {sbd};border-radius:10px;}}")
        ll = QHBoxLayout(lcw)
        ll.setContentsMargins(18, 0, 18, 0)
        ll.setSpacing(16)
        il = QLabel()
        il.setFixedSize(32, 32)
        il.setAlignment(Qt.AlignCenter)
        il.setStyleSheet("background:transparent;border:none;")
        il.setPixmap(vector_pixmap("globe", 22, tm))
        ll.addWidget(il)
        tw = QWidget()
        tw.setStyleSheet("background:transparent;border:none;")
        tl = QVBoxLayout(tw)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)
        t = StrongBodyLabel(LM.tr("settings.language_card_title"))
        t.setStyleSheet(f"background:transparent;border:none;font-weight:bold;color:{tm};")
        d = CaptionLabel(LM.tr("settings.language_desc"))
        d.setStyleSheet(f"background:transparent;border:none;color:{muted};")
        tl.addWidget(t)
        tl.addWidget(d)
        ll.addWidget(tw, 1)
        self.langCombo = ComboBox()
        for text, data in lang_items:
            self.langCombo.addItem(text, userData=data)
        idx = self.langCombo.findData(LM.current_lang)
        if idx >= 0:
            self.langCombo.setCurrentIndex(idx)
        self.langCombo.setFixedWidth(160)
        self.langCombo.currentIndexChanged.connect(self._onLanguageChanged)
        ll.addWidget(self.langCombo)
        g3 = SettingCardGroup(LM.tr("settings.language"))
        g3.addSettingCard(lcw)
        layout.addWidget(g3)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _onThemeChanged(self, checked):
        setTheme(Theme.DARK if checked else Theme.LIGHT)
        cfg = _load_config()
        cfg['dark_mode'] = checked
        _save_config(cfg)

    def _onLanguageChanged(self, index):
        lc = self.langCombo.currentData()
        if lc and lc != LM.current_lang:
            LM.saveLang(lc)
            _restartApp()


class UpdateChecker(QThread):
    """后台检查 GitHub Releases 是否有新版本"""
    checked = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self):
        rels = []
        # 1) GitHub API
        try:
            r = requests.get(
                GITHUB_API_RELEASES,
                headers={"User-Agent": "FluentView", "Accept": "application/vnd.github+json"},
                timeout=15)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict) or item.get('draft'):
                        continue
                    rels.append({
                        'tag': item.get('tag_name', '') or item.get('name', ''),
                        'name': item.get('name', ''),
                        'url': item.get('html_url', GITHUB_RELEASES_URL),
                    })
        except Exception:
            rels = []
        # 2) 回退：抓取 Releases 页面
        if not rels:
            try:
                r = requests.get(GITHUB_RELEASES_URL, headers=WH, timeout=15)
                r.raise_for_status()
                tags = []
                for t in re.findall(r'/minecraft-os/FluentView/releases/tag/([^"\'<>\s]+)', r.text):
                    if t not in tags:
                        tags.append(t)
                if not tags:
                    raise RuntimeError("no release found")
                rels = [{'tag': t, 'name': t,
                         'url': GITHUB_RELEASES_URL + "/tag/" + t} for t in tags]
            except Exception as e:
                self.failed.emit(str(e))
                return
        self.checked.emit(rels)


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutPage")
        self.setStyleSheet("background:transparent;")
        self._checker = None
        l = QVBoxLayout(self)
        l.setContentsMargins(24, 24, 24, 24)
        l.setSpacing(16)
        l.addWidget(TitleLabel(LM.tr("about.title")))
        l.addWidget(BodyLabel(LM.tr("about.description")))
        verRow = QHBoxLayout()
        self.lblVersion = CaptionLabel(LM.tr("about.current_version", ver=APP_VERSION))
        self.lblVersion.setStyleSheet("font-size:12px;")
        verRow.addWidget(self.lblVersion)
        verRow.addStretch()
        l.addLayout(verRow)
        l.addSpacing(10)
        l.addWidget(SubtitleLabel(LM.tr("about.author_title")))
        for name, url in [("SYSTEM-WINOS-RE", ""), ("4795_Tester", ""), ("Xiaomi MiMo AI", "")]:
            if url:
                label = HyperlinkLabel(url, name)
            else:
                label = BodyLabel(name)
                label.setStyleSheet("font-size:14px;")
            l.addWidget(label)
        l.addSpacing(10)
        gb = PushButton(LM.tr("about.github_link"))
        gb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL)))
        l.addWidget(gb)
        # ── 自动更新 ──
        self.btnUpdate = PrimaryPushButton(LM.tr("about.btn_update"))
        self.btnUpdate.setIcon(vector_icon("sync", 16, "#ffffff"))
        self.btnUpdate.setFixedHeight(36)
        self.btnUpdate.clicked.connect(self.checkUpdate)
        l.addWidget(self.btnUpdate)
        l.addStretch()

    def checkUpdate(self):
        if self._checker is not None and self._checker.isRunning():
            return
        self.btnUpdate.setEnabled(False)
        self.btnUpdate.setText(LM.tr("about.update_checking"))
        self._checker = UpdateChecker()
        self._checker.checked.connect(self._onChecked)
        self._checker.failed.connect(self._onFailed)
        self._checker.finished.connect(lambda: self.btnUpdate.setEnabled(True))
        self._checker.start()

    def _onChecked(self, rels):
        self.btnUpdate.setText(LM.tr("about.btn_update"))
        if not rels:
            _notify_err(self, LM.tr("about.update_error"), LM.tr("about.update_error_msg"))
            return
        # 选取版本号最高的发布（而非创建时间最新，避免漏掉主版本升级）
        latest = max(rels, key=lambda r: _version_tuple(r.get('tag') or r.get('name') or ''))
        tag = latest.get('tag') or latest.get('name') or ''
        url = latest.get('url') or GITHUB_RELEASES_URL
        if _version_tuple(tag) > _version_tuple(APP_VERSION):
            box = MessageBox(LM.tr("about.update_found_title"),
                             LM.tr("about.update_found_msg", tag=tag), self.window())
            box.yesButton.setText(LM.tr("about.btn_open_release"))
            box.cancelButton.setText(LM.tr("about.btn_cancel"))
            box.yesButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            box.exec_()
        else:
            _notify_ok(self, LM.tr("about.update_latest"),
                       LM.tr("about.update_latest_msg", ver=APP_VERSION))

    def _onFailed(self, msg):
        self.btnUpdate.setText(LM.tr("about.btn_update"))
        _notify_err(self, LM.tr("about.update_error"), LM.tr("about.update_error_msg"))


WALLPAPER_BASE = "https://zhutix.com/wallpaper/"
WH = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

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
            r = requests.get(url, headers=WH, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            for item in soup.select('li.post-list-item'):
                if self._stop:
                    return
                img = item.select_one('img.post-thumb')
                le = item.select_one('a.thumb-link')
                te = item.select_one('.ycfm .imglist-char')
                if not img or not le:
                    continue
                tu = img.get('src') or img.get('data-src', '')
                if not tu:
                    continue
                du = le.get('href', '')
                tt = te.get_text(strip=True) if te else ''
                try:
                    tr = requests.get(tu, headers=WH, timeout=10)
                    qi = QImage()
                    qi.loadFromData(tr.content)
                    px = QPixmap.fromImage(qi)
                except:
                    px = QPixmap()
                self.itemLoaded.emit(tt, du, tu, px)
            self.loadDone.emit(bool(soup.select_one('a.next.page-numbers')))
        except Exception as e:
            self.loadError.emit(str(e))
    def stop(self):
        self._stop = True

class _DW(QThread):
    finished = pyqtSignal(bool)
    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest
    def run(self):
        try:
            r = requests.get(self.url, headers=WH, timeout=30, stream=True)
            r.raise_for_status()
            with open(self.dest, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            self.finished.emit(True)
        except:
            self.finished.emit(False)

class _DPW(QThread):
    done = pyqtSignal(list)
    def __init__(self, du):
        super().__init__()
        self.detail_url = du
    def run(self):
        try:
            r = requests.get(self.detail_url, headers=WH, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            urls = []
            for img in soup.select('img'):
                src = img.get('src', '')
                if 'b.zhutix.com' in src:
                    c = src.split('?')[0]
                    if c not in urls:
                        urls.append(c)
            self.done.emit(urls)
        except:
            self.done.emit([])

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
        self._bb = TransparentToolButton(FluentIcon.GLOBE)
        self._bb.setFixedSize(24, 24)
        self._bb.setToolTip(LM.tr("wallpaper.tooltip_browser"))
        self._bs = TransparentToolButton(FluentIcon.SAVE)
        self._bs.setFixedSize(24, 24)
        self._bs.setToolTip(LM.tr("wallpaper.tooltip_save_as"))
        self._ba = TransparentToolButton(FluentIcon.ADD)
        self._ba.setFixedSize(24, 24)
        self._ba.setToolTip(LM.tr("wallpaper.tooltip_add_gallery"))
        bl.addWidget(self._bb)
        bl.addWidget(self._bs)
        bl.addWidget(self._ba)
        self._bb.clicked.connect(lambda: self.actionOpen.emit(self._detailUrl))
        self._bs.clicked.connect(lambda: self.actionSave.emit(self._title, self._detailUrl))
        self._ba.clicked.connect(lambda: self.actionAddToGallery.emit(self._title, self._detailUrl))
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
            s = self._pixmap.scaled(THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((w - s.width()) // 2, 2, s)
        name = self._title if len(self._title) <= 22 else self._title[:19] + "..."
        p.setPen(QColor(60, 60, 60) if not isDarkTheme() else QColor(200, 200, 200))
        p.setFont(QFont("Microsoft YaHei", 8))
        p.drawText(QRect(0, THUMB_SIZE + 4, w, 20), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, name)
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

class WallpaperPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("wallpaperPage")
        self.setStyleSheet("background:transparent;")
        self._page = 1
        self._hasMore = True
        self._loading = False
        self._loader = None
        self._wallpapers = []
        self.btnRefresh = PushButton(LM.tr("wallpaper.btn_refresh"))
        self.btnLoadMore = PushButton(LM.tr("wallpaper.btn_load_more"))
        self.lblStatus = CaptionLabel(LM.tr("wallpaper.source_label", url="zhutix.com"))
        tb = QHBoxLayout()
        tb.setContentsMargins(14, 10, 14, 6)
        tb.setSpacing(8)
        tb.addWidget(self.btnRefresh)
        tb.addWidget(self.btnLoadMore)
        tb.addStretch()
        tb.addWidget(self.lblStatus)
        self.gridWidget = QWidget()
        self.gridWidget.setStyleSheet("background:transparent;")
        self.gridLayout = QGridLayout(self.gridWidget)
        self.gridLayout.setContentsMargins(14, 14, 14, 14)
        self.gridLayout.setSpacing(8)
        gs = QScrollArea()
        gs.setWidgetResizable(True)
        gs.setFrameShape(QFrame.NoFrame)
        gs.setStyleSheet("QScrollArea{background:transparent;}QScrollArea>QWidget>QWidget{background:transparent;}")
        gs.setWidget(self.gridWidget)
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
        l.addLayout(tb)
        l.addWidget(gs)
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

    def _onItem(self, t, du, tu, px):
        self._wallpapers.append((t, du, tu, px))
        self._addCard(t, du, tu, px)

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
        _notify_err(self, LM.tr("wallpaper.error_prefix", msg=msg))

    def _addCard(self, t, du, tu, px):
        cols = max(1, (self.gridWidget.width() - 28) // (THUMB_SIZE + 20))
        cnt = self.gridLayout.count()
        r, c = divmod(cnt, cols)
        card = WallpaperCard(t, tu, px)
        card.setDetailUrl(du)
        card.clicked.connect(lambda *a, u=du: __import__('webbrowser').open(u))
        card.actionOpen.connect(lambda u: __import__('webbrowser').open(u))
        card.actionSave.connect(self._saveAs)
        card.actionAddToGallery.connect(self._addToGallery)
        self.gridLayout.addWidget(card, r, c)

    def _saveAs(self, t, du):
        self.lblStatus.setText(LM.tr("wallpaper.getting_original"))
        self._dpw = _DPW(du)
        self._dpw.done.connect(lambda urls: self._doSaveAs(t, urls))
        self._dpw.start()

    def _doSaveAs(self, t, urls):
        if not urls:
            _notify_err(self, LM.tr("wallpaper.get_failed"), LM.tr("wallpaper.get_failed_msg"))
            self.lblStatus.setText("")
            return
        u = urls[0]
        ext = os.path.splitext(u.split('?')[0])[1] or '.jpg'
        dn = (t or "wallpaper").replace('/', '_').replace('\\', '_') + ext
        dest, _ = QFileDialog.getSaveFileName(
            self, LM.tr("wallpaper.save_dialog"),
            os.path.join(os.path.expanduser("~"), "Desktop", dn),
            f"图片文件 (*{ext});;所有文件 (*)")
        if not dest:
            self.lblStatus.setText("")
            return
        self.lblStatus.setText(LM.tr("wallpaper.downloading"))
        self._dl = _DW(u, dest)
        self._dl.finished.connect(lambda ok, d=dest: self._onSaveDone(ok, d))
        self._dl.start()

    def _onSaveDone(self, ok, path):
        if ok:
            _notify_ok(self, LM.tr("wallpaper.save_success"), LM.tr("wallpaper.save_success_msg", path=path))
            self.lblStatus.setText(LM.tr("wallpaper.download_complete"))
        else:
            _notify_err(self, LM.tr("wallpaper.save_failed"), LM.tr("wallpaper.save_failed_msg"))
            self.lblStatus.setText(LM.tr("wallpaper.download_failed"))

    def _addToGallery(self, t, du):
        self.lblStatus.setText(LM.tr("wallpaper.getting_original"))
        self._dpw2 = _DPW(du)
        self._dpw2.done.connect(lambda urls: self._doAdd(t, urls))
        self._dpw2.start()

    def _doAdd(self, t, urls):
        if not urls:
            _notify_err(self, LM.tr("wallpaper.get_failed"), LM.tr("wallpaper.get_failed_msg"))
            self.lblStatus.setText("")
            return
        u = urls[0]
        sd = os.path.join(os.environ.get('APPDATA', '.'), 'FluentView', 'wallpapers')
        os.makedirs(sd, exist_ok=True)
        ext = os.path.splitext(u.split('?')[0])[1] or '.jpg'
        fn = (t or "wallpaper").replace('/', '_').replace('\\', '_') + ext
        dest = os.path.join(sd, fn)
        if os.path.exists(dest):
            self._addFile(dest)
            return
        self.lblStatus.setText(LM.tr("wallpaper.downloading"))
        self._dl2 = _DW(u, dest)
        self._dl2.finished.connect(lambda ok, d=dest: self._onAddDone(ok, d))
        self._dl2.start()

    def _onAddDone(self, ok, path):
        if ok:
            self._addFile(path)
        else:
            _notify_err(self, LM.tr("wallpaper.save_failed"), LM.tr("wallpaper.save_failed_msg"))

    def _addFile(self, path):
        w = self.window()
        if hasattr(w, 'galleryPage'):
            w.galleryPage.addFiles([path])
        _notify_ok(self, LM.tr("wallpaper.add_success"), LM.tr("wallpaper.add_success_msg"))
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
        cols = max(1, (self.gridWidget.width() - 28) // (THUMB_SIZE + 20))
        for i, (t, du, tu, px) in enumerate(self._wallpapers):
            card = WallpaperCard(t, tu, px)
            card.setDetailUrl(du)
            card.clicked.connect(lambda *a, u=du: __import__('webbrowser').open(u))
            card.actionOpen.connect(lambda u: __import__('webbrowser').open(u))
            card.actionSave.connect(self._saveAs)
            card.actionAddToGallery.connect(self._addToGallery)
            r, c = divmod(i, cols)
            self.gridLayout.addWidget(card, r, c)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(LM.tr("app.title"))
        self.resize(1280, 720)
        self.setMinimumSize(960, 640)
        scr = QApplication.primaryScreen().geometry()
        self.move((scr.width() - self.width()) // 2, (scr.height() - self.height()) // 2)
        self.galleryPage = GalleryPage()
        self.editPage = EditPage()
        self.exportPage = ExportPage()
        self.wallpaperPage = WallpaperPage()
        self.settingsPage = SettingsPage()
        self.aboutPage = AboutPage()
        self.addSubInterface(self.galleryPage, FluentIcon.PHOTO, LM.tr("navigation.gallery"), position=NavigationItemPosition.TOP)
        self.addSubInterface(self.editPage, vector_icon("edit", 20), LM.tr("navigation.edit"), position=NavigationItemPosition.TOP)
        self.addSubInterface(self.wallpaperPage, FluentIcon.PALETTE, LM.tr("navigation.wallpaper"), position=NavigationItemPosition.TOP)
        self.addSubInterface(self.exportPage, FluentIcon.SAVE, LM.tr("navigation.export_nav"), position=NavigationItemPosition.TOP)
        self.navigationInterface.addSeparator(NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settingsPage, FluentIcon.SETTING, LM.tr("navigation.settings"), position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.aboutPage, FluentIcon.INFO, LM.tr("navigation.about"), position=NavigationItemPosition.BOTTOM)
        gp = self.galleryPage
        gp.btnOpen.clicked.connect(self._openFiles)
        gp.btnOpenFolder.clicked.connect(self._openFolder)
        gp.btnClear.clicked.connect(self._clearGallery)
        gp.btnEdit.clicked.connect(self._editImage)
        gp.btnRotate.clicked.connect(lambda: gp.viewer.rotateCW())
        gp.btnZoomIn.clicked.connect(lambda: gp.viewer.zoomIn())
        gp.btnZoomOut.clicked.connect(lambda: gp.viewer.zoomOut())
        gp.btnFit.clicked.connect(lambda: gp.viewer.fitToWindow())
        gp.btnFull.clicked.connect(self._toggleFull)
        gp._fullCallback = self._toggleFull
        gp.viewer.zoomChanged.connect(self._syncExport)
        self.editPage.saved.connect(self._onImageEdited)
        saved = _load_image_paths()
        if saved:
            self.galleryPage.addFiles(saved)

    def openFiles(self, paths):
        self.galleryPage.addFiles(paths)
        if paths:
            self.switchTo(self.galleryPage)

    def _openFiles(self):
        files, _ = QFileDialog.getOpenFileNames(self, LM.tr("file_dialog.select_images"), "", IMAGE_FILTER_STR())
        if files:
            self.galleryPage.addFiles(files)

    def _openFolder(self):
        d = QFileDialog.getExistingDirectory(self, LM.tr("file_dialog.select_folder"))
        if d:
            self.galleryPage.loadFolder(d)

    def _clearGallery(self):
        self.galleryPage.clearGallery()
        _save_image_paths([])
        _notify_ok(self.galleryPage, LM.tr("gallery.cleared_title"), LM.tr("gallery.cleared_msg"))

    def _toggleFull(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _editImage(self):
        gp = self.galleryPage
        if not gp._current or gp.viewer._orig is None:
            _notify_warn(gp, LM.tr("editor.no_image_title"), LM.tr("editor.no_image"))
            return
        pm = gp.viewer.getRotatedPixmap()
        self.editPage.loadImage(pm, gp._current)
        self.switchTo(self.editPage)

    def _onImageEdited(self, path, pixmap):
        # 编辑好的图片加载到“图片导出”分类
        self.exportPage.addEditedImage(path, pixmap)
        # WinUI3 原生风格弹窗提示
        box = MessageBox(LM.tr("editor.save_ok_title"), LM.tr("editor.save_ok_msg"), self)
        box.yesButton.setText(LM.tr("editor.btn_ok"))
        box.cancelButton.setVisible(False)
        box.exec_()
        self.switchTo(self.exportPage)

    def _syncExport(self):
        path, pix = self.galleryPage.getCurrentImage()
        if path:
            self.exportPage.setSource(path, pix)

    def closeEvent(self, e):
        self.galleryPage._stopLoader()
        super().closeEvent(e)


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    LM.init()
    cfg = _load_config()
    setTheme(Theme.DARK if cfg.get('dark_mode') else Theme.LIGHT)
    is_first = not cfg.get('first_run_done', False)
    window = MainWindow()
    args = [a for a in sys.argv[1:] if os.path.isfile(a) and os.path.splitext(a)[1].lower() in IMAGE_EXTS]
    if args:
        window.openFiles(args)
    window.show()
    if is_first:
        QTimer.singleShot(300, lambda: FirstRunWizard(window).exec_())
    sys.exit(app.exec_())