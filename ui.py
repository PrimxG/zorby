import sys

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QPoint, QSize, Qt, QVariantAnimation
from PyQt5.QtGui import QColor, QBrush, QFont, QLinearGradient, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QWidget


class Orb(QWidget):
    def __init__(self, size: int, click_callback, drag_callback) -> None:
        super().__init__()
        self.resize(size, size)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._click_callback = click_callback
        self._drag_callback = drag_callback
        self._mode_text = "Break Mode"
        self._focus_minutes = 0
        self._message_text = ""
        self._break_alert = False
        self._prev_mode_text = self._mode_text
        self._prev_focus_minutes = self._focus_minutes
        self._prev_message_text = self._message_text
        self._prev_break_alert = self._break_alert
        self._today_text = "0m"
        self._best_text = "0m"
        self._sessions_count = 0
        self._state = "idle"
        self._color_anim = QVariantAnimation(self)
        self._color_anim.setDuration(800)
        self._color_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._color_anim.valueChanged.connect(self._on_color_anim)
        self._pulse_scale = 1.0
        self._text_opacity = 1.0
        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setDuration(2600)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._pulse_anim.valueChanged.connect(self._on_pulse_anim)
        self._pulse_anim.start()
        self._text_fade_anim = QVariantAnimation(self)
        self._text_fade_anim.setDuration(260)
        self._text_fade_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._text_fade_anim.valueChanged.connect(self._on_text_fade_anim)

        self._current_start = QColor("#5B6470")
        self._current_end = QColor("#3F4854")
        self._current_glow = QColor("#707884")
        self._current_glow.setAlpha(30)
        self._pulse_glow_alpha = self._current_glow.alpha()
        self._anim_from_start = QColor(self._current_start)
        self._anim_from_end = QColor(self._current_end)
        self._anim_from_glow = QColor(self._current_glow)
        self._anim_to_start = QColor(self._current_start)
        self._anim_to_end = QColor(self._current_end)
        self._anim_to_glow = QColor(self._current_glow)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._drag_callback("press", event.globalPos())

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if event.buttons() & Qt.LeftButton:
            self._drag_callback("move", event.globalPos())

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._drag_callback("release", event.globalPos())

    def set_mode_text(self, text: str) -> None:
        if self._mode_text != text:
            self._prev_mode_text = self._mode_text
            self._prev_focus_minutes = self._focus_minutes
            self._prev_message_text = self._message_text
            self._prev_break_alert = self._break_alert
            self._mode_text = text
            self._start_text_fade()
            self.update()

    def set_focus_minutes(self, minutes: int) -> None:
        if self._focus_minutes != minutes:
            self._prev_mode_text = self._mode_text
            self._prev_focus_minutes = self._focus_minutes
            self._prev_message_text = self._message_text
            self._prev_break_alert = self._break_alert
            self._focus_minutes = minutes
            self._start_text_fade()
            self.update()

    def set_message_text(self, text: str) -> None:
        if self._message_text != text:
            self._prev_mode_text = self._mode_text
            self._prev_focus_minutes = self._focus_minutes
            self._prev_message_text = self._message_text
            self._prev_break_alert = self._break_alert
            self._message_text = text
            self._start_text_fade()
            self.update()

    def set_break_alert(self, enabled: bool) -> None:
        if self._break_alert != enabled:
            self._prev_mode_text = self._mode_text
            self._prev_focus_minutes = self._focus_minutes
            self._prev_message_text = self._message_text
            self._prev_break_alert = self._break_alert
            self._break_alert = enabled
            self._start_text_fade()
            self.update()

    def set_stats(self, today_text: str, best_text: str, sessions_count: int) -> None:
        changed = (
            self._today_text != today_text
            or self._best_text != best_text
            or self._sessions_count != sessions_count
        )
        if changed:
            self._today_text = today_text
            self._best_text = best_text
            self._sessions_count = sessions_count
            self._start_text_fade()
            self.update()

    def set_state(self, state: str) -> None:
        normalized = state if state in ("work", "entertainment", "idle") else "idle"
        if normalized == self._state:
            return
        self._state = normalized

        if normalized == "work":
            target_start = QColor("#4F8CFF")
            target_end = QColor("#8B5CF6")
            target_glow = QColor("#6D8BFF")
            target_glow.setAlpha(55)
        elif normalized == "entertainment":
            target_start = QColor("#22C55E")
            target_end = QColor("#16A34A")
            target_glow = QColor("#22C55E")
            target_glow.setAlpha(45)
        else:
            target_start = QColor("#5B6470")
            target_end = QColor("#3F4854")
            target_glow = QColor("#707884")
            target_glow.setAlpha(30)

        self._anim_from_start = QColor(self._current_start)
        self._anim_from_end = QColor(self._current_end)
        self._anim_from_glow = QColor(self._current_glow)
        self._anim_to_start = target_start
        self._anim_to_end = target_end
        self._anim_to_glow = target_glow

        self._color_anim.stop()
        self._color_anim.setStartValue(0.0)
        self._color_anim.setEndValue(1.0)
        self._color_anim.start()

    def _start_text_fade(self) -> None:
        self._text_fade_anim.stop()
        self._text_fade_anim.setStartValue(0.0)
        self._text_fade_anim.setEndValue(1.0)
        self._text_fade_anim.start()

    def _on_pulse_anim(self, value: float) -> None:
        t = float(value)
        # Subtle pulse: 1.0 -> 1.02 -> 1.0 with slow glow breathing.
        breath = 1.0 - abs(2.0 * t - 1.0)
        self._pulse_scale = 1.0 + 0.02 * breath
        base_alpha = self._current_glow.alpha()
        self._pulse_glow_alpha = min(255, max(0, int(base_alpha + 12 * breath)))
        self.update()

    def _on_text_fade_anim(self, value: float) -> None:
        self._text_opacity = float(value)
        self.update()

    def _on_color_anim(self, value: float) -> None:
        t = float(value)
        self._current_start = self._mix_color(self._anim_from_start, self._anim_to_start, t)
        self._current_end = self._mix_color(self._anim_from_end, self._anim_to_end, t)
        self._current_glow = self._mix_color(self._anim_from_glow, self._anim_to_glow, t)
        self.update()

    @staticmethod
    def _mix_color(a: QColor, b: QColor, t: float) -> QColor:
        return QColor(
            int(a.red() + (b.red() - a.red()) * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue() + (b.blue() - a.blue()) * t),
            int(a.alpha() + (b.alpha() - a.alpha()) * t),
        )

    def paintEvent(self, event):  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self.width() < 150:
            center = self.rect().center()
            painter.translate(center)
            painter.scale(self._pulse_scale, self._pulse_scale)
            painter.translate(-center)

        r = self.rect().adjusted(2, 2, -3, -3)
        gradient = QLinearGradient(r.topLeft(), r.bottomRight())
        gradient.setColorAt(0.0, self._current_start)
        gradient.setColorAt(1.0, self._current_end)

        painter.setPen(QPen(Qt.NoPen))
        glow_color = QColor(self._current_glow)
        glow_color.setAlpha(self._pulse_glow_alpha)
        painter.setBrush(QBrush(glow_color))
        glow_rect = r.adjusted(-2, -2, 2, 2)
        glow_radius = min(42, min(glow_rect.width(), glow_rect.height()) // 2)
        painter.drawRoundedRect(glow_rect, glow_radius, glow_radius)

        painter.setBrush(QBrush(gradient))
        radius = min(40, min(r.width(), r.height()) // 2)
        painter.drawRoundedRect(r, radius, radius)

        if self.width() >= 150:
            current_opacity = self._text_opacity
            old_opacity = 1.0 - current_opacity
            painter.setPen(Qt.white)
            font = painter.font()
            font.setFamily("Segoe UI")
            font.setPointSize(font.pointSize() + 2)
            font.setBold(True)
            sub_font = QFont(font)
            sub_font.setBold(False)
            msg_font = QFont(sub_font)
            msg_font.setPointSize(max(8, msg_font.pointSize() - 1))
            mode_rect = r.adjusted(0, -46, 0, 0)
            timer_rect = r.adjusted(0, -6, 0, 0)
            quote_rect = r.adjusted(20, 26, -20, -64)

            if old_opacity > 0.01:
                painter.setOpacity(old_opacity)
                painter.setFont(font)
                painter.drawText(mode_rect, Qt.AlignCenter, self._prev_mode_text)
                painter.setFont(sub_font)
                painter.drawText(timer_rect, Qt.AlignCenter, f"Focus Time: {self._prev_focus_minutes} min")
                if self._prev_message_text:
                    painter.setFont(msg_font)
                    painter.drawText(quote_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self._prev_message_text)

            painter.setOpacity(current_opacity)
            painter.setFont(font)
            painter.drawText(mode_rect, Qt.AlignCenter, self._mode_text)
            painter.setFont(sub_font)
            painter.drawText(timer_rect, Qt.AlignCenter, f"Focus Time: {self._focus_minutes} min")
            if self._message_text:
                painter.setFont(msg_font)
                painter.drawText(quote_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self._message_text)

            if self._break_alert or self._prev_break_alert:
                alert_rect = r.adjusted(20, 132, -20, -10)
                painter.setBrush(QColor(255, 214, 102, 60))
                painter.setPen(QPen(QColor("#FFD166")))
                painter.drawRoundedRect(alert_rect, 10, 10)
                alert_font = QFont(msg_font)
                alert_font.setBold(True)
                painter.setFont(alert_font)
                painter.setPen(QColor("#FFE7A6"))
                if old_opacity > 0.01 and self._prev_break_alert:
                    painter.setOpacity(old_opacity)
                    painter.drawText(alert_rect, Qt.AlignCenter, "Take a break and recharge ⚡")
                if self._break_alert:
                    painter.setOpacity(current_opacity)
                    painter.drawText(alert_rect, Qt.AlignCenter, "Take a break and recharge ⚡")

            stats_font = QFont("Segoe UI", 8)
            painter.setOpacity(1.0)
            painter.setFont(stats_font)
            painter.setPen(QColor(235, 240, 255, 215))
            stats_rect = r.adjusted(20, 104, -20, -38)
            painter.drawText(
                stats_rect,
                Qt.AlignLeft | Qt.AlignTop,
                f"Today: {self._today_text}\nBest: {self._best_text}\nSessions: {self._sessions_count}",
            )
        elif self._break_alert:
            painter.setOpacity(self._text_opacity)
            bubble = self.rect().adjusted(8, -34, 178, -4)
            painter.setBrush(QColor(255, 214, 102, 220))
            painter.setPen(QPen(QColor("#D9A200")))
            painter.drawRoundedRect(bubble, 10, 10)
            bubble_font = QFont("Segoe UI", 9)
            bubble_font.setBold(True)
            painter.setFont(bubble_font)
            painter.setPen(QColor("#3A2A00"))
            painter.drawText(bubble.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.TextWordWrap, "Take a break and recharge ⚡")
            painter.setOpacity(1.0)


class FloatingOrbWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.collapsed_w = 80
        self.collapsed_h = 80
        self.expanded_w = 300
        self.expanded_h = 200
        margin = 24

        screen = QApplication.primaryScreen()
        self.resize(self.collapsed_w, self.collapsed_h)
        self.setMinimumSize(self.collapsed_w, self.collapsed_h)
        self.setMaximumSize(self.expanded_w, self.expanded_h)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self._animation = None
        self._expanded = False
        self._drag_offset = QPoint()
        self._drag_started = False
        self._dragging = False

        self.orb = Orb(self.collapsed_w, self.toggle_orb, self.handle_drag)
        self.orb.setParent(self)
        self.orb.move(0, 0)

        if screen:
            geom = screen.availableGeometry()
            x = geom.right() - self.expanded_w - margin + 1
            y = geom.top() + margin + 64
            self.move(self._clamp_pos(QPoint(x, y), QSize(self.expanded_w, self.expanded_h), padding=0))

    def resizeEvent(self, event):  # type: ignore[override]
        self.orb.setGeometry(self.rect())
        super().resizeEvent(event)

    def toggle_orb(self) -> None:
        if self._animation is not None and self._animation.state() == QPropertyAnimation.Running:
            return

        start = self.size()
        if self._expanded:
            end = QSize(self.collapsed_w, self.collapsed_h)
            self._expanded = False
        else:
            end = QSize(self.expanded_w, self.expanded_h)
            self._expanded = True

        self.move(self._clamp_pos(self.pos(), end, padding=0))
        self._animation = QPropertyAnimation(self, b"size")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.InOutSine)
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def set_mode(self, activity: str) -> None:
        mode_text = "Focus Mode" if activity == "work" else "Break Mode"
        self.orb.set_mode_text(mode_text)
        self.orb.set_state(activity)

    def set_focus_minutes(self, minutes: int) -> None:
        self.orb.set_focus_minutes(minutes)

    def set_message(self, text: str) -> None:
        self.orb.set_message_text(text)

    def set_break_alert(self, enabled: bool) -> None:
        self.orb.set_break_alert(enabled)

    def set_stats(self, today_text: str, best_text: str, sessions_count: int) -> None:
        self.orb.set_stats(today_text, best_text, sessions_count)

    def handle_drag(self, kind: str, global_pos: QPoint) -> None:
        if kind == "press":
            self._drag_started = True
            self._dragging = False
            self._drag_offset = global_pos - self.frameGeometry().topLeft()
            return
        if kind == "move" and self._drag_started:
            self._dragging = True
            self.move(self._clamp_pos(global_pos - self._drag_offset, self.size(), padding=0))
            return
        if kind == "release":
            if self._drag_started and not self._dragging:
                print("Orb clicked")
                self.toggle_orb()
            else:
                self.move(self._clamp_pos(self.pos(), self.size(), padding=0))
            self._drag_started = False
            self._dragging = False

    def _clamp_pos(self, pos: QPoint, size: QSize, padding: int = 0) -> QPoint:
        screen = QApplication.screenAt(pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return pos

        geom = screen.availableGeometry()
        max_x = geom.right() - size.width() - padding + 1
        max_y = geom.bottom() - size.height() - padding + 1
        x = max(geom.left() + padding, min(pos.x(), max_x))
        y = max(geom.top() + padding, min(pos.y(), max_y))
        return QPoint(x, y)


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    win = FloatingOrbWindow()
    win.show()
    win.raise_()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

