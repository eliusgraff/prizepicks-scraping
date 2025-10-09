import traceback
import os
from datetime import datetime as dt
import inspect

#Data structure to hold all the data that was parsed from the PrizePicks API request
class parsed_data:
    '''
    Data structure to hold all the data that was parsed from the PrizePicks API request. The structure holds both the
    data and includes infromation. Data gets its own section since it is the most importatnt arnd largest section of
    the data we get from PrizePicks. The includes are not as important but do provide useful context to what exactly
    the data all means.

    data_order - a list containing the order in which the data values will appear in the paralell lists

    data_values - a list of lista where each list contains data for each entry in the 'data' section of the prizepicks response
    
    included_tag_values - a dict where each key is the name of an included type and values are dicts mapping attribute names to their values
    '''
    #In the future can data just be added into the includes section since it is really all the same format?
    data_order = list()
    data_values = list()
    included_tag_values = dict()

    def __init__(self, d_order = None, d_vals = None, it_vals = None):
        self.data_order = d_order
        self.data_values = d_vals
        self.included_tag_values = it_vals

class player_stats:
    '''
    Class to hold all the data that is parsed from the prizepick databse for a players perfromqance in a given game
    This is important to calaculate if they covered their spread or not.

    name - the name of the player

    id - the player_id assigned in the games request response - this is not the same as the player_id assigned in the
    projecttions request. I'm not sure that there is a clear way to map them, so will have to use context. I'm saving
    this just in case it becomes useful in the futures

    team - provides context for which player the stats are for

    position - this is going to be key context to making sure the correct player is attached to the correct stats. In
    the case where two players with the exact same name playe the same position, on the same team, then this will not be helpful

    dnp - did not play. This is a bool that tells us if the player played or not. PrizePicks uses this to determin if a bet needs
    to be refunded or not.
    '''
    name = None
    id = None
    team = None
    position = None
    dnp = None
    stats = None

    def __init__(self, player_name, player_id, player_team, player_postion, player_dnp, player_stats):
        self.name = player_name
        self.id = player_id
        self.team = player_team
        self.position = player_postion
        self.dnp = player_dnp
        self.stats = player_stats

log_path = os.path.join(os.path.dirname(__file__),"logs")

#wrapper class to capture exception info and data to debug
class debug_exc (Exception):

    exc = None          #exception object of the exception the data is collected from
    caller = None       #will auto-populate the name of the caller function so it is easy to know where the exception was created
    error_code = None   #error code from the module where the exception occured
    trace_back = None   #traceback.format_exc() from the except block, this gets the traceback info as a string
    data_dict = None    #whatever data was passed into the fucntion which caused the exception as well as anything else that may be needed for debug
    prefix = None       #Identifier to give more info in the file name about where the exception occured
    file_path = None

    #Constructor to take in the initial exception and store it along with additional debug info to be dumpped to a file 
    def __init__(self, e, ec, dd, p):
        self.exc = e
        self.caller = inspect.currentframe().f_back.f_code.co_name
        self.error_code = ec
        self.trace_back = e.__traceback__#traceback.format_stack()
        self.data_dict = dd
        self.prefix = p
        global log_path
        self.file_path = os.path.join(log_path,f"SNAP_{self.prefix}_{dt.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")

    '''
    I want to limit the number of snaps that are saved, so in here, should run a function which checks to see if I need to delete a snap before I 
    create a new one
    '''
    #Function to dump exception + debug info to a file. Caller can pass in fn to override the default. Function returns full path to file.
    def dump(self, fn = None):
        
        fn = self.file_path if fn is None else fn
        with open(fn,"w", encoding='utf-8') as f:
            f.write(f"{self.exc.__class__.__name__}\n\n")
            f.write(f"{self.caller} ERRORCODE: {self.error_code}\n\n")
            f.write("".join(traceback.format_exception(type(self.exc), self.exc, self.exc.__traceback__)))
            f.write("\n")
            for k,v in self.data_dict.items():
                f.write(f"{k} : {v}\n")

        return fn
