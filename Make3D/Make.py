# ===============================================================================
# Copyright (c) 2013 Pierre Moulon, Bruno Duisit.

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# ===============================================================================

# ===============================================================================
# Copyright (c) 2014-2015 SEACAVE
# *
# * Author(s):
# *
# *      cDc <cdc.seacave@gmail.com>
# *
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU Affero General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU Affero General Public License for more details.
# *
# * You should have received a copy of the GNU Affero General Public License
# * along with this program.  If not, see <http://www.gnu.org/licenses/>
# ===============================================================================


#=================   Mask R-CNN   ========================
#
# The main Mask R-CNN model implementation.

# Copyright (c) 2017 Matterport, Inc.
# Licensed under the MIT License (see LICENSE for details)
# Written by Waleed Abdulla
#=========================================================

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.14.0
#
# WARNING! All changes made in this file will be lost!


import os
import subprocess
import sys
import pptk
import math
import random
import string
import numpy as np
import skimage.io
import matplotlib
import matplotlib.pyplot as plt
import ssl
import plyfile
import cv2
import time
from shutil import copyfile
# from wmctrl import Window
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QWindow
from PyQt5.QtCore import Qt, QThread, QWaitCondition, QMutex, pyqtSignal, QObject

from Binary import Image_Edit
from Mask_RCNN.detect import detection

#option Dictionary 
# ex option["features"]["-m"] = SIFT
option = dict()
option["features"] = dict()
option["matches"] = dict()
option["seq"] = dict()
option["densify"] = dict()
option["mesh"] = dict()
option["refine"] = dict()
option["texture"] = dict()

WinID = []
stepCount = 0

imgNum = 0

program_dir = os.getcwd()
input_dir = os.path.join(program_dir, "Image") + "/"
output_dir = ""

OPENMVG_SFM_BIN = os.path.join(program_dir, "Binary")
CAMERA_SENSOR_WIDTH_DIRECTORY = os.path.join(program_dir, "Camera")
camera_file_params = os.path.join(CAMERA_SENSOR_WIDTH_DIRECTORY, "sensor_width_camera_database.txt")

ChangeWhite_dir = ""
matches_dir = ""
reconstruction_dir = ""
Scene_dir = ""
Mvs_dir = ""

mrcnn_swt = False

class Start(QThread):
        when_step_finished = pyqtSignal()

        def __init__(self):
            QThread.__init__(self)

        def __del__(self):
            self.wait()

        def run(self):
            global output_dir, ChangeWhite_dir, matches_dir, reconstruction_dir, Scene_dir, OPENMVG_SFM_BIN, input_dir, camera_file_params, program_dir, option
            global mrcnn_swt
            #====================================================
            count = 0           # 단계별 상황
            pSteps = None       # 프로세스
            ends = False        # 종료하였는지,
            
            mrcnn_isOn = mrcnn_swt      #Mask_RCNN  ON/OFF

            start_time = time.time()    # OpenMVG 시작 시간
            start_time_mvs = 0          # OpenMVS 시작 시간
            #====================================================
            
            # 이미지 사진 리스트 목록
            file_list = os.listdir(input_dir)
            
            # Extension 확장자 찾기
            for str_ in file_list:
                if "_mask" not in str_:
                    extension = str_[-4:]
                    break
                    
            while True:
                #==============================
                #       1. Mask_RCNN
                #==============================
                if mrcnn_isOn:
                    print ("0. Make mask Image")
                    detection.Make_Mask()
                    
                    # 마스크 존재하지 않는 사진들을 삭제
                    Image_Edit.Not_Mask_Delete(input_dir)

                #==============================
                #       2. Image Listing
                #==============================
                elif count == 0:
                    print ("1. Intrinsics analysis")
                    pSteps = subprocess.Popen( [os.path.join(OPENMVG_SFM_BIN, "openMVG_main_SfMInit_ImageListing"),  "-i", input_dir, "-o", matches_dir, "-d", camera_file_params] )

                    file_list = os.listdir(input_dir)
                    # 세로 길이가 길 경우, 반시계로 90도 돌림
                    for str_ in file_list:
                        img_ = os.path.join(input_dir, str_)

                        if str_[-4] != '.':
                            continue
                            
                        if "_mask" in str_:
                            img = cv2.imread(img_, 0)
                        else:
                            img = cv2.imread(img_)

                        rotated_mat = Image_Edit.Rotation(img)
                        # 사진 저장
                        img_r = input_dir + str_
                        cv2.imwrite(img_r, rotated_mat)
               
                #==============================
                #       3.   Feature
                #==============================
                elif count == 1:

                    param = list([os.path.join(OPENMVG_SFM_BIN, "openMVG_main_ComputeFeatures"), "-i", matches_dir+"/sfm_data.json", "-o", matches_dir])

                    for op in option["features"]:
                        param.append(op)
                        param.append(option["features"][op])

                    print ("2. Compute features")
                    pSteps = subprocess.Popen( param )

                #==============================
                #    4. Export Feature Image
                #==============================
                elif count == 2:

                    # Feature Image 저장할 폴더 생성
                    pFeature_dir = os.path.join(output_dir, "FeatureImage")
                    if not os.path.exists(pFeature_dir):
                        os.mkdir(pFeature_dir)

                    # 인자 값 작성
                    param = list([os.path.join(OPENMVG_SFM_BIN, "openMVG_main_exportKeypoints"), "-i", matches_dir+"/sfm_data.json", "-d", matches_dir, "-o", pFeature_dir])

                    pSteps = subprocess.Popen( param )

                #==============================
                #       5.    Matching
                #==============================
                elif count == 3:

                    param = list([os.path.join(OPENMVG_SFM_BIN, "openMVG_main_ComputeMatches"), "-i", matches_dir+"/sfm_data.json", "-o", matches_dir, "-f", "1"])

                    tmp_ = option["matches"]["-n"]
                    tmp_ = "".join(tmp_.split('\n'))
                    option["matches"]["-n"] = tmp_

                    for op in option["matches"]:
                        param.append(op)
                        param.append(option["matches"][op])

                    print(param)
                    print ("3. Compute matches")
                    pSteps = subprocess.Popen( param )

                #==============================
                #       6. Export Matches
                #==============================
                elif count == 4:

                    # Matching Image 저장할 폴더 생성
                    pMatches_dir = os.path.join(output_dir, "MatchImage")
                    if not os.path.exists(pMatches_dir):
                        os.mkdir(pMatches_dir)

                    param = list([os.path.join(OPENMVG_SFM_BIN, "openMVG_main_exportMatches"), "-i", matches_dir+"/sfm_data.json", "-d", matches_dir, "-m", matches_dir + "/matches.putative.bin", "-o", pMatches_dir])

                    pSteps = subprocess.Popen( param )

                #==============================
                #      7. Incremental SfM
                #==============================
                elif count == 5:
                    # Create the reconstruction if not present
                    if not os.path.exists(reconstruction_dir):
                        os.mkdir(reconstruction_dir)

                    # Create the ChangeBlack if not present
                    if not os.path.exists(ChangeWhite_dir):
                        os.mkdir(ChangeWhite_dir)

                    # 마스크 존재할 때, 배경이 제거된 사진 생성
                    Image_Edit.White_Change(input_dir, ChangeWhite_dir)
                    
                    param = list([os.path.join(OPENMVG_SFM_BIN, "openMVG_main_IncrementalSfM"), "-i", matches_dir+"/sfm_data.json", "-m", matches_dir, "-o", reconstruction_dir])
                    
                    tmp_ = option["seq"]["-f"]
                    tmp_ = "".join(tmp_.split('\n'))
                    option["seq"]["-f"] = tmp_
                    
                    for op in option["seq"]:
                        param.append(op)
                        param.append(option["seq"][op])


                    print ("4. Do Sequential/Incremental reconstruction")
                    pSteps = subprocess.Popen( param )

                #=============================================
                #     8. Colorize, Robust, OpenMVG2OpenMVS
                #=============================================
                elif count == 6:
                    print ("5. Colorize Structure")
                    pSteps = subprocess.Popen( [os.path.join(OPENMVG_SFM_BIN, "openMVG_main_ComputeSfM_DataColor"),  "-i", reconstruction_dir+"/sfm_data.bin", "-o", os.path.join(reconstruction_dir,"colorized.ply")] )
            
                elif count == 7:
                    print ("6. Structure from Known Poses (robust triangulation)")
                    pSteps = subprocess.Popen( [os.path.join(OPENMVG_SFM_BIN, "openMVG_main_ComputeStructureFromKnownPoses"),  "-i", reconstruction_dir+"/sfm_data.bin", "-m", matches_dir, "-f", os.path.join(matches_dir, "matches.putative.bin"), "-o", os.path.join(reconstruction_dir,"robust.bin")] )
            
                elif count == 8:
                    print ("7. Colorize Structure")
                    pSteps = subprocess.Popen( [os.path.join(OPENMVG_SFM_BIN, "openMVG_main_ComputeSfM_DataColor"),  "-i", reconstruction_dir+"/robust.bin", "-o", os.path.join(reconstruction_dir,"robust_colorized.ply")] )

                elif count == 10:
                    print ("7-2. OpenMVG2OpenMVS")
                    if not os.path.exists(Scene_dir):
                        os.mkdir(Scene_dir)

                    pSteps = subprocess.Popen( [os.path.join(OPENMVG_SFM_BIN, "openMVG_main_openMVG2openMVS"),  "-i", reconstruction_dir+"/robust.bin", "-o", os.path.join(Scene_dir,"scene.mvs")] )
            
                #==============================
                #    9. Densify Point Cloud
                #==============================
                elif count == 11:
                    self.when_step_finished.emit()

                    print("8. Densify Point Cloud")
                    OPENMVS_BIN = OPENMVG_SFM_BIN
                    param = list([os.path.join(OPENMVS_BIN, "DensifyPointCloud"), "scene.mvs","-w", Scene_dir])

                    for op in option["densify"]:
                        param.append(op)
                        param.append(option["densify"][op])
                    
                    pSteps = subprocess.Popen(param) 

                #==============================
                #     10. Reconstruct Mesh
                #==============================
                elif count == 12:
                    self.when_step_finished.emit()

                    print("9. Reconstruct the mesh")
                    OPENMVS_BIN = OPENMVG_SFM_BIN
                    param = list([os.path.join(OPENMVS_BIN, "ReconstructMesh"), "scene_dense.mvs","-w", Scene_dir])
                    
                    for op in option["mesh"]:
                        param.append(op)
                        param.append(option["mesh"][op])

                    pSteps = subprocess.Popen(param) 
                
                #==============================
                #      11. Refine Mesh
                #==============================
                elif count == 13:
                    print("10. Refine the mesh")
                    OPENMVS_BIN = OPENMVG_SFM_BIN
                    param = list([os.path.join(OPENMVS_BIN, "RefineMesh"), "scene_dense_mesh.mvs","-w", Scene_dir])
                    
                    for op in option["refine"]:
                        param.append(op)
                        param.append(option["refine"][op])

                    pSteps = subprocess.Popen(param)

                #==============================
                #      12. Texture
                #==============================
                elif count == 14:
                    self.when_step_finished.emit()

                    print("11. Texture the mesh")
                    OPENMVS_BIN = OPENMVG_SFM_BIN
                    param = list([os.path.join(OPENMVS_BIN, "TextureMesh"), "scene_dense_mesh_refine.mvs","-w", Scene_dir])
                    
                    for op in option["texture"]:
                        param.append(op)
                        param.append(option["texture"][op])

                    pSteps = subprocess.Popen(param)
                    # 끝나기 위한 True


                #==============================
                #      Mask_RCNN 종료시,
                #==============================
                if mrcnn_isOn:
                    while True:
                        if detection.poll():
                            with open(output_dir + 'Progress/Mask_RCNN.txt' ,'wt') as t:
                                end_time = time.time()
                                t.writelines("총 걸린 시간: " + str(end_time - start_time) + "초\n")
                            mrcnn_isOn = False
                            break 

                #==================================
                #      OpenMVG_OpenMVS 이벤트 루프
                #==================================
                elif not ends:
                    while True:
                        if pSteps.poll() is not None:
                            if count == 10:
                                with open(output_dir + 'Progress/OpenMVG.txt' ,'wt') as t:
                                    end_time = time.time()
                                    t.writelines("총 걸린 시간: " + str(end_time - start_time) + "초\n")
                                    start_time_mvs = time.time()

                            elif count == 14:
                                ends = True
                            count += 1
                            break
                    
                #==============================
                #       종료 시, 루프문 탈출
                #==============================
                elif ends == True:
                    with open(output_dir + 'Progress/OpenMVS.txt' ,'wt') as t:
                        end_time = time.time()
                        t.writelines("총 걸린 시간: " + str(end_time - start_time) + "초\n")
                        t.writelines("OpenMVS 만 걸린 시간: " + str(end_time - start_time_mvs) + "초")    
                    self.when_step_finished.emit()
                    return

                


