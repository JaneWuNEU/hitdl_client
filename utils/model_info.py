# -*- coding: utf-8 -*-
import xml.dom.minidom
import numpy as np
import sys
sys.path.append(".")
class ModelInfo():
    def __init__(self):
        pass
    def get_input_shape(self,model_name):
        dom = xml.dom.minidom.parse('utils/model_info.xml')
        # root is an document element
        root = dom.documentElement
        # model is an element of each model
        model = root.getElementsByTagName(model_name)[0]
        input_shape = eval(model.getElementsByTagName('input_shape')[0].firstChild.data)
        return input_shape



    def get_layer_name_by_index(self,model_name,layer_index):
        """
        :param model_name:
        :param layer_index: [1,layer_num]
        layer_index==0 means the input layer.
        :return:
        """
        dom = xml.dom.minidom.parse('utils/model_info.xml')
        # root is an document element
        root = dom.documentElement
        # model is an element of each model
        model = root.getElementsByTagName(model_name)[0]
        layer_name = model.getElementsByTagName('model_layer_name')[0].firstChild.data
        layer_name = eval(layer_name.replace(" ","").replace("\n",""))
        result = None
        if layer_index == -1:
            result = layer_name[len(layer_name)]
        else:
            result = layer_name[layer_index]
        #result = result.replace("/","_")
        return result





#ModelInfo.get_model_layer_shape('inception_v3',None)