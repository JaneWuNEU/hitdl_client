#import tensorflow as tf
import numpy as np
import cv2
import socket
import struct
import pickle
import time
import sys
sys.path.append("./")
from utils.image_classes import class_names
from utils.util import SocketCommunication as sock
import os
from utils.util import Static_Info
from utils.util import SocketCommunication
from threading import Thread
import json
import threading.Queue as Queue
from datetime import datetime
import codecs
from multiprocessing import Process
import tensorflow as tf
'''
from model_zoo.models.alexnet import alexnet
from model_zoo.models.autoencoder import autoencoder
from model_zoo.models.srgan import srgan
from model_zoo.models.vgg16 import vgg16
'''
from utils.model_info import ModelInfo
class ThreadMonitor_notice(Thread):
    """
    get notice from the server
    """
    def __init__(self, model_id, server_port):
        # super().__init__(self)
        Thread.__init__(self)
        self.model_id = model_id
        # print("model notice",model_id)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IP = model_id["model_id"].split('*')[1] # open 2000+$user_num port and listen to the server's response
        self.PORT = server_port
        self.server.bind((self.IP, self.PORT))
        self.server.listen(100)
        self.server_notice = None
        self.sock_tool = SocketCommunication()
        self.stop = False

    def stop_thread(self):
        self.stop = True

    def get_server_notice(self):
        if self.server_notice is None:
            self.server_notice = {}
            self.server_notice["r1"] = -1
            self.server_notice["port"] = 0
        return self.server_notice

    def run(self):
        while not self.stop:
            try:
                conn, addr = self.server.accept()
                # receive data
                result = self.sock_tool.recv_data(conn)
                #print("server_notice", result)
                self.server_notice = eval(result)
                conn.close()
            except Exception as e:
                print("error happens when monitoring server's response",e)

class ThreadMonitor_bandwidth(Thread):   # help to send the bandwidth message
    def __init__(self, bandwidth_port):
        super().__init__(self)
        self.bandwidth_port = bandwidth_port

    def run(self):
        file_path = os.getcwd() + "/images/zebra.jpeg"
        file_name = (os.path.split(file_path))[1]
        with open(file_path, 'rb')as f:
            date = f.read()
            size = len(date)
        handler = {'file_name': file_name, 'length': size}
        handler_json = json.dumps(handler)
        handler_bytes = handler_json.encode('utf-8')
        s_handler = struct.pack('i', len(handler_bytes))

        band = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        band.bind((Static_Info.USER_IP, self.bandwidth_port))
        band.listen(5)
        k = 0
        while True:
            conn, addr = band.accept()
            s_hander = conn.recv(4)     # 获取报头长度bytes
            s_hander = struct.unpack('i', s_hander)[0]     # 解包bytes-》tuple-》int，获得报头长度
            b_hander = conn.recv(s_hander)     # 获取报头数据，bytes
            json_hander = b_hander.decode('utf-8')      # 报头数据解码 bytes-》str
            hander = json.loads(json_hander)   # 报头数据反序列化 str-》dict
            file_size = hander['length']    # 获取报头字典，取的文件长度，取出文件内容
            size = 0
            start_time = time.time()
            while size < file_size:
                data = conn.recv(1024)
                size = size + len(data)
            end_time = time.time()
            bandwidth = file_size / (end_time - start_time) / 1000 / 1000 * 8
            conn.sendall(bytes(str(bandwidth), encoding='UTF-8'))
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client.bind((Static_Info.USER_IP, (self.bandwidth_port-10000) * 100 + 21000 + k))
            client.connect((Static_Info.SERVER_IP, self.bandwidth_port))
            client.send(s_handler)
            client.send(handler_bytes)
            client.send(date)
            client.close()
            k = (k + 1) % 100

