from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, SessionNotCreatedException
from webdriver_manager.chrome import ChromeDriverManager
import helper
import time
#import httpx #- Not used in current implementation, could be added back in  future

def make_selenium_request (league, chromedriver_path = None, tmo_value = 5):
    '''
    Function to make a call to get lines/spreads from prizepicks. Function takes in a league name and makes a call to PrizePicks API to get all
    the current bets for that given league. Function requires chromedriver be installed

    Function has a few ways it can fail and report bad status:
        1 - invalid league
        2 - invalid chromedriver path
        3 - timeout loading webpage
    '''
    league = validate_league(league)
    if league is None:

        return 1

    '''using as defaults for api call'''
    page_num = 20
    single_stat = "true"
    game_mode = "pickem"
    api_call =  f"https://api.prizepicks.com/projections?league_id={league}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"
    #can I make this headless or go faster at least?
    ops = webdriver.ChromeOptions()
    ops.add_experimental_option('excludeSwitches', ['enable-logging']) #may add this back in future, but for now this is just annoying
    #ops.add_argument("--headless=new")
    cd_info = chromedriver_path if chromedriver_path is not None else helper.get_secret("chromedriver")
    if cd_info.get('path') is None:

        print("CRITICAL:Not chromedriver path found, exiting!")
        return 2
    
    try:

        session = webdriver.Chrome(options=ops)

    except SessionNotCreatedException:

        print("Got exception for SessionNotCreatedException. Attmepting reinstall and retry connection")
        session = webdriver.Chrome(ChromeDriverManager().install(), options=ops)

    session.get(api_call)
    try:

        tmo = WebDriverWait(session, tmo_value).until(EC.presence_of_element_located((By.XPATH, '/html/body/pre')))

    except TimeoutException:

        return 3
    
    source = session.page_source
    session.quit()
    return source

def validate_league(league):
    '''
    Function to return league number if known. If league is not known, then returns None.
    '''
    known_leagues = {
        "NFL":9,
        "CFB":15,
        "MLB":2,
        "WNBA":3,
        "Soccer":82,
        "CFB2H": 150
    }
    return known_leagues.get(league)

#Not used but may come back to try and make this work in the future
def make_httpx_request( league = None ):
    raise NotImplementedError
    '''
    league = string which is an acronym in league_dict which the caller can pick from to get all the prizepicks bets available
   
    Function which will make request to prizepicks API for bets for the passed in league described below:
    First, it validates that league passed into it is one of the known valid ones. If not, will return 1. If no values is passed in, this will default to NFL.
    Second, it makes the request to prizepicks api.
    Third, if request was unsuccessful for whatever reason, then basic troubleshooting will be done.
    Fourth, request will be returned to caller (even if request was ultimatley unsuccessful).
    '''

    '''using as placeholders for api call'''
    page_num = 20
    single_stat = "true"
    game_mode = "pickem"

    '''---Validate input---'''

    league = validate_league(league)
    if league is None:
        '''---League not recognized, try again---'''
        return (1)
    
    '''---Make request to prizepicks api---'''
    my_header = {
        "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding" : "gzip, deflate, br, zstd",
        "Accept-language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Priority" : "u=0, i",
        "Sec-Ch-Ua": "Chromium\";v=\"128\", \"Not;A=Brand\";v=\"24\", \"Google Chrome\";v=\"128\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "naviagte",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1" ,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Connection": "close"
       }
    
    prizepicks_url = "https://app.prizepicks.com/"
    api_call =  f"https://api.prizepicks.com/projections?league_id={league}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"
        
    print(f"--------Calling: {api_call}----------")
    my_request = httpx.get(prizepicks_url, headers=my_header)
    print(my_request.text)
    print("\n-----------------\n")
    print(my_request.request.headers)
    
    if my_request.status_code == 200:
        print("We did it!")
    else:
        print("Still bad")

    return my_request
