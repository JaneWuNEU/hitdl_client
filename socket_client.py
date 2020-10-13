import socket
import time
from multiprocessing import Process
#from old_code.tc_client import Set_client_bandwidth
import  sys
import os
import codecs
import pickle
import numpy as np
import struct
sys.path.append("./")
import pandas as pd
#from utils.util import ControlBandwidth
class ControlBandwidth:
    def reset_bandwidth(self):
        del_root = "tc qdisc del root dev em4"
        create_root = "tc qdisc add dev em4 root handle 1: htb default 10"
        create_root_class = "tc class add dev em4 parent 1: classid 1:10 htb rate 1000mbit"
        self.__excecute__(del_root)
        self.__excecute__(create_root)
        self.__excecute__(create_root_class)
    def change_bandwidth_demo(self,ports_list,total_bd):
        self.reset_bandwidth()
        class_id = 20
        print("===================================")
        for dport in ports_list:
            # 1. create a class under the root
            create_class = "tc class add dev em4 parent 1: classid 1:" + str(class_id) + " htb rate " + str(
                total_bd) + "mbit ceil " + str(total_bd) + "mbit"
            create_branch = "tc qdisc add dev em4 parent 1:" + str(class_id) + " handle " + str(
                class_id) + ": sfq perturb 10"
            create_filter = "tc filter add dev em4 protocol ip parent 1: prio 1 u32 match ip dport " + str(
                dport) + " 0xffff flowid 1:" + str(class_id)
            print("create_class",create_class)
            print("create_branch", create_branch)
            print("create_filter", create_filter)
            class_id = class_id + 1
            self.__excecute__(create_class)
            self.__excecute__(create_branch)
            self.__excecute__(create_filter)

    def change_bandwidth(self,edge_notice):
        """
        each model instance has an individual port which has limited bandwidth.
        This bandwidth is calcuated as $MODEL_USER_BANDWIDHT * $user_num_per_ins
        input:
        ports_details: Dict. e.g.{ inception:[], #ports list assigned for each model instance  resnet:[], mobilenet:[] }
        model_details: dict. e.g. {inception:{k:,ins_num: X,user_num_per_ins:Y} resnet:{...},mobilenet:{...}},
        """
        ports_details = edge_notice["port_details"]
        model_details = edge_notice["model_details"]
        self.reset_bandwidth()
        class_id = 20
        for model_name in ["inception","mobilenet","resnet"]:
            ports_list = ports_details[model_name]
            total_bd = Static_Info[model_name.capitalize()+"USER_BANDWIDTH"]*model_details[model_name]["user_num_per_ins"]
            for dport in ports_list:
                # 1. create a class under the root
                create_class = "tc class add dev em4 parent 1: classid 1:"+str(class_id)+" htb rate "+str(total_bd)+"mbit ceil "+str(total_bd)+"mbit"
                create_branch = "tc qdisc add dev em4 parent 1:"+str(class_id)+" handle "+str(class_id)+": sfq perturb 10"
                create_filter = "tc filter add dev em4 protocol ip parent 1: prio 1 u32 match ip dport "+str(dport)+" 0xffff flowid 1:"+str(class_id)
                class_id = class_id+1
                self.__excecute__(create_class)
                self.__excecute__(create_branch)
                self.__excecute__(create_filter)


    def __excecute__(self,command):
        sudoPassword = "wujing123"
        p = os.system('echo %s|sudo -S %s' % (sudoPassword, command))
def listen_port():
    """
    listen to the data sent from gpu01
    """
    edge_port = 10990
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    server.bind(("0.0.0.0",edge_port))
    server.listen()
    conn,addr = server.accept()
    data = conn.recv(100)
    conn.close()
    print(data)
def send_large_data(user_num):
    """
    send data to gpu01
    """
    gpu01_ip = "192.168.1.16"
    gpu01_port = 10990

    data = '*'*204800

    for i in range(10000):
        a = time.time()
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # client.bind(('0.0.0.0',gpu01_port+user_num))
        client.connect((gpu01_ip, gpu01_port))
        b = time.time()
        amount= client.send(bytes(data))
        c = time.time()
        client.close()
        d = time.time()
        print("connect",b-a,"send",c-b,"close",d-c)
        print("amount",amount,"speed",amount*8/1024.0/1024/(c-b),"Mb/s")
        time.sleep(0.5)

