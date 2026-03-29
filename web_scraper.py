from datetime import datetime, timezone
from utils import debug_exc
import subprocess
import pycurl
from io import BytesIO
import certifi
import json
from requests import exceptions as http_exceptions
import time
import random
import os
import logging
from logging.handlers import RotatingFileHandler

###Code which runs when this module is imported###
log_prefix = "SCRAPER"
log_path = os.path.join(os.path.dirname(__file__),"logs")
if not os.path.isdir(log_path): 
    os.mkdir(log_path)
LOG = logging.getLogger(log_prefix)
LOG.setLevel("DEBUG")
my_handler = RotatingFileHandler(os.path.join(log_path,f"{log_prefix}.log"), maxBytes=5000000)
my_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
LOG.addHandler(my_handler)

#delete temp vars which are not used again
del log_path
del my_handler
###end import code###

known_leagues = {
    "NFL":9,
    "CFB":15,
    "MLB":2,
    "WNBA":3,
    "SOCCER":82,
    "CFB2H": 150,
    "NBA": 7,
    "NHL": 8,
    "TENNIS":5,
}

#headers I pulled from web browser after logging into prizepicks and navigating the site
lgin_hdrs = '''\
    -H 'Host: api.prizepicks.com'\
    -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'\
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'\
    -H 'Accept-Language: en-US,en;q=0.5'\
    -H 'Accept-Encoding: gzip, deflate, br, zstd'\
    -H 'Connection: keep-alive'\
    -H 'Upgrade-Insecure-Requests: 1'\
    -H 'Sec-Fetch-Dest: document'\
    -H 'Sec-Fetch-Mode: navigate'\
    -H 'Sec-Fetch-Site: none'\
    -H 'Sec-Fetch-User: ?1'\
    -H 'Alt-Used: api.prizepicks.com'\
    -H 'Priority: u=6'\
    -H 'Cache-Control: max-age=0'\
    -H 'TE: trailers'\
    -H 'Referer: https://app.prizepicks.com/'\
'''

#headers I pulled from web browser when going just straight for the api endpoint
direct_hdrs = '''\
    -H 'Host: api.prizepicks.com'\
    -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'\
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'\
    -H 'Accept-Language: en-US,en;q=0.5'\
    -H 'Accept-Encoding: gzip, deflate, br, zstd'\
    -H 'Sec-GPC: 1'\
    -H 'Connection: keep-alive'\
    -H 'Upgrade-Insecure-Requests: 1'\
    -H 'Sec-Fetch-Dest: document'\
    -H 'Sec-Fetch-Mode: navigate'\
    -H 'Sec-Fetch-Site: none'\
    -H 'Sec-Fetch-User: ?1'\
    -H 'Priority: u=0, i'\
    -H 'TE: trailers'\
    -H 'Referer: https://app.prizepicks.com/'\
'''

#these are the headers that have been working from Oct'25-Feb'26 - found on internet somewhere
base_hdrs = '''\
    -H 'sec-ch-ua: "Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'\
    -H 'sec-ch-ua-mobile: ?0'\
    -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'\
    -H 'Content-Type: application/json'\
    -H 'Accept: application/json'\
    -H 'Referer: https://app.prizepicks.com/'\
    -H 'X-Device-ID: 1a9d6304-65f3-4304-8523-ccf458d3c0c4'\
    -H 'sec-ch-ua-platform: "macOS"'\
'''

#variables for testing
error_rate = 0   #Specify rate at which get_prizepicks will raise errors 0 = turned off, 1 means every call will raise an error
error_depth = None  #Specify how deep to force error recovery. None turns this off and  -1 means it will go through full recovery
error_out = False #Even if injected error recovery is sucessful, if this is true then an error is raised anyway
is_error = False #Flag to indicate whether error is injected or not
num_fails = 0 #number of times failure injections will occur

