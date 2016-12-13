import os
from qgis.PyQt.QtGui import QIcon
from webappbuilder.webbappwidget import WebAppWidget

class Attribution(WebAppWidget):

    def write(self, appdef, folder, app, progress):
        app.ol3controls.append("new ol.control.Attribution({collapsible: false})")

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "attribution.png"))

    def iconFile(self):
        return os.path.join(os.path.dirname(__file__), "attribution.png")

    def description(self):
        return "Attribution"