def conn_port(user_num,gpu01_port,local_port):
    """
    send data to gpu01
    """
    gpu01_ip = "192.168.1.16"
    try:
        # print("pause user", edge_ip, edge_port)
        j = 0
        a = time.time()
        b = time.time()
        for i in range(100):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            #client.bind(("192.168.1.14",local_port))
            client.connect((gpu01_ip, gpu01_port))
            a = time.time()
            data = client.send(bytes("*"*1024000))
            b = time.time()
            print("user", user_num, "  ith", i,1,"speed",data*8.0/1024/1024/(b-a),"Mbit/s")
            client.close()
            os.system('fuser -k -n tcp ' + str(local_port))
        '''
        while j<50:
            client.send(bytes("pid "+str(os.getpid())+" index "+str(j))+" round "+str(i)+"+++++++++++")
            print("socket ",client.getsockname(),"send j",j,"peer name",client.getpeername())
            j = j+1
            time.sleep(3)
        client.close()
        i = i + 1
        '''
    except Exception as e:
        print(e)

#request_records[str(upload_data["data"]["pic_num"])]["mobile_send_time"] = round(b-a,3)
'''
# 1. set the bandwidth
controller = ControlBandwidth()
controller.change_bandwidth_demo([10990,10991],100)
for i in range(5):
    #os.system('fuser -k -n tcp '+str(10990+i))
    edge = Process(target=conn_port,args=[i,10990,1100])
    edge.start()

for i in range(5,5+5):
    #os.system('fuser -k -n tcp '+str(10990+i))
    edge = Process(target=conn_port,args=[i,10991,1200])
    edge.start()
'''
model_name = "inception"
layer_name_dict = {"inception":['input','Conv2d_1a_3x3','Conv2d_2a_3x3' ,'Conv2d_2b_3x3' ,'MaxPool_3a_3x3' ,'Conv2d_3b_1x1' ,'Conv2d_4a_3x3'
                        ,'MaxPool_5a_3x3' ,'Mixed_5b' ,'Mixed_5c' ,'Mixed_5d' ,'Mixed_6a','Mixed_6b' ,'Mixed_6c' ,'Mixed_6d'
                        ,'Mixed_6e' ,'Mixed_7a' ,'Mixed_7b' ,'Mixed_7c','Predictions'],
              "resnet":["input","conv1", "pool1", 'block1/unit_1', 'block1/unit_2', 'block1/unit_3',
                 'block2/unit_1', 'block2/unit_2', 'block2/unit_3', 'block2/unit_4',
                 'block3/unit_1', 'block3/unit_2', 'block3/unit_3', 'block3/unit_4',
                 'block3/unit_5', 'block3/unit_6', 'block4/unit_1', 'block4/unit_2',
                 'block4/unit_3', "global_pool",'predictions'],
              "mobilenet":['input','Conv2d_0', 'Conv2d_1_pointwise', 'Conv2d_2_pointwise',
                'Conv2d_3_pointwise', 'Conv2d_4_pointwise', 'Conv2d_5_pointwise',
                'Conv2d_6_pointwise', 'Conv2d_7_pointwise', 'Conv2d_8_pointwise',
                'Conv2d_9_pointwise', 'Conv2d_10_pointwise', 'Conv2d_11_pointwise',
                'Conv2d_12_pointwise', 'Conv2d_13_pointwise','Predictions']}


#for layer_name_list in layer_name_dict[model_name]:
def layer_size():
    layer_size_file = "input_data/layer_size.xlsx"
    writer = pd.ExcelWriter(layer_size_file)
    for model_name in ["inception","resnet"]:
        layer_name_list = layer_name_dict[model_name]
        layer_size = {}
        for layer_name in layer_name_list[:len(layer_name_list)-1]:
            layer_name = layer_name.replace("/","_")
            im = np.load("input_data/" + model_name + "/"+layer_name+"_guitar.npy")
            im = im[np.newaxis, :]
            data = codecs.encode(pickle.dumps(im), "base64").decode()
            upload_data = {"recv_port":1000,"data":data,"user_ip":'192.168.1.16',"user_id":2}
            content = bytes(str(upload_data), encoding="utf-8")
            msg = struct.pack('>I', len(content)) + content
            layer_size[layer_name] = len(msg)
        result = pd.DataFrame(data = layer_size,index=["size(B)"])
        result.to_excel(excel_writer=writer,sheet_name=model_name)
    writer.save()
    writer.close()

