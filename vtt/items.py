"""Scene items: grid, fog of war, dynamic lighting, tokens and interactive map objects.

The admin view and the player display paint the same items; `is_admin(widget)` lets an item draw
differently for the DM (see-through fog, hidden things at half opacity, DM-only markers).
"""
import copy, math, time, uuid
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QGraphicsItem
from . import rules

ANIM_LEN = 1.2
KIND_COLORS = {"pc": "#3a6ea5", "ally": "#2e8b57", "enemy": "#b22222", "neutral": "#c9a227"}
_PIX = {}


def pix(path):
    if not path:
        return None
    if path not in _PIX:
        _PIX[path] = QPixmap(path)
    return None if _PIX[path].isNull() else _PIX[path]


def is_admin(widget):
    return bool(widget is not None and widget.property("admin"))


def gold_pen(width=2):
    pen = QPen(QColor("#e0b84f"), width, Qt.DashLine)
    pen.setCosmetic(True)
    return pen


class Grid(QGraphicsItem):
    KEYS = ("on", "size", "ox", "oy", "color", "alpha")

    def __init__(self):
        super().__init__()
        self.on, self.size, self.ox, self.oy, self.color, self.alpha = False, 70.0, 0.0, 0.0, "#ffffff", 0.4
        self.rect = QRectF()
        self.setZValue(1)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        return self.rect

    def set_rect(self, r):
        self.prepareGeometryChange()
        self.rect = QRectF(r)

    def paint(self, p, opt, widget=None):
        if not self.on or self.size < 5:
            return
        r, lines = self.rect, []
        x = r.left() + self.ox % self.size
        while x <= r.right():
            lines.append(QLineF(x, r.top(), x, r.bottom()))
            x += self.size
        y = r.top() + self.oy % self.size
        while y <= r.bottom():
            lines.append(QLineF(r.left(), y, r.right(), y))
            y += self.size
        p.setOpacity(self.alpha)
        p.setPen(QPen(QColor(self.color), max(1.0, self.size / 40)))
        p.drawLines(lines)


