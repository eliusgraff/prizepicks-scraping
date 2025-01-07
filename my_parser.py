from bs4 import BeautifulSoup
import json
from datetime import datetime
import prizepicks_db as ppdb

def parse_webpage(webpage):
    '''
    This function takes in an HTML webpage from prizepicks API request, strips the HTML from it and just goes through each of the tags in the json
    about the bets and stats. This function will also facilitate sending the parsed data to the local mySQL database.

    Prizepicks API json is formatted with each of the bets in one tag called 'data', then more of the payers and stats info in the 'included' tag
    which fill in additional necessary data about the bets like the player's info, what the stat is and other things.

    Parsing the data tags will return a list of values to coorespond to each of the values in the 'data_order' list. Before adding it all into the mySQL db.
    '''
    '''---Get the json data from the raw html---'''
    
    soup = valid_wp(webpage)
    if soup is False:

        return False
    
    json_data = json.loads(soup.find('pre').text)

    '''---Defining order that data will go in as to align with SQL columns---'''
    data_order = [
        "type",
        "id",
        "adjusted_odds",
        "board_time",
        "description",
        "end_time",
        "flash_sale_line_score",
        "game_id",
        "hr_20",
        "in_game",
        "is_live",
        "is_promo",
        "line_score",
        "odds_type",
        "projection_type",
        "rank",
        "refundable",
        "start_time",
        "stat_type",
        "status",
        "tv_channel",
        "updated_at",
        "duration",
        "league",
        "new_player",
        "projection_type_id",
        "score",
        "stat_type_id"
    ]

    '''---Define large data structure where all the parsed data will reside until it is sent to mySQL---'''
    data_values = []

    print("Parsing 'data' tags...")
    for item in json_data['data']:

        '''---For each of the tags in the 'data' tag, send them all to the 'data' parser to get the necessary data from the json---'''
        my_data = parse_data(item, data_order)
        data_values.append(my_data)

    print(f"Parsed 'data' with {len(data_values)} entries")

    '''---After the 'data' section of the json, it goes to the 'included' tag which can contain many different tags---'''

    '''---Defining order for all the the types of tags within the 'included' tag---'''
    included_tag_orders = {
        "duration":             ["id", "name"],
        "league":               ["id", "active", "f2p_enabled", "icon", "image_url", "last_five_games_enabled", "league_icon_id", "name", "projections_count", "rank", "show_trending", "is_data"],
        "league_data":          ["league_id", "time_set", "data"],
        "lfg_ignored_leagues":  ["id", "league_num"],
        "new_player":           ["id", "name", "position", "image_url", "display_name", "combo", "league_id", "team_id"],
        "projection_type":      ["id", "name"],
        "stat_average":         ["id", "average", "count"],
        "stat_type":            ["id", "lfg_ignored_leagues", "name", "rank"],
        "team":                 ["id", "primary_color", "abbreviation", "name", "tertiary_color", "secondary_color", "market"]
    }

    '''---Large structure where all the data will get stored before going to mysql---'''
    included_tag_values = {
        "duration": [],
        "league": [],
        "league_data": [],
        "lfg_ignored_leagues": [],
        "new_player": [],
        "projection_type": [],
        "stat_average": [],
        "stat_type": [],
        "team": []
    }

    print("Parsing 'included' tags...")

    for item in json_data['included']:

        '''---Going through all of the 'included' tags and parsing them one by one---'''
        my_type = item['type']
        '''
        'new_player' and 'league' tags have relationship dicts which make them different from 
        the other tags in the 'included' tag, so they need their own parsers
        '''
        if my_type in included_tag_orders:

            parsed_include = parse_included(item, included_tag_orders[my_type])

        else:
            '''---Since all of the tags should be parsed, this checks to make sure all tag types are correctly parsed and saved---'''
            print(f"Concerned about this one, please review:")

            for k,v in item.items():

                print(f"{k}\t{v}")

            print("Review needed. Exiting....")
            exit()

        '''---Adding the parsed tag to the big data dictionary to store before sending to mySQL---'''

        '''
        'league' and 'stat_type' tags can include additional list of data, but not always. In the case that the list of data is included in
        there, this must be handled uniquely to get the list of data also saved in the database. This code handles those cases.
        '''
        if my_type == "league" and parsed_include[-1] is not None:

            league_data = parsed_include[-1]
            data_list = league_data[0]
            timestamp = league_data[1]
            league_id = parsed_include[0]
            for val in data_list:

                included_tag_values['league_data'].append([league_id, timestamp, val])

            parsed_include[-1] = True
        
        elif my_type == "stat_type":

            if isinstance(parsed_include[1], list) and len(parsed_include) > 0:

                ignored_leagues = parsed_include[1]
                for league_num in ignored_leagues:

                    '''
                    To find this data in the SQL db, the 'lfg_ignored_leagues' table rows will keep track of the stat_type id and
                    the league number this way it can be recalled based on the stat_type id or vice versa
                    '''
                    lfg_row = [parsed_include[0], league_num]
                    included_tag_values['lfg_ignored_leagues'].append(lfg_row)

                parsed_include[1] = True

            else: parsed_include[1] = None

        included_tag_values[my_type].append(parsed_include)
        my_tot = 0
    

    for k,v in included_tag_values.items():
        '''---checking that all of the rows are the correct length before sending them to sql---'''
        for row in v: assert len(row) == len(included_tag_orders[k])

        '''---Counting total number of entries parsed---'''
        my_tot+=len(v)

    print(f"Parsed 'include' with {my_tot} entries")
    return ppdb.send_to_sql(data_order, data_values, included_tag_orders, included_tag_values)

