# -*- coding: utf-8 -*-
"""
/***************************************************************************
 centroidfinder
                                 A QGIS plugin
 Calcula o centroid em relação a uma camada de pontos
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-09-24
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Andre Sachetti
        email                : andresachetti1@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QDialog, QComboBox, QLineEdit, QPushButton, QVBoxLayout, QLabel
from qgis.core import *


# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .centroid_finder_dialog import centroidfinderDialog
import os.path
import processing
import sys, os
from osgeo import ogr

class centroidfinder:
    def __init__(self, iface):
        """Construtor do plugin. Recebe a interface do QGIS."""
        self.iface = iface  # Interface do QGIS
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

    def initGui(self):
        """Inicializa a interface gráfica do plugin (menu e botão)."""
        # Criar a ação para o menu e a barra de ferramentas
        icon_path = os.path.join(self.plugin_dir, 'icon.png')  # Substitua com o ícone que você quiser
        self.action = QAction(QIcon(icon_path), "Calcular Ponto Central Ponderado", self.iface.mainWindow())

        # Conectar o clique da ação ao método 'run'
        self.action.triggered.connect(self.run)

        # Adicionar o botão na barra de ferramentas do QGIS
        self.iface.addToolBarIcon(self.action)

        # Adicionar a ação ao menu de plugins do QGIS
        self.iface.addPluginToMenu("&Centroid Finder", self.action)

    def unload(self):
        """Remove o plugin do QGIS quando ele for desativado."""
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Centroid Finder", self.action)

    def run(self):
        """Executa o plugin quando o botão for clicado."""
        # Verificar se o diálogo já foi inicializado
        if not self.dialog:
            from .centroid_finder_dialog import centroidfinderDialog
            self.dialog = centroidfinderDialog()

        # Mostrar o diálogo
        self.dialog.show()
        self.dialog.exec_()

        # Obter os valores da interface (camada de entrada e nome da camada de saída)
        input_layer = self.dialog.get_input_layer()
        output_layer_name = self.dialog.get_output_layer_name()

        # Validar a camada de entrada
        if not input_layer:
            self.iface.messageBar().pushMessage("Erro", "Selecione uma camada de entrada.", level=3)
            return

        # Verificar se a camada tem as colunas necessárias
        required_fields = ['LATITUDE', 'LONGITUDE', 'PESO']
        missing_fields = [field for field in required_fields if field not in input_layer.fields().names()]
        if missing_fields:
            self.iface.messageBar().pushMessage("Erro", f"Faltando as colunas: {', '.join(missing_fields)}", level=3)
            return

        # Calcular o ponto central ponderado
        soma_latitude_peso = 0
        soma_longitude_peso = 0
        soma_pesos = 0

        for feature in input_layer.getFeatures():
            latitude = feature['LATITUDE']
            longitude = feature['LONGITUDE']
            peso = feature['PESO']

            soma_latitude_peso += latitude * peso
            soma_longitude_peso += longitude * peso
            soma_pesos += peso

        if soma_pesos == 0:
            self.iface.messageBar().pushMessage("Erro", "A soma dos pesos é zero, cálculo impossível.", level=3)
            return

        latitude_central = soma_latitude_peso / soma_pesos
        longitude_central = soma_longitude_peso / soma_pesos

        # Criar o ponto central
        ponto_central = QgsPointXY(longitude_central, latitude_central)
        geometry = QgsGeometry.fromPointXY(ponto_central)

        # Criar nova camada de saída com o ponto central
        output_layer = QgsVectorLayer("Point?crs=EPSG:4326", output_layer_name, "memory")
        prov = output_layer.dataProvider()
        
        # Adicionar os campos de latitude e longitude
        prov.addAttributes([
            QgsField("LATITUDE", QVariant.Double),
            QgsField("LONGITUDE", QVariant.Double)
        ])
        output_layer.updateFields()

        # Criar a feição e adicionar à nova camada
        central_feature = QgsFeature()
        central_feature.setGeometry(geometry)
        central_feature.setAttributes([latitude_central, longitude_central])
        prov.addFeatures([central_feature])

        # Adicionar a camada de saída ao projeto
        QgsProject.instance().addMapLayer(output_layer)
        self.iface.messageBar().pushMessage("Sucesso", "Ponto central ponderado adicionado ao projeto.", level=1)
