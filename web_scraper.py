import nodriver as uc
from datetime import datetime, timezone
from prizepicks_db import create_scrape_id

known_leagues = {
    "NFL":9,
    "CFB":15,
    "MLB":2,
    "WNBA":3,
    "Soccer":82,
    "CFB2H": 150,
    "NBA": 7,
}

async def scrape(api_request):
    '''
    Function takes in a prizepicks API call as a str and make a request to that endpoint using nodriver
    '''
    my_config = uc.Config(headless=False)
    browser = await uc.start(my_config)
    '''---Make request to prizepicks api---'''
    wp = await browser.get(api_request)
    '''---get the full-page HTML---'''
    html_content = await wp.get_content()
    '''---close the page---'''
    await wp.close()
    return html_content

def get_prizepicks(league):
    '''
    Function which takes in a league acronym as a str. Function makes sure the league is a known one.
    If not, returns 1.

    Once league is validated it makes a call to the prizepicks api to get the latest data for that league.
    Any problems here, it will return 2.
    '''

    league_num = known_leagues.get(league.upper())
    if league_num is None:
        return 1
    
    '''---Setting up API endpoint str and making that request---'''
    page_num = 20
    single_stat = "true"
    game_mode = "pickem"
    api_call =  f"https://api.prizepicks.com/projections?league_id={league_num}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"

    print(f"Scraping from endpoint: {api_call}")
    webpage = uc.loop().run_until_complete(scrape(api_call))
    scrape_id = create_scrape_id(1, league_num, datetime.now(timezone.utc).replace(tzinfo=None))
    return (webpage, scrape_id)


