import shutil
import os
import subprocess
from datetime import datetime as dt
import traceback
import inspect
from pathlib import Path

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
    def __init__(self, e, ec, dd, p=None):
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


def print_dict(my_dict):
    for k,v in my_dict.items():
        print(f"{k}\t{v}")

#Function used to get personal info from secret file. Caller passes in a string 'query' and this function
#goes line by line in the fn passed into the function looking for the query. The file is expected to be formatted like
#(description)_(variable name)=(value). Example for mysql database password would be something like: 'mysql_pw=my_password'.
def get_secret(query, fn = "secrets.txt"):
    
    #This function only parses lines if query matches the description. It puts the matched lines into a dictionary where the 
    #variable names are the keys and the values are the values.
    
        #requires that the user have a file called 'secrets.txt' where 3 of the lines in it are:
        #mysql_un=username
        #mysql_pw=password
        #mysql_hn=hostname
        #mysql_db_name=db_name
        #OPTIONALLY if you are in a secure environment you can include the password to your sudo command so that you are not 
        #prompted for it each time. This is obviously very dangerous so please only do this if you are being very careful
        #the password won't be printed to the command line directly but will be used in the python subprocess call to run
        #commands in the shell the keyword to do this is sudo
        #mysql_sudo=sudo_password

    dir_path = os.path.dirname(os.path.abspath(__file__))
    fn = os.path.join(dir_path, fn)
    my_dict = {}
    with open(fn, "r") as f:
        '''---Going line by line in file looking for query---'''
        for line in f:
            desc_delim = line.find("_")
            if desc_delim == -1:
                '''---If format is not as expected, then skip that line and print warning to console---'''
                print(f"WARNING: Should have '_' in this line:\n{line}\n")

            if line.find(query) > -1:
                '''---If query is found, parse the line---'''
                key_delim = line.find("=")
                if key_delim == -1:
                    '''---If format is not as expected, then skip that line and print warning to console---'''
                    print(f"WARNING: Should have '=' in this line:\n{line}\n")
                    continue

                key = line[desc_delim+1:key_delim]
                value = line[key_delim+1:].replace("\n","")
                my_dict[key] = value

    return my_dict

def dev_files_check():
    '''
    Rather than wrestle with gitignoring all the dev files, I'm just going to pull them in with this function
    whenever I cant find what I need. All the dev files are stored outside of the repo so that when they are deleted when I rebase,
    I can simply pull them back in and we are all good!
    '''
    raise NotImplementedError
    dest_dir = pathlib.Path(__file__).parent.resolve()
    src_dir = str(pathlib.Path(__file__).parent.resolve())
    src_dir.rfind('\\')
    src_dir = src_dir[:src_dir.rfind('\\')+1]
    src_dir += "dev_files"
    
    if not os.path.exists(src_dir):
        print(f"Source directory '{src_dir}' does not exist.")
        return

    '''---Create the destination directory if it doesn't exist---'''
    os.makedirs(dest_dir, exist_ok=True)

    '''---Iterate over files in the source directory---'''
    for filename in os.listdir(src_dir):
        src_file = os.path.join(src_dir, filename)

        '''---Check if it's a file (not a directory)---'''
        if os.path.isfile(src_file):
            dest_file = os.path.join(dest_dir, filename)
            shutil.copy2(src_file, dest_file)

#takes in a SN for a hard drive outside of the drive holding the Linux FS. If it is in the system it makes sure it is mounted and returns the mount point
def mount_hdd(sn):

    mount_point = "/mnt/Main_Drive"
    if os.name != "posix":
        print("This only works for Linux systems")
        return False
    
    #find device name for the drive with given SN in the system
    dev_details = subprocess.run(f"ls -l /dev/disk/by-id | grep {sn}", shell=True, capture_output=True, check=True, text=True).stdout
    
    #Since SN should just find one drive, if more than one are found, then don't know how to handle that so do nothing
    if len(dev_details.splitlines()) > 1:
        print("Too many results came up, need to be more specific with SN or which partition to target")
        return False
    
    #Cant find drive with that SN
    elif len(dev_details.splitlines()) == 0:
        print("Could not find drive with provided SN")
        return False
    
    dev_name = dev_details[dev_details.rfind('/')+1:].strip()

    #Checking if the drive is already mounted or not
    blk_info = subprocess.run(f"lsblk | grep {dev_name}", shell=True, capture_output=True, check=True, text=True).stdout
    dir_name = blk_info.find("/")
    if dir_name > -1:
        print(f"Already mounted at {blk_info[dir_name:]}")
        return blk_info[dir_name:]
    
    print(f"Not mounted yet, mounting {dev_name} to {mount_point}")
    
    subprocess.run(f"sudo mkdir -p {mount_point}", shell=True, capture_output=True, check=True, text=True)
    cmd = f"sudo mount /dev/{dev_name} {mount_point}"
    try:
        subprocess.run(cmd, shell=True, capture_output=True, check=True, text=True)

    except subprocess.CalledProcessError as e:
        print(f"MOUNT FAILED\n\nstdout:{e.stdout}\n\nstderr:{e.stderr}\n\ncmd:{cmd}\n\nerror:{e}")

        return False
    print(f"Mounting {dev_name} to {mount_point} SUCCEEDED")
    return mount_point

#Function to look in passed in dir for files with suffix (excluding any names that contain the excluded substr) and return their names
def fn_to_dep(dir, suffix, exclude):
    exclude = exclude.lower()
    fns = []
    for fn in os.listdir(dir):
        print(f"fn - {fn}")
        if fn.endswith(suffix) and fn.lower().find(exclude) == -1:
            fns.append(fn)
    
    if len(fns) == 0: print(f"No files to deprecate in {Path(".").resolve()}")
    return fns    

#Function just to dump mysql schema for storage as things change
def dump_mysql_schema( dep = False, dir = ".", suffix = "sql_schema.sql"):

    if dep is True:
        fns = fn_to_dep(dir,suffix,'deprecated')
    
    config = get_secret("mysql")
    schema_dump_cmd = f"echo '{config['sudo']}' | sudo -S mysqldump -u {config['un']} --password={config['pw']} --no-data {config['db_name']} > '{dt.now().strftime("%Y_%m_%d_%H_%M_%S")}sql_schema.sql'"
    subprocess.run(schema_dump_cmd, shell=True)

    if dep is True and len(fns) > 0:
        usr = input(f"Input 'y' if you would you like to deprecate these files: {fns}")
        if usr == 'y':
            for fn in fns:
                print(f"Deprecating: {fn}")
                subprocess.run(f"mv {fn} DEPRECATED_{fn}", shell = True)

        else: print("skipping dreprecation")