class Thread(QThread):
    global output_dir, mrcnn_swt
    # 사용자 정의 시그널 선언
    change_value = pyqtSignal(int)
    change_label = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)
        self.cond = QWaitCondition()
        self.mutex = QMutex()
        self.cnt = 0
        self._status = True

    def __del__(self):
        self.wait()

    def toggle_status(self):
        self._status = not self._status

        if self._status:
            self.cond.wakeAll()

    @property
    def status(self):
        return self._status

    def run(self):
        while True:
            if not os.path.isfile(output_dir + 'Progress/progress.txt'):
                continue

            with open(output_dir + 'Progress/progress.txt' ,'r') as textfile:
                while True:
                    textfile.readline()
                    step = textfile.readline()[:-1]
                    textfile.readline()
                    percent = textfile.readline()
                    
                    textfile.seek(0)

                    if not step:
                        continue
                    elif step == "- Make Mask_Image -":
                        self.change_label.emit("[0/11] Mask Iamge")
                    elif step == "- Feature -":
                        self.change_label.emit("[1/11] Feature")
                    elif step == "- Export Feature -":
                        self.change_label.emit("[2/11] Export Feature")
                    elif step == "- Matching -":
                        self.change_label.emit("[3/11] Matching - 1/2 ")
                    elif step == "- Geometric filtering -":
                        self.change_label.emit("[3/11] Matching - 2/2")
                    elif step == "- Export Matches -":
                        self.change_label.emit("[4/11] Export Matches")
                    elif step == "- Resection -":
                        self.change_label.emit("[5/11] Incremental Sfm")
                    elif step == "- Structure Color -":
                        self.change_label.emit("[6/11] Structure Color")
                    elif step == "- OpenMVG2OpenMVS_UNDISTORT -":
                        self.change_label.emit("[7/11] Undistort Image")
                    elif step == "- Estimated depth-maps -":
                        self.change_label.emit("[8/11] Densify Point Cloud - 1/2")
                    elif step == "- Filtered depth-maps -":
                        self.change_label.emit("[8/11] Densify Point Cloud - 2/2")
                    elif step == "- Points inserted -":
                        self.change_label.emit("[9/11] Reconstruct Mesh - 1/2")
                    elif step == "- Points weighted -":
                        self.change_label.emit("[9/11] Reconstruct Mesh - 2/2")
                    elif step == "- Processed iterations1 -":
                        self.change_label.emit("[10/11] Refine Mesh - 1/3")
                    elif step == "- Processed iterations2 -":
                        self.change_label.emit("[10/11] Refine Mesh - 2/3")
                    elif step == "- Processed iterations3 -":
                        self.change_label.emit("[10/11] Refine Mesh - 3/3")
                    elif step == "- Texture -":
                        self.change_label.emit("[11/11] Texture")
                    
                    self.change_value.emit(int(percent))
                    self.msleep(100)  # ※주의 QThread에서 제공하는 sleep을 사용


class QRDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setupUI()
    
    def setupUI(self):
        self.setGeometry(600, 200, 300, 300)
        self.setWindowTitle("Open on a Browser")
        self.centralWidget = QtWidgets.QWidget(self)

        self.label = QtWidgets.QLabel(self.centralWidget)
        self.label.setGeometry(QtCore.QRect(0,0,300,300))
        pixmap = QtGui.QPixmap()
        pixmap.load("UI_Image/QRCode.png")
        pixmap = pixmap.scaled(300, 300)
        self.label.setPixmap(pixmap)


