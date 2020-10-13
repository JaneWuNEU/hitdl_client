
import sys
import os
import time
class Set_client_bandwidth():

    def __init__(self):
        self.sudoPassword = '123456'

        pass

    def init_tc(self ,usernum, start_bw = 20):
        '''
        初始化 当前用户的  tc 管道 ， 默认带宽为 20 mbps  用户创建时调用.
        :param usernum:
        :return:

        父类1  classid 1:2  带宽总和 1000mb
        父类2  classid 1:3  带宽总和 1000mb
        用户管道类(父类1 的子类) classid 1:20***
        带宽管道类(父类2 的子类) classid 1:30***

        '''
        if usernum == 1 :                # 判断当前用户是否为第一个用户，若为username为1 ，则表示新一轮实验开始，需要重设tc 和 iptabals
            self.reset_tc_iptables()

        init_tc1 = "tc qdisc add dev eno1 root handle 1: htb default 20"                    # 初始化根队列
        init_tc2 = "tc class add dev eno1 parent 1:1 classid 1:2 htb rate 1000mbit prio 3"  # 初始化父类1
        init_tc3 = "tc class add dev eno1 parent 1:1 classid 1:3 htb rate 1000mbit prio 3"  # 初始化父类2

        user_port_down = 11000+usernum*100           # 单用户端口下界
        user_port_up   = 11000+usernum*100+999       # 单用户端口上界

        test_bw_port_down = 21000+usernum*100        # 测试带宽端口下界
        test_bw_port_up   = 21000+usernum*100 +999      # 测试带宽端口上界


        init_user_class_com= 'tc class add dev eno1 parent 1:2 classid 1:2{} htb rate {}mbit ceil {}mbit'.format(usernum,start_bw,start_bw)  # 用户类

        init_bw_class_com = "tc class add dev eno1 parent 1:3 classid 1:3{} htb rate {}mbit ceil {}mbit".format(usernum,start_bw,start_bw)   # 带宽类

        init_user_sfq_com = "tc qdisc add dev eno1 parent 1:2{} handle 22{}:0 sfq perturb 5".format(usernum,usernum)                       # 散列算法
        init_bw_sfq_com = "tc qdisc add dev eno1 parent 1:3{} handle 23{}:0 sfq perturb 5".format(usernum,usernum)                         # 散列算法

        init_user_filter_com = "tc filter add dev eno1 parent 1:0 protocol ip prio 3 handle 12{} fw classid 1:2{}".format(usernum,usernum)   # 用户类过滤器
        init_bw_filter_com = 'tc filter add dev eno1 parent 1:0 protocol ip prio 3 handle 13{} fw classid 1:3{}'.format(usernum,usernum)     # 带宽类过滤器


        init_iptables1 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --sport {}:{} -j MARK --set-mark 12{}".format(user_port_down,user_port_up,usernum)     #iptables 标定用户类数据
        init_iptables2 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --sport {}:{} -j RETURN".format(user_port_down,user_port_up)

        init_iptables3 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --sport {}:{} -j MARK --set-mark 13{}".format(test_bw_port_down,test_bw_port_up , usernum)  # IPtables 标定带宽类数据
        init_iptables4 = "iptables -t mangle -A OUTPUT -p tcp --match tcp --sport {}:{} -j RETURN".format(test_bw_port_down,test_bw_port_up ,)

        # print(init_tc1)
        # print(init_tc2)
        # print(init_tc3)
        # print(init_user_class_com)
        # print(init_bw_class_com)
        # print(init_user_sfq_com)
        # print(init_bw_sfq_com)
        # print(init_user_filter_com)
        # print(init_bw_filter_com)
        # print(init_iptables1)
        # print(init_iptables2)
        # print(init_iptables3)
        # print(init_iptables4)

        self.exshell(init_tc1)
        self.exshell(init_tc2)
        self.exshell(init_tc3)

        self.exshell(init_user_class_com)
        self.exshell(init_bw_class_com)
        self.exshell(init_user_sfq_com)
        self.exshell(init_bw_sfq_com)
        self.exshell(init_user_filter_com)
        self.exshell(init_bw_filter_com)
        self.exshell(init_iptables1)
        self.exshell(init_iptables2)
        self.exshell(init_iptables3)
        self.exshell(init_iptables4)

    def exshell(self,command):
        r = os.popen('echo %s|sudo -S %s' % (self.sudoPassword, command))
        text = r.read().strip()
        print(text)
        r.close()

    def reset_tc_iptables(self):
        '''
        若 TC 操作输出结果 “找不到设备”  说明已删除tc 规则

        若 iptables 操作输出结果找不到 “iptablesRules文件”  则说明当前路径不存在重载文件 "Reset_iptables",
        需按以下方法生成手动删除iptables规则 (Chain OUTPUT 下的规则 )，并生成原始的iptablesRules文件:
            “批量删除 iptables 规则 ：　
            你先用iptables-save > iptablesRules将所有的iptables规则导出到iptableRules文件 ，
            然后你用文件编辑器修改这个文件，将你不想要的所有规则都删掉，保存
            修改完之后运行 iptables-restore < iptablesRules”

        :return:
        '''
        del_tc =    "tc qdisc del dev eno1 root"  # 删除根队列 根队列删除后，所有tc class 都会删除
        del_iptables = "iptables-restore < iptablesRules"  # 重载 iptables 规则 ，

        # 先必须将原始的iptables规则 保存到文件   iptables-store > Reset_iptables
        # reset 调用  iptables-restore < Reset_iptables  ，用原始设置覆盖改变的规则

        self.exshell(del_tc)
        self.exshell(del_iptables)

    def change_bandwidth(self,user_num , bandwidth):
        '''
        改变用户带宽
        用户运行时每隔  10s / 5s 调用

        :param user_num:
        :param bandwidth:   想要设定的带宽值 单位:mbit/s
        :return:
        '''

        set_user = 'tc class change dev eno1 parent 1:2 classid 1:2{} htb rate {}mbit ceil {}mbit'.format(user_num,
                                                                                                           bandwidth,
                                                                                                           bandwidth)
        set_testw = "tc class change dev eno1 parent 1:3 classid 1:3{} htb rate {}mbit ceil {}mbit".format(user_num,
                                                                                                            bandwidth,
                                                                                                            bandwidth)
        self.exshell(set_user)
        self.exshell(set_testw)

        print("bandwidth_control :  user_num : {}  up_load bandwidth: {} mbit/s".format(user_num, bandwidth))


if __name__ == '__main__':
    bw_control = Set_client_bandwidth()
    bw_control.reset_tc_iptables()

    usertotle = 10
    user_start = 1
    for user in range(user_start,user_start+usertotle) :                   # 初始化每个用户的管道
        bw_control.init_tc(user)
    time.sleep(5)
    while(True):

        for user in range (user_start,user_start+usertotle+1):                # 更改每个用户的带宽  ，带宽数据来源： 文件 、 硬数据..
            bw_control.change_bandwidth(user_num=user, bandwidth=20)

        time.sleep(10)

        # 每隔十秒变动一次



