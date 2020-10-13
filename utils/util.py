# -*- coding: utf-8 -*-
import struct
import sys
import os
import numpy as np
import pandas as pd
import sys
sys.path.append("./")
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
        clsss_id = 20

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
        for model_name in ["inception","resnet"]:
            if model_name == "inception":
                total_bd = edge_notice["bandwidth"]["inception"]
                #ceil_bd = total_bd*model_details[model_name]["user_num_per_ins"]
                #Static_Info.INCEPTION_USER_BANDWIDTH#Static_Info.INCEPTION_USER_BANDWIDTH*model_details[model_name]["user_num_per_ins"]
            elif model_name == "resnet":
                total_bd = edge_notice["bandwidth"]["resnet"]
                #ceil_bd=total_bd*model_details[model_name]["user_num_per_ins"]
                #Static_Info.RESNET_USER_BANDWIDTH#Static_Info.RESNET_USER_BANDWIDTH*model_details[model_name]["user_num_per_ins"]
            for ports_list in ports_details[model_name]:
                for dport in ports_list:
                    # 1. create a class under the root
                    create_class = "tc class add dev em4 parent 1: classid 1:"+str(class_id)+" htb rate "+str(total_bd)+"mbit "#ceil "+str(total_bd)+"mbit"
                    create_branch = "tc qdisc add dev em4 parent 1:"+str(class_id)+" handle "+str(class_id)+": sfq perturb 10"
                    create_filter = "tc filter add dev em4 protocol ip parent 1: prio 1 u32 match ip dport "+str(dport)+" 0xffff flowid 1:"+str(class_id)
                    print(create_class)
                    print("$$$$$$$$$",create_filter)
                    class_id = class_id+1
                    self.__excecute__(create_class)
                    self.__excecute__(create_branch)
                    self.__excecute__(create_filter)
        print("==========finsih========")


    def __excecute__(self,command):
        sudoPassword = "wujing123"
        p = os.system('echo %s|sudo -S %s' % (sudoPassword, command))

class SocketCommunication:
   def recvall(self, conn, n):
      # Helper function to recv n bytes or return None if EOF is hit
      data = b''
      while len(data) < n:
         packet = conn.recv(n - len(data))
         if not packet:
            return None
         data += packet
      return data
   def send_data_bytes(self,conn,content):
       msg = struct.pack('>I', len(content)) + content
       size = conn.send(msg)
       #print("=============send size",size)
       return sys.getsizeof(msg)
   def send_data(self,conn, content):
      # Prefix each message with a 4-byte length (network byte order)
      # Send data to the server
      content = bytes(content, encoding="utf-8")
      msg = struct.pack('>I', len(content)) + content
      conn.send(msg)
      return sys.getsizeof(msg)

   def recv_data(self,conn):
      # Receive data from the server
      # Return result(an numpy array)
      resp_len = self.recvall(conn, 4)
      if not resp_len:
         return None
      resp_len = struct.unpack('>I', resp_len)[0]
      if not resp_len:
         return None
      result = self.recvall(conn, resp_len)
      result = result.decode("utf8")
      return eval(result)

class Static_Info:
   # ====== edge and mobile controller ip
   EDGE_IP = "192.168.1.25"
   LISTENER_IP = '192.168.1.14'
   LISTENER_PORT= 10980

   # ======= user ip and port
   SERVER_USER_IP = '192.168.1.14'
   RASP_USER_IP_START = 20
   RECV_PORT_INTERVEL = 50
   SERVER_RECV_PORT_START = 2000

   # ===== the number of intras processed by users
   # from  inception,mobilenet and resnet
   INCEPTION_USER_INTRA = 1
   RESNET_USER_INTRA = 1
   MOBILENET_USER_INTRA = 4

   # ======= frame rate of each model
   INCEPTION_FRAME_RATE = 4
   RESNET_FRAME_RATE = 5

   #======the maximum number of CPU cores for SERVER_USER
   # =====the maximum number of RASP_USER
   SERVER_CORE_UPPER = 16

   #======== user bandwidth for models
   INCEPTION_USER_BANDWIDTH = 109.9    #Mbits/s
   RESNET_USER_BANDWIDTH = 109.9
   MOBILENET_USER_BANDWIDTH = 109.9

   SEND_FAILS_TIMES = 5
   ACCEPT_WAIT_TIME = 2

   RECORDS_PERIODS = 5

def process_request_records(file_path):

    for model_name in ["inception","resnet"]:
        #file_name = "D:\current_system\client\\records/"+file_path+"/"+model_name
        file_name = "../records/" + file_path + "/" + model_name
        print(file_name)
        if not os.path.exists(file_name):
            print("the mobile side has not created the instances of ",model_name)
            continue
        else:
            # 1. list the number of instance of the model
            model_ins_list = os.listdir(file_name)
            for model_ins in list(model_ins_list):
                # 2. list the users under a specific instance
                if not os.path.isdir(file_name+"/"+model_ins):
                    continue
                user_path = file_name+"/"+model_ins
                writer = pd.ExcelWriter(file_name+"/"+model_name+"_"+model_ins+".xlsx")
                print("=========",file_name+"/"+model_name+"_"+model_ins+"_"+file_path+".xlsx")
                user_index = 0
                for user_ins in os.listdir(user_path):
                    user_ins_file = user_path+"/"+user_ins
                    #print("=============file=========",user_ins_file)
                    # 3. 把同一个ins下不同的user的数据以sheet的形式保存在以实例名为文件名的xlsx文件里
                    result = {}
                    with open(user_ins_file,"r") as f:
                        lines = f.readlines()
                        for line in lines:
                            if line[0] =="=":
                                continue
                            else:
                                pic_num = line[1:line.find(":")]
                                items = eval(line[line.find(":")+1:])
                                if items["end_time"]==0:
                                    items["e2e_time"] = 0
                                else:
                                    items["e2e_time"] = items["end_time"]-items["start_time"]
                                result[str(pic_num)] = items
                    #print(result.values())
                    result_pd = pd.DataFrame(data=result.values(),index=result.keys())
                    result_pd.to_excel(excel_writer=writer,sheet_name="User_"+str(user_index))
                    user_index  = user_index+1
                writer.save()
                writer.close()
'''
import sys
sys.path.append(".")
file_names = os.listdir("../records")
print(file_names)
for file_path in file_names:
    process_request_records(file_path)
'''











