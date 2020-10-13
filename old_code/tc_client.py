
import sys
import os
import time
class Set_client_bandwidth():

    def __init__(self):
        self.sudoPassword = 'wujing123'
        pass

    def init_tc(self ,ports, start_bw = 3,dev_name = 'em4'):

        init_tc1 = "tc qdisc add dev em4 root handle 1: htb default 20"
        init_tc2 = "tc class add dev em4 parent 1: classid 1:20 htb rate 1000mbit prio 3"

        init_user_class_com= 'tc class add dev em4 parent 1:1 classid 1:20 htb rate 88mbit ceil 88 mbit'#.format(start_bw+0.1,start_bw)
        init_user_filter_com = "tc filter add dev em4 protocol ip parent 1:1 prio 3 u32 match ip dport 10990 0xffff flowid 1:20"
        ##"tc filter add dev em4 parent 1:2 protocol ip prio 3 handle 121 fw flowid 1:21"

        for port in ports:
            ports_str = str(port)+","
        ports_str = ports_str[:ports_str.rindex(",")]

        print("ports list",ports_str)
        #init_iptables1 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --dports "+ports_str+" -j MARK --set-mark 120"
        #init_iptables2 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --dports "+ports_str+" -j RETURN"
        #init_iptables1 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --dport 10990 -j MARK --set-mark 121"
        #init_iptables2 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --dport 10990 -j RETURN"
        self.exshell(init_tc1)
        self.exshell(init_tc2)
        self.exshell(init_user_class_com)
        self.exshell(init_user_filter_com)
        #self.exshell(init_iptables1)
        #self.exshell(init_iptables2)
        '''
        init_user_class_com= 'tc class add dev em4 parent 1:2 classid 1:22 htb rate {}kbps ceil {}kbps'.format(start_bw,start_bw)
        init_user_filter_com = "tc filter add dev em4 parent 1:2 protocol ip prio 3 handle 121 fw classid 1:22"
        init_iptables1 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --sport 10992 -j MARK --set-mark 122"
        init_iptables2 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --sport 10992 -j RETURN"
        self.exshell(init_iptables1)
        self.exshell(init_iptables2)
        print("=====================")
        '''

    def exshell(self,command):
        r = os.popen('echo %s|sudo -S %s' % (self.sudoPassword, command))
        text = r.read().strip()
        print(text)
        r.close()

    def reset_tc_iptables(self,dev_name = 'em4'):
        del_tc =    "tc qdisc del dev em4 root"
        del_iptables = "iptables-restore < iptablesRules"
        self.exshell(del_tc)
        self.exshell(del_iptables)

    def change_bandwidth(self,user_num , bandwidth,dev_name = 'em4'):

        set_user = 'tc class change dev em4 parent 1:2 classid 1:2{} htb rate {}mbit ceil {}mbit'.format(user_num,
                                                                                                           bandwidth,
                                                                                                           bandwidth)
        set_testw = "tc class change dev em4 parent 1:3 classid 1:3{} htb rate {}mbit ceil {}mbit".format(user_num,
                                                                                                            bandwidth,
                                                                                                            bandwidth)
        self.exshell(set_user)
        self.exshell(set_testw)
        print("bandwidth_control :  user_num : {}  up_load bandwidth: {} mbit/s".format(user_num, bandwidth))





