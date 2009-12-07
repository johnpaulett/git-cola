import sys
import math
from PyQt4 import QtCore, QtGui

def git_dag():
    """Return a pre-populated git DAG widget."""
    from cola.models import commit
    view = GraphView()
    view.add_commits(commit.commits())
    view.show()
    return view


class Edge(QtGui.QGraphicsItem):
    _type = QtGui.QGraphicsItem.UserType + 2

    def __init__(self, source, dest):
        QtGui.QGraphicsItem.__init__(self)

        self.arrow_size = 5.0
        self.source_pt = QtCore.QPointF()
        self.dest_pt = QtCore.QPointF()
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.source = source
        self.dest = dest
        self.source.add_edge(self)
        self.dest.add_edge(self)
        self.setZValue(-2)
        self.adjust()

    def type(self):
        return Edge._type

    def adjust(self):
        if not self.source or not self.dest:
            return

        line = QtCore.QLineF(
                self.mapFromItem(self.source, self.source.glyph().center()),
                self.mapFromItem(self.dest, self.dest.glyph().center()))
        length = line.length()
        if length == 0.0:
            return

        offset = QtCore.QPointF((line.dx() * 10) / length,
                                (line.dy() * 10) / length)

        self.prepareGeometryChange()
        self.source_pt = line.p1() + offset
        self.dest_pt = line.p2() - offset

    def boundingRect(self):
        if not self.source or not self.dest:
            return QtCore.QRectF()

        penWidth = 1
        extra = (penWidth + self.arrow_size) / 2.0

        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        return (QtCore.QRectF(self.source_pt,
                              QtCore.QSizeF(width, height))
                      .normalized()
                      .adjusted(-extra, -extra, extra, extra))

    def paint(self, painter, option, widget):
        if not self.source or not self.dest:
            return
        # Draw the line itself.
        line = QtCore.QLineF(self.source_pt, self.dest_pt)
        length = line.length()
        if length < 7.0 or length > 2 ** 11:
            return

        painter.setPen(QtGui.QPen(QtCore.Qt.white, 0,
                                  QtCore.Qt.SolidLine,
                                  QtCore.Qt.FlatCap,
                                  QtCore.Qt.MiterJoin))
        painter.drawLine(line)
        return

        # Draw the arrows if there's enough room.
        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = 2.0 * math.pi - angle

        dest_x = (self.dest_pt +
                  QtCore.QPointF(math.sin(angle - math.pi/3.) *
                                 self.arrow_size,
                                 math.cos(angle - math.pi/3.) *
                                 self.arrow_size))
        dest_y = (self.dest_pt +
                  QtCore.QPointF(math.sin(angle - math.pi + math.pi/3.) *
                                 self.arrow_size,
                                 math.cos(angle - math.pi + math.pi/3.) *
                                 self.arrow_size))

        #painter.setBrush(QtCore.Qt.white)
        #painter.drawPolygon(QtGui.QPolygonF([line.p2(), dest_x, dest_y]))


class Node(QtGui.QGraphicsItem):
    _type = QtGui.QGraphicsItem.UserType + 1

    def __init__(self, graph, commit):
        QtGui.QGraphicsItem.__init__(self)
        self.setZValue(0)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
        self.commit = commit
        self._graph = graph
        self._width = 180
        # Starts with enough space for two tags. Any more and the node
        # needs to be taller to accomodate.
        self._height = 18 
        if len(self.commit.tags) > 1:
            self._height = len(self.commit.tags) * 9 + 6 # +6 padding
        self._edges = []

        self._colors = {}
        self._colors['bg'] = QtGui.QColor.fromRgb(16, 16, 16)
        self._colors['selected'] = QtGui.QColor.fromRgb(192, 192, 16)
        self._colors['outline'] = QtGui.QColor.fromRgb(0, 0, 0)
        self._colors['node'] = QtGui.QColor.fromRgb(255, 111, 69)

        self._grad = QtGui.QLinearGradient(0.0, 0.0, 0.0, self._height)
        self._grad.setColorAt(0, self._colors['node'])
        self._grad.setColorAt(1, self._colors['node'].darker())

        self.pressed = False
        self.dragged = False
        self.skipped = False

    def type(self):
        return Node._type

    def add_edge(self, edge):
        self._edges.append(edge)
        edge.adjust()

    def boundingRect(self):
        return self.shape().boundingRect()

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRect(-self._width/2., -self._height/2.,
                     self._width, self._height)
        return path

    def glyph(self):
        """Provides location of the glyph representing this node

        The node contains a glyph (a circle or ellipse) representing the
        node, as well as other text alongside the glyph.  Knowing the
        location of the glyph, rather than the entire node allows us to
        make edges point at the center of the glyph, rather than at the
        center of the entire node.
        """
        glyph = QtCore.QRectF(-self._width/2., -9,
                              self._width/4., 18)
        return glyph

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setZValue(1)
            painter.setPen(self._colors['selected'])
        else:
            self.setZValue(0)
            painter.setPen(self._colors['outline'])
        painter.setBrush(self._grad)

        # Draw glyph
        painter.drawEllipse(self.glyph())
        sha1_text = self.commit.sha1
        font = painter.font()
        font.setPointSize(5)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.black)
        text_options = QtGui.QTextOption()
        text_options.setAlignment(QtCore.Qt.AlignCenter)
        painter.drawText(self.glyph(), sha1_text, text_options)

        # Draw tags
        if not len(self.commit.tags):
            return
        # Those 2's affecting width are just for padding
        text_box = QtCore.QRectF(-self._width/4.+2, -self._height/2.,
                                 self._width*(3/4.)-2, self._height)
        painter.drawRoundedRect(text_box, 4, 4)
        tag_text = "\n".join(self.commit.tags)
        text_options.setAlignment(QtCore.Qt.AlignVCenter)
        # A bit of padding for the text
        painter.translate(2.,0.)
        painter.drawText(text_box, tag_text, text_options)


    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemPositionChange:
            for edge in self._edges:
                edge.adjust()
            #self._graph.itemMoved()
        return QtGui.QGraphicsItem.itemChange(self, change, value)

    def mousePressEvent(self, event):
        self.selected = self.isSelected()
        self.pressed = True
        QtGui.QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)
        if (not self.dragged
                and self.selected
                and event.button() == QtCore.Qt.LeftButton):
            self.setSelected(False)
            self.skipped = True
            return
        self.skipped = False
        self.pressed = False
        self.dragged = False


