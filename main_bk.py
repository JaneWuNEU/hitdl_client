from threading import Thread,Event
import sys
sys.path.append("./")
import socket
import time
from multiprocessing import Process,Value
from utils.util import Static_Info,SocketCommunication,ControlBandwidth
import os
import pandas as pd
from datetime import datetime
from user import User
import numpy as np
from multiprocessing import Process,Manager
comm_sock = SocketCommunication()
import signal
import datetime
def logout_users(user_list,recv_port_list):
    i = 0
    for model_name in ["resnet","inception"]:

        model_user_list = user_list[model_name]
        if len(user_list)!=0:
            for user in model_user_list:
                # 0. logout users by set the $activate_flag_list as -1
                # 1. release the recv_port
                #try:
                #os.system('fuser -k -n tcp  '+str(recv_port))
                os.kill(user.run_model_pid,signal.SIGKILL)
                #print("#################logout users##################",user.user_id,user.model_name)
                #except Exception as e:
                #print("error happens when logouts users",e)
                i = i+1
    #return user_list
def listen_notice(edge_notice_event,create_user_finish_event,edge_notice):
    '''
    listen to the notice from the edge.
    When the notice comes, change the state of the shared edge_notice, which triggers
    the following adjustment. What's more, there are two kind of notices
    1. create users ==>  remove the out-date $model_details of the $edge_notice and rewrite the newest info
    2. activate users==> refresh the $port_details of the $edge_notice
    '''
    listner_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listner_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    listner_sock.bind((Static_Info.LISTENER_IP,Static_Info.LISTENER_PORT))
    listner_sock.listen(5)
    file_path = "notice"
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    file_name = "notice_"+datetime.datetime.now().strftime("%H:%M:%S")+".txt"
    # print("--------------welcome to hitdl-------------")
    while True:
        try:
            conn,add = listner_sock.accept()
            data = comm_sock.recv_data(conn)
            conn.close()
            print("----------------------listen notice gets data--------------------",data)
            if data['type'] == 'create':
                # 1. refresh the $model_details
                edge_notice['model_details'] = data['model_details']
                edge_notice['port_details'] = None
                edge_notice['type']='create'
                edge_notice['bandwidth'] = data["bandwidth"]
                edge_notice_event.set()
                with open(file_path + "/" + file_name, "a") as f:
                    f.write("#create#"+str(edge_notice)+"\\n")

            elif data['type'] == 'activate':
                # 2. refresh the $port_details
                while not create_user_finish_event.is_set():
                    time.sleep(0.5)
                edge_notice['port_details'] = data['port_details']
                edge_notice['type'] = 'activate'
                edge_notice['bandwidth'] = data["bandwidth"]
                # print("-------bbbbbbbbbbb-----", edge_notice)
                edge_notice_event.set()
                with open(file_path + "/" + file_name, "a") as f:
                    f.write("*activate*"+str(edge_notice)+"\\n")


        except Exception as e:
            print("error happens when receving the edge's notice",e)



