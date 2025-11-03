from datetime import datetime, timezone
from parsed_data import debug_exc
import subprocess
import pycurl
from io import BytesIO
import json

known_leagues = {
    "NFL":9,
    "CFB":15,
    "MLB":2,
    "WNBA":3,
    "SOCCER":82,
    "CFB2H": 150,
    "NBA": 7,
}

log_prefix = "SCRAPER"

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
        return 1
    
    api_call = f"https://api.prizepicks.com/projections?league_id={league_num}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"
    
    #Catch any issues with get request and wrap error in debug_exc class for future debug
    try:
        webpage = cml_curl(api_call)

    except Exception as e:
        raise debug_exc(e, "1", {"apiep":api_call}, log_prefix)
    #Catch any issues with get json conversion and wrap error in debug_exc class for future debug
    try:
        wp_json = json.loads(webpage)
    except Exception as e:
        raise debug_exc(e, "2", {"wp":webpage, "apiep":api_call}, log_prefix)
    
    scrape_id = ppdb.create_scrape_id(0, league_num, datetime.now(timezone.utc).replace(tzinfo=None))
    return (wp_json, scrape_id, api_call)

def cml_curl(api_ep):
    #It runs the curl command represended in the cmd from the host OS. It makes the api endpoint request with a bunch of headers which prizepicks seems to
    #be ok with 

    cmd = f'''
    curl '{api_ep}'\
    -H 'sec-ch-ua: "Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'\
    -H 'sec-ch-ua-mobile: ?0'\
    -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'\
    -H 'Content-Type: application/json'\
    -H 'Accept: application/json'\
    -H 'Referer: https://app.prizepicks.com/'\
    -H 'X-Device-ID: 1a9d6304-65f3-4304-8523-ccf458d3c0c4'\
    -H 'sec-ch-ua-platform: "macOS"'\
    '''
    try:
        # Execute the command and capture stdout and stderr
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

    except subprocess.CalledProcessError as e:
        # Handle errors if the curl command returns a non-zero exit code
        print(f"Curl command failed with error code {e.returncode}")
        print(f"Stderr: {e.stderr}")
        raise debug_exc(e, e.returncode, {"apiep":api_ep, "cmd":cmd, "curl_err":e.stderr})

    return result.stdout

def pycurl_curl(api_ep):
    #Uses pycurl library to send request to prizepicks endpoint with the headers it seems to accept

    buffer = BytesIO()
    c_send = pycurl.Curl()
    c_send.setopt(pycurl.URL, api_ep)
    c_headers = [
        'sec-ch-ua: "Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile: ?0',
        'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Content-Type: application/json',
        'Accept: application/json',
        'Referer: https://app.prizepicks.com/',
        'X-Device-ID: 1a9d6304-65f3-4304-8523-ccf458d3c0c4',
        'sec-ch-ua-platform: "macOS"',
    ]
    c_send.setopt(pycurl.HTTPHEADER, c_headers)
    c_send.setopt(pycurl.WRITEDATA, buffer)
    c_send.perform()
    c_send.close()
    body = buffer.getvalue()
    return body.decode('iso-8859-1')
