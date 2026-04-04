"""
打包脚本 - 将主程序打包为自包含的一键程序
使用方法: python build.py
"""

import os
import shutil
import subprocess
import sys


def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name, ignore_errors=True)


def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("错误: PyInstaller 未安装")
        print("请运行: pip install pyinstaller")
        return False


def ensure_icon_exists():
    """确保图标文件存在"""
    icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'app_icon.ico')
    if os.path.exists(icon_path):
        print(f"图标文件已存在: {icon_path}")
        return True
    
    print("图标文件不存在，正在生成...")
    create_icon_script = os.path.join(os.path.dirname(__file__), 'scripts', 'create_icon.py')
    if os.path.exists(create_icon_script):
        result = subprocess.run([sys.executable, create_icon_script], capture_output=True)
        if result.returncode == 0:
            print("图标生成成功")
            return True
        else:
            print(f"图标生成失败: {result.stderr.decode()}")
            return False
    else:
        print(f"错误: 找不到图标生成脚本 {create_icon_script}")
        return False


def build():
    """执行打包"""
    if not check_pyinstaller():
        sys.exit(1)

    if not ensure_icon_exists():
        print("警告: 图标文件不存在，打包将不使用图标")

    print("\n" + "=" * 50)
    print("开始打包 YHModsManager 主程序")
    print("=" * 50 + "\n")

    clean_build_dirs()

    spec_file = "mods_manager.spec"
    if not os.path.exists(spec_file):
        print(f"错误: 找不到 {spec_file}")
        sys.exit(1)

    print(f"使用配置文件: {spec_file}")

    cmd = [sys.executable, "-m", "PyInstaller", "--clean", spec_file]

    print(f"执行命令: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=os.getcwd())

    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("打包成功!")
        print("=" * 50)
        print(f"\n输出文件: dist/YHModsManager.exe")
        print("\n注意: 此打包不包含插件")
        print("如需插件功能，请单独打包插件后放入程序目录")
    else:
        print("\n打包失败!")
        sys.exit(1)


if __name__ == "__main__":
    build()
