import mysql.connector
import helper
from datetime import datetime

#Long term, this should not need to be root user
def root_login():
    '''
    This function is used to retrive the username, host name, and password to gain access to the local
    mySQL database. requires that the user have a file called 'secrets.txt' where 3 of the lines in it are:
    mysql_un=username
    mysql_pw=password
    mysql_hn=hostname
    
    So, to access this, that file must be setup beforehand and then this function will work properly as it
    is simply reading those 3 items from the file. It muse have *accurate* user info of the 3
    fields above to get into the SQL DB
    '''
    my_dict = helper.get_secret("mysql")
    '''---Checking to make sure all the necessary parts were read from file---'''
    not_found_list = []
    if my_dict.get('un') is None: not_found_list.append('un')
    if my_dict.get('pw') is None: not_found_list.append('pw')
    if my_dict.get('hn') is None: not_found_list.append('hn')
    if len(not_found_list) > 0:
        print(f"WARNING: Missing values in dict:{not_found_list}")
        return None

    return my_dict

def create_db_connection(db_name="prizepicks", host_name= None, user_name = None, user_password = None):
    '''
    Function to create a connection to the local mySQL database. Credentials can be passed in or they default to None and if host_name is left as None
    then the root_login() function will get the root login data form a file somewhere on the computer
    '''
    if host_name is None:
        creds = root_login()
        host_name = creds['hn']
        user_name = creds['un']
        user_password = creds['pw']

    connection = mysql.connector.connect(
        host=host_name,
        user=user_name,
        passwd=user_password,
        database=db_name
    )

    print("MySQL Database connection successful")
    return connection

def list_to_db( table, headers, data, cursor):
    raise NotImplemented
    '''
    Function which will send passed in descriptors and data to the local prizepicks mySQL database
    Argumetns are:
        table - name of the table the data will be inserted into
            ex: "new_player" or "lfg_ignored_leagues"
        headers - a list of names of the columns of the target table in order for how they apprear in the data
            ex: ["id", "name", "position", "image_url", "display_name", "combo", "league_id", "team_id"] or ["id", "league_num"]
        data - a list of lists where each sub-list is the list of data that is going into the database. The data point at each index is
            described by that same index of 'headers' list
            ex: [
                ['172250', 'Jude Bellingham', 'Midfielder', 'https://static.prizepicks.com/images/players/soccer/e83ula4wockmc2xid7185kcq2.webp', 'Jude Bellingham', False, 82, '3372'],
                ['197873', 'Jyllissa Harris', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Houston_Dash.webp', 'Jyllissa Harris', False, 82, '4156'],
                ['171076', 'JÃ¸rgen Strand Larsen', 'Attacker', 'https://static.prizepicks.com/images/manual/JÃ¸rgen Strand Larsen.png', 'JÃ¸rgen Strand Larsen', False, 82, '3356'],
                ['215896', 'Courtney Petersen', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Racing_Louisville.webp', 'Courtney Petersen', False, 82, '4160']
                ]
                or
                [
                ['718', 82]
                ]
    '''
    id_index = headers.index("id")
    cols_query = f"SHOW COLUMNS FROM {table};"
    cursor.execute(cols_query)
    cols_list = cursor.fetchall()

    #make sure I cols list looks how I expect
    for each in cols_list:
        print(each)
    exit()

    assert len(headers) < len(cols_list)
    for i, name in enumerate(headers):
        if name != cols_list[i][0]:
            print(f"Headers:\t{headers}")
            print(f"Cols:\t{cols_list}")
            break
        input()

    for row in data:
        my_query = f"SELECT * FROM {table} WHERE ISLATEST = TRUE AND ID = {row[id_index]};"
        latest_data = read_query(cursor, my_query)
        write_query = None

        if len(latest_data) == 0:
            write_query = f"INSERT INTO {table} VALUES {tuple(row+[0,True])}"
            cursor.execute(write_query)
        
        for i, val in enumerate(row):
            if val != latest_data[i]:
                #if it is ok to be different
                #   continue
                #else
                #   update existing row islatest flag to false
                #   add in new row with version = n+1
                is_same = False
                #   break
        
def send_to_sql(data_cols, data_values, includes_cols, include_values):
    '''---Creating mysql connecrtion and cursor objects so we can set up the transfer---'''
    conn = create_db_connection()
    cursor = conn.cursor()
    
    '''---Sending the values for the 'data' table to mySQL---'''
    list_to_data_table(data_cols, data_values, cursor)
    conn.commit()
    conn.close()
    print("Completed adding to data table, check to see if things look good")
    exit()

    '''---Going through all the includes and adding those now---'''
    for name, cols in includes_cols.items():
        list_to_db(name, cols, include_values[name])

    '''---Saving changes to the databse and closing the connection---'''
    #I should look into what it best practive and when to commit the sql executions I think I like doing it at the end so that if something goes wrong then just nothing is added and it's no problem
    conn.commit()
    conn.close()
    return True

