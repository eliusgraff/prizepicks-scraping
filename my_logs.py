import os
import logging
from time import perf_counter

def log_perf(func):

    def wrapper(*args, **kwargs):
        perf_log = logging.getLogger("perf")
        s=perf_counter()
        ret_obj = func(*args, **kwargs)
        t=perf_counter()-s
        perf_log.debug(f"{func.__name__}:{str(t)}")
        #print(f"logged: {func.__name__}:{str(t)}")
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
    
    '''---Set up logger object name and level---'''
    _Performance_Log = logging.getLogger("perf")
    _Performance_Log.setLevel("DEBUG")

    '''---Defining and setting formatter and file handler---'''
    file_handler = logging.FileHandler(f"{log_path}\\Performance.log")
    _Performance_Log.addHandler(file_handler)
    _Performance_Log.critical(f"-------NEW RUN STARTING-------")
    return
