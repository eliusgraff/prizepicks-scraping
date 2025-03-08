import mysql.connector
from mysql.connector import errorcode
import helper
from datetime import datetime, timezone
from parsed_data import parsed_data
from my_logs import log_perf

class one_to_many:
    '''
    Helper class to help with holding data for many to many relationships. To compare and decide what needs to be updated
    '''
    base_id = int
    target_ids = set()
    version = int
    islatest = bool

    def __init__(self, b_id, ver, latest, t_id_set):
        self.base_id = b_id
        self.target_ids = t_id_set
        self.version = ver
        self.islatest = latest

#Rest of mysql reserved words here: https://dev.mysql.com/doc/refman/8.4/en/keywords.html
SQL_RESERVED_WORDS = {
    "type",
    "description",
    "rank",
    "status"
}

PROJECTION_TIME_SERIES = {
    "line_score",
    "trending_count"
}


def remove_mysql_prefix(name_list):
    '''
    Shitty code that I should just do with list comprehension, but this is easier to read for now
    '''
    clean_list = list()
    for col_name in name_list:
        if len(col_name) > 3 and col_name[:3] == "my_":
            clean_list.append(col_name[3:])
        else:
            clean_list.append(col_name)
    return clean_list

def get_cols(table_names):
    '''
    Function takes in a list of table names and returns a dict where the keys are the table names and the values are lists of the columns in those tables
    '''
    conn = create_db_connection()
    cursor = conn.cursor()
    cols_dict = dict()
    if isinstance(table_names, list):
        for table in table_names:
            cursor.execute(f"SHOW COLUMNS FROM {table};")
            cols = cursor.fetchall()
            #Should add logic here to do the sql conversion to remove 'my_' from the column names
            cols_dict[table] = [each[0] for each in cols]
        #very poor way to go through and make sure that all the mysql reserved word column names are obvuscated from rest of program by removeing the 'my_' from the beginning of some col names
        for table in cols_dict:
            cols_dict[table] = remove_mysql_prefix(cols_dict[table])

    elif isinstance(table_names, str):
        cursor.execute(f"SHOW COLUMNS FROM {table_names};")
        cols = cursor.fetchall()
        cols_dict[table_names] = [each[0] for each in cols]
        #very poor way to go through and make sure that all the mysql reserved word column names are obvuscated from rest of program by removeing the 'my_' from the beginning of some col names
        cols_dict[table_names] = remove_mysql_prefix(cols_dict[table_names])

    else:
        raise TypeError(f"table_names must be a list or a str. Got type: {type(table_names)}")
    
    conn.close()

    return cols_dict

def is_equal(newval, oldval):
    '''
    Since types get sticks when parsing with numbers being its or stings as well as bools being represented as 1,0, True, False, and None. Some additional logic is needed to account for
    this to avoid incorrectly detecting inequalities
    '''
    bool_equalities = {
        "None":False,
        "True":True,
        "False":False,
        "0":False,
        "1":True
    }
    '''---This can be adjusted to deside how close numbers have to be to be considered the same---'''
    NUMBER_THRESHOLD = 0.999

    b_new = bool_equalities.get(str(newval))
    b_old = bool_equalities.get(str(oldval))
    if b_new is not None and b_old is not None:
        return b_new == b_old
    
    if isinstance(newval,float) and isinstance(oldval, float):

        return (min(oldval,newval)/max(oldval,newval)) > NUMBER_THRESHOLD

    return newval == oldval

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
    if my_dict.get('un') is None: 
        not_found_list.append('un')

    if my_dict.get('pw') is None: 
        not_found_list.append('pw')

    if my_dict.get('hn') is None: 
        not_found_list.append('hn')

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

def write_to_mysql(data, table_name, cursor):
    
    if len(data) == 0:

        return
    
    insert_query = f"INSERT INTO {table_name} VALUES ({', '.join(['%s']*len(data[0]) )});"
    cursor.executemany(insert_query, data)