def read_query(cursor, query):
    
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Exception as E:
        print(f"Attempting query: {query}\nBut error occured")
        raise E

def execute_query(cursor, query):
    cursor.execute(query)

def list_to_data_table( headers, data, cursor):
    '''
    Function which will send passed in data into the 'data' table of the local mySQL database
    Argumetns are:
        headers - a list of names of the columns of the target table in order for how they apprear in the data
    
        data - a list of lists where each sub-list is the list of data that is going into the database. The data point at each index is
            described by that same index of 'headers' list
            ****UPDATE THIS TO SHOW THE ACTAUL VALID DATA EXAMPLE*****
            ex: [
                ['172250', 'Jude Bellingham', 'Midfielder', 'https://static.prizepicks.com/images/players/soccer/e83ula4wockmc2xid7185kcq2.webp', 'Jude Bellingham', False, 82, '3372'],
                ['197873', 'Jyllissa Harris', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Houston_Dash.webp', 'Jyllissa Harris', False, 82, '4156'],
                ['171076', 'JÃ¸rgen Strand Larsen', 'Attacker', 'https://static.prizepicks.com/images/manual/JÃ¸rgen Strand Larsen.png', 'JÃ¸rgen Strand Larsen', False, 82, '3356'],
                ['215896', 'Courtney Petersen', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Racing_Louisville.webp', 'Courtney Petersen', False, 82, '4160']
                ]

    '''
    '''---Setting up vairables needed for function---'''
    reserved_words = {
        "status",
        "rank",
        "description",
        "type"
        }

    allow_change = {
        "board_time", 
        "my_rank", 
        "updated_at",
        "line_score"
        }

    '''---Some fields I expect to be datetimes, so if they are given, parse them as datetime---'''
    my_dts={
        "board_time",
        "end_time",
        "start_time",
        "updated_at"
    }

    '''---Some fields are boolean, but SQL returns them as 1 or 0, so I need to know which ones I need to cast correctly---'''
    my_bools = {
        "islatest",
        "hr_20",
        "in_game",
        "is_live",
        "is_promo",
        "refundable"
    }
    insert_list = list()
    insert_line_score = list()
    updated_ids = set()
    table = 'my_data'
    #Can this be done with list comprehension?
    fix_headers = []
    for header in headers:
        if header in reserved_words: fix_headers.append(f"my_{header}")
        else: fix_headers.append(header)
    id_index = headers.index("id")
    line_index = headers.index("line_score")

    '''---Make sure columns are aligned with DB---'''
    cols_query = f"SHOW COLUMNS FROM {table};"
    cursor.execute(cols_query)
    cols_list = cursor.fetchall()
    fix_headers = fix_headers + ['my_version','islatest'] 
    try:
        assert len(fix_headers) == len(cols_list)   
        for i, v in enumerate(cols_list):
            assert v[0] == fix_headers[i]
    except AssertionError as AE:
        print(f"Item comparison:\n{v[0]}\n{fix_headers[i]}")
        print(f"Fix headers:\n{fix_headers}")
        print(f"Col list:\n{cols_list}")
        raise AE

    '''---Pull in all existing rows from the db into a dict for quick recall---'''
    id_list = [values[id_index] for values in data]
    my_query = f"SELECT * FROM {table} WHERE ISLATEST = TRUE AND ID IN {tuple(id_list)};"    
    existing_data = read_query(cursor, my_query)
    data_dict = dict()

    '''---Making sure that the data in the db already does not have double-up of same ids that are 'latest'---'''
    for row in existing_data:
        if row[id_index] in existing_data:
            '''
            Since there should only be one row with a target id that is also the latest, this check to make sure that is enforced. Since this should not be possible
            I don't want to spend a lot of time on this, but in the case it does pop up, then this will catch is and whatever is causing it should be patched but if
            nothing else this conflict should be handled logically
            '''
            print(f"Two instances of 'islatest' for same id:\nExisting:\n{existing_data}\nIncoming:\n{row}")
            print("This is unexpected and should not be possible, plz fix")
            assert row[id_index] not in existing_data

        data_dict[row[id_index]] = row

    for row in data:
        '''
        Looping through each of the incoming rows of parsed data to check if they need to be inserted into the db or if existing rows need to be updated
        '''
        row_id = row[id_index]
        if row_id in updated_ids:
            '''---Cheecking to make sure same id is not in to be sent into DB  twice---'''
            print(f"THIS IS UNEXPECTED AND SHOULD NOT BE ABLE TO HAPPEN. THIS IS SECOND TIME THIS ID IS UPDATED IN THE SAME API REQUEST:\n{row}")
            print("For now this will just be for refernce but if there is a case where this can happen, then this will need to be handled logically")
            input("Skipping this one, press enter to continue")
            continue
        updated_ids.add(row_id)
        '''
        Go through each row of data passed into the function and check to see if there already existing entry in the db for it. 
            If there is no existing entry, then add it right in. 
            Elif there exists entry for incoming id already, check if any values have changed
                if important values have changed - add new row to the db and set old one to not being latest and update version number of the new one
        '''
        '''---Checking to see what already exists in the db---'''
        
        if data_dict.get(row_id) is None:
            '''
            If there is nothing already in the DB matching the data id, insert the values straight into the DB. Since this is the first time this
            data is inserted, adding [0,True] to the end of the row to align with the 'version' and 'islatest' columns
            '''
            new_row = row + [0,True]
            insert_list.append(new_row)
            insert_line_score.append([row_id, row[headers.index("projection_type")], row[line_index]])
        
        else:
            '''
            If there is already data for this id in the DB, then go through each column and check to see if anything changed. If something changed that
            is not expected to regularly change, then the 'islatest' version of the existing row must be changed to False and the 'version' and islatest'
            columns of the incoming row must be set to be n+1 and True
            '''
            print(f"Found change! On id:{row_id}")
            existing_row = data_dict[row_id]
            line_score_flag = row[line_index] == existing_row[line_index]
            disallowed_flag = False
            for i, val in enumerate(row):
                
                if headers[i] in my_dts and isinstance(val, str):
                    my_val = datetime.fromisoformat(val)
                    '''elif headers[i] in my_bools:
                        my_val = int(val)'''
                else:
                    my_val = val

                if my_val != existing_row[i] and headers[i] not in allow_change:
                    '''
                    To keep track of how info changes over time I will keep track of versions over time. In the case I find a field that not 'allowed' to change has changed
                    then this code adds in the new info and marks the old data as not the latest version.
                    '''                    
                    disallowed_flag = True
                    new_version = existing_row[fix_headers.index('my_version')] + 1
                    new_row = row + [new_version, True]
                    update_existing = f"UPDATE {table} SET islatest = FALSE WHERE islatest = TRUE AND id = {row[id_index]};"
                    cursor.execute(update_existing)
                    insert_list.append(new_row)
                    print("Dissallowed changed")
                    print(f"{my_val}\t{existing_row[i]}\n{type(my_val)}\t{type(existing_row[i])}\n{headers[i]}\t{allow_change}")
                    #input()
                    break
            
            if line_score_flag:
                '''
                This handles the tracking of changing line scores. In the case where just the line score is changed, then this updates the 'my_data' database to reflect that. If
                other dissallowed items changed, then this is updated when that data is saved to the DB.

                In any case, if the line_score_flag is raised, then new line needs to be added to the 'spread_history' table
                '''
                if not disallowed_flag:
                    print(" scoreline changed")
                    update_score = f"UPDATE {table} SET line_score = {my_val} WHERE my_id = {row[id_index]} AND islatest = TRUE;"
                    cursor.execute(update_score)
                
                insert_line_score.append([row_id, row[headers.index("projection_type")], row[line_index]])
                
    add_new_lines(insert_list, insert_line_score, cursor)
            
def add_new_lines(my_data_list, spread_history_list, cursor):
    my_data_write_query = f"INSERT INTO my_data VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
    spread_history_write_query = f"INSERT INTO spread_history VALUES(%s,%s,%s,NOW());"
    cursor.executemany(my_data_write_query, my_data_list)
    cursor.executemany(spread_history_write_query, spread_history_list)



def add_new_line_score( bet_id, bet_type, spread, cursor):
    '''
    Function takes in a new data point and adds it into the spread_history table so that as spreads change over time
    the whole history of how those change can be kept and analyzed
    '''
    col_names = ["bet_id", "bet_type", "spread", "time"]
    vals = [bet_id, bet_type, spread]
    my_query = f"INSERT INTO spread_history VALUES (%s,%s,%s,NOW())"
    cursor.execute(my_query, vals)

def list_to_string(my_list):
    raise NotImplementedError
    to_return = ""
    for string in my_list:
        to_return += str(string) + ", "
    to_return = to_return[:-2]
    print(f"Converted string into: {to_return}")
    return to_return