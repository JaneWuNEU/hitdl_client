import numpy as np
import cv2
import os
import codecs
#from utils.util import read_image
import sys
from threading import  Timer
sys.path.append(".")
def deal_image():
    image_path = "images/fireboat.jpg"
    img_byte = open(image_path, 'rb').read()

    img = cv2.imread(image_path)

    #图片信息由byte转为string,并改变编码方式
    img_str = codecs.encode(img_byte, "base64").decode()

    #图片
    output_data = codecs.decode(img_str.encode(), "base64")
    print(type(img_str),type(output_data))
    nparr = np.fromstring(output_data, np.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    rgb_image = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
    print((img_np==rgb_image).all())
    #("image",type(img_np))
    #print(type(output_data),len(output_data))

def helle():
    print("hello")
    timer = Timer(3, helle)
    timer.start()
#timer = Timer(3,helle)
#timer.start()
#data = np.random.random(1024)
#print(np.size(data)*data.itemsize)