def remove_duplicate_row(table_name, id_val, cursor):

    my_query = f"SELECT * FROM {table_name} WHERE ISLATEST = TRUE AND ID = {id_val};"
    rows = read_query(cursor, my_query)
    print(f"First read\n{rows}")
    if len(rows) == 0:

        print(f"Could not find anything for sql query: {my_query}\nThis is unexpected, returning bad status.")
        return False
    
    elif len(rows) == 1:

        print(f"This looks good to me, no problems to fix here. Only got 1 row with: {my_query}")
        return True
    
    to_comp = list(rows[0])
    for each in rows[1:]:

        for i, v in enumerate(each):

            if to_comp[i] != v:
                
                if to_comp[i] == None and v != False:

                    if str(to_comp[i]) != str(v):

                        print(f"Rows not same, not sure how to fix this.")
                        for each in rows: print(each)
                        return False
                
    for i,v in enumerate(to_comp):
        if v == None:
            to_comp[i] = False
    to_comp[-1] = 0

    del_query = f"DELETE FROM {table_name} WHERE ISLATEST = TRUE AND ID = {id_val};"
    insert_query = f"INSERT INTO {table_name} VALUES{tuple(to_comp)};"
    try:

        cursor.execute(del_query)
        cursor.execute(insert_query)

    except mysql.connector.errors.ProgrammingError as E:

        print(del_query)
        print(insert_query)
        raise E
    
    my_query = f"SELECT * FROM {table_name} WHERE ISLATEST = TRUE AND ID = {id_val};"
    rows = read_query(cursor, my_query)
    print(f"After read\n{rows}\n")

    return True

