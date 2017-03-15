# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
import os
import re
from qgis.core import *
from qgis.gui import *
import qgis
import subprocess
import uuid
import base64
from PyQt4.QtCore import *
from PyQt4.QtGui import QFileDialog, QApplication, QCursor
import inspect
import codecs
import json
from qgiscommons.networkaccessmanager import NetworkAccessManager
from qgiscommons.settings import pluginSetting, setPluginSetting
import urllib.parse

#authEndpointUrl = "https://api.dev.boundlessgeo.io/v1/token/"
#wabCompilerUrl = "http://localhost:8080/package/"
tokenRealm = "Connect token server"

def wabCompilerUrl():
    return urllib.parse.unquote(pluginSetting("sdkendpoint"))

def authUrl():
    return urllib.parse.unquote(pluginSetting("tokenendpoint"))

def authCfg():
    return urllib.parse.unquote(pluginSetting("authcfg"))

class topics:
    """Class to store PyPubSub topics shared among various parts of code."""
    endFunction = "endFunction"
    endWriteWebApp = "endWriteWebApp"
    endAppSDKification = "endAppSDKification"

    def __init__():
        pass

MULTIPLE_SELECTION_DISABLED = 0
MULTIPLE_SELECTION_ALT_KEY = 1
MULTIPLE_SELECTION_SHIFT_KEY = 2
MULTIPLE_SELECTION_NO_KEY = 3


try:
    from qgis.core import QGis
    TYPE_MAP = {
        QGis.WKBPoint: 'Point',
        QGis.WKBLineString: 'LineString',
        QGis.WKBPolygon: 'Polygon',
        QGis.WKBMultiPoint: 'MultiPoint',
        QGis.WKBMultiLineString: 'MultiLineString',
        QGis.WKBMultiPolygon: 'MultiPolygon',
    }
    QGisPoint = QGis.WKBPoint

except ImportError:
    from qgis.core import Qgis as QGis
    from qgis.core import QgsWkbTypes
    TYPE_MAP = {
        QgsWkbTypes.Point: 'Point',
        QgsWkbTypes.LineString: 'LineString',
        QgsWkbTypes.Polygon: 'Polygon',
        QgsWkbTypes.MultiPoint: 'MultiPoint',
        QgsWkbTypes.MultiLineString: 'MultiLineString',
        QgsWkbTypes.MultiPolygon: 'MultiPolygon',
    }
    QGisPoint = QgsWkbTypes.Point

class Layer():

    def __init__(self, layer, visible, popup, clusterDistance, clusterColor,
                 allowSelection, showInOverview, timeInfo, showInControls,
                 singleTile):
        self.layer = layer
        self.visible = visible
        self.popup = popup
        self.clusterDistance = clusterDistance
        self.clusterColor = clusterColor
        self.allowSelection = allowSelection
        self.showInOverview = showInOverview
        self.timeInfo = timeInfo
        self.showInControls = showInControls
        self.singleTile = singleTile

    @staticmethod
    def fromDict(d):
        layer = Layer(*[None] * 10)
        for a, b in d.iteritems():
            setattr(layer, a, b)
        layer.layer = findProjectLayerByName(layer.layer)
        return layer


def replaceInTemplate(template, values):
    path = os.path.join(os.path.dirname(__file__), "templates", template)
    with codecs.open(path, encoding="utf-8") as f:
        lines = f.readlines()
    s = "".join(lines)
    for name,value in values.iteritems():
        s = s.replace(name, value)
    return s

def exportLayers(layers, folder, progress, precision, crsid, forPreview):
    progress.setText("Writing local layer files")
    destCrs = QgsCoordinateReferenceSystem(crsid)
    layersFolder = os.path.join(folder, "data")
    QDir().mkpath(layersFolder)
    reducePrecision = re.compile(r"([0-9]+\.[0-9]{%s})([0-9]+)" % precision)
    removeSpaces = lambda txt:'"'.join( it if i%2 else ''.join(it.split())
                         for i,it in enumerate(txt.split('"')))
    ext = "js" if forPreview else "json"
    regexp = re.compile(r'"geometry":.*?null\}')
    for i, appLayer in enumerate(layers):
        layer = appLayer.layer
        if layer.type() == layer.VectorLayer:
            path = os.path.join(layersFolder, "lyr_%s.%s" % (safeName(layer.name()), ext))
            QgsVectorFileWriter.writeAsVectorFormat(layer,  path, "utf-8", destCrs, 'GeoJson')
            with codecs.open(path, encoding="utf-8") as f:
                lines = f.readlines()
            with codecs.open(path, "w", encoding="utf-8") as f:
                if forPreview:
                    f.write("%s_geojson_callback(" % safeName(layer.name()))
                for line in lines:
                    line = reducePrecision.sub(r"\1", line)
                    line = line.strip("\n\t ")
                    line = removeSpaces(line)
                    if layer.wkbType()==QGis.WKBMultiPoint:
                        line = line.replace("MultiPoint", "Point")
                        line = line.replace("[ [", "[")
                        line = line.replace("] ]", "]")
                        line = line.replace("[[", "[")
                        line = line.replace("]]", "]")
                    line = regexp.sub(r'"geometry":null', line)
                    f.write(line)
                if forPreview:
                    f.write(");")
        elif layer.type() == layer.RasterLayer:
            destFile = os.path.join(layersFolder, safeName(layer.name()) + ".png").replace("\\", "/")
            img = layer.previewAsImage(QSize(layer.width(),layer.height()))
            img.save(destFile)
        progress.setProgress(int(i*100.0/len(layers)))


