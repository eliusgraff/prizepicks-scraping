import nodriver as uc

async def scrape(api_request):
    '''
    Function takes in a prizepicks API call as a str and make a request to that endpoint using nodriver
    '''
    '''---Set up nodriver config---'''
    my_config = uc.Config(headless=False)
    '''---start a new Chrome instance---'''
    driver = await uc.start(my_config)
    '''---Make request to prizepicks api---'''
    page = await driver.get(api_request)
    '''---get the full-page HTML---'''
    html_content = await page.get_content()
    '''---close the page---'''
    await page.close()
    return html_content

def new_get_prizepicks(league):
    '''
    Function which takes in a league acronym as a str. Function makes sure the league is a known one.
    If not, returns 1.

    Once league is validated it makes a call to the prizepicks api to get the latest data for that league.
    Any problems here, it will return 2.
    '''
    known_leagues = {
        "NFL":9,
        "CFB":15,
        "MLB":2,
        "WNBA":3,
        "Soccer":82,
        "CFB2H": 150
    }
    league_num = known_leagues.get(league.upper())
    if league_num is None:
        return 1
    
    '''---Setting up API endpoint str and making that request---'''
    page_num = 20
    single_stat = "true"
    game_mode = "pickem"
    api_call =  f"https://api.prizepicks.com/projections?league_id={league_num}&per_page={page_num}&single_stat={single_stat}&game_mode={game_mode}"
    webpage = uc.loop().run_until_complete(scrape(api_call))
    return webpage

def game_status(id):
    '''
    Function used to get the status of a game from prizepicks. Takes in a game id and makes request for that game's data
    from prizepeicks. This will return a JSON object for the data of the game.

    Currently does not accept a list of games, but it should in the future!
    '''
    game_api_call = f"https://api.prizepicks.com/games?external_game_ids={id}&limit=50"
    #league_ids_api = "https://api.prizepicks.com/leagues?state_code=CA&game_mode=pickem"
    return uc.loop().run_until_complete(scrape(game_api_call))
    