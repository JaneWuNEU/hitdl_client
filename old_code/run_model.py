import time
#import tensorflow as tf
import numpy as np
import cv2
def run_model(model_name, data, r, model_ins,model_delay_ratio):
    period = 0
    if model_name == "alexnet":
        local_time = {"0":5.194,"2":11.672,"5":16.087,"6":27.121}
        period = local_time[str(r)]
    elif model_name == "vgg16":
        #2.6,91.88146667,140.7911333,236.2307333,365.0177333,432.5874667
        local_time = {"0":2.6,"3":91.881,"6":140.791,"10":236.230,"14":365.017,"19":432.587}
        period = local_time[str(r)]
    elif model_name == "autoencoder":
        local_time = {"0":2.6,"3":29.5874}
        period = local_time[str(r)]
    else:
        local_time = {"0":2.6}
        period = local_time[str(r)]
    time.sleep(period*model_delay_ratio/1000)
    # run each model
    """
    if model_name == 'alexnet':
        data = cv2.resize(data.astype(np.float32), (227, 227))
        output_data = model_ins.run_model(r, [data])
        #print("np.size(output_data)",np.size(output_data))
    elif model_name == 'autoencoder':
        data = cv2.resize(data.astype(np.float32), (256, 256))
        output_data = model_ins.run_model(r, [data])

    elif model_name == 'srgan':
        output_data = model_ins.run_model(r, [data])

    else:
        data = cv2.resize(data.astype(np.float32), (224, 224))
        output_data = model_ins.run_model(r, [data])
    #print(" output_data.dtype ",output_data.dtype)
    """
    #return output_data
    return np.load("./layer_data/"+model_name+'_r_'+str(r)+'_b_1.npy')
