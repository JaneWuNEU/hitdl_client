import socket
from utils.util import Static_Info
from threading import Event,Thread
from queue import Queue
from utils.util import SocketCommunication
import time
import tensorflow as tf
import model_zoo.net.resnet_v2 as resnet_v2
import model_zoo.net.inception_v3 as inception_v3
import model_zoo.net.mobilenet_v1 as mobilenet_v1
import tensorflow.contrib.slim as slim
from utils.util import Static_Info
import numpy as np
from utils.model_info import ModelInfo
import codecs
import pickle
import os
import datetime
import pandas as pd
from tensorflow.python.util import deprecation
deprecation._PRINT_DEPRECATION_WARNINGS = False
import datetime
#from multiprocessing import Queue,Manager
import zlib
class User:
    def __init__(self,k,model_name,user_id,ins_id,ins_port,user_ip,core_id,records_file):
        '''
        initialize member variables
        '''
        # ==== create necessary member variables ===
        self.k = k
        self.model_name = model_name
        self.user_id = user_id
        self.ins_id = ins_id
        self.ins_port = ins_port
        self.user_ip = user_ip
        self.core_id = core_id
        self.recv_port = None
        self.logout_event = Event()
        self.request_records = {}
        self.model_info  = ModelInfo()
        self.recv_socket = None
        self.run_model_pid = None
        self.records_file = records_file

    def process_image(self,sess, out,input_images,im,activate_flag,data_queue,request_records):
        '''
        process images and add records the process
        tips:
        '''

        pic_num = 0
        start_send_queue = False
        # 0. confirm the frame interval
        if self.model_name == "inception":
            frame_interval = 1.0/Static_Info.INCEPTION_FRAME_RATE
        elif self.model_name == "resnet":
            frame_interval = 1.0 / Static_Info.RESNET_FRAME_RATE

        image_id = -1
        while True:
            # 1. process the image
            start_time = time.time()
            if activate_flag.value == 0:  # have not been activated.
                if out != None:
                    a = time.time()
                    result = sess.run(out, feed_dict={input_images: im})
                    image_id = np.argmax(result[0])
                    b = round(time.time(),3)
                else:
                    a = time.time()
                    b = time.time()
                #print("========local run ===========",self.user_id)
                process_image_interval = b-a
                request_records[str(pic_num)]={"start_time":start_time,"end_time":b, "image_id":image_id,"local_total_time":b-a,"local_run_time":b-a,
                                               "mobile_send_time":-1, "mobile_recv_time":-1,"edge_run_time":-1,"queue_time":0,"edge_recv_time":0,"bandwidth":0,
                                               "mobile_enqueue":b-a}
            elif activate_flag.value>0:

                if self.k !=0:
                    a = time.time()
                    result = sess.run(out, feed_dict={input_images: im})
                    #print("++++++++++++++++++++",result.shape)
                    b = time.time()
                    local_run = b-a
                else:
                    result = im
                    local_run = 0
                    #print("+++++++++++++++++++",self.model_name)
                image_id = 0
                end_time = 0
                data_queue.put({'data':result,"pic_num":pic_num})
                # 2. record the time cost of processing an image
                process_image_interval = time.time()-start_time
                #print("总时间",process_image_interval)
                request_records[str(pic_num)]={"start_time":start_time,"end_time":end_time, "image_id":image_id,"local_total_time":process_image_interval,"local_run_time":local_run,
                                               "mobile_send_time":0, "mobile_recv_time":0,"edge_run_time":0,"queue_time":0,"edge_recv_time":0,"bandwidth":0,"mobile_enqueue":0}
                process_image_interval = time.time()-start_time
            # 3. check if the sleep is necessary so as to ensure the process in a fixed frame rate
            if np.round(frame_interval-process_image_interval,3)>0.003:
                #print(")))))))))))))))",frame_interval,process_image_interval,np.round(frame_interval-process_image_interval,3))
                time.sleep(np.round(frame_interval-process_image_interval,3))

            pic_num = pic_num+1

    def get_recv_port(self):
        return self.recv_port


    def bound_pid(self,pid):
        intra = len(self.core_id)
        core_str = ''
        for i in self.core_id:
            core_str = core_str+str(i)+","
        core_str = core_str[:core_str.rindex(",")]
        if intra == 1:
            os.system("taskset -cp "+core_str+" " + str(pid))
        elif intra == 2:
            os.system("taskset -cp "+core_str+" " + str(pid))

    def run_model(self,activate_flag,recv_port,request_records):
        """
        The user should run the complete model in specific CPU cores defined by $core_id after being created.
        Only the the edge activates the user can it run the model in a hybrird way.
        1.create a queue to share with the sending thread.
        2. listen to the signal from the main process
           when the signal is  -1, it means logouts.
           when the signal is 0, it means the user has not been activated.
           when the signal is >0, it means the recv port of some model ins.
        """
        # 0. bind pid
        if self.model_name in ["resnet","inception"]:
            pid = os.getpid()
            self.bound_pid(pid)

        # 0.1 start the threads to send and receive data
        ''''''
        data_queue = Queue()
        request_records ={}
        recv_port={"recv_port":-1}
        Thread(target=self.recv_data, args=[activate_flag, recv_port, request_records]).start()
        Thread(target=self.send_data,args=[activate_flag,data_queue,recv_port,request_records]).start()

        # recv_port, recv_socket = self.assign_recv_port()


        # 1. initialize the model
        sess_config = tf.ConfigProto(intra_op_parallelism_threads=len(self.core_id), log_device_placement=False)
        partition_layer_name = self.model_info.get_layer_name_by_index(self.model_name, self.k)
        if self.model_name == "inception":
            model_path = "model_zoo/weights/inception_v3_quant.ckpt"
            input_images = tf.placeholder(dtype=tf.float32, shape=[None, 299, 299, 3], name='input')
            im = np.load("input_data/inception/inception_input_guitar.npy")
            im = im[np.newaxis,:]
            with tf.Session(config=sess_config) as sess:
                with tf.contrib.slim.arg_scope(inception_v3.inception_v3_arg_scope()):
                    if partition_layer_name!="input":
                        out, endpoints = inception_v3.inception_v3(inputs=input_images,partition_layer='input',final_endpoint=partition_layer_name)
                        sess.run(tf.global_variables_initializer())
                        saver = tf.train.Saver()
                        saver.restore(sess, model_path)
                        # 0.1 start the threads to send and receive data
                        self.process_image(sess,out,input_images,im,activate_flag,data_queue,request_records)
                    else:
                        self.process_image(sess, None, input_images, im, activate_flag, data_queue, request_records)
        elif self.model_name == "resnet":
            model_path = "model_zoo/weights/resnet_v2_50.ckpt"
            input_images = tf.placeholder(dtype=tf.float32, shape=[None, 224,224,3], name='input')
            im = np.load("input_data/resnet/resnet_input_guitar.npy")
            im = im[np.newaxis,:]
            with tf.Session(config=sess_config) as sess:
                with slim.arg_scope(resnet_v2.resnet_arg_scope()):
                    if partition_layer_name!="input":
                        out, endpoints = resnet_v2.resnet_v2_50(inputs=input_images,is_training=False,partition_layer='input',final_endpoints=partition_layer_name)
                        #print("++++++++++++++++", out)
                        sess.run(tf.global_variables_initializer())
                        saver = tf.train.Saver()
                        saver.restore(sess, model_path)
                        #print(endpoints)
                        self.process_image(sess, out, input_images, im,activate_flag,data_queue,request_records)
                    else:
                        self.process_image(sess, None, input_images, im, activate_flag, data_queue, request_records)

    def send_data(self,activate_flag,data_queue,recv_port,request_records):
        import sys
        sock_tools = SocketCommunication()
        #print("********** 准备发送数据  ***********")
        ''''''
        while True:
            if activate_flag.value >0:
                #print("********** 开始发送 ***********",self.ins_id,self.user_id)
                try:
                    data = data_queue.get()
                    a = time.time()
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    client.connect((Static_Info.EDGE_IP,activate_flag.value))
                    upload_data = {"recv_port":recv_port["recv_port"],"data":data,"user_ip":self.user_ip,"user_id":self.user_id}
                    f = time.time()

                    upload_pickles = pickle.dumps(upload_data)
                    b = time.time()
                    #print("########建立连接######", self.model_name, f - a,b-f)
                    #print("#######user send ",self.model_name,self.user_id,upload_data["data"]["pic_num"],round(time.time(),2))
                    a = time.time()
                    size = sock_tools.send_data_bytes(client,upload_pickles)
                    b = time.time()
                    #print("send size++++++++",self.model_name,sys.getsizeof(upload_pickles))
                    request_records[str(upload_data["data"]["pic_num"])]["mobile_send_time"] = round(b-a,3)
                    #print("=============upload bandwidth=========",self.user_id,b-a,activate_flag.value)
                except Exception as e:
                    #print("error happens when user send data when",self.model_name, self.user_id,Static_Info.EDGE_IP,activate_flag.value)
                    #print(e)
                    pass


    def assign_recv_port(self):

        temp_revc_port = Static_Info.SERVER_RECV_PORT_START+self.user_id*Static_Info.RECV_PORT_INTERVEL
        # 1. open a socket to listen to the results from the edge
        recv_socket = None
        while True:
            try:
                recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                recv_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                recv_socket.bind((self.user_ip, temp_revc_port))
                recv_socket.listen(5)
                recv_port = temp_revc_port
                break
            except Exception as e:
                #print("error happens when assigning recv ports ",temp_revc_port,"to user ",self.user_id,self.model_name,e)
                temp_revc_port = temp_revc_port+1
        return recv_port,recv_socket

    def recv_data(self,activate_flag,recv_port,shared_request_records):

        """
        Different types of users have different methods to assign ports.
        SERVER_USER as 1000+$user_id*$RECV_PORT_INTERVEL, RASP_USER as 2000+$user_id*$RECV_PORT_INTERVEL.
        Note that the exception may be thrown during opening a specific port marked as $wrong_port, when try a new port
        as $(wrong_port++) until an available port appears.
        """
        # 2. receive the results until the user logouts
        recv_port_id,recv_socket = self.assign_recv_port()
        recv_port["recv_port"] = recv_port_id
        comm_sock = SocketCommunication()

        file_name = "user_" + str(self.user_id) + "_" + self.model_name + "_ins_" + str(self.ins_id) + "u="+str(self.user_id)+"_k="+str(self.k)+".txt"
        file_path = "records/" + self.records_file + "/" + self.model_name+"/ins_"+str(self.ins_id)
        print("===========create files=============",file_path)
        if not os.path.exists(file_path):
            try:
                os.makedirs(file_path)
            except Exception as e:
                print("error happens when creating records files",e)
        start_time = time.time()

        while True:
            #if activate_flag.value>=0:
            conn,add = recv_socket.accept()

            last_recv_time = time.time()
            a = time.time()
            result = comm_sock.recv_data(conn)
            b = time.time()
            recv_time = b-a
            conn.close()
            end_time = time.time()
            # 2.1 depend on the edge result to refresh the records
            #print("==========recv========",self.user_id,self.ins_port)
            try:
                shared_request_records[str(result["pic_num"])]["mobile_recv_time"] = round(recv_time,3)
                shared_request_records[str(result["pic_num"])].update(result)
                if shared_request_records[str(result["pic_num"])]["end_time"] == 0:
                    shared_request_records[str(result["pic_num"])]["end_time"] = end_time
                # "mobile_recv_time":0,"edge_run_time":0,"queue_time":0,"edge_recv_time":0
                shared_request_records[str(result["pic_num"])]["edge_run_time"] = result["edge_run_time"]
                shared_request_records[str(result["pic_num"])]["queue_time"] = result["queue_time"]
                shared_request_records[str(result["pic_num"])]["edge_recv_time"] = result["edge_recv_time"]
                shared_request_records[str(result["pic_num"])]["bandwidth"] = result["bandwidth"]
                shared_request_records[str(result["pic_num"])]["local_run_time"] = result["local_run_time"]
                shared_request_records[str(result["pic_num"])]["mobile_enqueue"] = result["mobile_enqueue"]
                shared_request_records[str(result["pic_num"])]["local_total_time"] = result["local_total_time"]
            except Exception as e:
                pass
            if time.time() - start_time >= Static_Info.RECORDS_PERIODS:
                pic_num_keys = list(shared_request_records.keys())
                with open(file_path + "/"+file_name, "a") as f:
                    f.write("==========write the file============"+datetime.datetime.now().strftime("%H:%M:%S_"+str(self.ins_id)+"_"+str(self.user_id))+"==============\n")
                    records = ""
                    for pic_num in pic_num_keys:
                        try:
                            record = shared_request_records[pic_num]
                            records = records+"#"+pic_num+":"+str(record)+"\n"
                            shared_request_records.pop(pic_num)
                        except Exception as e:
                            print("error happens when saving records",pic_num)
                    f.writelines(records)
                start_time = time.time()


                #print('user', self.user_id, "model", self.model_name, 'recv_data', str(result["pic_num"]))

        # 测试如果类继承与Process，main方法是在主进程运行还是子进程运行