class Fog(QGraphicsItem):
    MAX = 2048  # mask resolution cap; scaled up smoothly over the map

    def __init__(self, app):
        super().__init__()
        self.app, self.on, self.rect, self.img = app, False, QRectF(), QImage()
        self.touched = False  # has the DM painted or set this fog yet?
        self.setZValue(6)
        self.setAcceptedMouseButtons(Qt.NoButton)  # clicks fall through to tokens under the fog

    def boundingRect(self):
        return self.rect

    def f(self):
        return min(1.0, self.MAX / max(self.rect.width(), self.rect.height(), 1))

    def set_rect(self, r):
        if r == self.rect and not self.img.isNull():
            return
        self.prepareGeometryChange()
        self.rect = QRectF(r)
        self.fill(True, touched=False)

    def fill(self, covered, touched=True):
        self.touched = touched
        f = self.f()
        self.img = QImage(max(1, math.ceil(self.rect.width() * f)), max(1, math.ceil(self.rect.height() * f)),
                          QImage.Format_ARGB32_Premultiplied)
        self.img.fill(QColor(0, 0, 0) if covered else Qt.transparent)
        self.update()

    def stroke(self, a, b, r, reveal):
        f, o = self.f(), self.rect.topLeft()
        A, B = (a - o) * f, (b - o) * f
        self.touched = True
        p = QPainter(self.img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_Clear if reveal else QPainter.CompositionMode_SourceOver)
        p.setPen(QPen(Qt.black, 2 * r * f, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(A, B)
        p.setPen(Qt.NoPen)
        p.setBrush(Qt.black)
        p.drawEllipse(B, r * f, r * f)
        p.end()
        self.update()

    def clear_rect(self, r):
        f, o = self.f(), self.rect.topLeft()
        p = QPainter(self.img)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(QRectF((r.topLeft() - o) * f, r.size() * f), Qt.black)
        p.end()
        self.update()

    def paint(self, p, opt, widget=None):
        if not self.on or self.img.isNull():
            return
        if is_admin(widget):
            p.setOpacity(0.55)  # DM sees through the fog, players don't
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(self.rect, self.img)


class Lighting(QGraphicsItem):
    """Darkness layer with holes cut by light sources, plus an additive coloured glow per light."""
    MAX = 1024

    def __init__(self, app):
        super().__init__()
        self.app, self.enabled, self.darkness, self.tint = app, False, 0.0, "#0a1030"
        self.rect, self.img, self.glows, self.dirty = QRectF(), QImage(), [], True
        self.setZValue(5)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        return self.rect

    def set_rect(self, r):
        self.prepareGeometryChange()
        self.rect = QRectF(r)
        self.dirty = True

    def flickers(self):
        return any(e.light_spec() and e.light.get("flicker") for e in self.app.entities())

    def rebuild(self, t):
        self.dirty = False
        if self.rect.isEmpty():
            return
        f = min(1.0, self.MAX / max(self.rect.width(), self.rect.height()))
        w, h = max(1, math.ceil(self.rect.width() * f)), max(1, math.ceil(self.rect.height() * f))
        if self.img.width() != w or self.img.height() != h:
            self.img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        c = QColor(self.tint)
        c.setAlphaF(max(0.0, min(1.0, self.darkness)))
        self.img.fill(c)
        p = QPainter(self.img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        o, per_ft = self.rect.topLeft(), self.app.grid.size / 5
        self.glows = []
        for e in self.app.entities():
            L = e.light_spec()
            if not L or L["bright"] + L["dim"] <= 0:
                continue
            seed = sum(map(ord, e.id))
            fl = 1 + L.get("flicker", 0) * (0.05 * math.sin(t * 9.1 + seed) + 0.03 * math.sin(t * 23.7 + seed * 1.7))
            R = (L["bright"] + L["dim"]) * per_ft * fl
            c = (e.scenePos() - o) * f
            g = QRadialGradient(c, R * f)
            g.setColorAt(0, QColor(0, 0, 0, 255))
            g.setColorAt(L["bright"] / (L["bright"] + L["dim"]), QColor(0, 0, 0, 235))  # bright zone, then dim falloff
            g.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(g)
            p.drawEllipse(c, R * f, R * f)
            self.glows.append((e.scenePos(), R, QColor(L["color"])))
        p.end()
        self.update()

    def paint(self, p, opt, widget=None):
        if not self.enabled or self.img.isNull():
            return
        p.save()
        p.setClipRect(self.rect)
        if is_admin(widget):
            p.setOpacity(0.5)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(self.rect, self.img)
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setPen(Qt.NoPen)
        alpha = int(15 + 40 * self.darkness)  # subtle colour; the darkness cut-out does the real lighting
        for c, R, col in self.glows:
            g = QRadialGradient(c, R)
            g.setColorAt(0, QColor(col.red(), col.green(), col.blue(), alpha))
            g.setColorAt(1, QColor(col.red(), col.green(), col.blue(), 0))
            p.setBrush(g)
            p.drawEllipse(c, R, R)
        p.restore()


class Entity(QGraphicsItem):
    """Base for tokens and objects: attributes come from DEFAULTS and round-trip through to_dict()."""
    DEFAULTS = {}

    def __init__(self, app, data=None):
        super().__init__()
        self.app, data = app, data or {}
        for k, v in self.DEFAULTS.items():
            setattr(self, k, copy.deepcopy(data.get(k, v)))
        self.id = self.id or uuid.uuid4().hex[:8]
        self.anim_t = -99.0
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(data.get("x", 0), data.get("y", 0))
        self.refresh()

    def to_dict(self):
        d = {k: copy.deepcopy(getattr(self, k)) for k in self.DEFAULTS}
        d["x"], d["y"] = self.pos().x(), self.pos().y()
        return d

    def light_spec(self):
        return self.light if self.light and self.lit and not self.hidden else None

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.light:
            self.app.lighting.dirty = True
        return super().itemChange(change, value)

    def refresh(self):
        self.prepareGeometryChange()
        self.setToolTip(self.tooltip())
        self.update()
        self.app.lighting.dirty = True

    def tooltip(self):
        return self.name + (f"\nDM: {self.notes}" if self.notes else "")


class Token(Entity):
    DEFAULTS = dict(id="", name="Goblin", kind="enemy", color="#5a1a1a", cells=1.0, img="", hp=7, max_hp=7, temp=0, ac=15,
                    init_mod=2, init=None, in_combat=False, level=1, cr="1/4", atk=0, dpr=0, conditions={}, exhaustion=0, concentrating=False, dead=False,
                    hidden=False, tag="", notes="", light=None, lit=True)

    def __init__(self, app, data=None):
        super().__init__(app, data)
        self.setZValue(3)
        self.setCursor(Qt.OpenHandCursor)

    def r(self):
        return self.cells * self.app.grid.size / 2

    def boundingRect(self):
        r = self.r() * 1.7
        return QRectF(-r, -r, 2 * r, 2 * r)

    def shape(self):
        path = QPainterPath()
        path.addEllipse(QPointF(), self.r(), self.r())
        return path

    def badges(self):
        out = [rules.badge(n) for n in self.conditions]
        if self.exhaustion:
            out.append((f"E{self.exhaustion}", rules.CONDITIONS["Exhaustion"][1]))
        if self.concentrating:
            out.append(rules.CONCENTRATION)
        return out

    def tooltip(self):
        lines = [f"{self.name} ({self.kind})  HP {self.hp}/{self.max_hp}" + (f" +{self.temp}" if self.temp else "") + f"  AC {self.ac}"]
        for n, left in self.conditions.items():
            lines.append(f"• {n}{f' ({left} rnd)' if left else ''}: {rules.summary(n, self.app.ruleset)}")
        if self.exhaustion:
            lines.append(f"• Exhaustion {self.exhaustion}: {rules.summary('Exhaustion', self.app.ruleset)}")
        if self.concentrating:
            lines.append("• Concentrating")
        if self.notes:
            lines.append(f"DM: {self.notes}")
        return "\n".join(lines)

    def paint(self, p, opt, widget=None):
        admin = is_admin(widget)
        if self.hidden and not admin:
            return
        r = self.r()
        rect = QRectF(-r, -r, 2 * r, 2 * r)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.hidden:
            p.setOpacity(0.5)
        if self.app.active_id == self.id:  # whose turn it is
            g = QRadialGradient(QPointF(), r * 1.6)
            g.setColorAt(0.55, QColor(255, 210, 90, 220))
            g.setColorAt(1, QColor(255, 210, 90, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(QPointF(), r * 1.6, r * 1.6)
        path = QPainterPath()
        path.addEllipse(rect)
        p.fillPath(path, QColor(self.color))
        pm = pix(self.img)
        if pm:
            side = min(pm.width(), pm.height())
            p.save()
            p.setClipPath(path)
            p.drawPixmap(rect, pm, QRectF((pm.width() - side) / 2, (pm.height() - side) / 2, side, side))
            p.restore()
        else:
            font = p.font()
            font.setBold(True)
            font.setPixelSize(max(1, int(r * 0.7)))
            p.setFont(font)
            p.setPen(QColor("#f3e6c4"))
            p.drawText(rect, Qt.AlignCenter, self.name[:3])
        if self.dead:
            p.fillPath(path, QColor(0, 0, 0, 150))
            p.setPen(QPen(QColor("#b22222"), r * 0.15, Qt.SolidLine, Qt.RoundCap))
            k = r * 0.55
            p.drawLine(QPointF(-k, -k), QPointF(k, k))
            p.drawLine(QPointF(k, -k), QPointF(-k, k))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(KIND_COLORS.get(self.kind, "#888")), r * 0.14))  # side ring: enemy red, PC blue...
        p.drawEllipse(rect)
        if rules.bloodied(self):
            p.setPen(QPen(QColor("#ff2a2a"), r * 0.06, Qt.DashLine))
            p.drawEllipse(QPointF(), r * 1.12, r * 1.12)
        br = max(r * 0.3, 5)
        font = p.font()
        font.setBold(True)
        font.setPixelSize(max(1, int(br * 0.95)))
        p.setFont(font)
        for i, (abbr, col) in enumerate(self.badges()):  # condition badges around the ring
            a = math.radians(-45 + i * 32)
            c = QPointF(math.cos(a) * r, math.sin(a) * r)
            p.setPen(QPen(QColor(0, 0, 0, 200), br * 0.15))
            p.setBrush(QColor(col))
            p.drawEllipse(c, br, br)
            p.setPen(Qt.white)
            p.drawText(QRectF(c.x() - br, c.y() - br, 2 * br, 2 * br), Qt.AlignCenter, abbr)
        if admin or (self.kind == "pc" and self.app.pc_hp):
            w, h, y = 2 * r, r * 0.18, r * 1.18
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 200))
            p.drawRect(QRectF(-r, y, w, h))
            ratio = self.hp / max(1, self.max_hp)
            p.setBrush(QColor("#4caf50" if ratio > 0.5 else "#e67e22" if ratio > 0.25 else "#c0392b"))
            p.drawRect(QRectF(-r, y, w * ratio, h))
            if self.temp:
                p.setBrush(QColor("#5aa0ff"))
                p.drawRect(QRectF(-r, y + h * 0.6, w * min(1, self.temp / max(1, self.max_hp)), h * 0.4))
        if admin and self.isSelected():
            p.setOpacity(1)
            p.setPen(gold_pen())
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(), r * 1.3, r * 1.3)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if self.app.snap:
            self.setPos(self.app.snapped(self.pos(), self.cells))


