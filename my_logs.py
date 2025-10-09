import os
import logging
from logging.handlers import RotatingFileHandler
from time import perf_counter

###Code which runs when this module is imported###
log_path = os.path.join(os.path.dirname(__file__),"logs")
if not os.path.isdir(log_path): 
    os.mkdir(log_path)
#Set up logger for perfromance
PERF_LOG = logging.getLogger("perf")
PERF_LOG.setLevel("DEBUG")
PERF_LOG.addHandler(RotatingFileHandler(os.path.join(log_path,"Performance.log"), maxBytes=5000000, backupCount=3))
###end import code###

def log_perf(func):

    def wrapper(*args, **kwargs):
        s=perf_counter()
        ret_obj = func(*args, **kwargs)
        t=perf_counter()-s
        global PERF_LOG
        PERF_LOG.debug(f"{func.__name__}:{str(t)}")
        return ret_obj

    return wrapper
