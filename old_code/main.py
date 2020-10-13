import os
import time
import sys
sys.path.append("./")
import socket
from old_code.communication import ThreadMonitor_model, ThreadMonitor_notice,ProcessModel_instance
from utils.model_info import ModelInfo
from utils.util import SocketCommunication
from openpyxl import Workbook
from utils.util import Static_Info
import tensorflow as tf
import tf_slim as slim
import model_zoo.net.resnet_v2 as resnet_v2
import model_zoo.net.inception_v3 as inception_v3
import tf_slim.nets.mobilenet_v1 as mobilenet_v1

register_info = {'r1': -1, 'port': 0}
i = 3
request_result = {"device":{},"edge":{}}
user_num = None
class MainRun:
    def __init__(self, model_delay_ratio, user_num, model_type, mobile_type, device):
        '''
        initialize main
        :param user_num: identify each user
        :param model_type: number 1~4 represent 'alexnet', 'autoencoder', 'vgg16', 'srgan'
        :param mobile_type: 'M' + str(num)
        :param device:
        '''
        #self.mobile_db = mobile_db
        self.user_num = user_num
        self.model_type = Static_Info.model_type[model_type-1]
        self.mobile_type = 'M' + str(mobile_type)
        self.bandwidth_port = 10000 + user_num #
        self.server_port = 20000 + user_num
        self.model_port = 30000 + user_num
        self.record = dict()
        self.device = device
        self.model_delay_ratio = model_delay_ratio
        self.model_id = self.generate_model_id(self.model_type, self.mobile_type, str(user_num))   # generate model_id
        print('Your user number is ', user_num)
        print('The system is initializing. Please wait...')

        self.thread_monitor_notice = None
        self.thread_model_result = None


        model_info = ModelInfo()
        self.model_name = self.model_id["model_id"].split('*')[0]
        self.layer_num = model_info.get_layer_nums(self.model_name)
        input_shape = model_info.get_input_shape(self.model_name)
        self.image_path = "images/guitar.jpg"
        self.local_model_time = []
        print("Initialization has complete! Camera is ready! You can registration now!")
        self.model_delay_ratio = model_delay_ratio
        self.socket_re_deregister = SocketCommunication()
        self.record = {}

    def generate_model_id(self, model_type, mobile_type, user_num):
        #print("model_type",model_type)
        model_id = '*'.join([model_type, Static_Info.USER_IP, mobile_type, user_num])
        return {"model_id": model_id}
    def register(self):
        '''
        Send register info
        :return:
        '''
        result = True
        #try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # 1. connect servers
            client.connect((Static_Info.SERVER_IP, 10990))
            print((Static_Info.SERVER_IP, 10990))
            # 2. send register info
            self.socket_re_deregister.send_data(client,str(self.model_id))  # send registration info to the server
            print("send registering data")
            response = self.socket_re_deregister.recv_data(client)
            if response == 'Have Registered': #have registerd
                result = False
            elif response == 'Register Successfully': #register succesfully
                # listen to the server's response namely notice info
                try:
                    self.thread_monitor_notice = ThreadMonitor_notice(self.model_id, self.server_port)
                    self.thread_monitor_notice.start()
                except Exception as e:
                    print("monitor_notice",e,self.server_port)
                    result = False
                    mgs = 'fuser -k -n tcp '+str(self.server_port)
                    os.system(mgs)
                try:
                    self.thread_model_result = ThreadMonitor_model(self.model_id, self.model_port)
                    self.thread_model_result.start()
                    self.process_model_instance = ProcessModel_instance(self.model_id)
                except Exception as e:
                    print("create model monitor")
                    result = False
                    mgs = 'fuser -k -n tcp '+str(self.model_port)
                    os.system(mgs)
            else:
                result = False
            client.close()
        except Exception as e:
            print("fail to register",e)
            result = False
        return result
    def deregister(self):
        '''
        Send deregister request
        :return:
        1-->deregister failed
        0-->register failed
        '''
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 1. connect server
            client.connect((Static_Info.SERVER_IP, 10980))
            self.socket_re_deregister.send_data(client,str(self.model_id))
            client.close()
            self.thread_model_result.stop_thread()
            self.thread_monitor_notice.stop_thread()
            self.process_model_instance.close_send_socket()
        except Exception as e:
            print('Deregistration Failed!',e)
            return 1
        return 0

    def capture_image(self, interval):
        """
        run complete model locally or run the partitioned model.
        r1 = -1, run the complete model, return the final result.
        Otherwise, run the partitioned model, return pic_num.
        :param picture_num:
        :return:
        """
        capture_begin = time.time()
        picture_num = 1
        sess_config = tf.ConfigProto(intra_op_parallelism_threads=2, log_device_placement=False)
        if self.model_name == "inception_v3":
            model_path = "model_zoo/weights/inception_v3_quant.ckpt"
            input_images = tf.placeholder(dtype=tf.float32, shape=[None, 299, 299, 3], name='input')
            with tf.Session(config=sess_config) as sess:
                with tf.contrib.slim.arg_scope(mobilenet_v1.mobilenet_v1_arg_scope(is_training=False)):
                    out, endpoints = mobilenet_v1.mobilenet_v1(inputs=input_images, is_training=False)
                    sess.run(tf.global_variables_initializer())
                    saver = tf.train.Saver()
                    saver.restore(sess, model_path)
                    while time.time() - capture_begin < interval:
                        start = time.time()
                        self.record[str(picture_num)] = {}
                        self.record[str(picture_num)]['start time'] = start
                        notice_info = self.thread_monitor_notice.get_server_notice()
                        r1 = notice_info['r1']
                        port = int(notice_info['port'])
                        t = time.time()
                        self.record[str(picture_num)]['run start'] = t
                        # r1,server_port,picture_num,out,endpoints,sess,input_images
                        result = self.process_model_instance.process_image(r1, port, picture_num,out,endpoints,sess,input_images)
                        picture_num += 1
        elif self.model_name == "resnet50":
            model_path = "model_zoo/weights/resnet_v2_50.ckpt"
            input_images = tf.placeholder(dtype=tf.float32, shape=[None, 224,224,3], name='input')
            with tf.Session(config=sess_config) as sess:
                with slim.arg_scope(resnet_v2.resnet_arg_scope()):
                    out, end_points = resnet_v2.resnet_v2_50(inputs=input_images,is_training=False)
                    sess.run(tf.global_variables_initializer())
                    saver = tf.train.Saver()
                    saver.restore(sess, model_path)
                    while time.time() - capture_begin < interval:
                        start = time.time()
                        self.record[str(picture_num)] = {}
                        self.record[str(picture_num)]['start time'] = start
                        notice_info = self.thread_monitor_notice.get_server_notice()
                        r1 = notice_info['r1']
                        port = int(notice_info['port'])
                        t = time.time()
                        self.record[str(picture_num)]['run start'] = t
                        result = self.process_model_instance.process_image(self.frame, r1, port, picture_num,
                                                                           self.image_path,out,end_points,sess)
                        picture_num += 1
        else:
            model_path = "model_zoo/weights/mobilenet_v1_1.0_224.ckpt"
            input_images = tf.placeholder(dtype=tf.float32, shape=[None, 224,224,3], name='input')
            with tf.Session(config=sess_config) as sess:
                with slim.arg_scope(inception_v3.inception_v3_arg_scope()):
                    out, end_points = inception_v3.inception_v3(inputs=input_images, is_training=False,create_aux_logits=False)
                    sess.run(tf.global_variables_initializer())
                    saver = tf.train.Saver()
                    saver.restore(sess, model_path)

                    while time.time() - capture_begin < interval:
                        start = time.time()
                        self.record[str(picture_num)] = {}
                        self.record[str(picture_num)]['start time'] = start
                        notice_info = self.thread_monitor_notice.get_server_notice()
                        r1 = notice_info['r1']
                        port = int(notice_info['port'])
                        t = time.time()
                        self.record[str(picture_num)]['run start'] = t
                        result = self.process_model_instance.process_image(self.frame, r1, port, picture_num,
                                                                           self.image_path,out,end_points,sess)
                        picture_num += 1


    def write_to_file(self):
        wb = Workbook()
        ws = wb.active  # 激活 worksheet
        row = ['usernum_picturenum', 'start time', 'end time', 'total time','local/edge','run start','client start','socket start','socket end']
        ws.append(row)
        for key in self.record:
            if 'end time' in self.record[key].keys():
                row = [str(self.user_num)+'_' + key, self.record[key]['start time'], self.record[key]['end time'],
                       self.record[key]['end time'] - self.record[key]['start time'], 'local']
            elif 'end time at edge' in self.record[key].keys():
                row = [str(self.user_num)+'_' + key, self.record[key]['start time'], self.record[key]['end time at edge'],
                       self.record[key]['end time at edge'] - self.record[key]['start time'], 'edge',self.record[key]['run start'],self.record[key]['client start'],self.record[key]['socket start'],self.record[key]['socket end']]
            else:
                row = [str(self.user_num)+'_' + key, self.record[key]['start time'], 'NULL', 'NULL', 'NULL']
            ws.append(row)
        wb.save('./'+str(self.user_num)+'.xlsx')

def start_client(user_num_input,model_type,mobile_type,model_delay_ratio):
    global user_num
    user_num = user_num_input
    mobile = MainRun(model_delay_ratio,user_num,model_type,mobile_type, "CPU:0")
    while not mobile.register():    # If registration failed, try again until succeed
        pass
    print("register successfully")

    mobile.capture_image(180)
    while mobile.deregister():    # If deregistration failed, try again until succeed
        pass
    print("user num",user_num,"deregsiter successfully")