def create_users(user_list,model_details):
    '''
    controller maintains a user list and a core list
    Depend on the $model_details to create users.
    1. read the $ins_num and $user_num_per_ins to create users
    2. Intialize an user with necessary info according to $model_details
     Note that error happens when there is no sufficient cpu cores.
    3. start a new process for each user, and then it to specific number of CPU cores (marked as intra) defined in Static_info
    Note that user has different types and various intra. Meanwhile, CPU cores must be allocated carefully without no intersect
    between different users.

    '''
    def create_inception_user(now_time):
        '''
        return no_available_core:
        False: there is available CPU cores to create resnet users.
        True: there is no available CPU cores.
        '''
        inception_details = model_details["inception"]
        available_core_id = 0
        available_user_id = 0

        # 1. get the intra for mobile users.
        inception_user_intra = Static_Info.INCEPTION_USER_INTRA
        no_available_core = False
        ins_num = 0
        user_num = 0
        for elem in inception_details:
            user_num = user_num + elem["ins_num"]*elem["user_num_per_ins"]
            ins_num = ins_num + elem["ins_num"]
        for ins_id in range(ins_num):
            for user_index in range(user_num):
                core_id = []
                # 1.1 find out the available core id for the users.
                '''
                Pay attention that the cores assigned to a model must lie on the same physical process.
                1. 禁止虚拟核
                2. 做逻辑控制，避免跨物理CPU===> if each user just occupies on CPU cores, we do not need to consider the situation 
                that the cores a user occupies lying on two different physical processor.
                NUMA node0 CPU(s):     0,2,4,6,8,10,12,14
                NUMA node1 CPU(s):     1,3,5,7,9,11,13,15
                '''
                for i in range(inception_user_intra):
                    if available_core_id >= Static_Info.SERVER_CORE_UPPER:
                        no_available_core = True
                        print("there is no sufficient cores for inception after it creates ", len(user_list), " users")
                        return no_available_core,None

                    core_id.append(available_core_id)
                    available_core_id = available_core_id + 1
                # 1.2 create the user object
                user = User(inception_details["k"], "inception", available_user_id, ins_id, None,
                            Static_Info.SERVER_USER_IP, core_id,now_time)
                available_user_id = available_user_id + 1
                user_list["inception"].append(user)
        return no_available_core,available_core_id,available_user_id

    def create_resnet_users(available_core_id,available_user_id,now_time):
        inception_user_number = len(user_list["resnet"])
        resnet_details = model_details["resnet"]
        resnet_user_intra = Static_Info.RESNET_USER_INTRA
        ins_num = 0
        user_num = 0
        for elem in resnet_details:
            user_num = user_num + elem["ins_num"]*elem["user_num_per_ins"]
            ins_num = ins_num + elem["ins_num"]
        for ins_id in range(ins_num):
            for user_index in range(user_num):
                core_id = []
                # 1.1 find out the available core id for the users.
                for i in range(resnet_user_intra):
                    if available_core_id >= Static_Info.SERVER_CORE_UPPER:
                        no_available_core = True
                        print("there is no sufficient cores for resnet after it creates ",len(user_list) - inception_user_number, " users")
                        return
                    core_id.append(available_core_id)
                    available_core_id = available_core_id + 1
                user = User(resnet_details["k"], "resnet", available_user_id, ins_id, None,
                            Static_Info.SERVER_USER_IP, core_id,now_time)
                available_user_id = available_user_id + 1
                user_list["resnet"].append(user)
        return available_core_id,available_user_id
    now_time = datetime.datetime.now().strftime("%d-%H-%M-%S")
    # 1. create users for models
    # 1.1 for inception
    result = create_inception_user(now_time)
    if result[0] == False:
        # 1.2 for resnet
        # this means there is still available CPU cores to create users of resnet
        available_core_id, available_user_id=create_resnet_users(result[1],result[2],now_time)
    print("#################",user_list)

    # 2.start process for each user and bind the specific ports.
    activate_flag_dict = {"resnet":[],"inception":[]}
    recv_port_list = []
    request_records_list = []
    for model_name in ["resnet","inception"]:
        model_user_list = user_list[model_name]
        for user in model_user_list:
            request_records = {}#manager.dict()
            activate_flag = Value("i",0)
            #recv_port = Value("i",0)
            model_name = user.model_name
            core_id = user.core_id

            user_process = Process(target=user.run_model,args=[activate_flag,None,request_records])
            user_process.start()
            user.run_model_pid = user_process.pid
            activate_flag_dict[model_name].append(activate_flag)
            request_records_list.append(request_records)
    return user_list,activate_flag_dict,recv_port_list,request_records_list

def activate_users(user_list,port_details,activate_flag_dict):
    '''
    The main process shares a variable $activate_flag as type of  multiprocessing.Value
    with each user's process.
    When the $activate_flag is zero, it means the user just created without being activated.
    When the $activate_flag >0, it means the user is activated and is able to send data to the edge.
    The receving port of the edge is represent as the value of $activate_flag.
    When $activate_flag is -1, it means to logout the users
    '''
    for model_name in ["inception","resnet"]:
        user_index = 0
        if len(port_details[model_name])==0:
            continue
        user_per_ins = len(port_details[model_name][0])
        if user_per_ins ==0:
            continue
        print("============user list==========",user_list)
        user_index = 0
        for user in user_list[model_name]:
            model_name = user.model_name
            ins_id = int(user_index/user_per_ins)
            activate_flag_list = activate_flag_dict[model_name]
            user_ins_id = int(user_index%user_per_ins) # user在ins内的相对位置
            activate_flag_list[user_index].value = port_details[model_name][ins_id][user_ins_id]
            print(user_index,ins_id,user_ins_id,activate_flag_list[user_index].value)
            user_index = user_index + 1


if __name__ == '__main__':
    # 0. start a thread to listen to the notice from the edge
    edge_notice_ev = Event()
    create_user_finish_event = Event()
    edge_notice = {'model_details':None,
                   'port_details':None,
                   'type':None}
    notice_thread = Thread(target=listen_notice,args=[edge_notice_ev,create_user_finish_event,edge_notice])
    notice_thread.start()

    # maintain a user list and a instance list.
    user_list = {"resnet":[],"inception":[]}
    activate_flag_dict = None
    recv_port_list = []
    request_records_list = None
    bandwidth_controller = ControlBandwidth()
    start = time.time()
    i = 0
    manager = Manager()
    while True:
        if edge_notice_ev.is_set():

            if edge_notice['type'] == 'create':
                # 1. logout users
                logout_users(user_list,recv_port_list)
                # 2. create users
                del user_list
                user_list,activate_flag_dict,recv_port_list,request_records_list = create_users({"resnet":[],"inception":[]},edge_notice['model_details'])
                '''
                for model_name in ["resnet","inception"]:
                    for user in user_list[model_name]:
                        print(user.user_id)
                '''
                create_user_finish_event.set()
                edge_notice_ev.clear()

            elif edge_notice['type'] == 'activate':
                # 3. activate users
                bandwidth_controller.change_bandwidth(edge_notice)
                activate_users(user_list,edge_notice['port_details'],activate_flag_dict)

                create_user_finish_event.clear()
                edge_notice_ev.clear()
                i = i + 1
