"""
Toast提示组件 - 可复用的自动消失提示界面
"""
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QColor, QPainter, QBrush, QFont
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect

from .styles import FontSize, get_calculated_font_size, get_ui_constant
from .theme_manager import get_color


def _get_toast_config():
    """获取Toast配置，从ui_constants.json读取"""
    return get_ui_constant('toast', 'default_duration', 2000), \
        get_ui_constant('toast', 'default_fade_duration', 300), \
        get_ui_constant('toast', 'default_border_radius', 6), \
        get_ui_constant('toast', 'default_padding', 8), \
        get_ui_constant('toast', 'default_font_size', 12), \
        get_ui_constant('toast', 'default_bg_alpha', 220)


class ToastWidget(QWidget):
    """
    Toast提示组件

    显示一个会自动透明化消失的小提示界面
    支持自定义位置、持续时间、样式
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        (self._default_duration, self._default_fade_duration,
         self._default_border_radius, self._default_padding,
         self._default_font_size, self._default_bg_alpha) = _get_toast_config()

        self._bg_color = QColor(get_color('toast_background'))
        self._bg_color.setAlpha(self._default_bg_alpha)
        self._text_color = QColor(get_color('toast_text'))
        self._border_radius = self._default_border_radius
        self._padding = self._default_padding
        self._font_size = self._default_font_size
        self._duration = self._default_duration
        self._fade_duration = self._default_fade_duration

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.hide()
        self.resize(0, 0)

        self._init_ui()
        self._setup_animations()

        self._hide_timer = QTimer(self)
        self._hide_timer.timeout.connect(self._start_fade_out)

    def _init_ui(self):
        """初始化UI"""
        from PyQt6.QtGui import QPalette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self._padding, self._padding, self._padding, self._padding)
        layout.setSpacing(0)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setProperty("labelType", "toast")
        font = QFont()
        font.setPointSize(get_calculated_font_size(self._default_font_size, FontSize.BASE))
        self._label.setFont(font)
        palette = self._label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, self._text_color)
        self._label.setPalette(palette)
        layout.addWidget(self._label)

    def paintEvent(self, event):
        """绘制背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制半透明背景
        brush = QBrush(self._bg_color)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), self._border_radius, self._border_radius)

    def _setup_animations(self):
        """设置动画"""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in_animation.setDuration(self._fade_duration)
        self._fade_in_animation.setStartValue(0)
        self._fade_in_animation.setEndValue(1)
        self._fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._fade_out_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out_animation.setDuration(self._fade_duration)
        self._fade_out_animation.setStartValue(1)
        self._fade_out_animation.setEndValue(0)
        self._fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_out_animation.finished.connect(self.hide)

    def show_message(
            self,
            message: str,
            duration: int = None,
            position: QPoint = None,
            parent_widget: QWidget = None
    ):
        """
        显示Toast消息

        Args:
            message: 显示的消息文本
            duration: 显示持续时间（毫秒），默认2000ms
            position: 显示位置，默认在父窗口底部居中
            parent_widget: 父窗口，用于计算默认位置
        """
        # 停止之前的定时器和动画
        self._hide_timer.stop()
        self._fade_out_animation.stop()
        self._fade_in_animation.stop()

        # 设置消息
        self._label.setText(message)
        self.adjustSize()

        # 计算位置
        if position is None:
            position = self._calculate_default_position(parent_widget or self.parent())

        # 确保Toast不会超出屏幕边界
        position = self._adjust_position_to_screen(position)

        # 先设置位置，再显示窗口
        self.move(position)

        # 确保透明度为0后再显示
        self._opacity_effect.setOpacity(0)
        self.show()
        self.raise_()

        # 淡入
        self._fade_in_animation.start()

        # 启动定时器
        self._duration = duration or self._default_duration
        self._hide_timer.start(self._duration)

    def _calculate_default_position(self, parent_widget: QWidget) -> QPoint:
        """计算默认显示位置（父窗口底部居中）"""
        if parent_widget is None:
            return QPoint(100, 100)

        parent_rect = parent_widget.geometry()
        x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
        y = parent_rect.y() + parent_rect.height() - self.height() - 50

        return QPoint(x, y)

    def _adjust_position_to_screen(self, position: QPoint) -> QPoint:
        """调整位置确保不超出屏幕"""
        from PyQt6.QtWidgets import QApplication

        screen = QApplication.primaryScreen().geometry()
        x = max(10, min(position.x(), screen.width() - self.width() - 10))
        y = max(10, min(position.y(), screen.height() - self.height() - 10))

        return QPoint(x, y)

    def _start_fade_out(self):
        """开始淡出动画"""
        self._fade_out_animation.start()

    def set_style(
            self,
            bg_color: QColor = None,
            text_color: QColor = None,
            border_radius: int = None,
            font_size: int = None,
            padding: int = None,
            bg_alpha: int = None
    ):
        """
        设置自定义样式

        Args:
            bg_color: 背景颜色（QColor对象）
            text_color: 文字颜色（QColor对象）
            border_radius: 圆角半径
            font_size: 字体大小
            padding: 内边距（像素）
            bg_alpha: 背景透明度 (0-255)
        """
        if bg_color:
            self._bg_color = QColor(bg_color)
        if bg_alpha is not None:
            self._bg_color.setAlpha(bg_alpha)
        if text_color:
            self._text_color = QColor(text_color)
            from PyQt6.QtGui import QPalette
            palette = self._label.palette()
            palette.setColor(QPalette.ColorRole.WindowText, self._text_color)
            self._label.setPalette(palette)
        if border_radius is not None:
            self._border_radius = border_radius
        if font_size is not None:
            self._font_size = font_size
            font = QFont()
            font.setPointSize(get_calculated_font_size(self._default_font_size, FontSize.BASE))
            self._label.setFont(font)
        if padding is not None:
            self._padding = padding
            layout = self.layout()
            if layout:
                layout.setContentsMargins(self._padding, self._padding, self._padding, self._padding)

    def set_duration(self, duration: int):
        """设置默认显示持续时间（毫秒）"""
        self._duration = duration

    def set_fade_duration(self, duration: int):
        """设置淡入淡出动画持续时间（毫秒）"""
        self._fade_duration = duration
        self._fade_in_animation.setDuration(duration)
        self._fade_out_animation.setDuration(duration)


