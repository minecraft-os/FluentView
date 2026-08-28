# Fluent Photo Viewer

基于 PyQt5 + PyQt-Fluent-Widgets 的现代风格照片查看器。

## 截图

> 程序启动后可看到 Fluent 风格的导航栏、缩略图网格、图片查看器等界面。

## 功能

### 图片浏览
- **添加文件** — 支持多选打开 JPG / PNG / BMP / GIF 图片
- **添加文件夹** — 打开文件夹自动扫描所有支持格式的图片
- **缩略图网格** — 自适应列数，窗口缩放时自动重新排列
- **图片查看** — 点击缩略图进入全尺寸查看模式
- **上一张 / 下一张** — 键盘 ← → 或底部按钮切换
- **缩放** — 放大 / 缩小 / 适配屏幕，鼠标滚轮也可缩放
- **旋转** — 每次顺时针旋转 90°
- **全屏预览** — 按 F 键或点击全屏按钮
- **返回缩略图** — 查看模式下点击返回按钮回到网格
- **照片信息** — 底部栏显示文件名、分辨率、文件大小
- **填充** — 生成 16 张彩色示例图片用于演示

### 导出
- 预览当前选中图片
- 选择保存位置，导出为 JPG / PNG / BMP

### 设置
- 深色 / 浅色主题切换（Fluent 风格设置卡片）

### 关于
- 作者信息：SYSTEM-WINOS-RE、4795_Tester、Xiaomi MiMo AI

## 键盘快捷键

| 按键 | 功能 |
|------|------|
| `←` | 上一张 |
| `→` | 下一张 |
| `+` / `=` | 放大 |
| `-` | 缩小 |
| `0` | 适配屏幕 |
| `R` | 旋转 90° |
| `F` | 全屏切换 |
| `Esc` | 退出全屏 |
| `Ctrl+S` | 导出图片 |

## 文件关联

支持命令行直接打开图片：

```bash
python photo_viewer.py image.jpg
python photo_viewer.py img1.png img2.jpg
```

## 运行环境

- Python 3.8+
- PyQt5
- PyQt-Fluent-Widgets

## 安装依赖

```bash
pip install PyQt5 PyQt-Fluent-Widgets
```

## 启动

```bash
python photo_viewer.py
```

## 作者

- **SYSTEM-WINOS-RE**
- **4795_Tester**
- **Xiaomi MiMo AI**
