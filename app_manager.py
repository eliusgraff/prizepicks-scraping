import os
import web_scraper
import my_parser
from prizepicks_db import send_to_sql
import my_logs

class PassingException(Exception):
    pass

def save_wp_data(wp, fn):
    '''
    Function to take data from PrizePicks API and save it as a file.
    It takes 2 arguments:
        wp - wbpage data to be saved
        fn - name of file to save the webpage data at
    '''
    with open(fn, 'w', encoding='utf-8') as file:
        file.write(wp)

    print(f"Wrote WP to: {fn}")

def get_wp_example(fn = "example_wp.html", local = True, ow = False, league = "NFL"):
    '''
    Function to load in example file for development use or request a new one from the prizepicks API.
    
    3 parameters are passed in:
        fn - file name as a string of the file that is to be used
        local - bool which dictates whether an existing local file should be used or not
        ow - bool which tells whether to overwrite any existing files which may have the same name as what was passed in

    This function default to picking "NFL" data, but that can be changed to any of a number of the following abbreviations
    which are recognized by the scraper and PrizePicks database: "NFL", "CFB", "MLB", "WNBA", "Soccer", "CFB2H".
    '''
    use_local = local
    ow_local = ow
    wp = None
    my_lg = league
    fn = "test files\\"+fn

    '''
    This line checks to see if there is an existing file that matches fn. If not, then the code will create and fill in a file with
    that name from Prizepicks API call. This will override any other flags for local or ow sent in by user.
    '''
    file_check = os.path.isfile(fn)
    
    if ow_local:

        print(f"OW Local '{fn}'...")
        wp = web_scraper.make_selenium_request(my_lg)
        save_wp_data(wp, fn)

    elif use_local:

        print(f"Reading from local file '{fn}'")
        if file_check is False:

            '''---If local file does not exist then create and fill one with default API request---'''
            print(f"File '{fn} does not exist or is empty")
            wp = web_scraper.make_selenium_request(my_lg)
            if ow_local is True:

                print(f"Re-writing {fn}")
                save_wp_data(wp, fn)

        else:

            print(f"Reading from:{fn}")
            with open(fn, 'r') as file:

                wp = file.read()

            print("Read complete!")

    else:

        print("Parsing data from internet request...")
        wp = web_scraper.make_selenium_request(my_lg)
    
    return wp

def handle_parser_error(wp_ec, retry_request):
    
    err_msgs = {
        1 : "---WARNING:Webpage not valid, retry webpage...",
        2 : "---WARNING:Got JSONDecodeError while creating dict from json, retry webpage...",
        3 : "Len of data parsed is 0. Quitting parsing.",
        4 : "---WARNING:Data tags sent but no includes. Unexpected. Quitting parsing, moving to the next.",
        5 : "---WARNING:Found row length inconcisent with expectations. Quitting parsing, moving to the next"
    }
    
    if wp_ec in err_msgs:
        print(err_msgs[wp_ec])
    else:
        print(f"Returned with error code {wp_ec}")
        return False
    if wp_ec == 2:
        print(f"Retry web scrape")
        new_data = my_parser.parse_webpage(web_scraper.new_get_prizepicks(retry_request))
        if isinstance(new_data, int):
            return False
        else:
            return new_data
    return False

    

def validate():
    '''
    Function used for testing development and validation of branch for gatting data from the parsed state and into mySQL.
    Takes no arguemtns so that test design is not limited by passed-in vars and returns true when everything passes!!!
    '''
    known_leagues = {
    "NFL":9,
    "CFB":15,
    "MLB":2,
    "WNBA":3,
    "Soccer":82
    }

    my_logs.create_loggers()
    for each in known_leagues:
        
        scrape_data = web_scraper.new_get_prizepicks(each)
        if isinstance(scrape_data, int):
            print(f"Failed scrpaing with status: {scrape_data}")
            print("Skipping to next league")
            continue
        wp_data = my_parser.parse_webpage(scrape_data)
        '''
        Since there are cases where json parses come up empty or incorrect, the parser will return different codes
        to manage that, this alerts user of those conditions and stops program from proceeding with unexpected inputs
        If expected input is confirmed, then go ahead and send it to SQL
        '''
        #Add this to event logging
        if isinstance(wp_data, int):
            wp_data = handle_parser_error(wp_data, each)
            if wp_data is False:
                continue

        else:
            send_to_sql(wp_data)

    return True

if __name__ == "__main__":
    '''
    Eventually, this will be the code that is the manager for the scraper that keep running all the time
    '''
    validate()
    exit()
    my_logs.create_loggers()
    scrape_status = web_scraper.new_get_prizepicks("NFL")
    if isinstance(scrape_status, int):
        print(f"Something went wrong scraping with errorcode: {scrape_status}")
        exit()
    
    wp_data = my_parser.parse_webpage(scrape_status)
    sql_status = send_to_sql(wp_data)