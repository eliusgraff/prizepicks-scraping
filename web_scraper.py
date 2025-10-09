from datetime import datetime, timezone
from curl_cffi import requests
from parsed_data import debug_exc

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
    league_num = known_leagues.get(league.upper())
    if league_num is None:
        return 1
    
    #Setting up API endpoint str and making that request
    page_num = 20
    single_stat = "true"
    game_mode = "pickem"
    api_call =  f"https://api.prizepicks.com/projections?league_id={league_num}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"

    #Catch any issues with get request and wrap error in debug_exc class for future debug
    try:
        webpage = requests.get(api_call, impersonate='chrome')
    except Exception as e:
        raise debug_exc(e, "1", {"apiep":api_call}, log_prefix)
    #Catch any issues with get json conversion and wrap error in debug_exc class for future debug
    try:
        wp_json = webpage.json()
    except Exception as e:
        raise debug_exc(e, "2", {"wp":webpage, "apiep":api_call}, log_prefix)
    
    scrape_id = ppdb.create_scrape_id(0, league_num, datetime.now(timezone.utc).replace(tzinfo=None))
    return (wp_json, scrape_id, api_call)
