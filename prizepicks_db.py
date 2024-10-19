import mysql.connector
import helper

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

    '''---Going through all the includes and adding those now---'''
    for name, cols in includes_cols.items():
        list_to_db(name, cols, include_values[name])

    '''---Saving changes to the databse and closing the connection---'''
    #I should look into what it best practive and when to commit the sql executions I think I like doing it at the end so that if something goes wrong then just nothing is added and it's no problem
    conn.commit()
    conn.close()

def read_query(cursor, query):
    cursor.execute(query)
    result = cursor.fetchall()
    return result

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
    table = 'data'
    id_index = headers.index("id")
    line_index = headers.index("line_score")
    cols_query = f"SHOW COLUMNS FROM {table};"
    cursor.execute(cols_query)
    cols_list = cursor.fetchall()
    allow_change = {"board_time", "rank", "updated_at"}

    for each in cols_list:
        print(each)
    input("Make sure response is as expected")

    headers = headers + ['version','islatest']    
    headers_set = set(headers)
    for each in cols_list:
        assert each[0] in headers_set
        headers_set.remove(each[0])
    if len(headers_set) > 0:
        print(f"This is not allowed! Headers do not match col names\nheaders:{headers}\nCol names:{cols_list}\nStuck in header_set:{headers_set}")
    assert len(headers_set) == 0
    header_tuple = tuple(headers)

    for row in data:
        '''
        Go through each row of data passed into the function and check to see if there already existing entry in the db for it. 
            If there is no existing entry, then add it right in. 
            Elif there exists entry for incoming id already, check if any values have changed
                if important values have changed - add new row to the db and set old one to not being latest and update version number of the new one
        '''
        '''---Checking to see what already exists in the db---'''
        my_query = f"SELECT {header_tuple} FROM {table} WHERE ISLATEST = TRUE AND ID = {row[id_index]};"
        existing_data = read_query(cursor, my_query)
        for each in existing_data:
            print(each)
        input("Does this look right?")
        write_query = None

        if len(existing_data) == 0:
            '''
            If there is nothing already in the DB matching the data id, insert the values straight into the DB. Since this is the first time this
            data is inserted, adding [0,True] to the end of the row to align with the 'version' and 'islatest' columns
            '''
            new_row = row + [0,True]
            write_query = f"INSERT INTO {table} {header_tuple} VALUES {tuple(new_row)};"
            cursor.execute(write_query)
            add_new_line_score( row[id_index], row[headers.index("projection_type")], row[line_index], cursor )

        elif len(existing_data) > 0:
            '''---Since there should only be one row with a target id that is also the latest, this check to make sure that is enforced---'''
            print(f"Two instances of 'islatest' for same id:\nExisting:{existing_data}\nIncoming:{new_row}")
            print("This is unexpected and should not be possible, plz fix")
            assert len(existing_data) < 2
        
        else:
            '''
            If there is already data for this id in the DB, then go through each column and check to see if anything changed. If something changed that
            is not expected to regularly change, then the 'islatest' version of the existing row must be changed to False and the 'version' and islatest'
            columns of the incoming row must be set to be n+1 and True
            '''
            for i, val in enumerate(row):
                if val != existing_data[i]:
                    '''
                    There are some items that I expect may change over time and don't care to chart them this is the logic for determining if I need to
                    create a new 'version' of a row to input into the db as well as handle the case where the line spread changes wihtout having to create 
                    whole new version
                    '''
                    if i == line_index:
                        '''
                        line_score is expected to change and has it's own table for tracking that, this just updates that 'spread_history' table and
                        raises the flag that the score did change so that way the latest version of the table can reflect that
                        '''
                        add_new_line_score( row[id_index], row[headers.index("projection_type")], val, cursor )
                        update_score = f"UPDATE {table} SET line_score = {val} WHERE islatest = TRUE;"
                        cursor.execute(update_score)

                    elif headers[i] not in allow_change:
                        '''
                        If there is a field that has changed that is not allowed to change without new version, then the old version needs to be changed and the new
                        version needs to be inserted into the db. Just for the sake of simplicity, as soon as one unallowed change is made, we will update the whole row
                        immedeatley rather than try and keep track of all the individual cols that changed.
                        '''
                        if i < line_index and row[line_index] != existing_data[line_index]:
                            '''
                            In the case where a field changes that is not allowed to change before the program gets to the 'line_score' field then any changes in 
                            that would not be reflected in the table that tracks the expected changes of that value. This code block checks if there are any changes 
                            to be made and makes them if needed before the whole line is updated
                            '''
                            add_new_line_score( row[id_index], row[headers.index("projection_type")], existing_data[line_index], cursor )
                        
                        '''---Getting the version number for the new entry to update existing row and add in new row for the latest version---'''
                        new_version = existing_data[headers.index('version')] + 1
                        new_row = row + [new_version, True]
                        update_existing = f"UPDATE {table} SET islatest = FALSE WHERE islatest = TRUE AND id = {row[id_index]};"
                        insert_query = f"INSERT INTO {table} {header_tuple} VALUES {tuple(new_row)};"
                        cursor.execute(update_existing)
                        cursor.execute(insert_query)
                        break

def add_new_line_score( bet_id, bet_type, spread, cursor):
    '''
    Function takes in a new data point and adds it into the spread_history table so that as spreads change over time
    the whole history of how those change can be kept and analyzed
    '''
    col_names = ["bet_id", "bet_type", "spread", "time"]
    vals = [bet_id, bet_type, spread, "NOW()"]
    my_query = f"INSERT INTO spread_history {tuple(col_names)} VALUES {tuple(vals)}"
    cursor.execute(my_query)