def parse_included(my_tag, order):
    '''
    This function is used to parse any of the 'included' tags in the json from prizepicks api. It takes in the tag, called 'my_tag' and
    a list 'order' of how the tag data should be ordered for insertion into mysql. The function returns a list of the values from the 
    tag in the order defined by the 'order' list.
    '''
    '''
    Using a dict to store the data as it is parsed until ordering at the very end of the function. 'not_found' is used to make 
    sure that all of the items that are expected to be in the tag, are found before sending to mysql. This will also help for validation
    and may be able to be excluded in the future for performance gains.
    '''
    my_dict = dict()
    not_found = set(order)

    '''---For 'new_player' and 'league' tags, some special parsing is need to get some unique data, so we need to account for that---'''
    if my_tag['type'] == 'new_player':

        my_dict['team_id'] = my_tag['relationships']['team_data']['data']['id']
        not_found.remove('team_id')

    elif my_tag['type'] == 'league':

        temp_data = my_tag['relationships']['projection_filters']['data']
        if len(temp_data) > 0:

            my_dict['is_data'] = None

        else:

            my_dict['is_data'] = (temp_data, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        not_found.remove('is_data')        

    '''---All tags have 'id' field which is needed, so hard-code this in---'''
    my_dict['id'] = int(my_tag['id'])
    not_found.remove('id')

    '''---Look for the remaining tags we need in the attributes tag and add those to the dict---'''
    remaining = not_found.copy()
    for attr in remaining:

        try:

            my_dict[attr] = my_tag['attributes'][attr]

        except Exception as e:

            print(my_tag)
            print(f"Something went wrong atting attribute values to my_dict. Got exception:\n{e}")
            raise e

        not_found.remove(attr)

    '''---Print statements to help with validation---'''
    #should be able to remove this in the future, not useful for production
    if len(not_found) > 0:

        print(f"\n\n------------From below tag------------\n")
        for key, val in my_tag.items():print(f"{key}\t{val}")
        print("\n-----------Could not find data for the following-----------\n")
        for k in not_found: print(f"{k},")
        print()
        input("Review if this is ok...")

    to_return = [ my_dict[item] for item in order ]

    return to_return

def parse_data(data_item, order):
    '''
    Function will be used to parse the 'data' tags in the json from prizepicks api. This takes in a 'data item' which is a tag from the parsed json
    and parses it into columns to eventually send to mysql database. 
    
    This also has some tracking/debugging in it where I'm tracking which items are not getting filled up or being double-filled. It may not be very 
    useful in the future, but for validation, I'm going to leave it in there.
    '''
    '''---Dict sets up all the columns that will be added into SQL db for the data table---'''
    my_dict = {
        "type": None,
        "id": None,
        "adjusted_odds": None,
        "board_time": None,
        "description": None,
        "end_time": None,
        "flash_sale_line_score": None,
        "game_id": None,
        "hr_20": None,
        "in_game": None,
        "is_live": None,
        "is_promo": None,
        "line_score": None,
        "odds_type": None,
        "projection_type": None,
        "rank": None,
        "refundable": None,
        "start_time": None,
        "stat_type": None,
        "status": None,
        "tv_channel": None,
        "updated_at": None,
        "duration": None,
        "league": None,
        "new_player": None,
        "projection_type_id": None,
        "score": None,
        "stat_type_id": None
    }

    '''---Some fields are not always in a data tag, so this allows the code to know which things it is ok to not have in a tag---'''
    not_promised = {
        "hr_20"
    }

    '''---Setting up structure to track what fields have been parsed from the tag---'''
    not_found = set(my_dict.keys())

    '''---Where the data is not held in a sub-dict, can add that info directly from the json tag to my_dict without iterating over the sub-dict---'''
    my_dict['type'] = data_item['type']
    my_dict['id'] = int(data_item['id'])
    not_found.remove('type')
    not_found.remove('id')

    '''---Parsing attributes sub-dict---'''
    for attr, val in data_item['attributes'].items():

        if attr in my_dict:

            my_dict[attr] = val
            not_found.remove(attr)

    '''---Parsing relationships sub-dict data and data from its sub-dicts---'''
    relationship_dicts = ["league", "new_player", "duration"]
    relationship_data = ["score"]
    for sub_dict in relationship_dicts:

        my_dict[sub_dict] = data_item['relationships'][sub_dict]['data'].get('id')
        not_found.remove(sub_dict)

    for sub_dict in relationship_data:

        my_dict[sub_dict] = data_item['relationships'][sub_dict].get('data')
        not_found.remove(sub_dict)

    '''
    These are 2 exceptions where the naming is not the same between prizepicks api and my db since thes'stat_type' and 'projection_type' 
    are already used in the 'attuributes' tag, so need to hard-code these exceptions.
    '''
    #If these are stored in another table, I may not need to save everything twice, I can just get this info from the other table using the ids - will check on that as work continues
    my_dict["projection_type_id"] = data_item['relationships']['projection_type']['data'].get('id')
    my_dict["stat_type_id"] = data_item['relationships']['stat_type']['data'].get('id')
    not_found.remove('projection_type_id')
    not_found.remove('stat_type_id')
    
    '''
    This code block is just for dev/validation purposes it just prints out anything that was expected by not seen by the parser
    '''
    if len(not_found) > 0:
        '''---Since some things are not garunteed to be in a data tag, this makes sure it is only notifying tester if something expected is missing---'''
        to_print = []
        for item in not_found:
            '''---For combo projections where players are on differnt teams, a game_id may not be assigned, so this accounts for that case---'''
            if item == 'game_id' and data_item['attributes']['stat_type'].find("(Combo)") >-1:
                continue
            elif item not in not_promised:
                to_print.append(item)

        '''---Printing out everything in the tag and all the things missing from the tag---'''
        if len(to_print) > 0:
            print(f"\n\n------------From below tag------------\n")
            for key, val in data_item.items(): print(f"{key}\t{val}")
            print("\n-----------Could not find data for the following-----------\n")
            for k in not_found: print(f"{k},")
            print()
            input("Review if this is ok...")

    return [my_dict[key] for key in order]

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