def findLayerByName(name, layers):
    for layer in layers:
        if layer.layer.name() == name:
            return layer

def safeName(name):
    #TODO: we are assuming that at least one character is valid...
    validChars = '123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
    return ''.join(c for c in name if c in validChars).lower()


def findProjectLayerByName(name):
    layers = QgsProject.instance().layerTreeRoot().findLayers()
    for layer in layers:
        mapLayer = layer.layer()
        if mapLayer.name() == name:
            return mapLayer


def run(f):
    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
    try:
        return f()
    finally:
        QApplication.restoreOverrideCursor()

def setRepositoryAuth(authConfigId):
    """Add auth to the repository
    """
    setPluginSetting("authcfg", authConfigId)

def getRepositoryAuth():
    """check if a authcfg is already configured in settings, otherwise try to get
    connect plugin auth configuration.
    """
    authcfg = authCfg()
    if not authcfg:
        # check if auth setting is available in connect plugin
        try:
            from boundlessconnect.plugins import boundlessRepoName
            from pyplugin_installer.installer_data import reposGroup
            authcfg = getSetting(reposGroup + '/' + boundlessRepoName, 'authcfg')
        except:
            pass

    return authcfg

def getCredentialsFromAuthDb(authcfg):
    credentials = (None, None)
    if authcfg:
        authConfig = QgsAuthMethodConfig()
        if QgsAuthManager.instance().loadAuthenticationConfig(authcfg, authConfig, True):
            credentials = (authConfig.config('username'), authConfig.config('password'))

    return credentials

def getToken():
    """
    Function to get a access token from endpoint sending "custom" basic auth.
    Parameters

    The return value is a token string or Exception

    ----------
    exception_class : Exception
        Custom exception class
    """
    token = None

    # get authcfg to point to saved credentials in QGIS Auth manager
    authcfg = getRepositoryAuth()
    if not authcfg:
        ok, usr, pwd = QgsCredentials.instance().get(tokenRealm, "", "")
        if not ok:
            # try to select a saved identity
            # TODO: embed QgsAuthConfigSelect to get a saved identity

            # TODO: return token=None or Exception ?
            return token
    else:
        usr, pwd = getCredentialsFromAuthDb(authcfg)
        if not usr and not pwd:
            raise Exception("Cannot find stored credentials with authcfg = {}".format(authcfg))

    # prepare data for the token request
    httpAuth = base64.encodestring('{}:{}'.format(usr, pwd))[:-1]
    headers = {}
    headers["Authorization"] = "Basic {}".format(httpAuth)
    headers["Content-Type"] = "application/json"

    # request token in synchronous way => block GUI
    nam = NetworkAccessManager(debug=True)
    try:
        res, resText = nam.request(authUrl(), method="GET", headers=headers)
    except Exception as e:
        if nam.http_call_result.status_code == 403:
            raise Exception("Permission denied")
        else:
            raise e

    # todo: check res code in case not authorization
    if not res.ok:
        raise Exception("Cannot get token: {}".format(res.reason))

    # parse token from resText
    resDict = json.loads(str(resText))
    try:
        token = resDict["token"]
    except:
        pass

    if token is None:
        raise Exception("Cannot get authentication token")
    
    # If I get a valid token and no previous authcfg => save current valid
    # credentials in authDb
    if not authcfg:
        authConfig = QgsAuthMethodConfig('Basic')
        authcfg = QgsAuthManager.instance().uniqueConfigId()
        authConfig.setId(authcfg)
        authConfig.setConfig('username', usr)
        authConfig.setConfig('password', pwd)
        authConfig.setUri(authUrl())
        authConfig.setName('Boundless Connect Portal')

        if QgsAuthManager.instance().storeAuthenticationConfig(authConfig):
            # save authcfg to reference credential config for the next setssion
            setRepositoryAuth(authcfg)
        else:
            QMessageBox.information(self, self.tr('Error!'), self.tr('Unable to save credentials'))

    return token