class ThreadMonitor_model(Thread):

    def __init__(self, model_id, model_port):
        """
        receive process result from the edge
        """
        # super().__init__(self)
        Thread.__init__(self)
        self.model_id = model_id
        self.model_name = self.model_id["model_id"].split('*')[0]
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IP = model_id["model_id"].split('*')[1]
        # open 1099 port and listen to the server's response
        self.PORT = model_port
        self.server.bind((Static_Info.USER_IP, self.PORT))
        self.server.listen(100)
        self.socket_tool = SocketCommunication()
        self.stop = False

    def stop_thread(self):
        self.stop = True

    def run(self):
        try:
            print("receive results from the server")
            conn, addr = self.server.accept()
            while not self.stop:
                try:
                    result = self.socket_tool.recv_data(conn)
                    if result is not None:
                        result = result.split('_')  # pic_num, data, edge_return_time
                        edge_return_time = result[2]
                        ID = result[0]
                        data = codecs.decode(result[1].encode(), "base64")
                        result = pickle.loads(data)
                        #print("returned results",result)
                        print("model_name", self.model_name)
                        if self.model_name == "inception_v3":
                            index = np.argmax(result)
                            result = ID + ': This is ' + class_names[index]
                            print("edge model returns",result)
                        else:
                            print("other models")
                except Exception as e:
                    print("monitor model result errors",e)
            conn.close()
        except Exception as e:
            print("open model monitor responsing port errors",e)

class ProcessModel_instance():
    def __init__(self, model_id):
        self.user_num = model_id["model_id"].split("*")[3]
        self.model_name = model_id["model_id"].split("*")[0]
        self.model_id = model_id["model_id"]
        self.SEND_PORT = 11000 + int(self.user_num)*100 #发送数据的端口
        self.establish_conn = False
        self.interval = None
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.client.bind((Static_Info.USER_IP, self.SEND_PORT))
        self.sock_tool = SocketCommunication()
        self.model_info = ModelInfo()
        self.data_queue = Queue.Queue()
        self.cur_server_port = None
        send_data2edge_thread = Thread(target=self.send_data_to_edge)
        send_data2edge_thread.start()
    def send_data_to_edge(self):
        # 1. establish connection
        while True:
            if not self.establish_conn:  # connection has never build
                self.client.connect((Static_Info.SERVER_IP, self.cur_server_port))
                self.SERVER_PORT = self.cur_server_port
                self.establish_conn = True
            elif self.SERVER_PORT != self.cur_server_port:  # change port
                try:
                    self.client.close()
                    self.client.connect((Static_Info.SERVER_IP,self.cur_server_port))
                    self.SERVER_PORT = self.cur_server_port
                    self.establish_conn = True
                except Exception as e:
                    print("establish server model connection failed", e)
            try:
                # 2. process the local part
                DATA = self.data_queue.get()
                t1 = time.time()
                data_size = self.send_data(self.client, DATA["DATA"])
                t2 = time.time()
                print("send to edge",DATA["pic_num"],datetime.now().strftime("%H:%M:%S"),"time cost",t2-t1)
                # print("user num",self.user_num,"edge image",picture_num,"send time",send_time,\
                #      "speed(MB/s)",1.0*data_size/1024/1024/send_time)
            except Exception as e:
                print("send data to edge errors", e)

    def close_send_socket(self):
        try:
            self.client.close()
        except Exception as e:
            print("error happens when closing the socket which sending data to edge")

    def process_image(self,r1,server_port,picture_num,out,endpoints,sess,input_images):
        # 1. process the local part
        self.cur_server_port = server_port
        if self.current_r1 == None or self.current_r1 != r1:
            self.current_r1 = r1
            layer_name = self.model_info.get_layer_name_by_index(self.model_name,self.current_r1)

        # 2. depend on the model name and partition layer to create the input placeholder
        if r1 == -1: # run locally
            print("run locally",picture_num)
            im = np.load(self.model_name+"_input_guitar.npy")
            im = im[np.newaxis, :]
            output_result = sess.run(out,feed_dict={input_images:im})

        else: # run in edge
            output_layer = endpoints[layer_name]
            im = np.load(self.model_name + "_input_guitar.npy")
            im = im[np.newaxis, :]
            output_data= sess.run(out,feed_dict={input_images:im})
            DATA = codecs.encode(pickle.dumps(output_data[0]), "base64").decode()
            DATA = str(self.user_num) + '_' + str(picture_num) + '_' + DATA + "_" + str(r1) + "_" + str(time.time())
            self.data_queue.put({"DATA":DATA,"pic_num":picture_num})
            print("picture",picture_num," Add_queue_time",datetime.now().strftime("%H:%M:%S"))
            # send the result to the edge asynchronously









            ''''''