def list_to_db(table, headers, data, cursor):
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

    '''
    Since there is a many-to-many relationship in the 'league' values, this needs a second table to represent this. This code helps
    accomodate this by checking if the table name is in the dict which has list of all the tables which need nonstandard id naming
    '''
    interm_tables = {
        "lfg_ignored_leagues"
    }

    '''
    There are cases where the names used by PrizePicks are either inconsistent or not the same as the names used in the mySQL database. This chunk of code accounts
    for those discrepancies and makes sure that the names are aligned so that the data can be added to the database correctly
    '''
    id_names = {
        "league_data": "league_id",
    }
    id_title = "id"
    if table in id_names:
        print(f"Adjusting id_title")
        id_title = id_names[table]

    id_index = headers.index(id_title)
    cols_query = f"SHOW COLUMNS FROM {table};"
    cursor.execute(cols_query)
    cols_list = cursor.fetchall()
    cols_list = [col[0] for col in cols_list]
    main_list = []

    '''---make sure the cols list looks same as what is expected---'''
    #in future may be able to make sure that as long as all the col names are represented in the list passed to the function, then it can be handled
    #This should probably be it's own function
    for i, header in enumerate(headers):

        if header != cols_list[i]:

            print(cols_list[i])
            print(header)
            print(f"Cols:\t{cols_list}")
            print(f"Headers:\t{headers}")
            raise ValueError("Headers do not match")

    #I think this can be optimized here with all the casting vs what is actually being used
    id_set = set([row[id_index] for row in data])
    id_list = tuple(id_set)
    my_len = len(id_list)
    if my_len == 0:

        print(f"No data to add for {table}. Returning...")
        return
    
    elif len(id_list) == 1:

        '''---There are issues with sending tuples of length 1 as a list into mySQL, this fixes that issue with a bandaid---'''
        id_list = f"({id_list[0]})"

    '''---Loading all latest data from mysql to compare with new data---'''
    my_query = f"SELECT * FROM {table} WHERE ISLATEST = TRUE AND ID IN {id_list};"    
    existing_data = read_query(cursor, my_query)
    
    if table in interm_tables:

        '''
        Our data may contain many-to-many relationships. Represent this, an interm table is used. lfg_ignored_leagues for example is an interm table used to connect the lfg_ignored_leagues to stat type.
        Since a stat types may ignore multiple leagues and one league may be ignored by multiple stat types, this interm table is needed. Both stat_type and league have thie own tables with thier own 
        data in them. This way user can query the dba nd see which leagues are ignored by which stat types and vice versa, although I don't know what the practical use is of that.
        
        When this happens different logic must be used to account for this since it is valid for multiple rows with the same id all to have 'islatest' = True.
        '''
        if table == "lfg_ignored_leagues":

            main_list = interm_to_db(table, data, existing_data, id_index, headers.index('league_num'), cursor)

        else:

            print(f"No parser for this table name: {table}")
            raise NotImplementedError
        
        write_to_mysql(main_list, table, cursor)
        return
    
    '''---Adding all the existing latest data to a dictionary for quick recall---'''
    existing_data_dict = dict()
    for row in existing_data:
        
        row_id = row[id_index]
        '''
        Goes though and checks to make sure there is not multiple rows iwth the same id. This needs to be guarunteed here since I'm 
        not using primary keys for most of these tables
        '''
        if row_id in existing_data_dict:

            print(f"Two instances of id = {row_id} in table {table}")
            print("This is unexpected and should not be possible. Removing one of the duplicates for this, but this is nothing more than a band-aid and RC must be fixed!")
            if remove_duplicate_row(table, row_id, cursor):

                continue

            else:

                print("Could not simply remove duplicate row because both rows were not identical.")
                raise ValueError
            
        existing_data_dict[row_id] = row

    '''---Going through each row of data and checking if it needs to be added or updated---'''
    for row in data:
        row_id = row[id_index]
        if row_id not in existing_data_dict:

            '''---If there is no existing data for this id, then add it in---'''
            main_list.append(row+[0,True])

        else:
            '''---If there is already data for this id, then check to see if anything has changed---'''
            for i, val in enumerate(row):

                if not is_equal(val,existing_data_dict[row_id][i]):
                    update_existing = f"UPDATE {table} SET islatest = FALSE WHERE islatest = TRUE AND id = {row[id_index]};"
                    cursor.execute(update_existing)
                    main_list.append(row+[existing_data_dict[row_id][-2]+1,True])

    '''---Adding all the new data to the database---'''
    try:

        write_to_mysql(main_list, table, cursor)

    except mysql.connector.errors.IntegrityError as E:

        print(f"Headers {headers}\nid_title{id_title}\nid_index{id_index}\n")
        print(main_list)

        raise E

def send_to_sql(parsed_data_obj):
    '''
    Function takes in a parsed_data object and is responsible for sending all that information to mySQL database
    '''
    '''---assert that the argument is correct data structure---'''
    assert isinstance(parsed_data_obj, parsed_data)
    '''---Creating mysql connecrtion and cursor objects so we can set up the transfer---'''
    conn = create_db_connection()
    cursor = conn.cursor()

    '''---Send the values for the 'data' table to mySQL---'''
    #####change this func name to be specific to projection data
    list_to_data_table(parsed_data_obj.data_order, parsed_data_obj.data_values, cursor)

    '''---Send all the 'include' values to database---'''
    if parsed_data_obj.included_tag_orders is not None:
        includes_to_db(parsed_data_obj, cursor)

    '''---Saving changes to the databse and closing the connection---'''
    #I should look into what it best practice and when to commit the sql executions I think I like doing it at the end so that if something goes wrong then just nothing is added and it's no problem
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