class Prop(Entity):
    """A placed object. With no image it is a DM-only marker (light, note, trap, journal pin).
    Triggering it can open/close it, toggle its light, play a sound, animate, reveal tagged items,
    change the weather and open a journal entry."""
    DEFAULTS = dict(id="", name="Object", img="", alt_img="", icon="", cells=1.0, rotation=0.0, toggle=False, opened=False,
                    hidden=False, above=False, tag="", reveals="", sound="", anim="none", weather="", journal="",
                    notes="", light=None, lit=True)
    ICONS = {"light": "☀", "note": "✎", "trap": "☠", "pin": "⚑"}

    def refresh(self):
        self.setRotation(self.rotation)
        self.setZValue(9 if self.icon else 4 if self.above else 2)
        super().refresh()

    def cur_pix(self):
        return pix(self.alt_img) if self.opened and self.alt_img else pix(self.img)

    def box(self):
        side = self.cells * self.app.grid.size
        pm = self.cur_pix()
        if self.icon or not pm:
            s = side * 0.7 if self.icon else side
            return QRectF(-s / 2, -s / 2, s, s)
        k = side / max(pm.width(), pm.height())
        return QRectF(-pm.width() * k / 2, -pm.height() * k / 2, pm.width() * k, pm.height() * k)

    def boundingRect(self):
        b = self.box()
        return b.adjusted(-b.width() * 0.3, -b.height() * 0.3, b.width() * 0.3, b.height() * 0.3)

    def shape(self):
        path = QPainterPath()
        path.addRect(self.box())
        return path

    def interactive(self):
        return bool(self.toggle or self.alt_img or self.sound or self.reveals or self.weather or self.journal
                    or self.anim != "none" or self.light)

    def gone(self):
        return self.hidden or (self.opened and self.toggle and not self.alt_img)  # an open door with no 'open' art vanishes

    def paint(self, p, opt, widget=None):
        admin = is_admin(widget)
        if not admin and (self.icon or self.gone()):
            return
        box = self.box()
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        t = time.monotonic() - self.anim_t
        if t < ANIM_LEN:
            k = 1 - t / ANIM_LEN
            if self.anim == "pulse":
                s = 1 + 0.18 * math.sin(t * math.pi * 3 / ANIM_LEN) * k
                p.scale(s, s)
            elif self.anim == "shake":
                p.translate(math.sin(t * 45) * box.width() * 0.07 * k, 0)
            elif self.anim == "glow":
                R = max(box.width(), box.height()) * 0.8
                g = QRadialGradient(QPointF(), R)
                g.setColorAt(0, QColor(255, 215, 120, int(220 * k)))
                g.setColorAt(1, QColor(255, 215, 120, 0))
                p.setPen(Qt.NoPen)
                p.setBrush(g)
                p.drawEllipse(QPointF(), R, R)
        if self.gone():
            p.setOpacity(0.4)
        if self.icon:
            col = QColor(self.light["color"]) if self.icon == "light" and self.light else QColor("#c0392b" if self.icon == "trap" else "#e0b84f")
            p.setPen(QPen(col, box.width() * 0.07))
            p.setBrush(QColor(20, 14, 10, 220))
            p.drawEllipse(box)
            font = p.font()
            font.setPixelSize(max(1, int(box.height() * 0.55)))
            p.setFont(font)
            p.setPen(col)
            p.drawText(box, Qt.AlignCenter, self.ICONS.get(self.icon, "?"))
        elif self.cur_pix():
            pm = self.cur_pix()
            p.drawPixmap(box, pm, QRectF(pm.rect()))
        else:
            p.setPen(gold_pen(1))
            p.setBrush(QColor(40, 30, 20, 160))
            p.drawRect(box)
            p.drawText(box, Qt.AlignCenter | Qt.TextWordWrap, self.name)
        if admin:
            p.setOpacity(1)
            if self.interactive() and not self.icon:  # little gold diamond: "this can be triggered"
                d, c = max(4.0, box.width() * 0.07), box.topRight()
                path = QPainterPath()
                path.moveTo(c + QPointF(0, -d))
                path.lineTo(c + QPointF(d, 0))
                path.lineTo(c + QPointF(0, d))
                path.lineTo(c + QPointF(-d, 0))
                path.closeSubpath()
                p.fillPath(path, QColor("#e0b84f"))
            if self.isSelected():
                p.setPen(gold_pen())
                p.setBrush(Qt.NoBrush)
                p.drawRect(box.adjusted(-3, -3, 3, 3))

    def trigger(self):
        a, did = self.app, []
        if self.toggle or self.alt_img:
            self.opened = not self.opened
            did.append("opened" if self.opened else "closed")
        if self.light:
            self.lit = not self.lit
            did.append("lit" if self.lit else "doused")
        if self.sound:
            a.play_sound(self.sound)
            did.append("sound")
        if self.anim != "none":
            self.anim_t = time.monotonic()
            a.animating.add(self)
        if self.reveals:
            did.append(f"toggled {a.reveal_tag(self.reveals)} item(s) tagged '{self.reveals}'")
        if self.weather:
            a.set_weather(self.weather)
            did.append(f"weather → {self.weather}")
        if self.journal:
            a.open_entry(self.journal)
        self.refresh()
        return f"{self.name}: " + (", ".join(did) or "triggered")