if error_rate > 0 or error_depth is not None:
    LOG.debug(f"Testing mode enabled err_r8 = {error_rate} err_depth = {error_depth} num_fails = {num_fails}")
    input(f"Testing mode is on with error_rate: {error_rate} and error_depth: {error_depth} num_fails: {num_fails}. Press enter to continue...")
    

def get_prizepicks(league, ppdb):
    #Function which takes in a league acronym as a str. Function makes sure the league is a known one.
    #If not, returns 1.
    #Once league is validated it makes a call to the prizepicks api to get the latest data for that league.
    #Any problems here, it will return 1111 and all the exception info.
    
    page_num=250
    single_stat="true"
    game_mode="pickem"
    league_num = known_leagues.get(league.upper())

    if league_num is None:
        raise debug_exc(Exception("Invalid League"), "1", {"league":league}, log_prefix)
    
    api_call = f"https://api.prizepicks.com/projections?league_id={league_num}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"
    
    #If fake error is injected, then raise the exception to caller to test error handling and recovery
    if error_rate > 0:
        global is_error
        global num_fails
        if random.random() < error_rate and num_fails > 0:
            LOG.debug(f"~Injecting Fake Error~ Num err rem = {num_fails}")
            is_error = True
            if error_depth == 0:
                print(f"Num fails remaining: {num_fails}")
                print("~~~~~Injecting error for testing purposes~~~~~")
                num_fails -= 1
                LOG.debug(f"RAISING TEST ERROR 1")
                raise debug_exc(Exception("TEST"), "TEST1", {"apiep":api_call, "er_r8":error_rate, "depth":error_depth}, log_prefix)

    #Catch any issues with get request and wrap error in debug_exc class for future debug
    try:
        webpage = cml_curl(api_call)

    except Exception as e:
        LOG.critical(f"1: apiep={api_call} e={e}")
        raise debug_exc(e, "1", {"apiep":api_call}, log_prefix)

    #Catch any issues with get json conversion and wrap error in debug_exc class for future debug
    try:
        wp_json = json.loads(webpage)
    except Exception as e:
        LOG.critical(f"2: apiep={api_call} e={e}")
        raise debug_exc(e, "2", {"wp":webpage, "apiep":api_call}, log_prefix)

    scrape_id = ppdb.create_scrape_id(0, league_num, datetime.now(timezone.utc).replace(tzinfo=None))
    LOG.info(f"0: apiep={api_call} scrid={scrape_id}")
    return (wp_json, scrape_id, api_call)

#Function to create curl request from endpoint. Using a function so that if this needs to change in the future I only have to change it in one place
def _create_curl_request(ep):
    return f"curl --compressed -w '%{{http_code}}' '{ep}'"

#function executes curl command and returns webpage data and error code separately (in that order)
def exec_curl(cmd):

    try:
        # Execute the command and capture stdout and stderr
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

    except subprocess.CalledProcessError as e:
        # Handle errors if the curl command returns a non-zero exit code
        print(f"Curl command failed with error code {e.returncode}")
        print(f"Stderr: {e.stderr}")
        LOG.critical(f"1: curlcmd={cmd} retcode={e.returncode} stderr={e.stderr}")
        raise debug_exc(e, e.returncode, {"cmd":cmd, "curl_err":e.stderr}, log_prefix)
    
    return (result.stdout[:-3], result.stdout[-3:])

#Execute curl command to get the prizepicks api data
def cml_curl(api_ep):
    #create curl command based on the api endpoint which needs to be targeted and use base headers option and execute it
    base_curl_cmd = _create_curl_request(api_ep) + base_hdrs
    wp, HTTP_status_code = exec_curl(base_curl_cmd)
    
    #Code block to handle injected errors
    if is_error:
        if _injected_error_checking(1, HTTP_status_code, api_ep) == True:
            return wp

    #If anything other than good status comes back, then send this to error handling
    if HTTP_status_code != "200" or is_error:
        LOG.warning(f"1: apiep={api_ep} sts={HTTP_status_code}")
        wp = handle_error(api_ep, HTTP_status_code)

    return wp

