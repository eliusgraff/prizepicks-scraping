import os
import prizepicks_db
import web_scraper
import my_parser
import helper

def save_wp_data(wp, fn):
    if wp == 1:
        print("Issue with default params, nothing written")
    else:
        with open(fn, 'w') as file:
            file.write(wp)
        print(f"Wrote WP to: {fn}")

def get_wp_example(fn = "example_wp.json"):
    
    use_local = True
    ow_local = False
    file_check = os.path.isfile(fn)
    wp = None

    if ow_local:
        print(f"OW Local '{fn}'...")
        wp = web_scraper.make_selenium_request()
        save_wp_data(wp, fn)

    elif use_local:
        print(f"Reading from local file '{fn}'")
        if (file_check is False) or (os.stat(fn).st_size == 0):
            print(f"File '{fn} does not exist or is empty. Attempting re-write...")
            wp = web_scraper.make_selenium_request()
            save_wp_data(wp, fn)
        else:
            print(f"Reading from:{fn}")
            with open(fn, 'r') as file:
                wp = file.read()
            print("Read complete!")
    else:
        print("Parsing data from internet request...")
        wp = web_scraper.make_selenium_request()

if __name__ == "__main__":
    '''
    Eventually, this will be the code that is the manager for the scraper that keep running all the time
    '''
    wp = get_wp_example()