@log_perf
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

    '''---Some fields I expect to be datetimes, so if they are given, parse them as datetime---'''
    my_dts={
        "board_time": headers.index("board_time"),
        "end_time": headers.index("end_time"),
        "start_time": headers.index("start_time"),
        "updated_at": headers.index("updated_at")
    }

    insert_list = list()
    change_list = list()
    update_list = list()
    timeseries_values = dict()
    for key in PROJECTION_TIME_SERIES:
        timeseries_values[key] = list()

    table = 'dev_projection'
    table_history = f'{table}_change_history'
    #Can this be done with list comprehension?
    fix_headers = []
    for header in headers:
        if header in SQL_RESERVED_WORDS: fix_headers.append(f"my_{header}")
        else: fix_headers.append(header)
    id_index = headers.index("id")

    '''---Make sure columns are aligned with DB---'''
    cols_query = f"SHOW COLUMNS FROM {table};"
    cursor.execute(cols_query)
    cols_list = cursor.fetchall()
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
    id_list = tuple(values[id_index] for values in data)
    my_len = len(id_list)
    if my_len == 0:
        print(f"No data to add for {table}. Returning...")
        return
    
    elif len(id_list) == 1:

        id_list = f"({id_list[0]})"

    my_query = f"SELECT * FROM {table} WHERE ID IN {id_list};"
    existing_data = read_query(cursor, my_query)
    data_dict = dict()

    #With new database design, I should be able to use the projection id as the primary key for the table and remove this block of code!
    '''---Making sure that the data in the db already does not have double-up of same ids---'''
    for row in existing_data:

        if row[id_index] in existing_data:
            '''
            Since there should only be one row with a target id that is also the latest, this check to make sure that is enforced. Since this should not be possible
            I don't want to spend a lot of time on this, but in the case it does pop up, then this will catch is and whatever is causing it should be patched but if
            nothing else this conflict should be handled logically
            '''
            print(f"Two instances of same id:\nExisting:\n{existing_data}\nIncoming:\n{row}")
            print("This is unexpected and should not be possible, plz fix")
            assert row[id_index] not in existing_data

        data_dict[row[id_index]] = row
    ###End of block I should consider deleting###

    #This can eventually become a request id and then all the info about a specificc request can be saved. For now we will just save it based on time
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)

    for incoming_row in data:
        '''
        Looping through each of the incoming rows of parsed data to check if they need to be inserted into the db or if existing rows need to be updated
        '''
        row_id = incoming_row[id_index]
        #maybe this can be optimized to be done in line with the other loop
        for i in my_dts.values():
            if isinstance(incoming_row[i], str):
                my_dt = datetime.fromisoformat(incoming_row[i])
                utc_dt = my_dt.astimezone(timezone.utc)
                incoming_row[i] = utc_dt.replace(tzinfo=None)
        '''
        Go through each row of data passed into the function and check to see if there already existing entry in the db for it. 
            If there is no existing entry, then add it right in. 
            Elif there exists entry for incoming id already, check if any values have changed
                if important values have changed - add new row to the db and set old one to not being latest and update version number of the new one
        '''
        #If projection is not already in the DB, then just add that row and go on to the next one!
        if data_dict.get(row_id) is None:
            '''---If there is nothing already in the DB matching the data id, insert the values straight into the DB---'''
            insert_list.append(incoming_row)
            
        #If the projection is already in the DB, then check to see if anything has changed. If something is changed then it needs to be logged in the 'projection_change_history' table
        else:
            existing_row = data_dict[row_id]
            changed = False
            latest_row = list(existing_row)
            for i, val in enumerate(incoming_row):
                if existing_row[i] != val:
                    print(f"Existing val {existing_row[i]} != {val} from incoming. Column: {fix_headers[i]}")
                    changed = True
                    change_list.append([row_id, fix_headers[i], existing_row[i], current_time])
                    latest_row[i] = val
            if changed:
                update_list.append(latest_row)

        for timeseries in timeseries_values:
            ts_index = fix_headers.index(timeseries)
            if  ts_index != -1:
                timeseries_values[timeseries].append([row_id, incoming_row[ts_index], current_time])
    
    exit("PICK BACK UP HERE, NEED TO WRITE CODE TO MAKE SURE THE TS DATA GETS INTOT EH DB")
    add_new_lines(insert_list, change_list, update_list, table, table_history, cursor)
            
