from old_code.main import start_client
from multiprocessing import Process

user_start = 2
user_count = 1
model_type = 1
mobile_type = 1
model_delay_ratio = 2 # 本地模型的运行时间相对于测量时间的倍数
'''
os.system('sudo tc qdisc del dev eno1 root')
os.system('sudo tc qdisc add dev eno1 root handle 1: htb default 20')
os.system('sudo tc class add dev eno1 parent 1:0 classid 1:1 htb rate 400Mbit')
os.system('sudo tc class add dev eno1 parent 1:1 classid 1:20 htb rate 400Mbit ceil 400Mbit')
os.system('sudo tc qdisc add dev eno1 parent 1:20 handle 20: sfq perturb 10')
'''
for i in range(user_start,user_start+user_count):
     print(i)
     p = Process(target=start_client,args=(i,model_type,mobile_type,model_delay_ratio))
     p.start()
#     time.sleep(np.random.rand(1)[0]/100)
#    os.chdir('~/Documents/Python_Projects/client_wj')
#    os.system('python main.py ' + str(i)+' '+ str(model_type) +' '+  str(mobile_type) +' '+  str(model_delay_ratio))