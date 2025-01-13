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

def validate():
    '''
    Function used for testing development and validation of branch for gatting data from the parsed state and into mySQL.
    Takes no arguemtns so that test design is not limited by passed-in vars and returns true when everything passes!!!
    '''

    '''---Testing errors from bad caller---'''
    print(">>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF WP1<<<<<<<<<<<<<<")
    wp1 = get_wp_example("example_wp.html", local = True, ow = False, league="NFL")
    
    try:
        if not my_parser.parse_webpage(wp1):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of wp1")
        raise E
    exit("Finished with wp1")

    print("\n>>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF WP2<<<<<<<<<<<<<<")
    wp2 = get_wp_example("example_wp_inflight.html", local = True, ow = False, league="NFL")
    print("\n>>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF API1<<<<<<<<<<<<<<")
    api1 = get_wp_example("no_file_name1.html", local = True, ow = False, league="NFL")
    print("\n>>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF API2<<<<<<<<<<<<<<")
    api2 = get_wp_example("no_file_name2.html", local = True, ow = False, league="CFB")
    print("\n>>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF API3<<<<<<<<<<<<<<")
    api3 = get_wp_example("no_file_name3.html", local = True, ow = False, league="WNBA")
    print("\n>>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF API4<<<<<<<<<<<<<<")
    api4 = get_wp_example("no_file_name4.html", local = True, ow = False, league="Soccer")
    print("\n>>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF EMPTY_FILE<<<<<<<<<<<<<<")
    empty_file = get_wp_example("empty.html", local = True, ow = False, league="NFL")
    print("\n>>>>>>>>>>>>>>>PERFORMING DATA COLLECTION OF BAD_HTML<<<<<<<<<<<<<<")
    bad_html = get_wp_example("bad_html.html", local = True, ow = False)

    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF WP1<<<<<<<<<<<<<<")
    try:
        if not my_parser.parse_webpage(wp1):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of wp1")
        raise E
    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF WP2<<<<<<<<<<<<<<")
    try:
        if not my_parser.parse_webpage(wp2):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of wp2")
        raise E
    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF API1<<<<<<<<<<<<<<")
    try:
        if not my_parser.parse_webpage(api1):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of api1")
        raise E
    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF API2<<<<<<<<<<<<<<")
    try:
        if not my_parser.parse_webpage(api2):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of api2")
        raise E
    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF API3<<<<<<<<<<<<<<")
    try:
        if not my_parser.parse_webpage(api3):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of api3")
        raise E
    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF API4<<<<<<<<<<<<<<")
    try:
        if not my_parser.parse_webpage(api4):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of api4")
        raise E
    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF EMPTY_FILE<<<<<<<<<<<<<<")
    try:
        if my_parser.parse_webpage(empty_file):
            raise Exception
    except Exception as E:
        print("Did not pass parsing of empty_file")
        raise E
    print("\n>>>>>>>>>>>>>>>PERFORMING PARSING OF BAD_HTML<<<<<<<<<<<<<<")
    try:
        if my_parser.parse_webpage(bad_html):
            print("Did not pass parsing of bad html_file")
            raise Exception
    except Exception as E:
        print("Did not pass parsing of bad html_file")
        raise E
    
    return True

if __name__ == "__main__":
    '''
    Eventually, this will be the code that is the manager for the scraper that keep running all the time
    '''
    my_logs.create_loggers()
    scrape_status = web_scraper.new_get_prizepicks("NFL")
    if isinstance(scrape_status, int):
        print(f"Something went wrong with errorcode: {scrape_status}")
        exit()
    
    wp_data = my_parser.parse_webpage(scrape_status)
    sql_status = send_to_sql(wp_data)