class ImageListDialog(QDialog):
    def __init__(self, signal):
        super().__init__()
        self.path = signal
        self.setupUI()

    def setupUI(self):
        global output_dir
        self.setGeometry(200, 200, 800, 800)
        if self.path == "f":
            self.setWindowTitle("Feature Image List")
        elif self.path == "m":
            self.setWindowTitle("Match Image List")
        self.centeralWidget = QtWidgets.QWidget(self)

        #self.listview = QtWidgets.QListView(self.centeralWidget)
        self.listview = QtWidgets.QListWidget(self.centeralWidget)
        self.listview.setGeometry(QtCore.QRect(10, 10, 180, 780))
        self.listview.itemClicked.connect(self.openImageFile)

        self.imageLabel = QtWidgets.QLabel(self.centeralWidget)
        self.imageLabel.setGeometry(QtCore.QRect(200, 10, 580, 780))

        if self.path == "f":
            self.path = output_dir + "FeatureImage"
        elif self.path == "m":
            self.path = output_dir + "MatchImage"

        img_list = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(self.path):
            for file in f:
                if '.svg' in file:
                    #img_list.append(os.path.join(r, file))
                    img_list.append(file)

        for f in img_list:
            self.listview.addItem(f)      

    def openImageFile(self):
        #print(self.listview.currentItem().text())
        img = os.path.join(self.path, self.listview.currentItem().text())

        pixmap = QtGui.QPixmap()
        pixmap.load(img)
        pixmap = pixmap.scaled(580, 780)
        self.imageLabel.setPixmap(pixmap)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1500, 900)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 20, 1480, 50))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout_1 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_1.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_1.setObjectName("verticalLayout_1")
        self.v1_widget = QtWidgets.QWidget(self.verticalLayoutWidget)
        self.v1_widget.setObjectName("v1_widget")
        self.checkBox_rcnn = QtWidgets.QCheckBox("Masking", self.v1_widget)
        self.checkBox_rcnn.setGeometry(QtCore.QRect(150,10, 131, 31))
        self.btn_outputPath = QtWidgets.QPushButton(self.v1_widget)
        self.btn_outputPath.setGeometry(QtCore.QRect(10, 10, 131, 31))
        self.btn_outputPath.setObjectName("btn_outputPath")
        self.comboBox = QtWidgets.QComboBox(self.v1_widget)
        self.comboBox.setGeometry(QtCore.QRect(1290, 10, 180, 30))
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.label = QtWidgets.QLabel(self.v1_widget)
        self.label.setGeometry(QtCore.QRect(1120, 10, 141, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.horizontalSlider = QtWidgets.QSlider(self.v1_widget)
        self.horizontalSlider.setGeometry(QtCore.QRect(1120, 25, 141, 21))
        self.horizontalSlider.setMouseTracking(False)
        self.horizontalSlider.setSingleStep(50)
        self.horizontalSlider.setPageStep(50)
        self.horizontalSlider.setTracking(False)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.verticalLayout_1.addWidget(self.v1_widget)
        self.verticalLayoutWidget_2 = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget_2.setGeometry(QtCore.QRect(10, 70, 1480, 780))
        self.verticalLayoutWidget_2.setObjectName("verticalLayoutWidget_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.v2_widget = QtWidgets.QWidget(self.verticalLayoutWidget_2)
        self.v2_widget.setObjectName("v2_widget")

        #Compute Features options
        self.groupBox_computeFeatures = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_computeFeatures.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_computeFeatures.setObjectName("groupBox_computeFeatures")
        self.radioBtn_SIFT = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_SIFT.setGeometry(QtCore.QRect(20, 50, 112, 23))
        self.radioBtn_SIFT.setObjectName("radioBtn_SIFT")
        self.DescriberMethodGroup = QtWidgets.QButtonGroup(MainWindow)
        self.DescriberMethodGroup.setObjectName("DescriberMethodGroup")
        self.DescriberMethodGroup.addButton(self.radioBtn_SIFT)
        self.DescriberMethod = QtWidgets.QLabel(self.groupBox_computeFeatures)
        self.DescriberMethod.setGeometry(QtCore.QRect(10, 30, 161, 17))
        self.DescriberMethod.setObjectName("DescriberMethod")
        self.radioBtn_AKAZE_FLOAT = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_AKAZE_FLOAT.setGeometry(QtCore.QRect(20, 70, 131, 23))
        self.radioBtn_AKAZE_FLOAT.setObjectName("radioBtn_AKAZE_FLOAT")
        self.DescriberMethodGroup.addButton(self.radioBtn_AKAZE_FLOAT)
        self.radioBtn_AKAZE_MLDE = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_AKAZE_MLDE.setGeometry(QtCore.QRect(20, 90, 141, 23))
        self.radioBtn_AKAZE_MLDE.setObjectName("radioBtn_AKAZE_MLDE")
        self.DescriberMethodGroup.addButton(self.radioBtn_AKAZE_MLDE)
        self.Upright = QtWidgets.QLabel(self.groupBox_computeFeatures)
        self.Upright.setGeometry(QtCore.QRect(10, 130, 161, 17))
        self.Upright.setObjectName("Upright")
        self.radioBtn_0 = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_0.setGeometry(QtCore.QRect(20, 150, 112, 23))
        self.radioBtn_0.setObjectName("radioBtn_0")
        self.UprightGroup = QtWidgets.QButtonGroup(MainWindow)
        self.UprightGroup.setObjectName("UprightGroup")
        self.UprightGroup.addButton(self.radioBtn_0)
        self.radioBtn_1 = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_1.setGeometry(QtCore.QRect(20, 170, 112, 23))
        self.radioBtn_1.setObjectName("radioBtn_1")
        self.UprightGroup.addButton(self.radioBtn_1)
        self.Preset = QtWidgets.QLabel(self.groupBox_computeFeatures)
        self.Preset.setGeometry(QtCore.QRect(10, 200, 161, 17))
        self.Preset.setObjectName("Preset")
        self.radioBtn_NORMAL = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_NORMAL.setGeometry(QtCore.QRect(20, 220, 112, 23))
        self.radioBtn_NORMAL.setObjectName("radioBtn_NORMAL")
        self.PresetGroup = QtWidgets.QButtonGroup(MainWindow)
        self.PresetGroup.setObjectName("PresetGroup")
        self.PresetGroup.addButton(self.radioBtn_NORMAL)
        self.radioBtn_HIGH = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_HIGH.setGeometry(QtCore.QRect(20, 240, 112, 23))
        self.radioBtn_HIGH.setObjectName("radioBtn_HIGH")
        self.PresetGroup.addButton(self.radioBtn_HIGH)
        self.radioBtn_ULTRA = QtWidgets.QRadioButton(self.groupBox_computeFeatures)
        self.radioBtn_ULTRA.setGeometry(QtCore.QRect(20, 260, 112, 23))
        self.radioBtn_ULTRA.setObjectName("radioBtn_ULTRA")
        self.PresetGroup.addButton(self.radioBtn_ULTRA)

        #Compute Matches options
        self.groupBox_computeMathes = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_computeMathes.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_computeMathes.setObjectName("groupBox_computeMathes")
        self.groupBox_computeMathes.setVisible(False)
        self.radioBtn_08 = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_08.setGeometry(QtCore.QRect(20, 50, 112, 23))
        self.radioBtn_08.setObjectName("radioBtn_08")
        self.RatioGroup = QtWidgets.QButtonGroup(MainWindow)
        self.RatioGroup.setObjectName("RatioGroup")
        self.RatioGroup.addButton(self.radioBtn_08)
        self.Ratio = QtWidgets.QLabel(self.groupBox_computeMathes)
        self.Ratio.setGeometry(QtCore.QRect(10, 30, 161, 17))
        self.Ratio.setObjectName("Ratio")
        self.radioBtn_06 = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_06.setGeometry(QtCore.QRect(20, 70, 131, 23))
        self.radioBtn_06.setObjectName("radioBtn_06")
        self.RatioGroup.addButton(self.radioBtn_06)
        self.GeometricModel = QtWidgets.QLabel(self.groupBox_computeMathes)
        self.GeometricModel.setGeometry(QtCore.QRect(10, 100, 161, 17))
        self.GeometricModel.setObjectName("GeometricModel")
        self.radioBtn_f = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_f.setGeometry(QtCore.QRect(20, 120, 112, 23))
        self.radioBtn_f.setObjectName("radioBtn_f")
        self.GeometricModelGroup = QtWidgets.QButtonGroup(MainWindow)
        self.GeometricModelGroup.setObjectName("GeometricModelGroup")
        self.GeometricModelGroup.addButton(self.radioBtn_f)
        self.radioBtn_e = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_e.setGeometry(QtCore.QRect(20, 140, 112, 23))
        self.radioBtn_e.setObjectName("radioBtn_e")
        self.GeometricModelGroup.addButton(self.radioBtn_e)
        self.NearestMatching = QtWidgets.QLabel(self.groupBox_computeMathes)
        self.NearestMatching.setGeometry(QtCore.QRect(10, 190, 161, 17))
        self.NearestMatching.setObjectName("NearestMatching")
        self.radioBtn_AUTO = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_AUTO.setGeometry(QtCore.QRect(20, 210, 112, 23))
        self.radioBtn_AUTO.setObjectName("radioBtn_AUTO")
        self.NearestMatchingGroup = QtWidgets.QButtonGroup(MainWindow)
        self.NearestMatchingGroup.setObjectName("NearestMatchingGroup")
        self.NearestMatchingGroup.addButton(self.radioBtn_AUTO)
        self.radioBtn_BRUTEFORCEL2 = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_BRUTEFORCEL2.setGeometry(QtCore.QRect(20, 230, 141, 23))
        self.radioBtn_BRUTEFORCEL2.setObjectName("radioBtn_BRUTEFORCEL2")
        self.NearestMatchingGroup.addButton(self.radioBtn_BRUTEFORCEL2)
        self.radioBtn_ANNL2 = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_ANNL2.setGeometry(QtCore.QRect(20, 250, 112, 23))
        self.radioBtn_ANNL2.setObjectName("radioBtn_ANNL2")
        self.NearestMatchingGroup.addButton(self.radioBtn_ANNL2)
        self.radioBtn_h = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_h.setGeometry(QtCore.QRect(20, 160, 112, 23))
        self.radioBtn_h.setObjectName("radioBtn_h")
        self.GeometricModelGroup.addButton(self.radioBtn_h)
        self.radioBtn_CASCADHEASHINGL2 = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_CASCADHEASHINGL2.setGeometry(QtCore.QRect(20, 270, 181, 41))
        self.radioBtn_CASCADHEASHINGL2.setObjectName("radioBtn_CASCADHEASHINGL2")
        self.NearestMatchingGroup.addButton(self.radioBtn_CASCADHEASHINGL2)
        self.radioBtn_FASTCASCADEHASHINGL2 = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_FASTCASCADEHASHINGL2.setGeometry(QtCore.QRect(20, 310, 181, 41))
        self.radioBtn_FASTCASCADEHASHINGL2.setObjectName("radioBtn_FASTCASCADEHASHINGL2")
        self.NearestMatchingGroup.addButton(self.radioBtn_FASTCASCADEHASHINGL2)
        self.radioBtn_BRUTEFORCEHAMMING = QtWidgets.QRadioButton(self.groupBox_computeMathes)
        self.radioBtn_BRUTEFORCEHAMMING.setGeometry(QtCore.QRect(20, 350, 141, 41))
        self.radioBtn_BRUTEFORCEHAMMING.setObjectName("radioBtn_BRUTEFORCEHAMMING")
        self.NearestMatchingGroup.addButton(self.radioBtn_BRUTEFORCEHAMMING)
        
        #Sequential Reconstruction Options
        self.groupBox_sequential = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_sequential.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_sequential.setObjectName("groupBox_sequential")
        self.groupBox_sequential.setVisible(False)
        self.radioBtn_ALL = QtWidgets.QRadioButton(self.groupBox_sequential)
        self.radioBtn_ALL.setGeometry(QtCore.QRect(20, 50, 111, 41))
        self.radioBtn_ALL.setObjectName("radioBtn_ALL")
        self.RefineIntrinsics = QtWidgets.QLabel(self.groupBox_sequential)
        self.RefineIntrinsics.setGeometry(QtCore.QRect(10, 30, 161, 17))
        self.RefineIntrinsics.setObjectName("RefineIntrinsics")
        self.radioBtn_NONE = QtWidgets.QRadioButton(self.groupBox_sequential)
        self.radioBtn_NONE.setGeometry(QtCore.QRect(20, 90, 131, 23))
        self.radioBtn_NONE.setObjectName("radioBtn_NONE")
        self.radioBtn_FOCAL_LENGTH = QtWidgets.QRadioButton(self.groupBox_sequential)
        self.radioBtn_FOCAL_LENGTH.setGeometry(QtCore.QRect(20, 110, 141, 51))
        self.radioBtn_FOCAL_LENGTH.setObjectName("radioBtn_FOCAL_LENGTH")
        self.radioBtn_PRINCIPAL_POINT = QtWidgets.QRadioButton(self.groupBox_sequential)
        self.radioBtn_PRINCIPAL_POINT.setGeometry(QtCore.QRect(20, 160, 112, 51))
        self.radioBtn_PRINCIPAL_POINT.setObjectName("radioBtn_PRINCIPAL_POINT")
        self.radioBtn_DISTORTION = QtWidgets.QRadioButton(self.groupBox_sequential)
        self.radioBtn_DISTORTION.setGeometry(QtCore.QRect(20, 220, 112, 41))
        self.radioBtn_DISTORTION.setObjectName("radioBtn_DISTORTION")
        self.RefineIntrinsicsGroup = QtWidgets.QButtonGroup(MainWindow)
        self.RefineIntrinsicsGroup.setObjectName("RefineIntrinsicsGroup")   
        self.RefineIntrinsicsGroup.addButton(self.radioBtn_ALL)
        self.RefineIntrinsicsGroup.addButton(self.radioBtn_NONE)
        self.RefineIntrinsicsGroup.addButton(self.radioBtn_DISTORTION)
        self.RefineIntrinsicsGroup.addButton(self.radioBtn_PRINCIPAL_POINT)
        self.RefineIntrinsicsGroup.addButton(self.radioBtn_FOCAL_LENGTH)


        #MVG to MVS
        self.groupBox_MvgToMvs = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_MvgToMvs.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_MvgToMvs.setObjectName("groupBox_MvgToMvs")
        self.groupBox_MvgToMvs.setVisible(False)
        self.lbl_non = QtWidgets.QLabel(self.groupBox_MvgToMvs)
        self.lbl_non.setGeometry(QtCore.QRect(10, 30, 161, 17))
        self.lbl_non.setObjectName("lbl_non")
        self.checkBox_MvgToMvs = QtWidgets.QCheckBox("Disabled\n(이후 모든 과정을\n비활성화 합니다.)", self.groupBox_MvgToMvs)
        self.checkBox_MvgToMvs.setGeometry(QtCore.QRect(20,660, 131, 90))

        #Densify Point Cloud
        self.groupBox_densifyPointCloud = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_densifyPointCloud.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_densifyPointCloud.setObjectName("groupBox_densifyPointCloud")
        self.groupBox_densifyPointCloud.setVisible(False)
        self.ResolutionLevel = QtWidgets.QLabel(self.groupBox_densifyPointCloud)
        self.ResolutionLevel.setGeometry(QtCore.QRect(10, 30, 161, 41))
        self.ResolutionLevel.setObjectName("ResolutionLevel")
        self.radioBtn_RL_1 = QtWidgets.QRadioButton(self.groupBox_densifyPointCloud)
        self.radioBtn_RL_1.setGeometry(QtCore.QRect(20, 80, 112, 23))
        self.radioBtn_RL_1.setObjectName("radioBtn_RL_1")
        self.radioBtn_RL_2 = QtWidgets.QRadioButton(self.groupBox_densifyPointCloud)
        self.radioBtn_RL_2.setGeometry(QtCore.QRect(20, 100, 131, 23))
        self.radioBtn_RL_2.setObjectName("radioBtn_RL_2")
        self.radioBtn_RL_3 = QtWidgets.QRadioButton(self.groupBox_densifyPointCloud)
        self.radioBtn_RL_3.setGeometry(QtCore.QRect(20, 120, 131, 23))
        self.radioBtn_RL_3.setObjectName("radioBtn_RL_3")
        self.DensifyResolutionGroup = QtWidgets.QButtonGroup(MainWindow)
        self.DensifyResolutionGroup.setObjectName("DensifyResolutionGroup")   
        self.DensifyResolutionGroup.addButton(self.radioBtn_RL_1)
        self.DensifyResolutionGroup.addButton(self.radioBtn_RL_2)
        self.DensifyResolutionGroup.addButton(self.radioBtn_RL_3)
        self.checkBox_Densify = QtWidgets.QCheckBox("Disabled\n(이후 모든 과정을\n비활성화 합니다.)", self.groupBox_densifyPointCloud)
        self.checkBox_Densify.setGeometry(QtCore.QRect(20,660, 131, 90))
    
        #Reconstruct Mesh
        self.groupBox_reconstructMesh = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_reconstructMesh.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_reconstructMesh.setObjectName("groupBox_reconstructMesh")
        self.groupBox_reconstructMesh.setVisible(False)
        self.radioBtn_minPoint_25f = QtWidgets.QRadioButton(self.groupBox_reconstructMesh)
        self.radioBtn_minPoint_25f.setGeometry(QtCore.QRect(20, 60, 112, 23))
        self.radioBtn_minPoint_25f.setObjectName("radioBtn_minPoint_25f")
        self.mimPointDistance = QtWidgets.QLabel(self.groupBox_reconstructMesh)
        self.mimPointDistance.setGeometry(QtCore.QRect(10, 30, 161, 21))
        self.mimPointDistance.setObjectName("mimPointDistance")
        self.radioBtn_minPoint_6 = QtWidgets.QRadioButton(self.groupBox_reconstructMesh)
        self.radioBtn_minPoint_6.setGeometry(QtCore.QRect(20, 80, 161, 23))
        self.radioBtn_minPoint_6.setObjectName("radioBtn_minPoint_6")
        self.MinPointGroup = QtWidgets.QButtonGroup(MainWindow)
        self.MinPointGroup.setObjectName("MinPointGroup")   
        self.MinPointGroup.addButton(self.radioBtn_minPoint_25f)
        self.MinPointGroup.addButton(self.radioBtn_minPoint_6)
        self.checkBox_ReconstructMesh = QtWidgets.QCheckBox("Disabled\n(이후 모든 과정을\n비활성화 합니다.)", self.groupBox_reconstructMesh)
        self.checkBox_ReconstructMesh.setGeometry(QtCore.QRect(20,660, 131, 90))


        #Refine Mesh
        self.groupBox_refineMesh = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_refineMesh.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_refineMesh.setObjectName("groupBox_refineMesh")
        self.groupBox_refineMesh.setVisible(False)
        self.ResolutionLevel_2 = QtWidgets.QLabel(self.groupBox_refineMesh)
        self.ResolutionLevel_2.setGeometry(QtCore.QRect(10, 30, 161, 41))
        self.ResolutionLevel_2.setObjectName("ResolutionLevel_2")
        self.radioBtn_RL_4 = QtWidgets.QRadioButton(self.groupBox_refineMesh)
        self.radioBtn_RL_4.setGeometry(QtCore.QRect(20, 80, 112, 23))
        self.radioBtn_RL_4.setObjectName("radioBtn_RL_4")
        self.ResolutionGroup = QtWidgets.QButtonGroup(MainWindow)
        self.ResolutionGroup.setObjectName("ResolutionGroup")   
        self.ResolutionGroup.addButton(self.radioBtn_RL_4)
        self.radioBtn_RL_5 = QtWidgets.QRadioButton(self.groupBox_refineMesh)
        self.radioBtn_RL_5.setGeometry(QtCore.QRect(20, 100, 131, 23))
        self.radioBtn_RL_5.setObjectName("radioBtn_RL_5")
        self.ResolutionGroup.addButton(self.radioBtn_RL_5)
        self.radioBtn_RL_6 = QtWidgets.QRadioButton(self.groupBox_refineMesh)
        self.radioBtn_RL_6.setGeometry(QtCore.QRect(20, 120, 131, 23))
        self.radioBtn_RL_6.setObjectName("radioBtn_RL_6")
        self.ResolutionGroup.addButton(self.radioBtn_RL_6)
        self.MaxFaceArea = QtWidgets.QLabel(self.groupBox_refineMesh)
        self.MaxFaceArea.setGeometry(QtCore.QRect(10, 150, 161, 31))
        self.MaxFaceArea.setObjectName("MaxFaceArea")
        self.radioBtn_MaxFace_32 = QtWidgets.QRadioButton(self.groupBox_refineMesh)
        self.radioBtn_MaxFace_32.setGeometry(QtCore.QRect(20, 220, 131, 23))
        self.radioBtn_MaxFace_32.setObjectName("radioBtn_MaxFace_32")
        self.MaxFaceAreaGroup = QtWidgets.QButtonGroup(MainWindow)
        self.MaxFaceAreaGroup.setObjectName("MaxFaceAreaGroup")
        self.MaxFaceAreaGroup.addButton(self.radioBtn_MaxFace_32)
        self.radioBtn_MaxFace_64 = QtWidgets.QRadioButton(self.groupBox_refineMesh)
        self.radioBtn_MaxFace_64.setGeometry(QtCore.QRect(20, 180, 112, 23))
        self.radioBtn_MaxFace_64.setObjectName("radioBtn_MaxFace_64")
        self.MaxFaceAreaGroup.addButton(self.radioBtn_MaxFace_64)
        self.radioBtn_MaxFace_16 = QtWidgets.QRadioButton(self.groupBox_refineMesh)
        self.radioBtn_MaxFace_16.setGeometry(QtCore.QRect(20, 200, 112, 23))
        self.radioBtn_MaxFace_16.setObjectName("radioBtn_MaxFace_16")
        self.MaxFaceAreaGroup.addButton(self.radioBtn_MaxFace_16)
        self.MeshFile = QtWidgets.QLabel(self.groupBox_refineMesh)
        self.MeshFile.setGeometry(QtCore.QRect(10, 240, 161, 31))
        self.MeshFile.setObjectName("MeshFile")
        self.checkBox_RefineMesh = QtWidgets.QCheckBox("Disabled\n(이후 모든 과정을\n비활성화 합니다.)", self.groupBox_refineMesh)
        self.checkBox_RefineMesh.setGeometry(QtCore.QRect(20,660, 131, 90))

        #Texture Mesh
        self.groupBox_textureMesh = QtWidgets.QGroupBox(self.v2_widget)
        self.groupBox_textureMesh.setGeometry(QtCore.QRect(1290, 10, 180, 750))
        self.groupBox_textureMesh.setObjectName("groupBox_textureMesh")
        self.groupBox_textureMesh.setVisible(False)
        self.TextureMesh = QtWidgets.QLabel(self.groupBox_textureMesh)
        self.TextureMesh.setGeometry(QtCore.QRect(10, 30, 161, 41))
        self.TextureMesh.setObjectName("TextureMesh")
        self.radioBtn_RL_7 = QtWidgets.QRadioButton(self.groupBox_textureMesh)
        self.radioBtn_RL_7.setGeometry(QtCore.QRect(20, 80, 112, 23))
        self.radioBtn_RL_7.setObjectName("radioBtn_RL_7")
        self.radioBtn_RL_8 = QtWidgets.QRadioButton(self.groupBox_textureMesh)
        self.radioBtn_RL_8.setGeometry(QtCore.QRect(20, 100, 131, 23))
        self.radioBtn_RL_8.setObjectName("radioBtn_RL_8")
        self.radioBtn_RL_9 = QtWidgets.QRadioButton(self.groupBox_textureMesh)
        self.radioBtn_RL_9.setGeometry(QtCore.QRect(20, 120, 131, 23))
        self.radioBtn_RL_9.setObjectName("radioBtn_RL_9")
        self.TextureResolutionGroup = QtWidgets.QButtonGroup(MainWindow)
        self.TextureResolutionGroup.setObjectName("TextureResolutionGroup")   
        self.TextureResolutionGroup.addButton(self.radioBtn_RL_7)
        self.TextureResolutionGroup.addButton(self.radioBtn_RL_8)
        self.TextureResolutionGroup.addButton(self.radioBtn_RL_9)
        self.checkBox_TextureMesh = QtWidgets.QCheckBox("Disabled\n(이후 모든 과정을\n비활성화 합니다.)", self.groupBox_textureMesh)
        self.checkBox_TextureMesh.setGeometry(QtCore.QRect(20,660, 131, 90))

        #Tab layout
        self.tabs = QtWidgets.QTabWidget(self.v2_widget)
        self.tabs.setGeometry(QtCore.QRect(10, 10, 1250, 750))
        self.tab1 = QtWidgets.QWidget()
        
        self.tabs.addTab(self.tab1, "Point Cloud")

        #capture button
        self.btn_capture = QtWidgets.QPushButton(self.v2_widget)
        self.btn_capture.setGeometry(QtCore.QRect(1230, 0, 30, 30))
        self.btn_capture.setObjectName("btn_capture")
        self.btn_capture.setEnabled(False)

        self.verticalLayout_2.addWidget(self.v2_widget)
        self.verticalLayoutWidget_3 = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget_3.setGeometry(QtCore.QRect(10, 830, 1480, 50))
        self.verticalLayoutWidget_3.setObjectName("verticalLayoutWidget_3")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_3)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.v3_widget = QtWidgets.QWidget(self.verticalLayoutWidget_3)
        self.v3_widget.setObjectName("v3_widget")
        self.pgsb = QtWidgets.QProgressBar(self.v3_widget)
        self.pgsb.setGeometry(QtCore.QRect(10,15, 1250, 25))
        self.pgsb.setObjectName("pgsb")
        self.btn_start = QtWidgets.QPushButton(self.v3_widget)
        self.btn_start.setGeometry(QtCore.QRect(1350, 10, 120, 30))
        self.btn_start.setObjectName("btn_start")
        self.btn_QR = QtWidgets.QPushButton(self.v3_widget)
        self.btn_QR.setGeometry(QtCore.QRect(1290, 10, 50, 30))
        self.btn_QR.setObjectName("btn_QR")
        self.btn_QR.setEnabled(True)
        self.verticalLayout_3.addWidget(self.v3_widget)
        self.btn_fImage = QtWidgets.QPushButton(self.v2_widget)
        self.btn_fImage.setGeometry(QtCore.QRect(970, 0, 120, 30))
        self.btn_fImage.setObjectName("btn_fImage")
        self.btn_mImage = QtWidgets.QPushButton(self.v2_widget)
        self.btn_mImage.setGeometry(QtCore.QRect(1100, 0, 120, 30))
        self.btn_mImage.setObjectName("btn_fImage")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.lbl_pgsbStep = QtWidgets.QLabel("",self.statusbar)
        self.lbl_pgsbStep.setGeometry(QtCore.QRect(25, 0, 400, 20))

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        #Disabled checkbox 이벤트
        self.checkBox_MvgToMvs.stateChanged.connect(lambda: self.piplineDisabled(4))
        self.checkBox_Densify.stateChanged.connect(lambda: self.piplineDisabled(5))
        self.checkBox_ReconstructMesh.stateChanged.connect(lambda: self.piplineDisabled(6))
        self.checkBox_RefineMesh.stateChanged.connect(lambda: self.piplineDisabled(7))
        #self.checkBox_TextureMesh.stateChanged.connect(lambda: self.piplineDisabled(8))

        #capture 버튼 이벤트
        self.btn_capture.clicked.connect(self.captureFunc)
        #start 버튼 이벤트
        self.btn_start.clicked.connect(lambda: self.startPipline(MainWindow))
        #QR 버튼 이벤트
        self.btn_QR.clicked.connect(self.openQRDialog)
        #slider 이벤트
        self.horizontalSlider.valueChanged.connect(self.optionChecking)
        #comboBox 이벤트
        self.comboBox.currentIndexChanged.connect(lambda: self.comboBoxFunc(MyWindow))

        #feature image Dialog
        self.btn_fImage.clicked.connect(lambda: self.openImageDialog("f"))
        #match image Dialog
        self.btn_mImage.clicked.connect(lambda: self.openImageDialog("m"))
        #output path Dialog
        self.btn_outputPath.clicked.connect(lambda:self.outputDialogFunc(MyWindow))
        #radio button 이벤트
        self.DescriberMethodGroup.buttonToggled.connect(lambda: self.selectOptionFunc("features","-m"))
        self.UprightGroup.buttonToggled.connect(lambda: self.selectOptionFunc("features","-u"))
        self.PresetGroup.buttonToggled.connect(lambda: self.selectOptionFunc("features","-p"))
        self.RatioGroup.buttonToggled.connect(lambda: self.selectOptionFunc("matches","-r"))
        self.GeometricModelGroup.buttonToggled.connect(lambda: self.selectOptionFunc("matches","-g"))
        self.NearestMatchingGroup.buttonToggled.connect(lambda: self.selectOptionFunc("matches","-n"))
        self.RefineIntrinsicsGroup.buttonToggled.connect(lambda: self.selectOptionFunc("seq", "-f"))
        self.DensifyResolutionGroup.buttonToggled.connect(lambda: self.selectOptionFunc("densify", "--resolution-level"))
        self.MinPointGroup.buttonToggled.connect(lambda: self.selectOptionFunc("mesh", "-d"))
        self.ResolutionGroup.buttonToggled.connect(lambda: self.selectOptionFunc("refine", "--resolution-level"))
        self.MaxFaceAreaGroup.buttonToggled.connect(lambda: self.selectOptionFunc("refine", "--max-face-area"))
        self.TextureResolutionGroup.buttonToggled.connect(lambda: self.selectOptionFunc("texture", "--resolution-level"))
        #Low 품질로 옵셥 초기화
        self.radioBtn_SIFT.setChecked(True)
        self.radioBtn_0.setChecked(True)
        self.radioBtn_NORMAL.setChecked(True)
        self.radioBtn_08.setChecked(True)
        self.radioBtn_f.setChecked(True)
        self.radioBtn_FASTCASCADEHASHINGL2.setChecked(True)
        self.radioBtn_ALL.setChecked(True)
        self.radioBtn_RL_3.setChecked(True)
        self.radioBtn_minPoint_6.setChecked(True)
        self.radioBtn_RL_6.setChecked(True)
        self.radioBtn_MaxFace_16.setChecked(True)
        self.radioBtn_RL_9.setChecked(True)

        
    def updateProgressBar(self, maxVal):
            self.pgsb.setValue(maxVal)


    def captureFunc(self):
        global imgNum
        self.v.capture('screeshot'+ str(imgNum) +'.png')
        imgNum = imgNum + 1
        print("captured")

    def openQRDialog(self):
        Q_dlg = QRDialog()
        Q_dlg.exec_()

    def openImageDialog(self, signal):
        if signal == "f":
            print("open feature image Dialog")
            f_dlg = ImageListDialog("f")
            f_dlg.exec_()
        elif signal == "m":
            print("open match image Dialog")
            m_dlg = ImageListDialog("m")
            m_dlg.exec_()

    def piplineDisabled(self, currentIndex):
        if currentIndex == 4:
            if self.checkBox_MvgToMvs.isChecked() == True:
                self.checkBox_Densify.setChecked(True)
                self.checkBox_ReconstructMesh.setChecked(True)
                self.checkBox_RefineMesh.setChecked(True)
                self.checkBox_TextureMesh.setChecked(True)
                self.groupBox_densifyPointCloud.setEnabled(False)
                self.groupBox_reconstructMesh.setEnabled(False)
                self.groupBox_refineMesh.setEnabled(False)
                self.groupBox_textureMesh.setEnabled(False)
                self.groupBox_densifyPointCloud.update()
                self.groupBox_reconstructMesh.update()
                self.groupBox_refineMesh.update()
                self.groupBox_textureMesh.update()
            elif self.checkBox_MvgToMvs.isChecked() == False:
                self.checkBox_Densify.setChecked(False)
                self.checkBox_ReconstructMesh.setChecked(False)
                self.checkBox_RefineMesh.setChecked(False)
                self.checkBox_TextureMesh.setChecked(False)
                self.groupBox_densifyPointCloud.setEnabled(True)
                self.groupBox_reconstructMesh.setEnabled(True)
                self.groupBox_refineMesh.setEnabled(True)
                self.groupBox_textureMesh.setEnabled(True)
                self.groupBox_densifyPointCloud.update()
                self.groupBox_reconstructMesh.update()
                self.groupBox_refineMesh.update()
                self.groupBox_textureMesh.update()
        elif currentIndex == 5:
            if self.checkBox_Densify.isChecked() == True:
                self.checkBox_ReconstructMesh.setChecked(True)
                self.checkBox_RefineMesh.setChecked(True)
                self.checkBox_TextureMesh.setChecked(True)
                self.groupBox_reconstructMesh.setEnabled(False)
                self.groupBox_refineMesh.setEnabled(False)
                self.groupBox_textureMesh.setEnabled(False)
                self.groupBox_reconstructMesh.update()
                self.groupBox_refineMesh.update()
                self.groupBox_textureMesh.update()
            elif self.checkBox_Densify.isChecked() == False:
                self.checkBox_ReconstructMesh.setChecked(False)
                self.checkBox_RefineMesh.setChecked(False)
                self.checkBox_TextureMesh.setChecked(False)
                self.groupBox_reconstructMesh.setEnabled(True)
                self.groupBox_refineMesh.setEnabled(True)
                self.groupBox_textureMesh.setEnabled(True)
                self.groupBox_reconstructMesh.update()
                self.groupBox_refineMesh.update()
                self.groupBox_textureMesh.update()
        elif currentIndex == 6:
            if self.checkBox_ReconstructMesh.isChecked() == True:
                self.checkBox_RefineMesh.setChecked(True)
                self.checkBox_TextureMesh.setChecked(True)
                self.groupBox_refineMesh.setEnabled(False)
                self.groupBox_textureMesh.setEnabled(False)
                self.groupBox_refineMesh.update()
                self.groupBox_textureMesh.update()
            elif self.checkBox_ReconstructMesh.isChecked() == False:
                self.checkBox_RefineMesh.setChecked(False)
                self.checkBox_TextureMesh.setChecked(False)
                self.groupBox_refineMesh.setEnabled(True)
                self.groupBox_textureMesh.setEnabled(True)
                self.groupBox_refineMesh.update()
                self.groupBox_textureMesh.update()
        elif currentIndex == 7:
            if self.checkBox_RefineMesh.isChecked() == True:
                self.checkBox_TextureMesh.setChecked(True)
                self.groupBox_textureMesh.setEnabled(False)
                self.groupBox_textureMesh.update()
            elif self.checkBox_ReconstructMesh.isChecked() == False:
                self.checkBox_TextureMesh.setChecked(False)
                self.groupBox_textureMesh.setEnabled(True)
                self.groupBox_textureMesh.update()
            

    def optionChecking(self):
        #LOW Level로 옵션 초기화
        if self.horizontalSlider.value() >= 0 and self.horizontalSlider.value() <= 25:
            self.horizontalSlider.setValue = 0

            self.radioBtn_SIFT.setChecked(True)
            self.radioBtn_0.setChecked(True)
            self.radioBtn_NORMAL.setChecked(True)
            self.radioBtn_08.setChecked(True)
            self.radioBtn_f.setChecked(True)
            self.radioBtn_FASTCASCADEHASHINGL2.setChecked(True)
            self.radioBtn_RL_3.setChecked(True)
            self.radioBtn_minPoint_25f.setChecked(True)
            self.radioBtn_RL_6.setChecked(True)
            self.radioBtn_RL_9.setChecked(True)

        #MEDIUM Level로 옵션 초기화
        elif self.horizontalSlider.value() > 25 and self.horizontalSlider.value() <= 50:
            self.horizontalSlider.setValue = 50

            self.radioBtn_SIFT.setChecked(True)
            self.radioBtn_0.setChecked(True)
            self.radioBtn_HIGH.setChecked(True)
            self.radioBtn_08.setChecked(True)
            self.radioBtn_f.setChecked(True)
            self.radioBtn_ANNL2.setChecked(True)
            self.radioBtn_RL_2.setChecked(True)
            self.radioBtn_minPoint_25f.setChecked(True)
            self.radioBtn_RL_5.setChecked(True)
            self.radioBtn_RL_8.setChecked(True)

        #HIGH Level로 옵션 초기화
        elif self.horizontalSlider.value() > 50 and self.horizontalSlider.value() <= 100:
            self.horizontalSlider.setValue = 100

            self.radioBtn_SIFT.setChecked(True)
            self.radioBtn_0.setChecked(True)
            self.radioBtn_ULTRA.setChecked(True)
            self.radioBtn_08.setChecked(True)
            self.radioBtn_f.setChecked(True)
            self.radioBtn_ANNL2.setChecked(True)
            self.radioBtn_RL_1.setChecked(True)
            self.radioBtn_minPoint_6.setChecked(True)
            self.radioBtn_RL_4.setChecked(True)
            self.radioBtn_RL_7.setChecked(True)

    
    def getPlyContainer(self, MyWindow):
        #ply viewer 생성  & ply 파일 read
        global stepCount, WinID

        stepCount += 1

        #캡쳐 버튼 활성화
        self.btn_capture.setEnabled(True)

        find_str = list(["robust", "dense", "refine", "texture"])

        def returnDir(step_):
            if step_ == 1:
                return os.path.join(reconstruction_dir, "robust_colorized.ply")
            elif step_ == 2:
                return os.path.join(Scene_dir, "scene_dense.ply")
            elif step_ == 3:
                return os.path.join(Scene_dir, "scene_dense_mesh_refine.ply")
            elif step_ == 4:
                return os.path.join(Scene_dir, "scene_dense_mesh_refine_texture.ply")

        pSteps = subprocess.Popen( [os.path.join(OPENMVG_SFM_BIN, "Viewer"), returnDir(stepCount)] )
        grep = "wmctrl -l | grep -i " + find_str[stepCount-1] + " | awk '{print $1}'"
            
        while True:
            viewerWinID_str = subprocess.getoutput(grep)
            if viewerWinID_str != "":
                break

        window = QWindow.fromWinId(int(viewerWinID_str, 16))
        window.setFlags(Qt.FramelessWindowHint)
        MyWindow.windowcontainer = MyWindow.createWindowContainer(window)

        if stepCount == 1:
            self.tab1.layout = QtWidgets.QVBoxLayout()
            self.tab1.layout.addWidget(MyWindow.windowcontainer)
            self.tab1.setLayout(self.tab1.layout)
            time.sleep(0.2)

        elif stepCount == 2:
            self.tab2 = QtWidgets.QWidget()
            self.tab2.layout = QtWidgets.QVBoxLayout()
            self.tab2.layout.addWidget(MyWindow.windowcontainer)
            self.tab2.setLayout(self.tab2.layout)
            time.sleep(0.1)
            self.tabs.addTab(self.tab2, "Densify Point Cloud")

        elif stepCount == 3:
            self.tab3 = QtWidgets.QWidget()
            self.tab3.layout = QtWidgets.QVBoxLayout()
            self.tab3.layout.addWidget(MyWindow.windowcontainer)
            self.tab3.setLayout(self.tab3.layout)
            time.sleep(0.1)
            self.tabs.addTab(self.tab3, "Mesh")

        elif stepCount == 4:
            self.tab4 = QtWidgets.QWidget()
            self.tab4.layout = QtWidgets.QVBoxLayout()
            self.tab4.layout.addWidget(MyWindow.windowcontainer)
            self.tab4.setLayout(self.tab4.layout)
            time.sleep(0.1)
            self.tabs.addTab(self.tab4, "Texture")

        
    def startPipline(self, MainWindow):
        global mrcnn_swt

        # RCNN checkbox 확인
        if self.checkBox_rcnn.isChecked() == True:
            print("masking around the object")
            mrcnn_swt = True
        
        self.th = Thread()
        self.th.change_value.connect(self.updateProgressBar)
        self.th.change_label.connect(self.lbl_pgsbStep.setText)
        self.th.start()

        self.s = Start()
        self.s.when_step_finished.connect(lambda: self.getPlyContainer(MyWindow))
        self.s.start()
        print("Start")

    def selectOptionFunc(self, pipNum, signal):
        if pipNum == "features":
            if signal == "-m":
                option[pipNum][signal] = self.DescriberMethodGroup.checkedButton().text()
            elif signal == "-u":
                option[pipNum][signal] = self.UprightGroup.checkedButton().text()
            elif signal == "-p":
                option[pipNum][signal] = self.PresetGroup.checkedButton().text()
            print(option["features"])
        elif pipNum == "matches":
            if signal == "-r":
                option[pipNum][signal] = self.RatioGroup.checkedButton().text()
            elif signal == "-g":
                option[pipNum][signal] = self.GeometricModelGroup.checkedButton().text()
            elif signal == "-n":
                option[pipNum][signal] = self.NearestMatchingGroup.checkedButton().text()
            
            print(option["matches"])
        elif pipNum == "seq":
            if signal == "-f":
                option[pipNum][signal] = self.RefineIntrinsicsGroup.checkedButton().text()
            print(option["seq"])
        elif pipNum == "densify":
            if signal == "--resolution-level":
                option[pipNum][signal] = self.DensifyResolutionGroup.checkedButton().text()
            print(option["densify"])
        elif pipNum == "mesh":
            if signal == "-d":
                option[pipNum][signal] = self.MinPointGroup.checkedButton().text()
            print(option["mesh"])
        elif pipNum == "refine":
            if signal == "--resolution-level":
                option[pipNum][signal] = self.ResolutionGroup.checkedButton().text()
            elif signal == "--max-face-area":
                option[pipNum][signal] = self.MaxFaceAreaGroup.checkedButton().text()
            print(option["refine"])
        elif pipNum == "texture":
            if signal == "--resolution-level":
                option[pipNum][signal] = self.TextureResolutionGroup.checkedButton().text()
            print(option["texture"])

    def outputDialogFunc(self, MyWindow):
        #QFileDialog.getOpenFileName()
        global output_dir, ChangeWhite_dir, matches_dir, reconstruction_dir, Scene_dir
        
        output_dir = str(QFileDialog.getExistingDirectory(self.centralwidget)) + "/"
        ChangeWhite_dir = os.path.join(output_dir, "ChangeWhite")
        matches_dir = os.path.join(output_dir, "Matches")
        reconstruction_dir = os.path.join(output_dir, "Reconstruct")
        Scene_dir = os.path.join(output_dir,"Scene")
        Mvs_dir = os.path.join(output_dir,"Mvs")
        
        # Create the ouput/matches folder if not present
        if not os.path.exists(matches_dir):
            os.mkdir(matches_dir)


    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Coffee is Venti"))
        self.btn_outputPath.setText(_translate("MainWindow", "Output Path"))
        self.comboBox.setItemText(0, _translate("MainWindow", "Compute Features"))
        self.comboBox.setItemText(1, _translate("MainWindow", "Compute Matches"))
        self.comboBox.setItemText(2, _translate("MainWindow", "Reconstruction (Sequential)"))
        self.comboBox.setItemText(3, _translate("MainWindow", "========================"))
        self.comboBox.setItemText(4, _translate("MainWindow", "OpenMVG to OpenMVS"))
        self.comboBox.setItemText(5, _translate("MainWindow", "Densify Point Cloud"))
        self.comboBox.setItemText(6, _translate("MainWindow", "Reconstruct Mesh"))
        self.comboBox.setItemText(7, _translate("MainWindow", "Refine Mesh"))
        self.comboBox.setItemText(8, _translate("MainWindow", "Texture Mesh"))
        self.label.setText(_translate("MainWindow", " L                       M                     H"))
        self.groupBox_computeFeatures.setTitle(_translate("MainWindow", "Options"))
        self.radioBtn_SIFT.setText(_translate("MainWindow", "SIFT"))
        self.DescriberMethod.setText(_translate("MainWindow", "Describer Method ( -m )"))
        self.radioBtn_AKAZE_FLOAT.setText(_translate("MainWindow", "AKAZE_FLOAT"))
        self.radioBtn_AKAZE_MLDE.setText(_translate("MainWindow", "AKAZE_MLDB"))
        self.Upright.setText(_translate("MainWindow", "Upright ( -u )"))
        self.radioBtn_0.setText(_translate("MainWindow", "0"))
        self.radioBtn_1.setText(_translate("MainWindow", "1"))
        self.Preset.setText(_translate("MainWindow", "Preset ( -p )"))
        self.radioBtn_NORMAL.setText(_translate("MainWindow", "NORMAL"))
        self.radioBtn_HIGH.setText(_translate("MainWindow", "HIGH"))
        self.radioBtn_ULTRA.setText(_translate("MainWindow", "ULTRA"))
        self.groupBox_computeMathes.setTitle(_translate("MainWindow", "Options"))
        self.radioBtn_08.setText(_translate("MainWindow", "0.8"))
        self.Ratio.setText(_translate("MainWindow", "Ratio ( -r )"))
        self.radioBtn_06.setText(_translate("MainWindow", "0.6"))
        self.GeometricModel.setText(_translate("MainWindow", "Geometric Model ( -g )"))
        self.radioBtn_f.setText(_translate("MainWindow", "Fundamental"))
        self.radioBtn_e.setText(_translate("MainWindow", "Essential"))
        self.NearestMatching.setText(_translate("MainWindow", "Nearest Matching ( -n )"))
        self.radioBtn_AUTO.setText(_translate("MainWindow", "AUTO"))
        self.radioBtn_BRUTEFORCEL2.setText(_translate("MainWindow", "BRUTEFORCEL2"))
        self.radioBtn_ANNL2.setText(_translate("MainWindow", "ANNL2"))
        self.radioBtn_h.setText(_translate("MainWindow", "Homography"))
        self.radioBtn_CASCADHEASHINGL2.setText(_translate("MainWindow", "CASCADE\n"
"HASHINGL2"))
        self.radioBtn_FASTCASCADEHASHINGL2.setText(_translate("MainWindow", "FASTCASCADE\n"
"HASHINGL2"))
        self.radioBtn_BRUTEFORCEHAMMING.setText(_translate("MainWindow", "BRUTEFORCE\n"
"HAMMING"))
        self.groupBox_sequential.setTitle(_translate("MainWindow", "Options"))
        self.radioBtn_ALL.setText(_translate("MainWindow", "ADJUST_ALL"))
        self.RefineIntrinsics.setText(_translate("MainWindow", "Refine Instrinsics ( -f )"))
        self.radioBtn_NONE.setText(_translate("MainWindow", "NONE"))
        self.radioBtn_FOCAL_LENGTH.setText(_translate("MainWindow", "ADJUST_\n"
"FOCAL_LENGTH"))
        self.radioBtn_PRINCIPAL_POINT.setText(_translate("MainWindow", "ADJUST_\n"
"PRINCIPAL_\n"
"POINT"))
        self.radioBtn_DISTORTION.setText(_translate("MainWindow", "ADJUST_\n"
"DISTORTION"))

        self.groupBox_MvgToMvs.setTitle(_translate("MainWindow", "Options"))
        self.lbl_non.setText(_translate("MainWindow", "NONE"))
        self.groupBox_densifyPointCloud.setTitle(_translate("MainWindow", "Options"))
        self.ResolutionLevel.setText(_translate("MainWindow", "Resolution-Level\n"
"(Image Scale Down)"))
        self.radioBtn_RL_1.setText(_translate("MainWindow", "1"))
        self.radioBtn_RL_2.setText(_translate("MainWindow", "2"))
        self.radioBtn_RL_3.setText(_translate("MainWindow", "3"))
        self.groupBox_reconstructMesh.setTitle(_translate("MainWindow", "Options"))
        self.radioBtn_minPoint_25f.setText(_translate("MainWindow", "2.5f"))
        self.mimPointDistance.setText(_translate("MainWindow", "Min-Point-Distance"))
        self.radioBtn_minPoint_6.setText(_translate("MainWindow", "6"))
        self.groupBox_refineMesh.setTitle(_translate("MainWindow", "Options"))
        self.ResolutionLevel_2.setText(_translate("MainWindow", "Resolution-Level\n"
"(Image Scale Down)"))
        self.radioBtn_RL_4.setText(_translate("MainWindow", "1"))
        self.radioBtn_RL_5.setText(_translate("MainWindow", "2"))
        self.radioBtn_RL_6.setText(_translate("MainWindow", "3"))
        self.MaxFaceArea.setText(_translate("MainWindow", "Max-Face-Area"))
        self.radioBtn_MaxFace_32.setText(_translate("MainWindow", "32"))
        self.radioBtn_MaxFace_64.setText(_translate("MainWindow", "64"))
        self.radioBtn_MaxFace_16.setText(_translate("MainWindow", "16"))
        self.MeshFile.setText(_translate("MainWindow", "Mesh File"))
        self.groupBox_textureMesh.setTitle(_translate("MainWindow", "Options"))
        self.TextureMesh.setText(_translate("MainWindow", "Resolution-Level\n"
"(Image Scale Down)"))
        self.radioBtn_RL_7.setText(_translate("MainWindow", "1"))
        self.radioBtn_RL_8.setText(_translate("MainWindow", "2"))
        self.radioBtn_RL_9.setText(_translate("MainWindow", "3"))
        self.btn_capture.setIcon(QtGui.QIcon('UI_Image/capture.png'))
        self.btn_capture.setIconSize(QtCore.QSize(24,24))
        self.btn_start.setText(_translate("MainWindow", "Start"))
        self.btn_QR.setText(_translate("MainWindow", "QR"))
        self.btn_fImage.setIcon(QtGui.QIcon('UI_Image/imageIcon.png'))
        self.btn_fImage.setIconSize(QtCore.QSize(24,24))
        self.btn_fImage.setText(_translate("MainWindow", " Features"))
        self.btn_mImage.setIcon(QtGui.QIcon('UI_Image/imageIcon.png'))
        self.btn_mImage.setIconSize(QtCore.QSize(24,24))
        self.btn_mImage.setText(_translate("MainWindow", " Matches"))

    def comboBoxFunc(self, MyWindow):
        #Compute Features
        if self.comboBox.currentIndex() == 0:
            #옵션 창 변경
            self.groupBox_computeFeatures.setVisible(True)
            self.groupBox_computeMathes.setVisible(False)
            self.groupBox_sequential.setVisible(False)
            self.groupBox_MvgToMvs.setVisible(False)
            self.groupBox_densifyPointCloud.setVisible(False)
            self.groupBox_reconstructMesh.setVisible(False)
            self.groupBox_refineMesh.setVisible(False)
            self.groupBox_textureMesh.setVisible(False)
        #Compute Matches
        elif self.comboBox.currentIndex() == 1:
            self.groupBox_computeFeatures.setVisible(False)
            self.groupBox_computeMathes.setVisible(True)
            self.groupBox_sequential.setVisible(False)
            self.groupBox_MvgToMvs.setVisible(False)
            self.groupBox_densifyPointCloud.setVisible(False)
            self.groupBox_reconstructMesh.setVisible(False)
            self.groupBox_refineMesh.setVisible(False)
            self.groupBox_textureMesh.setVisible(False)
        #Sequential Reconstruction
        elif self.comboBox.currentIndex() == 2:
            self.groupBox_computeFeatures.setVisible(False)
            self.groupBox_computeMathes.setVisible(False)
            self.groupBox_sequential.setVisible(True)
            self.groupBox_MvgToMvs.setVisible(False)
            self.groupBox_densifyPointCloud.setVisible(False)
            self.groupBox_reconstructMesh.setVisible(False)
            self.groupBox_refineMesh.setVisible(False)
            self.groupBox_textureMesh.setVisible(False)
        #MVG to MVS
        elif self.comboBox.currentIndex() == 4:
            self.groupBox_computeFeatures.setVisible(False)
            self.groupBox_computeMathes.setVisible(False)
            self.groupBox_sequential.setVisible(False)
            self.groupBox_MvgToMvs.setVisible(True)
            self.groupBox_densifyPointCloud.setVisible(False)
            self.groupBox_reconstructMesh.setVisible(False)
            self.groupBox_refineMesh.setVisible(False)
            self.groupBox_textureMesh.setVisible(False)
        #Densify Point Cloud
        elif self.comboBox.currentIndex() == 5:
            self.groupBox_computeFeatures.setVisible(False)
            self.groupBox_computeMathes.setVisible(False)
            self.groupBox_sequential.setVisible(False)
            self.groupBox_MvgToMvs.setVisible(False)
            self.groupBox_densifyPointCloud.setVisible(True)
            self.groupBox_reconstructMesh.setVisible(False)
            self.groupBox_refineMesh.setVisible(False)
            self.groupBox_textureMesh.setVisible(False)
        #Reconstruct Mesh
        elif self.comboBox.currentIndex() == 6:
            self.groupBox_computeFeatures.setVisible(False)
            self.groupBox_computeMathes.setVisible(False)
            self.groupBox_sequential.setVisible(False)
            self.groupBox_MvgToMvs.setVisible(False)
            self.groupBox_densifyPointCloud.setVisible(False)
            self.groupBox_reconstructMesh.setVisible(True)
            self.groupBox_refineMesh.setVisible(False)
            self.groupBox_textureMesh.setVisible(False)
        #Refine Mesh
        elif self.comboBox.currentIndex() == 7:
            self.groupBox_computeFeatures.setVisible(False)
            self.groupBox_computeMathes.setVisible(False)
            self.groupBox_sequential.setVisible(False)
            self.groupBox_MvgToMvs.setVisible(False)
            self.groupBox_densifyPointCloud.setVisible(False)
            self.groupBox_reconstructMesh.setVisible(False)
            self.groupBox_refineMesh.setVisible(True)
            self.groupBox_textureMesh.setVisible(False)
        #Texture Mesh
        elif self.comboBox.currentIndex() == 8:
            self.groupBox_computeFeatures.setVisible(False)
            self.groupBox_computeMathes.setVisible(False)
            self.groupBox_sequential.setVisible(False)
            self.groupBox_MvgToMvs.setVisible(False)
            self.groupBox_densifyPointCloud.setVisible(False)
            self.groupBox_reconstructMesh.setVisible(False)
            self.groupBox_refineMesh.setVisible(False)
            self.groupBox_textureMesh.setVisible(True)
        
        self.groupBox_computeFeatures.update()
        self.groupBox_computeMathes.update()
        self.groupBox_sequential.update()
        self.groupBox_MvgToMvs.update()
        self.groupBox_densifyPointCloud.update()
        self.groupBox_reconstructMesh.update()
        self.groupBox_refineMesh.update()
        self.groupBox_textureMesh.update()
        #self.show()

        #self.setupUi(MyWindow)
        #MyWindow.show()


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        

        self.ui = Ui_MainWindow()
        self.startSetupUI()

    def startSetupUI(self):
        self.ui.setupUi(self)
        self.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = MyWindow()
    sys.exit(app.exec_())
