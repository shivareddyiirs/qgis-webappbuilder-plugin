from webappbuilder.webbappwidget import WebAppWidget
import os
from PyQt4.QtGui import QIcon

class LayersList(WebAppWidget):

    buttonIndex = 1
    buttonArea = WebAppWidget.BUTTON_AREA_RIGHT
    cssName = "layerlist"

    _parameters = {"tipLabel": "Layers",
                    "showOpacity": False,
                    "showZoomTo": False,
                    "showDownload": False,
                    "allowReordering": False,
                    "allowFiltering": True,
                    "showUpload": True,
                    "showNew": True,
                    "downloadFormat": ("GeoJSON", ("GeoJSON", "KML", "GPX"))}

    def write(self, appdef, folder, app, progress):
        def p(name):
            return str(self._parameters[name]).lower()
        app.panels.append('''React.createElement("div",{id: "layerlist"},
                                    React.createElement(LayerList, {showOpacity:%s, showDownload:%s,
                                        showGroupContent:true, showZoomTo:%s, allowReordering:%s,
                                        allowFiltering:%s, tipLabel:'%s',
                                        downloadFormat:'%s', showUpload:%s, map:map}))'''
                            % (p("showOpacity"),p("showDownload"), p("showZoomTo"),
                               p("allowReordering"), p("allowFiltering"), p("tipLabel"),
                               self._parameters["downloadFormat"][0], p("showUpload")))
        self.addReactComponent(app, "LayerList")

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "layer-list.png"))

    def iconFile(self):
        return os.path.join(os.path.dirname(__file__), "layer-list.png")

    def checkProblems(self, appdef, problems):
        if len(appdef["Layers"]) == 0:
            problems.append("Layer list widget added, but no layers have been included.")

        if self._parameters["showNew"] and "drawfeature" not in appdef["Widgets"]:
            problems.append("Layer list allows creating new layers, but DrawFeature component hasnt' been added")

    def description(self):
        return "Layers list"