#+---------------------------------------------------------------------------
class GraphView(QtGui.QGraphicsView):
    def __init__(self):
        QtGui.QGraphicsView.__init__(self)

        self._xoff = 200
        self._yoff = 42

        self._items = []
        self._nodes = []
        self._selected = []

        self._panning = False
        self._last_mouse = [0, 0]

        self.timerId = 0
        size = 30000

        self._zoom = 1
        self.scale(self._zoom, self._zoom)
        self.setDragMode(self.RubberBandDrag)

        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        scene.setSceneRect(-size/4, -size/2, size/2, size)
        self.setScene(scene)

        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)

        self.setMinimumSize(600, 600)
        self.setWindowTitle(self.tr('git dag'))

        self.setBackgroundColor()

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self.add(commits)
        self.layout(commits)
        self.link(commits)

    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_Plus:
            self._scale_view(1.5)
        elif key == QtCore.Qt.Key_Minus:
            self._scale_view(1 / 1.5)
        elif key == QtCore.Qt.Key_F:
            self._view_fit()
        elif event.key() == QtCore.Qt.Key_Z:
            self._move_nodes_to_mouse_position()
        else:
            QtGui.QGraphicsView.keyPressEvent(self, event)

    def _view_fit(self):
        """Fit selected items into the viewport"""

        items = self.scene().selectedItems()
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            xmin = sys.maxint
            ymin = sys.maxint
            xmax = -sys.maxint
            ymax = -sys.maxint
            for item in items:
                pos = item.pos()
                item_rect = item.boundingRect()
                xoff = item_rect.width()
                yoff = item_rect.height()
                xmin = min(xmin, pos.x())
                ymin = min(ymin, pos.y())
                xmax = max(xmax, pos.x()+xoff)
                ymax = max(ymax, pos.y()+yoff)
            rect = QtCore.QRectF(xmin, ymin, xmax-xmin, ymax-ymin)
        adjust = 42.0
        rect.setX(rect.x() - adjust)
        rect.setY(rect.y() - adjust)
        rect.setHeight(rect.height() + adjust)
        rect.setWidth(rect.width() + adjust)
        self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        self.scene().invalidate()

    def _save_selection(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        elif QtCore.Qt.ShiftModifier != event.modifiers():
            return
        self._selected = [ i for i in self._items if i.isSelected() ]

    def _restore_selection(self, event):
        if QtCore.Qt.ShiftModifier != event.modifiers():
            return
        for item in self._selected:
            if item.skipped:
                item.skipped = False
                continue
            item.setSelected(True)

    def _handle_event(self, eventhandler, event):
        self.update()
        self._save_selection(event)
        eventhandler(self, event)
        self._restore_selection(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MidButton:
            pos = event.pos()
            self._mouse_start = [pos.x(), pos.y()]
            self._saved_matrix = QtGui.QMatrix(self.matrix())
            self._panning = True
            return
        self._handle_event(QtGui.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self._panning:
            self._pan(event)
            return
        self._last_mouse[0] = pos.x()
        self._last_mouse[1] = pos.y()
        self._handle_event(QtGui.QGraphicsView.mouseMoveEvent, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MidButton:
            self._panning = False
            return
        self._handle_event(QtGui.QGraphicsView.mouseReleaseEvent, event)
        self._selected = []

    def _pan(self, event):
        pos = event.pos()
        dx = pos.x() - self._mouse_start[0]
        dy = pos.y() - self._mouse_start[1]

        if dx == 0 and dy == 0:
            return

        rect = QtCore.QRect(0, 0, abs(dx), abs(dy))
        delta = self.mapToScene(rect).boundingRect()

        tx = delta.width()
        if dx < 0.0:
            tx = -tx

        ty = delta.height()
        if dy < 0.0:
            ty = -ty

        matrix = QtGui.QMatrix(self._saved_matrix).translate(tx, ty)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def wheelEvent(self, event):
        """Handle Qt mouse wheel events."""
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self._wheel_zoom(event)
        else:
            self._wheel_pan(event)

    def _wheel_zoom(self, event):
        """Handle mouse wheel zooming."""
        zoom = math.pow(2.0, event.delta() / 512.0)
        factor = (self.matrix()
                        .scale(zoom, zoom)
                        .mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
                        .width())
        if factor < 0.02 or factor > 42.0:
            return
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self._zoom = zoom
        self.scale(zoom, zoom)

    def _wheel_pan(self, event):
        """Handle mouse wheel panning."""
        factor = (self.matrix()
                      .mapRect(QtCore.QRectF(0.0, 0.0, 25.0, 25.0)).width())

        if event.delta() < 0:
            s = -1.0
        else:
            s = 1.0

        matrix = QtGui.QMatrix(self.matrix()).translate(0, s * factor)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def _move_nodes_to_mouse_position(self):
        items = self.scene().selectedItems()
        if not items:
            return
        dx = 0
        dy = 0
        min_distance = sys.maxint
        for item in items:
            width = item.boundingRect().width()
            pos = item.pos()
            tmp_dx = self._last_mouse[0] - pos.x() - width/2.0
            tmp_dy = self._last_mouse[1] - pos.y() - width/2.0
            distance = math.sqrt(tmp_dx ** 2 + tmp_dy ** 2)
            if distance < min_distance:
                min_distance = distance
                dx = tmp_dx
                dy = tmp_dy
        for item in items:
            pos = item.pos()
            x = pos.x();
            y = pos.y()
            item.setPos( x + dx, y + dy )

    def setBackgroundColor(self, color=None):
        # To set a gradient background brush we need to use StretchToDeviceMode
        # but that seems to be segfaulting. Use a solid background.
        if not color:
            #color = QtGui.QGradient()
            #color.setCoordinateMode(QtGui.QGradient.StretchToDeviceMode)
            #color.setColorAt(0, QtCore.Qt.darkGray)
            #color.setColorAt(1, QtCore.Qt.black)
            color = QtGui.QColor(50,50,50)
        self.setBackgroundBrush(color)

    def _scale_view(self, scale):
        factor = (self.matrix().scale(scale, scale)
                               .mapRect(QtCore.QRectF(0, 0, 1, 1))
                               .width())
        if factor < 0.07 or factor > 100:
            return
        self._zoom = scale
        self.scale(scale, scale)

    def add(self, commits):
        self._commits = {}
        self._edges = {}
        self._nodes = {}
        scene = self.scene()
        for commit in commits:
            self._commits[commit.sha1] = commit
            for p in commit.parents:
                edgelist = self._edges.setdefault(p, [])
                edgelist.append(commit.sha1)
            node = Node(self, commit)
            scene.addItem(node)
            self._nodes[commit.sha1] = node
            self._items.append(node)


    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            node = self._nodes[commit.sha1]
            for parent in commit.parents:
                if parent not in self._nodes:
                    continue
                parent = self._nodes[parent]
                scene.addItem(Edge(parent, node))

    def layout(self, commits):
        gxmax = 0
        gymax = 0
        xpos = 0
        ypos = 0
        self._loc = {}
        self._cols = {}
        for commit in commits:
            if commit.sha1 not in self._edges:
                self._loc[commit.sha1] = (xpos, ypos)
                node = self._nodes.get(commit.sha1, None)
                node.setPos(xpos, ypos)
                xpos += self._xoff
                gxmax = max(xpos, gxmax)
                continue
            ymax = 0
            xmax = None
            for sha1 in self._edges[commit.sha1]:
                loc = self._loc[sha1]
                if xmax is None:
                    xmax = loc[0]
                xmax = min(xmax, loc[0])
                ymax = max(ymax, loc[1])
                gxmax = max(gxmax, xmax)
                gymax = max(gymax, ymax)
            if xmax is None:
                xmax = 0
            ymax += self._yoff
            gymax = max(gymax, ymax)
            if ymax in self._cols:
                xmax = max(xmax, self._cols[ymax] + self._xoff)
                gxmax = max(gxmax, xmax)
                self._cols[ymax] = xmax
            else:
                xmax = max(0, xmax)
                self._cols[ymax] = xmax

            sha1 = commit.sha1
            self._loc[sha1] = (xmax, ymax)
            node = self._nodes[sha1]
            node.setPos(xmax, ymax)

        xpad = 200
        ypad = 88
        self.scene().setSceneRect(-xpad, -ypad, gxmax+xpad, gymax+ypad*2)

if __name__ == "__main__":
    # Find the source tree
    from os import path
    src = path.dirname(path.dirname(path.dirname(__file__)))
    sys.path.insert(0, path.abspath(src))

    app = QtGui.QApplication(sys.argv)
    view = git_dag()
    sys.exit(app.exec_())