def add_new_lines(my_data_list, data_history_list, update_list, table_name, table_history_name, cursor):
    
    #Can I turn this into some kind of string comprehension?
    if len(my_data_list) > 0:
        data_alias_list = str()
        for _ in range(len(my_data_list[0])):
            data_alias_list += "%s,"
        my_data_write_query = f"INSERT INTO {table_name} VALUES ({data_alias_list[:-1]});"

    if len(data_history_list) > 0:
        history_alias_list = str()
        for _ in range(len(data_history_list[0])):
            history_alias_list += "%s,"
        history_write_query = f"INSERT INTO {table_history_name} VALUES({history_alias_list[:-1]});"

    if len(update_list) > 0:
        replace_alias_string = str()
        for _ in range(len(update_list[0])):
            replace_alias_string += "%s,"
        replace_query = f"REPLACE INTO {table_name} VALUES ({replace_alias_string[:-1]});"

    if len(my_data_list) > 0:
        try:
            cursor.executemany(my_data_write_query, my_data_list)
            print(f"Added {len(my_data_list)} rows to {table_name}")
        except mysql.connector.Error as sql_err:
            print(f"ERROR MESSAGE: {sql_err.msg}")
            print(history_write_query)
            for row in data_history_list:
                print(row)
            
    if len(update_list) > 0:
        try:
            cursor.executemany(replace_query, update_list)
            print(f"Updated {len(update_list)} rows in {table_name}")
        except mysql.connector.Error as sql_err:
            print(f"ERROR MESSAGE: {sql_err.msg}")
            print(replace_query)
            for row in update_list:
                print(row)

    if len(data_history_list) > 0:
        try:
            cursor.executemany(history_write_query, data_history_list)
            print(f"Added {len(data_history_list)} rows to {table_history_name}")
        except mysql.connector.Error as sql_err:
            print(f"ERROR MESSAGE: {sql_err.msg}")
            print(history_write_query)
            for row in data_history_list:
                print(row)

def sqlerr_1256_recovery(rows_list, table_name, cursor):
    print(f"Error 1265 ocurred during mysql insert of {table_name} values. Attempting to Recover...")
    recovery = add_by_row(rows_list, cursor, table_name)
    if recovery[0] == 1:
        print("1265 recovery failed")
    elif recovery[0] > 1:
        print("Partial recovery. Following rows not added:")
        for row in recovery[1]:
            print(row)
    elif recovery[0] == 0:
        print("All rows added successfully")

def add_by_row(my_data_list, cursor, table_name):
    #Function to go through line by line of my bulk query and try to see how many of them can be added when I go one at a time
    #This will also keep track of which rows will fail to be added
    problem_rows = list()
    for row in my_data_list:
        my_query = f"INSERT INTO {table_name} VALUES {tuple(row)};"
        try:
            cursor.execute(my_query)
        except mysql.connector.Error as sql_err:
            print(f"During recovery of prior error, another error occurred. ErrNum: {sql_err.errno}")
            print(f"Query: {my_query}")
            print(sql_err.msg)
            problem_rows.append(row)
    
    errcount = len(problem_rows)
    if errcount == len(my_data_list):
        print("Nothing was able to be recovered.")
        return (1, problem_rows)
    
    elif errcount > 0:
        print(f"Some rows were added successfully, but some were not. ErrCount: {errcount}")
        return (2, problem_rows)
        
    elif errcount == 0:
        print(f"All rows added successfully")
        return (0)
    
    return (3, problem_rows)

def add_new_line_score( bet_id, bet_type, spread, cursor):
    '''
    Function takes in a new data point and adds it into the spread_history table so that as spreads change over time
    the whole history of how those change can be kept and analyzed
    '''
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

