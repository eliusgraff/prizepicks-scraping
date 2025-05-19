from bs4 import BeautifulSoup
import json
from parsed_data import parsed_data
from my_logs import log_perf

def valid_wp(wp):
    '''
    Function to validate that the webpage is valid and ok to begin parsing before doing so. The function looks for a few things:
    1. Check if the wp passed in can even be parsed as html by beautifulsoup
    2. Looks for 'pre' tag since that is wher the json data is stored
    3. Skips one tag (where the json data should be) and checks to see if the tag following the json data is  'json-formatter-container'.

    Arguement:
        wp - variable containing data from the the prizepicks API call

    Funtion returns beautifulsoup instance if the wp looks parsable and false if not.
    '''
    try:
        to_validate = BeautifulSoup(wp, "html.parser")

    except:
        return False

    pre = to_validate.find("pre")

    if pre is None or pre.name != "pre":
        print("Expected to be 'pre' tag")
        return False
    json_data = pre.next_element
    div = json_data.next_element
    if div['class'][0] != "json-formatter-container":
        print("Expected to be json-formatter class")
        return False
    
    return to_validate

def discard_html(webpage):
    '''
    Function to get rid of the HTML around the json data that we are interested in parsing.
    Will return false if webpage is not in expected format and fails check for valid_wp.

    Returns dict of the json data.
    '''
    soup = valid_wp(webpage)
    if soup is False:
        return False
    
    return json.loads(soup.find('pre').text)

@log_perf
def parse_webpage(webpage, pp_db):
    '''
    This function takes in an HTML webpage from prizepicks API request, strips the HTML from it and just goes through each of the tags in the json
    about the bets and stats. This function will also facilitate sending the parsed data to the local mySQL database.

    Prizepicks API json is formatted with each of the bets in one tag called 'data', then more of the payers and stats info in the 'included' tag
    which fill in additional necessary data about the bets like the player's info, what the stat is and other things.

    Parsing the data tags will return a list of values to coorespond to each of the values in the 'data_order' list. Before adding it all into the mySQL db.
    '''
    '''---Get the json data from the raw html---'''
    
    try:
        json_data = discard_html(webpage)
        if json_data is False:
            return 1001
    except json.decoder.JSONDecodeError as e:
        return 1002
    
    col_orders = pp_db.get_data_to_parse()
    proj_order = col_orders['projection']
    '''---Define large data structure where all the parsed data will reside until it is sent to mySQL---'''
    data_values = parse_proj_json(json_data, proj_order)
    includes = parse_included_data(json_data.get("included"), col_orders)

    return parsed_data(col_orders['projection'], data_values, includes)

def parse_proj_data(data_item, col_order):
    '''
    Function will be used to parse the 'data' tags in the json from prizepicks api. This takes in a 'data item' which is a tag from the parsed json
    and parses it into columns to eventually send to mysql database. 
    
    This also has some tracking/debugging in it where I'm tracking which items are not getting filled up or being double-filled. It may not be very 
    useful in the future, but for validation, I'm going to leave it in there.
    '''

    #Create and fill up dict to hold all the data for given column
    my_dict = dict()
    for col in col_order:
        my_dict[col] = None

    for attr, val in data_item.items():
        if attr in col_order:
            my_dict[attr] = val

    '''---Parsing attributes sub-dict---'''
    for attr, val in data_item['attributes'].items():
        if attr in col_order:
            my_dict[attr] = val
        
    
    '''---Parsing relationships sub-dict data and data from its sub-dicts---'''
    #This also should eventually be able to be parsed based on what is pulled from mysql db, for now hard-code is fine...
    relationship_dicts = ["league", "new_player", "duration", "game"]
    relationship_data = ["score"]
    for sub_dict in relationship_dicts:
        if data_item['relationships'].get(sub_dict):
            my_dict[sub_dict] = data_item['relationships'][sub_dict]['data'].get('id')
        else:
            my_dict[sub_dict] = None

    for sub_dict in relationship_data:
        if data_item['relationships'].get(sub_dict):
            my_dict[sub_dict] = data_item['relationships'][sub_dict].get('data')
        else:
            my_dict[sub_dict] = None

    '''
    These are 2 exceptions where the naming is not the same between prizepicks api and my db since thes'stat_type' and 'projection_type' 
    are already used in the 'attuributes' tag, so need to hard-code these exceptions.
    '''
    #If these are stored in another table, I may not need to save everything twice, I can just get this info from the other table using the ids - will check on that as work continues
    my_dict["projection_type_id"] = data_item['relationships']['projection_type']['data'].get('id')
    my_dict["stat_type_id"] = data_item['relationships']['stat_type']['data'].get('id')

    return [my_dict[key] for key in col_order]

