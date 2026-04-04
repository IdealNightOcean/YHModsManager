"""
生成应用图标脚本
将 PNG 图标转换为各平台所需的图标格式
- Windows: .ico
- macOS: .icns (需要 sips 和 iconutil 工具)
"""

import os
import platform
import sys


def create_ico_from_png():
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap, QIcon

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    png_path = os.path.join(project_root, 'icons', 'app_icon.png')
    ico_path = os.path.join(project_root, 'icons', 'app_icon.ico')
    
    if not os.path.exists(png_path):
        print(f"Error: PNG file not found: {png_path}")
        return False
    
    source_pixmap = QPixmap(png_path)
    if source_pixmap.isNull():
        print(f"Error: Failed to load PNG file: {png_path}")
        return False
    
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icon = QIcon()
    
    for size in sizes:
        if source_pixmap.width() >= size:
            scaled_pixmap = source_pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            icon.addPixmap(scaled_pixmap)
    
    if icon.pixmap(256).save(ico_path, 'ICO'):
        print(f"Successfully created Windows ICO with multiple sizes: {ico_path}")
        print(f"  Included sizes: {[s for s in sizes if source_pixmap.width() >= s]}")
        return True
    else:
        print(f"Error: Failed to save ICO file: {ico_path}")
        return False


def create_icns_from_png():
    """macOS: 使用 sips 和 iconutil 创建 .icns 文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    png_path = os.path.join(project_root, 'icons', 'app_icon.png')
    icns_path = os.path.join(project_root, 'icons', 'app_icon.icns')
    
    if not os.path.exists(png_path):
        print(f"Error: PNG file not found: {png_path}")
        return False
    
    iconset_dir = os.path.join(project_root, 'icons', 'app_icon.iconset')
    os.makedirs(iconset_dir, exist_ok=True)
    
    sizes = [16, 32, 128, 256, 512]
    
    import subprocess
    
    for size in sizes:
        output_file = os.path.join(iconset_dir, f'icon_{size}x{size}.png')
        subprocess.run(['sips', '-z', str(size), str(size), png_path, '--out', output_file], capture_output=True)
        
        output_file_2x = os.path.join(iconset_dir, f'icon_{size}x{size}@2x.png')
        subprocess.run(['sips', '-z', str(size * 2), str(size * 2), png_path, '--out', output_file_2x], capture_output=True)
    
    result = subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', icns_path], capture_output=True)
    
    import shutil
    shutil.rmtree(iconset_dir)
    
    if result.returncode == 0:
        print(f"Successfully created macOS ICNS: {icns_path}")
        return True
    else:
        print(f"Error: Failed to create ICNS file")
        return False


def main():
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    system = platform.system()
    
    print(f"Creating icons for platform: {system}")

    if system == 'Windows':
        ico_success = create_ico_from_png()
    elif system == 'Darwin':
        ico_success = create_icns_from_png()
    else:
        print("Linux platform: PNG icon will be used directly")
        ico_success = True
    
    return ico_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