def create_relationships_dict(data, i_base, i_target):
    '''
    Helper function to take a list of lists and turn them into a dictionary where the keys are the base ids and the values are one_to_many objects
    which represent all the relationships the base object has with the target objects
    '''
    to_return = dict()
    for base_row in data:

        b_id = str(base_row[i_base])
        t_id = base_row[i_target]
        if b_id in to_return:

            to_return[b_id].target_ids.add(t_id)

        else:

            to_return[b_id] = one_to_many(b_id, base_row[-2], base_row[-1], set({t_id}))

    return to_return

def interm_to_db(table, new_data, existing_data, base_id_index, target_id_index, cursor):
    '''
    lfg_ignored_leagues is a table which is used to account for a many-to-many relationship. One stat_type may have many lfg_ignored_leagues. Although I don't know what
    they do or why they are needed, I decide the data must be saved so it should be accounted for. There is nothing unique about this fucntion for the lfg_ignored_leagues so
    it may be used in future for other cases where a many-to-one relationship is needed.

    I will use the term 'base' to refer to the object which is in the 'id' part of the table and is the object which may is having a relationship with another object
    I will use the term 'target' to refer to the object which is being refered to as one of the many relationships the 'base' object may be having.

    variables are:
        table - a str object with the name of the table the data will be inserted into

        headers - a list of strings which are the names of the columns in the target table in the order they appear in the mySQL database

        new_data - a list of lists where each sub-list is the data for a row to be added to the target table

        existing_data - a list of all the rows tagged 'latest' in the target table    
    
        id_set - a set with all the ids of the new base objects that is to be added to the target table

        id_index - an int which is the index of the 'id' column in the headers list. This is the id of the base object

        val_index - an int which is the index of the column which holds the values for the id of the target object

        cursor - a cursor object which is used to interact with the mySQL database
    '''
    '''
    this will be a dict of sets to make sure the same values is not double-added for the same id
    keys will be the values in the 'id' column and the values will be sets of the values already added to the list to be added to the db
    '''
    existing_relationships = create_relationships_dict(existing_data, base_id_index, target_id_index)
    new_relationships = create_relationships_dict(new_data, base_id_index, target_id_index)

    '''print("\nExisting:")
    for k1,v1 in existing_relationships.items():
        print(f"{k1}\t{v1.target_ids}")
    
    print("\nNew:")
    for k2,v2 in new_relationships.items():
        print(f"{k2}\t{v2.target_ids}")'''
    
    '''---List to hold all the new data to be added to the db---'''
    new_data_list = []


    for base_id in new_relationships:

        new_targets = new_relationships[base_id].target_ids

        '''---In case where base_id does not already exist in the db, need to account for it---'''
        existing_targets = existing_relationships.get(base_id)
        if existing_targets is not None:

            existing_targets = existing_targets.target_ids

        else:

            existing_targets = {}

        if base_id in existing_relationships:
        
            if new_targets != existing_targets:
            
                '''---If values for the base_id have changed, then need to add in all the new targets---'''
                '''---sql query to update all the old data to not being latest---'''
                update_existing = f"UPDATE {table} SET islatest = FALSE WHERE islatest = TRUE AND id = {base_id};"
                cursor.execute(update_existing)
                for t_id in new_targets:

                    '''---Adding in all the new data for this base_id---'''
                    new_data_list.append([base_id, t_id, existing_relationships[base_id].version+1, True])
            
        else:

            for t_id in new_targets:

                '''---Adding in all the new data for this base_id---'''
                new_data_list.append([base_id, t_id, 0, True])

    return new_data_list       

@log_perf
def includes_to_db(parsed_data_obj, cursor):
    '''
    Function takes a parsed_data object and turns all the includes data from that object into mysql
    '''
    for name, cols in parsed_data_obj.included_tag_orders.items():
        list_to_db(name, cols, parsed_data_obj.included_tag_values[name], cursor)
