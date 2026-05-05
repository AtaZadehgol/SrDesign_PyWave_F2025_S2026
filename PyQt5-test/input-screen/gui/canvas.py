# ============================================================================
# File: gui/canvas.py
# ============================================================================

from PyQt5.QtWidgets import QWidget, QDialog
from PyQt5.QtCore import Qt, QRect, QRectF, QPoint, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QPolygonF, QFont
from enum import Enum, auto
from gui.rectangle_dialog import RectangleEditDialog
from gui.source_dialog import SourceEditDialog
from gui.measurement_dialog import MeasurementEditDialog
from gui.advanced_params_dialog import AdvancedParametersDialog
import numpy as np
from decimal import Decimal

class DrawMode(Enum):
    RECTANGLE = auto()
    SOURCE = auto()
    MEASUREMENT = auto()

class DrawingCanvas(QWidget):
    """Canvas widget for EM Wave geometry modeling"""
    selection_changed = pyqtSignal(object)
    domain_loaded = pyqtSignal(int, int, float)  # nx, ny, delta_x

    def __init__(self):
        super().__init__()
        self.rectangles = []  # Now stores grid coordinates
        self.source_points = []  # Now stores grid coordinates
        self.measurement_points = []  # Now stores grid coordinates
        self.draw_history = []      #stores all objects drawn
        self.drawing = False
        self.start_point = None  # Pixel coords during drawing
        self.current_rect = None  # Pixel coords during drawing
        self.mode = DrawMode.RECTANGLE
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: white;")

        self.clipped_rect = None      # the clipped version of current_rect for preview
        self.last_clip_pos = None     # throttle: last mouse pos we ran clipping on

        #canvas settings for us
        self.SNAP_THRESHOLD = 15 #pixels
        self.RADIUS = 8
        self.CLOSE_THRESHOLD = np.ceil(np.sqrt(2*self.RADIUS*self.RADIUS)).astype(int)

        # --- INTEGER GRID VALUES (meters) ---
        self.delta_x = 0.05e-6  # 0.05 micrometers = 50 nanometers
        self.delta_y = 0.05e-6 # 0.05 micrometers = 50 nanometers
        #delta y functionalities in front end ONLY so not used

        # CPML
        self.num_cpml = 20  # default number of cpml layers

        # --- Interior region dimensions (cells) ---
        self.nx = 100     # default number of x cells
        self.ny = 100     # default number of y cells

        self.view_mode = '2d'
        self.grid_margin = 60
        self.pixels_per_grid_x = 50
        self.pixels_per_grid_y = 50
        self.grid_line_density = 1  # 1=Full, 2=Half, 4=Quarter, 0=None
        self.rectangle_counter = 0
        self.source_counter = 0
        self.measurement_counter = 0
        self.mouse_pos = None
        self.drawing_source = False
        self.drawing_measurement = False
        self.source_start_pixel = None
        self.source_preview_end = None

    def pixel_to_grid_x(self, pixel_x):
        """Convert pixel coordinate to grid coordinate (in meters)"""
        grid_area = self.get_grid_rect()
        relative_x = float(pixel_x - grid_area.left())
        grid_cells = relative_x / self.pixels_per_grid_x
        return grid_cells * self.delta_x

    def pixel_to_grid_y(self, pixel_y):
        """Convert pixel coordinate to grid coordinate (in meters)"""
        grid_area = self.get_grid_rect()
        relative_y = float(grid_area.bottom() - pixel_y)
        grid_cells = relative_y / self.pixels_per_grid_y
        return grid_cells * self.delta_y

    def grid_to_pixel_x(self, grid_x):
        """Convert grid coordinate (meters) to pixel coordinate"""
        grid_area = self.get_grid_rect()
        grid_cells = grid_x / self.delta_x
        pixel_x = grid_cells * self.pixels_per_grid_x + grid_area.left()
        return int(pixel_x)

    def grid_to_pixel_y(self, grid_y):
        """Convert grid coordinate (meters) to pixel coordinate"""
        grid_area = self.get_grid_rect()
        grid_cells = grid_y / self.delta_y
        pixel_y = grid_area.bottom() - grid_cells * self.pixels_per_grid_y
        return int(pixel_y)

    def update_pixels_per_cell(self):
        """Recalculate pixels per grid cell based on canvas size and nx/ny"""
        grid_area = self.get_grid_rect()
        self.pixels_per_grid_x = grid_area.width() / self.nx
        self.pixels_per_grid_y = grid_area.height() / self.ny
        self.update()

    def set_domain(self, nx, ny):
        """Set number of grid cells in x and y directions"""
        self.nx = max(1, nx)
        self.ny = max(1, ny)
        self.update_pixels_per_cell()

    def set_grid_spacing(self, delta_x, delta_y):
        """Set grid spacing (expects integer values in meters)"""
        self.delta_x = float(delta_x)
        self.delta_y = float(delta_y)
        self.update_pixels_per_cell()

    def get_grid_rect(self):
        """Get the rectangle defining the grid drawing area"""
        margin_left = 60
        margin_right = 40
        margin_top = 40
        margin_bottom = 85

        return QRect(
            margin_left,
            margin_top,
            self.width() - margin_left - margin_right,
            self.height() - margin_top - margin_bottom
        )

    def grid_rect_to_pixel_rect(self, rect_data):
        """Convert a rectangle's grid coordinates to pixel coordinates for drawing"""
        pixel_x = self.grid_to_pixel_x(rect_data['grid_x'])
        pixel_y = self.grid_to_pixel_y(rect_data['grid_y'])
        pixel_width = int((rect_data['grid_width'] / self.delta_x) * self.pixels_per_grid_x)
        pixel_height = int((rect_data['grid_height'] / self.delta_y) * self.pixels_per_grid_y)
        return QRect(pixel_x, pixel_y, pixel_width, pixel_height)

    def snap_to_grid(self, pixel_x, pixel_y):
        """Snap pixel coordinates to the nearest grid line intersection"""
        grid_area = self.get_grid_rect()
        # Find nearest grid line in x
        relative_x = pixel_x - grid_area.left()
        snapped_x = round(relative_x / self.pixels_per_grid_x) * self.pixels_per_grid_x
        snapped_pixel_x = int(grid_area.left() + snapped_x)

        # Find nearest grid line in y (y axis is flipped)
        relative_y = grid_area.bottom() - pixel_y
        snapped_y = round(relative_y / self.pixels_per_grid_y) * self.pixels_per_grid_y
        snapped_pixel_y = int(grid_area.bottom() - snapped_y)

        return snapped_pixel_x, snapped_pixel_y

    def snap_to_cpml_boundary(self, pixel_x, pixel_y):
        """Snap a pixel coordinate to the inner edge of the CPML if it falls inside it"""
        grid_area = self.get_grid_rect()
        cpml_w = int(self.num_cpml * self.pixels_per_grid_x)
        cpml_h = int(self.num_cpml * self.pixels_per_grid_y)

        inner_left   = grid_area.left()   + cpml_w
        inner_right  = grid_area.right()  - cpml_w
        inner_top    = grid_area.top()    + cpml_h
        inner_bottom = grid_area.bottom() - cpml_h

        snapped_x = max(inner_left, min(pixel_x, inner_right))
        snapped_y = max(inner_top,  min(pixel_y, inner_bottom))
        return snapped_x, snapped_y

    def get_cpml_rects(self):
        """Return four QRects representing the CPML border strips in pixel coords"""
        if self.num_cpml <= 0:
            return []
        grid_area = self.get_grid_rect()
        cpml_w = int(self.num_cpml * self.pixels_per_grid_x)
        cpml_h = int(self.num_cpml * self.pixels_per_grid_y)

        left   = QRect(grid_area.left(),
                    grid_area.top(),
                    cpml_w,
                    grid_area.height())
        right  = QRect(grid_area.right() - cpml_w,
                    grid_area.top(),
                    cpml_w,
                    grid_area.height())
        top    = QRect(grid_area.left(),
                    grid_area.top(),
                    grid_area.width(),
                    cpml_h)
        bottom = QRect(grid_area.left(),
                    grid_area.bottom() - cpml_h,
                    grid_area.width(),
                    cpml_h)
        return [left, right, top, bottom]

    def point_in_cpml(self, pixel_x, pixel_y):
        """Return True if pixel coordinate falls within the CPML border"""
        p = QPoint(pixel_x, pixel_y)
        return any(r.contains(p) for r in self.get_cpml_rects())

    def grid_rect_in_cpml(self, grid_x, grid_y, grid_x2=None, grid_y2=None):
        """Return True if a grid coordinate (or rect) overlaps the CPML zone"""
        px = self.grid_to_pixel_x(grid_x)
        py = self.grid_to_pixel_y(grid_y)
        if grid_x2 is None:
            return self.point_in_cpml(px, py)
        px2 = self.grid_to_pixel_x(grid_x2)
        py2 = self.grid_to_pixel_y(grid_y2)
        obj_rect = QRect(QPoint(min(px,px2), min(py,py2)),
                        QPoint(max(px,px2), max(py,py2)))
        return any(r.intersects(obj_rect) for r in self.get_cpml_rects())

    def set_num_cpml(self, num_cpml):
        self.num_cpml = max(0, num_cpml)
        self.update()

    def set_view_mode(self, mode):
        self.view_mode = mode
        self.update()

    def set_grid_line_density(self, density):
        """Set grid line display density. 1=Full (all needed lines), 2=Half, 4=Quarter, 0=None"""
        self.grid_line_density = density
        self.update()

    def draw_grid(self, painter):
        """Draw grid with micrometer labels"""
        grid_area = self.get_grid_rect()

        # Clear background
        painter.fillRect(self.rect(), QColor(255, 255, 255))


        cpml_color = QColor(125, 165, 250, 255)
        painter.setBrush(QBrush(cpml_color))
        for cpml_rect in self.get_cpml_rects():
            painter.setPen(Qt.NoPen)
            painter.drawRect(cpml_rect)
            painter.setPen(QPen(QColor(0,0,0), 2))
            painter.setFont(QFont('Times New Roman', 11, QFont.Bold))
            painter.drawText(cpml_rect, Qt.AlignCenter, f"CPML")

        # --- DRAW GRID LINES ---
        if self.grid_line_density > 0:
            painter.setPen(QPen(QColor(220, 220, 220), 1))
            step_x = self.pixels_per_grid_x * self.grid_line_density
            step_y = self.pixels_per_grid_y * self.grid_line_density

            x = grid_area.left()
            while x <= grid_area.right() + 1:
                painter.drawLine(x, grid_area.top(), x, grid_area.bottom())
                x += step_x

            y = grid_area.bottom()
            while y >= grid_area.top() - 1:
                painter.drawLine(grid_area.left(), y, grid_area.right(), y)
                y -= step_y

        # --- DRAW AXES ---
        axis_pen = QPen(QColor(0, 0, 0), 2)
        painter.setPen(axis_pen)
        # Bottom X-Axis
        painter.drawLine(grid_area.left(), grid_area.bottom(), grid_area.right(), grid_area.bottom())
        # Left Y-Axis
        painter.drawLine(grid_area.left(), grid_area.top(), grid_area.left(), grid_area.bottom())

        # --- LABELS & TICKS (convert meters to micrometers for display) ---
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))

        #axis labels
        painter.drawText(grid_area.width()/2, grid_area.bottom() + 35, f"x (µm)")
        painter.drawText(grid_area.left() - 55, grid_area.top()-10, f"y (µm)")

        # Delta Labels (convert meters to micrometers)
        font.setBold(True)
        painter.setFont(font)
        delta_x_um = self.delta_x * 1e6  # Convert meters to µm
        delta_y_um = self.delta_y * 1e6  # Convert meters to µm
        painter.drawText(grid_area.right() - 100, grid_area.bottom() + 35, f"Δx: {delta_x_um:.3f} µm")
        painter.drawText(grid_area.left() - 55, grid_area.top() - 25, f"Δy: {delta_y_um:.3f} µm")
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)

        # X-Axis Ticks and Labels (convert meters to micrometers)
        x = grid_area.left()
        x_value = 0.0  # In meters
        # ensure there aren't too many ticks
        if (self.nx > 30):
            x_inc = int(grid_area.width() / 20)
        else:
            x_inc = self.pixels_per_grid_x
        while x <= grid_area.right() + 1:
            painter.drawLine(x, grid_area.bottom() - 5, x, grid_area.bottom() + 5)
            x_value_um = x_value * 1e6  # Convert to micrometers for display
            painter.drawText(x - 20, grid_area.bottom() + 20, f"{x_value_um:.2f}")
            x += x_inc #self.pixels_per_grid_x
            #x_value += self.delta_x  # Increment in meters
            x_value = self.pixel_to_grid_x(x)

        # Y-Axis Ticks and Labels (convert meters to micrometers)
        # in meters because y axis keeps trying to increment at weird amounts
        y_value = 0.0 # meters
        y_inc = (self.ny*self.delta_y)/10
        while y_value <= (self.ny*self.delta_y):
            y = self.grid_to_pixel_y(y_value)
            painter.drawLine(grid_area.left() - 5, y, grid_area.left() + 5, y)
            y_value_um = y_value * 1e6  # Convert to micrometers for display
            painter.drawText(grid_area.left() - 45, y + 5, f"{y_value_um:.2f}")
            y_value += y_inc  # Increment in meters


    def set_mode(self, mode):
        if isinstance(mode, str):
            mode_map = {
                'rectangle': DrawMode.RECTANGLE,
                'source': DrawMode.SOURCE,
                'measurement': DrawMode.MEASUREMENT
            }
            mode = mode_map.get(mode.lower(), DrawMode.RECTANGLE)
        self.mode = mode

    def mousePressEvent(self, event):
        grid_area = self.get_grid_rect()

        if event.button() == Qt.LeftButton:
            # Prevent drawing outside grid
            if not grid_area.contains(event.pos()):
                return

            if self.mode == DrawMode.RECTANGLE:
                # Block if start point is inside an existing rectangle
                for r in self.rectangles:
                    if self.grid_rect_to_pixel_rect(r).contains(event.pos()):
                        return
                self.drawing = True
                self.start_point = event.pos()
                self.current_rect = QRect(self.start_point, self.start_point)
                self.clipped_rect = None


            elif self.mode == DrawMode.SOURCE:
                #check if clicking near an existing source - skip creation if so
                click_pos = event.pos()
                for src in self.source_points:
                    px = self.grid_to_pixel_x(src['grid_x'])
                    py = self.grid_to_pixel_y(src['grid_y'])
                    hit = False
                    if src.get('shape') == 'Line':
                        px2 = self.grid_to_pixel_x(src['grid_x2'])
                        py2 = self.grid_to_pixel_y(src['grid_y2'])
                        lx, ly = px2 - px, py2 - py
                        length_sq = lx * lx + ly * ly
                        if length_sq > 0:
                            t = max(0, min(1, ((click_pos.x() - px) * lx + (click_pos.y() - py) * ly) / length_sq))
                            nearest = QPoint(int(px + t * lx), int(py + t * ly))
                            hit = (nearest - click_pos).manhattanLength() <self.CLOSE_THRESHOLD
                    else:
                        hit = (QPoint(px, py) - click_pos).manhattanLength() <self.CLOSE_THRESHOLD
                    if hit:
                        return # let double click handle deal

                #start drawing - don't create source yet
                if not self.drawing_source:
                    self.drawing_source = True
                    self.source_start_pixel = QPoint(event.pos())
                    self.source_preview_end = QPoint(event.pos())

            elif self.mode == DrawMode.MEASUREMENT:
                #check if clicking near existing measurement
                click_pos = event.pos()
                for mp in self.measurement_points:
                    px = self.grid_to_pixel_x(mp['grid_x'])
                    py = self.grid_to_pixel_y(mp['grid_y'])
                    if mp.get('shape') == 'Line':
                        px2 = self.grid_to_pixel_x(mp['grid_x2'])
                        py2 = self.grid_to_pixel_y(mp['grid_y2'])
                        lx, ly = px2 - px, py2 - py
                        length_sq = lx * lx + ly * ly
                        if length_sq > 0:
                            t = max(0, min(1, ((click_pos.x() - px) * lx + (click_pos.y() - py) * ly) / length_sq))
                            nearest = QPoint(int(px + t * lx), int(py + t * ly))
                            if (nearest - click_pos).manhattanLength() < 12:
                                return
                    elif mp.get('shape') == 'Surface':
                        mp_rect = QRect(
                            self.grid_to_pixel_x(mp['grid_x']),
                            self.grid_to_pixel_y(mp['grid_y2']),  # y is flipped
                            int((abs(mp['grid_x2'] - mp['grid_x']) / self.delta_x) * self.pixels_per_grid_x),
                            int((abs(mp['grid_y2'] - mp['grid_y']) / self.delta_y) * self.pixels_per_grid_y)
                        )
                        if mp_rect.contains(click_pos):
                            return
                    else:
                        if (QPoint(px, py) - click_pos).manhattanLength() < 20:
                            return
                # Start drawing
                if not self.drawing_measurement:
                    self.drawing_measurement = True
                    self.measurement_start_pixel = QPoint(event.pos())
                    self.measurement_preview_end = QPoint(event.pos())

        elif event.button() == Qt.RightButton:
            click_pos = event.pos()

            # 1. Check Source Points
            for src_data in self.source_points:
                # Convert stored grid coords to pixel coords for hit testing
                pixel_x = self.grid_to_pixel_x(src_data['grid_x'])
                pixel_y = self.grid_to_pixel_y(src_data['grid_y'])
                pixel_point = QPoint(pixel_x, pixel_y)
                hit = False
                distance = (pixel_point - click_pos).manhattanLength()
                if src_data.get('shape') == 'Line':
                    px2 = self.grid_to_pixel_x(src_data['grid_x2'])
                    py2 = self.grid_to_pixel_y(src_data['grid_y2'])
                    lx, ly = px2 - pixel_x, py2 - pixel_y
                    length_sq = lx * lx + ly * ly
                    if length_sq > 0:
                        t = max(0, min(1, ((click_pos.x() - pixel_x) * lx + (click_pos.y() - pixel_y) * ly) / length_sq))
                        nearest = QPoint(int(pixel_x + t * lx), int(pixel_y + t * ly))
                        hit = (nearest - click_pos).manhattanLength() < self.CLOSE_THRESHOLD
                    else:
                        hit = distance < self.CLOSE_THRESHOLD
                else:
                    hit = distance < self.CLOSE_THRESHOLD
                if hit:
                    dialog = SourceEditDialog(src_data, self.delta_x, canvas=self, parent=self)
                    if dialog.exec_() == QDialog.Accepted:
                        props = dialog.get_properties()
                        if props.get("delete_flag"):
                            self.source_points.remove(src_data)
                    self.update()
                    return

            # 2. Check Measurement Points
            #TODO
            for mp_data in self.measurement_points:
                # Convert stored grid coords to pixel coords for hit testing
                pixel_x = self.grid_to_pixel_x(mp_data['grid_x'])
                pixel_y = self.grid_to_pixel_y(mp_data['grid_y'])
                pixel_point = QPoint(pixel_x, pixel_y)
                hit = False
                distance = (pixel_point - click_pos).manhattanLength()
                if mp_data.get('shape') == 'Line':
                    px2 = self.grid_to_pixel_x(mp_data['grid_x2'])
                    py2 = self.grid_to_pixel_y(mp_data['grid_y2'])
                    lx, ly = px2 - pixel_x, py2 - pixel_y
                    length_sq = lx * lx + ly * ly
                    if length_sq > 0:
                        t = max(0, min(1, ((click_pos.x() - pixel_x) * lx + (click_pos.y() - pixel_y) * ly) / length_sq))
                        nearest = QPoint(int(pixel_x + t * lx), int(pixel_y + t * ly))
                        hit = (nearest - click_pos).manhattanLength() < self.CLOSE_THRESHOLD
                    else:
                        hit = distance < self.CLOSE_THRESHOLD
                elif mp_data.get('shape') == 'Surface':
                    pixel_rect = self.grid_rect_to_pixel_rect(mp_data)
                    #Check if point is in surface rectangle
                    hit =  pixel_rect.contains(click_pos)
                else:
                    # Point (& radius)
                    hit = distance < self.CLOSE_THRESHOLD

                if hit:
                    dialog = MeasurementEditDialog(mp_data, self.delta_x, canvas=self, parent=self)
                    if dialog.exec_() == QDialog.Accepted:
                        props = dialog.get_properties()
                        if props.get("delete_flag"):
                            self.measurement_points.remove(mp_data)
                    self.update()
                    return

            # 3. Check Rectangles
            for rect_data in reversed(self.rectangles):
                # Convert stored grid coords to pixel rect for hit testing
                pixel_rect = self.grid_rect_to_pixel_rect(rect_data)
                if pixel_rect.contains(click_pos):
                    dialog = RectangleEditDialog(rect_data, self.delta_x, canvas=self, parent=self)
                    if dialog.exec_() == QDialog.Accepted:
                        props = dialog.get_properties()
                        if props.get("delete_flag", False):
                            self.rectangles.remove(rect_data)
                        else:
                            # Update grid coordinates directly
                            rect_data.update(props)


                    self.selection_changed.emit(None)
                    self.update()
                    return

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        if self.drawing and self.mode == DrawMode.RECTANGLE:
            grid_area = self.get_grid_rect()

            # Clamp to grid area        #TODO: clamp to interior region area!
            clamped_x = max(grid_area.left(), min(event.pos().x(), grid_area.right()))
            clamped_y = max(grid_area.top(), min(event.pos().y(), grid_area.bottom()))
            #if you wanted to preview rectangle snapped to grid - laggy
            #sx, sy = self.snap_to_grid(clamped_x, clamped_y)
            #self.current_rect = QRect(self.start_point, QPoint(sx, sy)).normalized()
            self.current_rect = QRect(self.start_point, QPoint(clamped_x, clamped_y)).normalized()

            ''' #shows rectangle clipped as drawn - but more laggy
            # Throttle: only recompute clip if mouse moved > 5px
            pos = event.pos()
            if self.last_clip_pos is None or (pos - self.last_clip_pos).manhattanLength() > 5:
                self.clipped_rect = self.clip_rect_against_existing(self.current_rect)
                self.last_clip_pos = pos
            '''

        if self.drawing_source and self.mode == DrawMode.SOURCE:
            self.source_preview_end = event.pos()

        if self.drawing_measurement and self.mode == DrawMode.MEASUREMENT:
            #TODO: clamp measurements?
            self.measurement_preview_end = event.pos()

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            # Recompute final clip at release position
            final_rect = self.clip_rect_against_existing(self.current_rect)
            '''
            if self.current_rect and self.current_rect.width() > 5:
                # Convert pixel rectangle to grid coordinates
                grid_x = self.pixel_to_grid_x(self.current_rect.x())
                grid_y = self.pixel_to_grid_y(self.current_rect.y())
                grid_width = (self.current_rect.width() / self.pixels_per_grid_x) * self.delta_x
                grid_height = (self.current_rect.height() / self.pixels_per_grid_y) * self.delta_y
            '''
            if final_rect and final_rect.width() > 5 and final_rect.height() > 5:
                '''
                    Snap rectangle to grid
                    and round to nearest delta x just for user appearance, makes no backend difference
                    (removing .001 from pixels not aligning with delta x)
                '''
                finalx, finaly = self.snap_to_grid(final_rect.x(), final_rect.y())
                grid_x = round(self.pixel_to_grid_x(finalx), 8)
                grid_y = round(self.pixel_to_grid_y(finaly), 8)

                finalw, finalh = self.snap_to_grid(final_rect.width() + finalx, final_rect.height()+ finaly)
                finalw = finalw - finalx
                finalh = finalh - finaly
                grid_width= (finalw / self.pixels_per_grid_x) * self.delta_x
                grid_height = (finalh / self.pixels_per_grid_y) * self.delta_y

                #round again
                grid_width = round(grid_width, 8)
                grid_height = round(grid_height, 8)

                # Auto-generate name and color
                self.rectangle_counter += 1
                rect_name = f"W_{self.rectangle_counter}"
                base_hue = (self.rectangle_counter * 40) % 360
                color = QColor.fromHsv(base_hue, 180, 230, 100)

                rect_data = {
                    'grid_x': grid_x,
                    'grid_y': grid_y,
                    'grid_width': grid_width,
                    'grid_height': grid_height,
                    'name': rect_name,
                    'material': 'Silicon',
                    'permittivity': 11.7,
                    'permeability': 1.0,
                    'conductivity': 0.0,
                    "rough_toggle": False,
                    "rough_std": 15.0e-9,
                    "rough_acl": 700.0e-9,
                    "ctype": 3,
                    "tol_std": 10.0,
                    "tol_acl": 10.0,
                    'color': color
                }
                self.rectangles.append(rect_data)
                self.draw_history.append(('rectangle', rect_data))
                self.selection_changed.emit(None)
            self.current_rect = None
            self.clipped_rect = None
            self.last_clip_pos = None
            self.update()

        if event.button() == Qt.LeftButton and self.drawing_source:
            self.drawing_source = False
            start = self.source_start_pixel
            end = event.pos()
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            drag_distance = (QPoint(dx, dy)).manhattanLength()

            self.source_counter += 1
            source_name = f"S {self.source_counter}"
            color = QColor.fromHsv(0, 200, 200)

            # snap to grid
            startx, starty = self.snap_to_grid(start.x(), start.y())
            endx, endy = self.snap_to_grid(end.x(), end.y())

            # snap to CPML boundary if necessary
            sx, sy = self.snap_to_cpml_boundary(startx, starty)
            # Convert to grid coordinates for storage
            grid_x = self.pixel_to_grid_x(sx)
            grid_y = self.pixel_to_grid_y(sy)

            # snap to CPML boundary if necessary
            """ sx, sy = self.snap_to_cpml_boundary(
                self.grid_to_pixel_x(grid_x),
                self.grid_to_pixel_y(grid_y)
            ) """

            # round to nearest delta x - just for user appearance, makes no backend difference (removing .001 from pixels not aligning with delta x)
            grid_x = round(grid_x, 8)
            grid_y = round(grid_y, 8)

            source_data = {
                'grid_x': grid_x,
                'grid_y': grid_y,
                'shape': 'Point',
                'name': source_name,
                'source_type': 'Gaussian Pulse',
                'amplitude': 20.0,
                'frequency': 194.8e12,
                'gauss_pulse_deg': -6.0,
                'gp_tsp_coef': 1.0,
                'gp_tpk_coef': 9.0,
                'wave_packet_bw': 0.1,
                'wp_tsp_coef': 2.0,
                'wp_tpk_coef': 9.0,
                'color': color
            }
            source_data['grid_x2'] = grid_x
            source_data['grid_y2'] = grid_y
            if drag_distance < self.RADIUS:
                #short drag = point
                source_data['shape'] = 'Point'

            else:
                # long drag = line
                source_data['shape'] = 'Line'
                # Rename it - not necessary if name is just S x
                #source_name = f"Source Line {self.source_counter}"
                source_data['name'] = source_name

                if abs(dx) >= abs(dy):
                    #horizontal
                    source_data['grid_x2'] = round(self.pixel_to_grid_x(endx), 8)
                else:
                    #vertical
                    source_data['grid_y2'] = round(self.pixel_to_grid_y(endy), 8)

                # clip line endpoint if in cpml
                if self.point_in_cpml(self.grid_to_pixel_x(source_data['grid_x2']),
                          self.grid_to_pixel_y(source_data['grid_y2'])):
                    ex, ey = self.snap_to_cpml_boundary(
                        self.grid_to_pixel_x(source_data['grid_x2']),
                        self.grid_to_pixel_y(source_data['grid_y2'])
                    )
                    source_data['grid_x2'] = self.pixel_to_grid_x(ex)
                    source_data['grid_y2'] = self.pixel_to_grid_y(ey)

            self.source_points.append(source_data)
            self.draw_history.append(('source', source_data))

            self.source_start_pixel = None
            self.source_preview_end = None

            self.selection_changed.emit((grid_x, grid_y, 0))
            self.update()

        if event.button() == Qt.LeftButton and self.drawing_measurement:
            self.drawing_measurement = False
            start = self.measurement_start_pixel
            end = event.pos()
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            abs_dx, abs_dy = abs(dx), abs(dy)

            self.measurement_counter += 1
            mp_name = f"M {self.measurement_counter}"
            color = QColor(0, 120, 80)

            # snap to grid
            startx, starty = self.snap_to_grid(start.x(), start.y())
            endx, endy = self.snap_to_grid(end.x(), end.y())

            # Convert to grid coordinates for storage
            grid_x = self.pixel_to_grid_x(startx)
            grid_y = self.pixel_to_grid_y(starty)

            # round to nearest delta x - just for user appearance, makes no backend difference (removing .001 from pixels not aligning with delta x)
            grid_x = round(grid_x, 8)
            grid_y = round(grid_y, 8)

            mp_data = {
                'grid_x': grid_x,
                'grid_y': grid_y,
                'grid_x2': grid_x,
                'grid_y2': grid_y,
                'name': mp_name,
                'shape': 'Point',
                'color': color
            }

            SNAP = self.SNAP_THRESHOLD  # pixels
            if (QPoint(dx, dy)).manhattanLength() < self.RADIUS:
                mp_data['shape'] = 'Point'
            elif abs_dx < SNAP:
                # mostly vertical = line
                mp_data['shape'] = 'Line'
                mp_data['grid_y2'] = round(self.pixel_to_grid_y(endy), 8)
            elif abs_dy < SNAP:
                # mostly horizontal = line
                mp_data['shape'] = 'Line'
                mp_data['grid_x2'] = round(self.pixel_to_grid_x(endx), 8)
            else:
                # both axes = surface (rectangle)
                mp_data['shape'] = 'Surface'
                mp_data['grid_x2'] = round(self.pixel_to_grid_x(endx), 8)
                mp_data['grid_y2'] = round(self.pixel_to_grid_y(endy), 8)

            mp_data['grid_width'] = abs(mp_data['grid_x'] - mp_data['grid_x2'])
            mp_data['grid_height'] = abs(mp_data['grid_y'] - mp_data['grid_y2'])

            self.measurement_points.append(mp_data)
            self.draw_history.append(('measurement', mp_data))
            self.measurement_start_pixel = None
            self.measurement_preview_end = None
            self.selection_changed.emit((grid_x, grid_y, 0))
            self.update()

    def mouseDoubleClickEvent(self, event):
        # Same logic as Right Click basically
        if event.button() == Qt.LeftButton:
            click_pos = event.pos()

            for rect_data in reversed(self.rectangles):
                pixel_rect = self.grid_rect_to_pixel_rect(rect_data)
                if pixel_rect.contains(click_pos):
                    dialog = RectangleEditDialog(rect_data, self.delta_x, canvas=self, parent=self)
                    if dialog.exec_() == QDialog.Accepted:
                        props = dialog.get_properties()
                        if props.get("delete_flag", False):
                            self.rectangles.remove(rect_data)
                        else:
                            # Update grid coordinates directly
                            rect_data.update(props)

                    self.selection_changed.emit(None)
                    self.update()
                    return

            for source_data in reversed(self.source_points):
                pixel_x = self.grid_to_pixel_x(source_data['grid_x'])
                pixel_y = self.grid_to_pixel_y(source_data['grid_y'])
                pixel_point = QPoint(pixel_x, pixel_y)
                hit = False
                distance = (pixel_point - click_pos).manhattanLength()
                if source_data.get('shape') == 'Line':
                    px2 = self.grid_to_pixel_x(source_data['grid_x2'])
                    py2 = self.grid_to_pixel_y(source_data['grid_y2'])
                    lx, ly = px2 - pixel_x, py2 - pixel_y
                    length_sq = lx * lx + ly * ly
                    if length_sq > 0:
                        t = max(0, min(1, ((click_pos.x() - pixel_x) * lx + (click_pos.y() - pixel_y) * ly) / length_sq))
                        nearest = QPoint(int(pixel_x + t * lx), int(pixel_y + t * ly))
                        hit = (nearest - click_pos).manhattanLength() < self.CLOSE_THRESHOLD
                    else:
                        hit = distance < self.CLOSE_THRESHOLD
                else:
                    hit = distance < self.CLOSE_THRESHOLD
                if hit:
                    dialog = SourceEditDialog(source_data, self.delta_x, canvas=self, parent=self)
                    if dialog.exec_() == QDialog.Accepted:
                        props = dialog.get_properties()
                        if props.get("delete_flag"):
                            self.source_points.remove(source_data)
                    self.selection_changed.emit(None)
                    self.update()
                    return

            for measurement_data in reversed(self.measurement_points):
                pixel_x = self.grid_to_pixel_x(measurement_data['grid_x'])
                pixel_y = self.grid_to_pixel_y(measurement_data['grid_y'])
                pixel_point = QPoint(pixel_x, pixel_y)
                hit = False
                distance = (pixel_point - click_pos).manhattanLength()
                if measurement_data.get('shape') == 'Line':
                    px2 = self.grid_to_pixel_x(measurement_data['grid_x2'])
                    py2 = self.grid_to_pixel_y(measurement_data['grid_y2'])
                    lx, ly = px2 - pixel_x, py2 - pixel_y
                    length_sq = lx * lx + ly * ly
                    if length_sq > 0:
                        t = max(0, min(1, ((click_pos.x() - pixel_x) * lx + (click_pos.y() - pixel_y) * ly) / length_sq))
                        nearest = QPoint(int(pixel_x + t * lx), int(pixel_y + t * ly))
                        hit = (nearest - click_pos).manhattanLength() < self.CLOSE_THRESHOLD
                    else:
                        hit = distance < self.CLOSE_THRESHOLD
                elif measurement_data.get('shape') == 'Surface':
                    pixel_rect = self.grid_rect_to_pixel_rect(measurement_data)
                    #Check if point is in surface rectangle
                    hit =  pixel_rect.contains(click_pos)
                else:
                    # Point
                    hit = distance < self.CLOSE_THRESHOLD

                if hit:
                    dialog = MeasurementEditDialog(measurement_data, self.delta_x, canvas=self, parent=self)
                    if dialog.exec_() == QDialog.Accepted:
                        props = dialog.get_properties()
                        if props.get("delete_flag"):
                            self.measurement_points.remove(measurement_data)
                    self.selection_changed.emit(None)
                    self.update()
                    return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.draw_grid(painter)
        if self.view_mode == '2d':
            self.draw_2d_view(painter)
        else:
            self.draw_3d_view(painter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_pixels_per_cell()

    def draw_2d_view(self, painter):
        grid_area = self.get_grid_rect()
        #painter.setClipRect(grid_area)  #don't show objects when they appear outside grid area

        # Draw rectangles (convert from grid coords to pixel coords)
        for rect_data in self.rectangles:
            pixel_rect = self.grid_rect_to_pixel_rect(rect_data)

            color = rect_data.get('color', QColor(100, 200, 255, 100))
            if isinstance(color, QColor): painter.setBrush(QBrush(color))
            elif isinstance(color, (list, tuple)): painter.setBrush(QBrush(QColor(*color)))
            else: painter.setBrush(QBrush(QColor(100, 200, 255, 100)))

            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawRect(pixel_rect)
            painter.setFont(QFont('Times New Roman', 11, QFont.Bold))
            painter.drawText(pixel_rect, Qt.AlignCenter, f"{rect_data.get('name')}\n{rect_data.get('material')}")

        # Draw current rectangle being drawn (already in pixel coords)
        if self.current_rect:

            painter.setPen(QPen(QColor(0, 0, 255), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(100, 200, 255, 100)))
            painter.drawRect(self.current_rect)
            ''' #shows clipped rectangle as drawn, more lag
            if self.clipped_rect is not None:
                painter.setPen(QPen(QColor(0, 0, 255), 2, Qt.DashLine))
                painter.setBrush(QBrush(QColor(100, 200, 255, 100)))
                painter.drawRect(self.clipped_rect)
            else:
                # Start blocked or fully collapsed — draw red to signal invalid
                painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.DashLine))
                painter.setBrush(QBrush(QColor(255, 100, 100, 60)))
                painter.drawRect(self.current_rect)
            '''

        # Draw source points (convert from grid coords to pixel coords)
        for src in self.source_points:
            pixel_x = self.grid_to_pixel_x(src['grid_x'])
            pixel_y = self.grid_to_pixel_y(src['grid_y'])
            pixel_point = QPoint(pixel_x, pixel_y)

            painter.setBrush(QBrush(src['color']))
            painter.setPen(QPen(src['color'].darker(150), 2))
            if src.get('shape') == 'Line':
                px2 = self.grid_to_pixel_x(src['grid_x2'])
                py2 = self.grid_to_pixel_y(src['grid_y2'])
                painter.drawLine(pixel_x, pixel_y, px2, py2)
                # Draw small circles at each endpoint
                painter.drawEllipse(pixel_point, 5, 5)
                painter.drawEllipse(QPoint(px2, py2), 5, 5)
                mid_x = (pixel_x + px2) // 2
                mid_y = (pixel_y + py2) // 2
                painter.drawText(mid_x + 8, mid_y - 4, src['name'])
            else:
                painter.drawEllipse(pixel_point, self.RADIUS, self.RADIUS)
                painter.drawText(pixel_point.x() + 12, pixel_point.y() + 5, src['name'])

        # Draw source drag preview (source currently being drawn)
        if self.drawing_source and self.source_start_pixel and self.source_preview_end:
            start = self.source_start_pixel
            end = self.source_preview_end
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            painter.setPen(QPen(QColor(255, 80, 80), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(255, 80, 80, 80)))
            if (QPoint(dx, dy)).manhattanLength() < self.RADIUS:
                painter.drawEllipse(start, self.RADIUS, self.RADIUS)
            elif abs(dx) >= abs(dy):
                painter.drawLine(start.x(), start.y(), end.x(), start.y())
            else:
                painter.drawLine(start.x(), start.y(), start.x(), end.y())

        # Draw Measurement Points
        GREEN = QColor(0, 120, 80)
        for mp in self.measurement_points:
            painter.setBrush(QBrush(mp['color']))
            painter.setPen(QPen(mp['color'].darker(150), 2))
            px = self.grid_to_pixel_x(mp['grid_x'])
            py = self.grid_to_pixel_y(mp['grid_y'])
            shape = mp.get('shape', 'Point')
            color = mp.get('color', GREEN)
            if isinstance(color, (list, tuple)):
                color = QColor(*color)
            painter.setPen(QPen(color.darker(150), 2))
            painter.setBrush(QBrush(color))
            if shape == 'Line':
                px2 = self.grid_to_pixel_x(mp['grid_x2'])
                py2 = self.grid_to_pixel_y(mp['grid_y2'])
                painter.drawLine(px, py, px2, py2)
                painter.drawRect(px - 4, py - 4, 8, 8)
                painter.drawRect(px2 - 4, py2 - 4, 8, 8)
                painter.drawText((px + px2) // 2 + 6, (py + py2) // 2, mp.get('name', 'M'))
            elif shape == 'Surface':
                px2 = self.grid_to_pixel_x(mp['grid_x2'])
                py2 = self.grid_to_pixel_y(mp['grid_y2'])
                surf_rect = QRect(QPoint(min(px,px2), min(py,py2)), QPoint(max(px,px2), max(py,py2)))
                painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 60)))
                painter.drawRect(surf_rect)
                painter.drawText(surf_rect, Qt.AlignCenter, mp.get('name', 'M'))
            else:   #Point
                painter.drawRect(px - 4, py - 4, 8, 8)
                painter.drawText(px + 10, py + 5, mp.get('name', 'M'))

        # Draw measurement drag preview
        if self.drawing_measurement and self.measurement_start_pixel and self.measurement_preview_end:
            start = self.measurement_start_pixel
            end = self.measurement_preview_end
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            abs_dx, abs_dy = abs(dx), abs(dy)
            painter.setPen(QPen(GREEN, 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 120, 80, 60)))
            SNAP = 15
            if (QPoint(dx, dy)).manhattanLength() < self.RADIUS:
                painter.drawRect(start.x() - 4, start.y() - 4, 8, 8)
            elif abs_dx < SNAP:
                painter.drawLine(start.x(), start.y(), start.x(), end.y())
            elif abs_dy < SNAP:
                painter.drawLine(start.x(), start.y(), end.x(), start.y())
            else:
                painter.drawRect(QRect(start, end).normalized())

        painter.setClipping(False)

    def draw_3d_view(self, painter):
        iso_angle = 0.5
        z_scale = 0.3
        default_height = 50

        def draw_rect_3d(rect, h, color_top, color_side, label=""):
            x1, y1 = rect.x(), rect.y()
            x2, y2 = x1 + rect.width(), y1
            x3, y3 = x1 + rect.width(), y1 + rect.height()
            x4, y4 = x1, y1 + rect.height()

            x1_t, y1_t = x1 - h * iso_angle, y1 - h * z_scale
            x2_t, y2_t = x2 - h * iso_angle, y2 - h * z_scale
            x3_t, y3_t = x3 - h * iso_angle, y3 - h * z_scale
            x4_t, y4_t = x4 - h * iso_angle, y4 - h * z_scale

            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.setBrush(QBrush(color_side))
            painter.drawPolygon(QPolygonF([QPointF(x1, y1), QPointF(x1_t, y1_t), QPointF(x4_t, y4_t), QPointF(x4, y4)]))
            painter.drawPolygon(QPolygonF([QPointF(x2, y2), QPointF(x2_t, y2_t), QPointF(x3_t, y3_t), QPointF(x3, y3)]))
            painter.drawPolygon(QPolygonF([QPointF(x4, y4), QPointF(x4_t, y4_t), QPointF(x3_t, y3_t), QPointF(x3, y3)]))

            painter.setBrush(QBrush(color_top))
            painter.drawPolygon(QPolygonF([QPointF(x1_t, y1_t), QPointF(x2_t, y2_t), QPointF(x3_t, y3_t), QPointF(x4_t, y4_t)]))

            painter.setPen(Qt.black)
            painter.drawText(int((x1_t + x3_t) / 2), int((y1_t + y3_t) / 2), label)

        # Draw rectangles (convert from grid coords)
        for rect_data in self.rectangles:
            pixel_rect = self.grid_rect_to_pixel_rect(rect_data)
            color = rect_data.get('color', QColor(180, 180, 255, 200))
            if isinstance(color, (list, tuple)): color = QColor(*color)
            draw_rect_3d(pixel_rect, default_height, color, color.darker(120), rect_data.get('name'))

        if self.current_rect:
            draw_rect_3d(self.current_rect, default_height, QColor(0,0,255,100), QColor(0,0,150,100))

    def clear_all(self):
        self.rectangles = []
        self.source_points = []
        self.measurement_points = []
        self.draw_history = []
        self.rectangle_counter = 0
        self.source_counter = 0
        self.measurement_counter = 0
        self.update()

    def update_global_roughness(self, roughnes):
        for rect in self.rectangles:
            rect['rough_toggle'] = roughnes.get('rough_toggle', False)
            rect['rough_std'] = roughnes['rough_std']
            rect['rough_acl'] = roughnes['rough_acl']
            rect['ctype'] = roughnes['ctype']
            rect['tol_std'] = roughnes['tol_std']
            rect['tol_acl'] = roughnes['tol_acl']

    def update_global_source_info(self, sinfo):
        for src in self.source_points:
            src['source_type'] = sinfo['s_type']
            src['amplitude'] = sinfo['amplitude']
            if src['source_type'] == 'Gaussian Pulse':
                src['gauss_pulse_deg'] = sinfo['gauss_pulse_deg']
                src['gp_tpk_coef'] = sinfo['gp_tpk_coef']
                src['gp_tsp_coef'] = sinfo['gp_tsp_coef']
            elif src['source_type'] == 'Wave Packet':
                src['frequency'] = sinfo['frequency']
                src['wave_packet_bw'] = sinfo['wave_packet_bw']
                src['wp_tpk_coef'] = sinfo['wp_tpk_coef']
                src['wp_tsp_coef'] = sinfo['wp_tsp_coef']
            else:
                src['frequency'] = sinfo['frequency']
                src['gp_tpk_coef'] = sinfo['gp_tpk_coef']
                src['gp_tsp_coef'] = sinfo['gp_tsp_coef']


    def remove_last(self):
        if not self.draw_history:
            return
        kind, obj = self.draw_history.pop()
        if kind == 'rectangle':
            self.rectangles.remove(obj)
        elif kind == 'source':
            self.source_points.remove(obj)
        elif kind == 'measurement':
            self.measurement_points.remove(obj)
        self.update()

    def remove_last_rectangle(self):
        if self.rectangles:
            self.rectangles.pop()
            self.update()

    # unused?
    def remove_specific_rectangle(self, rect_data):
        if rect_data in self.rectangles:
            self.rectangles.remove(rect_data)
            self.update()

    def clip_rect_against_existing(self, candidate):
        """
        Clip candidate QRect against all existing rectangles. and cpml
        Returns a QRect that doesn't overlap any existing rectangle,
        clipped from the narrowest side
        Returns None if the start point is inside an existing rectangle.
        """
        result = QRect(candidate)
        start = self.start_point

        # Treat CPML zones as blocking rects too
        blocking_rects = [self.grid_rect_to_pixel_rect(r) for r in self.rectangles]
        blocking_rects += self.get_cpml_rects()

        for existing in blocking_rects:
            if not result.intersects(existing):
                continue
            if existing.contains(start):
                return None

            intersection = result.intersected(existing)
            overlap_x = intersection.width()
            overlap_y = intersection.height()

            if overlap_x <= overlap_y:
                # Smaller overlap in x — clip on x axis
                # Determine which x side to clip
                if result.left() < existing.left():
                    result.setRight(existing.left())
                else:
                    result.setLeft(existing.right())
            else:
                # Smaller overlap in y — clip on y axis
                if result.top() < existing.top():
                    result.setBottom(existing.top())
                else:
                    result.setTop(existing.bottom())

            if result.width() <= 0 or result.height() <= 0:
                return None

        return result

    def get_last_rectangle(self):
        return self.rectangles[-1] if self.rectangles else None

    def get_solver_data(self):
        """Export data in solver-friendly format"""
        '''
        # Calculate grid dimensions in cells
        grid_rect = self.get_grid_rect()
        num_cells_x = grid_rect.width() // self.pixels_per_grid_x
        num_cells_y = grid_rect.height() // self.pixels_per_grid_y
        '''
        num_cells_x = self.nx
        num_cells_y = self.ny

        data = {
            'simulation_type': '', # set by welcome_dialog logic in manager
            'polarization_mode': '',
            'geometry': {
                'rectangles': [],
                'grid_spacing': {
                    'delta_x': float(self.delta_x),
                    'delta_y': float(self.delta_y),
                    'units': 'meters'
                },
                'grid_dimensions': {
                    'nx': num_cells_x, #number of cells in x direction
                    'ny': num_cells_y, #number of cells in y direction
                    'total_cells': num_cells_x * num_cells_y,
                    'domain_width': round(num_cells_x * self.delta_x, 8),
                    'domain_height': round(num_cells_y * self.delta_y, 8)
                }
            },
            'sources': [],
            'measurement_points': [],
            'metadata': {
                'created_by': 'EM Wave Visualization Tool',
                'version': '1.0'
            }
        }

        # Export Rectangles (already in grid coords!)
        for r in self.rectangles:
            # Handle color tuple conversion
            color = r.get('color', QColor(100, 200, 255))
            if isinstance(color, QColor):
                color_tuple = (color.red(), color.green(), color.blue(), color.alpha())
            else:
                color_tuple = color

            rect = {
                'position': {
                    'x': r['grid_x'],
                    'y': r['grid_y']
                },
                'dimensions': {
                    'width': r['grid_width'],
                    'height': r['grid_height']
                },
                'name': r.get('name', 'W_?'),
                'material': {
                    'name': r['material'],
                    'permittivity': r['permittivity'],
                    'permeability': r['permeability'],
                    'conductivity': r['conductivity']
                },
                'roughness': {
                    "rough_toggle": r['rough_toggle']
                },
                'color': color_tuple
            }
            if rect['roughness']['rough_toggle']:
                rect['roughness']["rough_std"] = r['rough_std']
                rect['roughness']["rough_acl"] = r['rough_acl']
                rect['roughness']["ctype"] = r['ctype']
                rect['roughness']["tol_std"] = r['tol_std']
                rect['roughness']["tol_acl"] = r['tol_acl']

            data['geometry']['rectangles'].append(rect)

        # Export Sources (already in grid coords!)
        for s in self.source_points:
            # Handle color
            color = s.get('color', QColor(255, 0, 0))
            if isinstance(color, QColor):
                color_tuple = (color.red(), color.green(), color.blue(), color.alpha())
            else:
                color_tuple = color

            src = {
                'x': s['grid_x'],
                'y': s['grid_y'],
                'name': s.get('name', 'Source'),
                'shape': s.get('shape', 'Point'),
                'source_type': s.get('source_type', 'Gaussian Pulse'),
                'amplitude': float(s.get('amplitude', 1.0)),
                'frequency': float(s.get('frequency', 194.8e12)),
                'color': color_tuple
            }
            s_type = s.get('source_type', 'Gaussian Pulse')
            if s_type == 'Gaussian Pulse':
                src['gauss_pulse_deg'] = float(s.get('gauss_pulse_deg', -6.0))
                src['gp_tsp_coef'] = float(s.get('gp_tsp_coef', 1.0))
                src['gp_tpk_coef'] = float(s.get('gp_tpk_coef', 9.0))
            elif s_type == 'Wave Packet':
                src['wave_packet_bw'] = float(s.get('wave_packet_bw', 0.1))
                src['wp_tsp_coef'] = float(s.get('wp_tsp_coef', 2.0))
                src['wp_tpk_coef'] = float(s.get('wp_tpk_coef', 9.0))
            else:
                src['gp_tsp_coef'] = float(s.get('gp_tsp_coef', 1.0))
                src['gp_tpk_coef'] = float(s.get('gp_tpk_coef', 9.0))

            if s['grid_x'] != s['grid_x2']:
                src['xend'] = s['grid_x2']
            if s['grid_y'] != s['grid_y2']:
                src['yend'] = s['grid_y2']

            data['sources'].append(src)

        # Export Measurement Points (already in grid coords!)
        for mp in self.measurement_points:
            # Handle color
            color = mp.get('color', QColor(255, 0, 0))
            if isinstance(color, QColor):
                color_tuple = (color.red(), color.green(), color.blue(), color.alpha())
            else:
                color_tuple = color

            measure = {
                'x': mp['grid_x'],
                'y': mp['grid_y'],
                'name': mp.get('name', 'Measurement'),
                'shape': mp.get('shape', 'Point'),
                'color': color_tuple
            }
            if mp['grid_x'] != mp['grid_x2']:
                measure['xend'] = mp['grid_x2']
            if mp['grid_y'] != mp['grid_y2']:
                measure['yend'] = mp['grid_y2']

            data['measurement_points'].append(measure)

        return data

    def load_from_data(self, data):
        """Load canvas state from saved project data"""
        # Clear existing data
        self.rectangles.clear()
        self.source_points.clear()
        self.measurement_points.clear()
        self.draw_history = []

        # Load rectangles from geometry data
        if 'geometry' in data and 'rectangles' in data['geometry']:
            for rect_data in data['geometry']['rectangles']:
                # Handle color conversion
                color = rect_data.get('color', (100, 200, 255, 100))
                if isinstance(color, (list, tuple)):
                    color = QColor(*color)

                # Reconstruct rectangle data dictionary
                rect = {
                    'grid_x': rect_data['position']['x'],
                    'grid_y': rect_data['position']['y'],
                    'grid_width': rect_data['dimensions']['width'],
                    'grid_height': rect_data['dimensions']['height'],
                    'name': rect_data.get('name', 'W_?'),
                    'material': rect_data['material']['name'],
                    'permittivity': rect_data['material']['permittivity'],
                    'permeability': rect_data['material']['permeability'],
                    'conductivity': rect_data['material']['conductivity'],
                    'rough_toggle': rect_data['roughness']['rough_toggle'],
                    'color': color
                }
                if rect['rough_toggle']:
                    rect["rough_std"] = rect_data['roughness']['rough_std']
                    rect["rough_acl"] = rect_data['roughness']['rough_acl']
                    rect["ctype"] = rect_data['roughness']['ctype']
                    rect["tol_std"] = rect_data['roughness']['tol_std']
                    rect["tol_acl"] = rect_data['roughness']['tol_acl']

                self.rectangles.append(rect)
                self.draw_history.append(('rectangle', rect))

                # Update counter to avoid name conflicts
                if rect['name'].startswith('W_'):
                    try:
                        num = int(rect['name'].split('_')[1])
                        self.rectangle_counter = max(self.rectangle_counter, num)
                    except (ValueError, IndexError):
                        pass

        # Load sources
        if 'sources' in data:
            for src_data in data['sources']:
                # Handle color conversion
                color = src_data.get('color', (255, 0, 0, 255))
                if isinstance(color, (list, tuple)):
                    color = QColor(*color)

                source = {
                    'grid_x': src_data['x'],
                    'grid_y': src_data['y'],
                    'grid_x2': src_data['x'],
                    'grid_y2': src_data['y'],
                    'name': src_data.get('name', 'Source'),
                    'shape': src_data.get('shape', 'Point'),
                    'source_type': src_data.get('source_type', 'Gaussian Pulse'),
                    'amplitude': src_data.get('amplitude', 20.0),
                    'frequency': src_data.get('frequency',194.8e12),
                    'gauss_pulse_deg': src_data.get('gauss_pulse_deg', -6.0),
                    'gp_tsp_coef': src_data.get('gp_tsp_coef',1.0),
                    'gp_tpk_coef': src_data.get('gp_tpk_coef',9.0),
                    'wave_packet_bw': src_data.get('wave_packet_bw',0.1),
                    'wp_tsp_coef': src_data.get('wp_tsp_coef',2.0),
                    'wp_tpk_coef': src_data.get('wp_tpk_coef',9.0),
                    'color': color
                }
                if 'xend' in src_data:
                    source['grid_x2'] = src_data['xend']
                if 'yend' in src_data:
                    source['grid_y2'] = src_data['yend']

                self.source_points.append(source)
                self.draw_history.append(('source', source))

                # Update counter
                if source['name'].startswith('Source '):
                    try:
                        num = int(source['name'].split(' ')[-1])
                        self.source_counter = max(self.source_counter, num)
                    except (ValueError, IndexError):
                        pass

        # Load measurement points
        if 'measurement_points' in data:
            for mp_data in data['measurement_points']:
                # Handle color conversion
                color = mp_data.get('color', (255, 0, 0, 255))
                if isinstance(color, (list, tuple)):
                    color = QColor(*color)

                measure = {
                    'grid_x': mp_data['x'],
                    'grid_y': mp_data['y'],
                    'grid_x2': mp_data['x'],
                    'grid_y2': mp_data['y'],
                    'name': mp_data.get('name', 'Measurement'),
                    'shape': mp_data.get('shape', 'Point'),
                    'color': color
                }
                if 'xend' in mp_data:
                    measure['grid_x2'] = mp_data['xend']
                if 'yend' in mp_data:
                    measure['grid_y2'] = mp_data['yend']

                if measure['shape'] == 'Surface':
                    measure['grid_width'] = abs(measure['grid_x'] - measure['grid_x2'])
                    measure['grid_height'] = abs(measure['grid_y'] - measure['grid_y2'])

                self.measurement_points.append(measure)
                self.draw_history.append(('measurement', measure))

                # Update counter
                if measure['name'].startswith('Measurement '):
                    try:
                        num = int(measure['name'].split(' ')[-1])
                        self.measurement_counter = max(self.measurement_counter, num)
                    except (ValueError, IndexError):
                        pass

        # Load grid spacing if present
        if 'geometry' in data and 'grid_spacing' in data['geometry']:
            grid_space = data['geometry']['grid_spacing']
            # Default to 0.05e-6 (50nm) instead of 10
            dx = grid_space.get('delta_x', 0.05e-6)
            self.set_grid_spacing(dx, dx)

        # Load grid dimensions if present
        if 'geometry' in data and 'grid_dimensions' in data['geometry']:
            grid_domain = data['geometry']['grid_dimensions']
            nx = grid_domain.get('nx', 20)
            ny = grid_domain.get('ny', 10)
            self.set_domain(nx, ny)

        self.domain_loaded.emit(self.nx, self.ny, self.delta_x * 1e6)  # convert delta_x back to µm for ribbon

        # Redraw the canvas
        self.update()