#Attempting to recover from HTTP Error code 403 
def access_denial (api_ep):
    #Since 403 is usually when the traffic is picked up by anti-bot software and blocked, this will attempt to wait varying ammounts of time and try different
    #headers and ways to make the curl request to see if we can't get around the old anti-bot stuff before raising a 'hard' error
    LOG.info(f"0: ***Entering EC 403 Recovery***")
    
    for i, hdrs in enumerate([lgin_hdrs,direct_hdrs]):
        curl_req = _create_curl_request(api_ep) + hdrs
        time.sleep(5)
        wp, ec = exec_curl(curl_req)

        if is_error:
            if _injected_error_checking(2+i, ec, api_ep) == True:
                return wp

        elif ec == '200':
            print(f"Sucessfully recovered by step {i}")
            LOG.info(f"0: curl_step={i} apiep={api_ep}")
            return wp
        else:
            LOG.warning(f"01: curl_step_fail={i} ec={ec}")
            print(f"Command failed with error code: {ec}. Trying next iteration.")
        
    return pycurl_curl(api_ep)
        
#When a curl command with base headers generates bad HTTP status send the curl_str and status code to this function and it will call recovery function if it exists
def handle_error(api_ep, HTTP_status_code):
    global is_error
    if HTTP_status_code == "403" or is_error:
        return access_denial(api_ep)
    else:
        raise debug_exc(http_exceptions.HTTPError, {"apiep":api_ep,"errcode":HTTP_status_code}, log_prefix)

def pycurl_curl(api_ep):
    #Uses pycurl library to send request to prizepicks endpoint with the headers it seems to accept

    LOG.info(f"00: ***Entering Pycurl 403 Recovery***")
    #print("Waiting 3 sec before starting this to avoid spam")
    time.sleep(3)

    for i,hdrs in enumerate ([base_hdrs,direct_hdrs,lgin_hdrs]):

        #Turn header string into a list to send to pycurl
        c_headers = hdrs.replace("'","").split("    -H ")[1:]

        sleep = 5
        time.sleep(sleep)
        
        #Setup and execute pycurl command
        buffer = BytesIO()
        c_send = pycurl.Curl()
        c_send.setopt(pycurl.URL, api_ep)
        c_send.setopt(pycurl.HTTPHEADER, c_headers)
        c_send.setopt(pycurl.WRITEDATA, buffer)
        c_send.perform()
        resp_code = c_send.getinfo(c_send.RESPONSE_CODE)
        c_send.close()
        
        wp = buffer.getvalue().decode('iso-8859-1')
        
        global is_error

        if is_error:
            if _injected_error_checking(4+i, resp_code, api_ep) == True:
                return wp

        elif resp_code == 200:
            print(f"Recovery succeeded with pycurl on step {i}")
            LOG.info(f"0: pycurl_step={i} apiep={api_ep}")
            return wp
        else:
            print(f"Attempt failed with resp_code {resp_code}. Trying next thing")
            LOG.info(f"01: pycurl_step_fail={i} ec={resp_code}")

    if is_error:
        is_error = False

        raise debug_exc(Exception("TEST"), "TEST2", {"apiep":api_ep, "er_r8":error_rate, "step":"MAX"}, log_prefix)
    
    raise debug_exc(http_exceptions.HTTPError, {"apiep":api_ep,"lastec":resp_code}, log_prefix)

def _injected_error_checking(step, sts, api_ep):
    print(f"HTTP status code at step {step}:{sts}")
    global error_out
    global error_depth
    #If we are forcing deeper error recovery than current step, keep going
    if error_depth == -1 or error_depth > step:
        return False

    #Turn off injected error flag if we are at target step
    global is_error
    is_error = False

    #If are erroring our or this recovery step is not good status then raise error
    if error_out or sts != "200":
        raise debug_exc(Exception("TEST"), "TEST3", {"apiep":api_ep, "er_r8":error_rate, "step":step,"httpsts":sts}, log_prefix)
    
    #If not error_out then return true so caller returns the webpage like normal 
    return True
