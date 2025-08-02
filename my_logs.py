import os
import logging
from time import perf_counter
from datetime import datetime

def log_perf(func):

    def wrapper(*args, **kwargs):
        perf_log = logging.getLogger("perf")
        s=perf_counter()
        ret_obj = func(*args, **kwargs)
        t=perf_counter()-s
        perf_log.debug(f"{func.__name__}:{str(t)}")
        return ret_obj

    return wrapper

def create_loggers():

    curdir_path = os.path.dirname(__file__)
    '''----------------PERFORMANCE LOGGING------------------'''
    '''
    Conctructor sets up the logger that is used by the class to makes sure no matter how many different 
    classes use the log, that they all go to the same place
    '''
    '''---Make sure correct directories exist---'''
    log_path = f"{str(curdir_path)}\\logs"
    if not os.path.isdir(log_path): 
        os.mkdir(log_path)
    cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    '''---Set up logger for perfromance---'''
    Performance_Log = logging.getLogger("perf")
    Performance_Log.setLevel("DEBUG")
    perf_file_handler = logging.FileHandler(f"{log_path}\\Performance.log")
    Performance_Log.addHandler(perf_file_handler)
    Performance_Log.critical(f"-------NEW RUN STARTING {cur_time}-------")
    
    '''---Set up logger for errors---'''
    Error_Log = logging.getLogger("err_log")
    Error_Log.setLevel("ERROR")
    error_file_handler = logging.FileHandler(f"{log_path}\\Error.log")
    Error_Log.addHandler(error_file_handler)
    Error_Log.critical(f"-------NEW RUN STARTING {cur_time}-------")