class ToastManager:
    """
    Toast管理器 - 全局单例，方便在应用各处显示Toast

    使用示例:
        from toast_widget import ToastManager

        # 初始化（在主窗口中调用一次）
        ToastManager.init(parent_window)

        # 在任何地方显示Toast
        ToastManager.show("复制成功！")
        ToastManager.show("保存完成", duration=3000)
        ToastManager.show_at_click("已复制", click_pos=QPoint(100, 200))
    """

    _instance: ToastWidget = None
    _parent: QWidget = None

    @classmethod
    def init(cls, parent: QWidget, base_font_size: int = 12):
        """初始化Toast管理器（在主窗口中调用一次）"""
        cls._parent = parent
        cls._instance = ToastWidget(parent)
        cls._instance.set_style(font_size=base_font_size)

    @classmethod
    def show(
            cls,
            message: str,
            duration: int = None,
            position: QPoint = None
    ):
        """
        显示Toast消息

        Args:
            message: 显示的消息文本
            duration: 显示持续时间（毫秒），默认2000ms
            position: 显示位置，默认在父窗口底部居中
        """
        if cls._instance is None:
            raise RuntimeError("ToastManager未初始化，请先调用ToastManager.init(parent)")

        cls._instance.show_message(
            message=message,
            duration=duration,
            position=position,
            parent_widget=cls._parent
        )

    @classmethod
    def show_at_click(
            cls,
            message: str,
            click_pos: QPoint,
            duration: int = None
    ):
        """
        在鼠标点击位置显示Toast

        Args:
            message: 显示的消息文本
            click_pos: 鼠标点击位置（全局坐标）
            duration: 显示持续时间（毫秒），默认2000ms
        """
        if cls._instance is None:
            raise RuntimeError("ToastManager未初始化，请先调用ToastManager.init(parent)")

        # 调整位置：在点击位置上方显示，避免遮挡
        x = click_pos.x() - cls._instance.width() // 2
        y = click_pos.y() - cls._instance.height() - 10

        cls._instance.show_message(
            message=message,
            duration=duration,
            position=QPoint(x, y),
            parent_widget=cls._parent
        )

    @classmethod
    def set_default_style(
            cls,
            bg_color: QColor = None,
            text_color: QColor = None,
            border_radius: int = None,
            font_size: int = None
    ):
        """设置默认样式"""
        if cls._instance is None:
            raise RuntimeError("ToastManager未初始化，请先调用ToastManager.init(parent)")

        cls._instance.set_style(
            bg_color=bg_color,
            text_color=text_color,
            border_radius=border_radius,
            font_size=font_size
        )