@log_perf
def parse_proj_json(json_data, order):

    data_values = []
    #print("Parsing 'projection' tags...")
    for item in json_data['data']:

        '''---For each of the tags in the 'data' tag, send them all to the 'data' parser to get the necessary data from the json---'''
        my_data = parse_proj_data(item, order)
        data_values.append(my_data)

    print(f"Parsed 'projections' with {len(data_values)} entries")
    return data_values

@log_perf
def parse_included_data(included_data, col_orders):
    '''
    When projection API is called, in addition to all the projection data, there is also data shared about stat types, stat averages, player, teams and leagues
    in the tag called 'included'. This data defines what the projection is (ie rushing vs passing yards), who the player is, what team they are on and so forth.
    The more data which can be collected the more predictions can be made based on the outcomes of the projections.
    '''
    parsed_data = dict()
    skipped = {'stat_average', 'duration'}
    for table_name in col_orders:
        parsed_data[table_name] = []
    
    #since projection is handled in a different function, we need to remove parsing it from this one
    del parsed_data['projection']

    #loop through each tag in the included data for parsing
    for tag in included_data:
        #If an unexpected tag is found, notify the user once per type and just skip them
        '''---Perhaps this could be added to logging somewhere---'''
        if tag['type'] not in col_orders:
            if tag['type'] not in skipped:
                input(f"!!!WARNING!!!\nTag '{tag['type']}' not in col_orders. Skipping...")
                skipped.add(tag['type'])
            continue
        
        #All of the included tags seem to follow the same/similar format, so by default they will
        #just have the id taken and then look through the 'attributes' for the data that can be added
        #sql DB
        my_tag = dict()

        for col in col_orders[tag['type']]:
            my_tag[col] = tag['attributes'].get(col)

        #new_player and game tags have some data which exists outside of the attributes tags, so these code blocks get that data and pull it into the dict
        if tag['type'] == "new_player":
            try:
                my_tag['team_id'] = tag['relationships']['team_data']['data']['id']
            except KeyError:
                print(f"Could not find team_id for player tag {tag['id']}. Unexpected but not critical...")
                my_tag['team_id'] = None
            try:
                my_tag['league_id'] = tag['relationships']['league']['data']['id']
            except KeyError:
                print(f"Could not find league_id for player tag {tag['id']}. Unexpected but not critical...")
                my_tag['league_id'] = None

        elif tag['type'] == "game":
            try:
                my_tag['home'] = tag['relationships']['home_team_data']['data']['id']
            except KeyError:
                print(f"Could not find home team id for game tag {tag['id']}. Bad but not critical, should be investigated...")
                '''---This should log a soft error somewhere---'''
                my_tag['home'] = None
            try:
                my_tag['away'] = tag['relationships']['away_team_data']['data']['id']
            except KeyError:
                print(f"Could not find away team id for game tag {tag['id']}. Bad but not critical, should be investigated...")
                '''---This should log a soft error somewhere---'''
                my_tag['away'] = None

        my_tag['id'] = tag['id']
        parsed_data[tag['type']].append(my_tag)

    return parsed_data
