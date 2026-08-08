"""PyQtGraph crosshair/tooltip ve QtCharts pasta hover davranışları."""

import pyqtgraph as pg


def install_crosshair(plot) -> None:
    state = getattr(plot, "_crosshair_state", None)
    if state is None:
        vertical = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#9CA3AF"))
        horizontal = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#9CA3AF"))
        label = pg.TextItem(anchor=(0, 1), fill=pg.mkBrush(20, 20, 20, 210))

        def moved(event):
            position = event[0] if isinstance(event, tuple) else event
            if not plot.sceneBoundingRect().contains(position):
                return
            point = plot.getPlotItem().vb.mapSceneToView(position)
            vertical.setPos(point.x())
            horizontal.setPos(point.y())
            label.setText(f"x: {point.x():.2f}\ny: {point.y():,.2f}", color="#FFFFFF")
            label.setPos(point.x(), point.y())

        proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=30, slot=moved)
        state = (vertical, horizontal, label, proxy)
        plot._crosshair_state = state
    for item in state[:3]:
        if item.scene() is None:
            plot.addItem(item, ignoreBounds=True)


def configure_pie_slice(slice_item, label: str, value: float) -> None:
    slice_item.setLabel(f"{label}: {value:,.2f}")
    slice_item.setLabelVisible(False)

    def hovered(active: bool) -> None:
        slice_item.setExploded(active)
        slice_item.setExplodeDistanceFactor(0.08)
        slice_item.setLabelVisible(active)

    slice_item.hovered.connect(hovered)
