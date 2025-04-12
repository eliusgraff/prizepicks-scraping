import nodriver as uc
from datetime import datetime, timezone
from prizepicks_db import create_scrape_id
import time

class web_scraper:


    _browser = None

    def __init__(self):
        uc.loop().run_until_complete(self.spinup_browser())

    async def spinup_browser(self):
        #Setup config and start nodriver browser
        my_config = uc.Config(headless=False)
        self._browser = await uc.start(my_config)
        return None

    def scrape(self, api_request):
        '''
        Function takes in a prizepicks API call as a str and make a request to that endpoint using nodriver
        '''
        '''---Make request to prizepicks api---'''
        wp = uc.loop().run_until_complete(self._browser.get(api_request))
        print("Got webpage!")
        '''---get the full-page HTML---'''
        html_content = uc.loop().run_until_complete(wp.get_content())
        '''---close the page---'''
        return html_content

    def new_get_prizepicks(self, league):
        '''
        Function which takes in a league acronym as a str. Function makes sure the league is a known one.
        If not, returns 1.

        Once league is validated it makes a call to the prizepicks api to get the latest data for that league.
        Any problems here, it will return 2.
        '''

        league_num = self.known_leagues.get(league.upper())
        if league_num is None:
            return 1
        
        '''---Setting up API endpoint str and making that request---'''
        page_num = 20
        single_stat = "true"
        game_mode = "pickem"
        api_call =  f"https://api.prizepicks.com/projections?league_id={league_num}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"

        print(f"Scraping from endpoint: {api_call}")
        webpage = self.scrape(api_call)
        print("Scraped data!")
        scrape_id = create_scrape_id(1, league_num, datetime.now(timezone.utc).replace(tzinfo=None))
        return (webpage, scrape_id)

    def game_status(self, id):
        raise NotImplementedError("This function is not yet implemented.")
        '''
        Function used to get the status of a game from prizepicks. Takes in a game id and makes request for that game's data
        from prizepeicks. This will return a JSON object for the data of the game.

        Currently does not accept a list of games, but it should in the future!
        '''
        temp = "https://api.prizepicks.com/games?external_game_ids=NFL_game_C7mkbeOdkX5xpB3iEfbRBFPh&limit=50"
        game_api_call = f"https://api.prizepicks.com/games?external_game_ids={id}&limit=50"
        
        #league_ids_api = "https://api.prizepicks.com/leagues?state_code=CA&game_mode=pickem"
        return uc.loop().run_until_complete(scrape(game_api_call))


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
    browser.close()
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


