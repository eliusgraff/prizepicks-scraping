import mysql.connector
import helper
from datetime import datetime, timezone, timedelta
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

class prizepicks_db:

    SQL_RESERVED_WORDS = {
        "type",
        "description",
        "rank",
        "status",
        "time"
    }
    PROJECTION_TIME_SERIES = {
        "line_score",
        "trending_count",
        "rank"
    }
    INCLUDED_TIME_SERIES = {
        'team':[],
        'new_player':[],
        'stat_type':[],
        'league':[],
        'game':[],
        'projection_type':[]
    }
    ENDPOINT_ID = {
        'projection':1,
        'game':2
    }
    _MY_TABLES = [
        'projection',
        'team',
        'new_player',
        'stat_type',
        'league',
        'game',
        'projection_type'
    ]
    _sql_conn = None
    _sql_cursor = None
    _sql_buffered_cursor = None
    _external_data_names = dict()
    _is_cleaning = False

    def __init__(self):
        self._sql_conn = self._create_db_connection()
        self._sql_cursor = self._sql_conn.cursor()
        self._sql_buffered_cursor = self._sql_conn.cursor(buffered = True)
        self._set_external_data_names()
        self._is_cleaning = False

    def _set_external_data_names(self):
        #Run to concisely get all the names of all the data names for a given data type parsed from the prizepicks api
        #This function runs through all the tables of the db, which are hard-coded into the _MY_TABLES member variale
        #And runs through all the tables in the db which could contain data about them and stores it in a dict which
        #Is stored as a member variable

        for table_name in self._MY_TABLES:
            
            '''Is there a way to combine these two read queries?'''
            #Get the info about all the columns of the target table, and just pick out the names
            self._sql_cursor.execute(f"SHOW COLUMNS FROM {table_name};")
            cols_list = self._sql_cursor.fetchall()
            table_cols = [each[0] for each in cols_list]
            #Some names are modifies to avoid mySQL reserved words, so this undoes that modification
            data_names = self._remove_mysql_prefix(table_cols)

            #timeseries data is stored in a special table for values expected to change often, so this 
            #gets the names of those columns
            '''---All the timeseries data should be stored in a dict somewhere and we should check against that to decide if we need to pull in timeseries data or not---'''
            ts_list = self.read_query(f"SELECT DISTINCT name FROM {table_name}_timeseries;")
            ts_names = [each[0] for each in ts_list]

            #Add the names of both the target table and the timeseries tables to save
            self._external_data_names[table_name] = data_names + ts_names

    def get_data_to_parse(self):
        #Don't want caller messing with the member variable directly, so this fuctions allows a caller to a
        #copy of those names
        return self._external_data_names.copy()

    def _create_db_connection(self, db_name="prizepicks", host_name= None, user_name = None, user_password = None):
        
        #Function to create a connection to the local mySQL database. Credentials can be passed in or they default to None and if host_name is left as None
        #then the root_login() function will get the root login data form a file somewhere on the computer
        if host_name is None:
            creds = self._root_login()
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
    
    #Long term, this should not need to be root user
    def _root_login(self):
        
        #This function is used to retrive the username, host name, and password to gain access to the local
        #mySQL database. requires that the user have a file called 'secrets.txt' where 3 of the lines in it are:
        #mysql_un=username
        #mysql_pw=password
        #mysql_hn=hostname
        
        #So, to access this, that file must be setup beforehand and then this function will work properly as it
        #is simply reading those 3 items from the file. It muse have *accurate* user info of the 3
        #fields above to get into the SQL DB
        
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

    def send_to_sql(self, parsed_data_obj, scrape_id):
        #Function called by app manager to send the parsed data to the local mySQL database
        
        assert isinstance(parsed_data_obj, parsed_data)

        #Sends values parsed into the projection table
        self._send_to_projection_table(parsed_data_obj.data_order, parsed_data_obj.data_values, scrape_id)
        self._send_included_data(parsed_data_obj.included_tag_values, scrape_id)
        
        #Commits changes made during above functions
        self._sql_conn.commit()
        return True
    
    def _create_col_ordering(self, headers, table): 
        #Function takes in the headers of the incoming data and maps them to the order which they appear in the mysql table 

        mysql_cols = list()
        mysql_map = list()
        dt_indexes = list()
        translated_headers = list()

        self._sql_cursor.execute(f"SHOW COLUMNS FROM {table};")
        cols_list = self._sql_cursor.fetchall()
        mysql_cols = [each[0] for each in cols_list]

        #This list will be used to map which index of the incoming headers corresponds to the index of the mysql columns
        mysql_map = [None]*len(mysql_cols)

        #Some cols are saved as datetimes. Keeping track of which cols in table are dts is important when checking for equality later
        for i, v in enumerate(cols_list):
            if v[1] == "datetime":
                dt_indexes.append(i)

        #Take the incoming header list and make sure all names are translated to be mysql-compatible
        for i,header in enumerate(headers):
            if header in self.SQL_RESERVED_WORDS: 
                header = f"my_{header}"
            translated_headers.append(header)
            try:
                col_num = mysql_cols.index(header)
                mysql_map[col_num] = i
            except ValueError:
                continue
        
        return (mysql_map, dt_indexes, translated_headers)

    def _get_existing_data(self, data, table, id_index):
        
        #Pull in all incoming row ids so db can be queried for existing rows
        id_list = tuple(values[id_index] for values in data)
        my_len = len(id_list)
        if my_len == 0:
            print(f"No data to add for {table}. Returning empty list.")
            return []
        '''elif len(id_list) == 1:
            id_list = f"({id_list[0]})"
        return self.read_query(f"SELECT * FROM {table} WHERE ID IN {id_list};")'''
    
    
        #build SQL query to get existing data from the db for the ids to compare with
        base_sql = f"SELECT * FROM {table} "
        where_clause = "" if id_list is None else f"WHERE ID in ({','.join([str(data_id) for data_id in id_list])})"
        sql_query = base_sql + where_clause
        return self.read_query(sql_query)

    def _add_timeseries(self, headers, incoming_row, row_id, scrape_id):
        #Function to create timeseries entires for each entry in the incoming row if it exists
        #If timeseries data does exist in the incoming row, then the row which must be added to the
        #mysql is returned

        timeseries_list = list()

        for timeseries in self.PROJECTION_TIME_SERIES:
            #Not all timeseries data is always guarunteed, so this check to make sure that the timeseries data actually exists before trying to add anything. 
            #If it does not exist then just skip it, that's ok.
            try:
                ts_index = headers.index(timeseries)
            except ValueError:
                input(f"Cant find {timeseries} in headers list. Is that ok?")
                continue
            if  incoming_row[ts_index] is not None:
                timeseries_list.append([row_id, timeseries, incoming_row[ts_index], scrape_id])

        return timeseries_list

    def _create_changes(self, num_cols, mapping, translated_headers, existing_row, temp_row, row_id, scrape_id, change_list):
        #This fucntion goes through each of the items of two existing and incoming data rows and compares them. If any differences then
        #They are added to the change list in the formate I want to store in the db and returned to the caller
        change_list = list()
        for i in range(num_cols):
            #If a value has changed, then add it to the change list and mark that a change has been made. This change will be logged in the appropriate change_history table
            if existing_row[i] != temp_row[i]:
                change_list.append([row_id, translated_headers[mapping[i]], existing_row[i], scrape_id])
        
        return change_list
    
    @log_perf
    def _send_to_projection_table( self, headers, data, scrape_id):
        #Function which will send passed in data into the 'data' table of the local mySQL database
        #Argumetns are:
        #    headers - a list of names of the columns of the target table in order for how they apprear in the data
         
        #    data - a list of lists where each sub-list is the list of data that is going into the database. The data point at each index is
        #        described by that same index of 'headers' list
        #        ex: [
        #            ['172250', 'Jude Bellingham', 'Midfielder', 'https://static.prizepicks.com/images/players/soccer/e83ula4wockmc2xid7185kcq2.webp', 'Jude Bellingham', False, 82, '3372'],
        #            ['197873', 'Jyllissa Harris', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Houston_Dash.webp', 'Jyllissa Harris', False, 82, '4156'],
        #            ['171076', 'JÃ¸rgen Strand Larsen', 'Attacker', 'https://static.prizepicks.com/images/manual/JÃ¸rgen Strand Larsen.png', 'JÃ¸rgen Strand Larsen', False, 82, '3356'],
        #            ['215896', 'Courtney Petersen', 'Defender', 'https://static.prizepicks.com/images/teams/NWSL/Racing_Louisville.webp', 'Courtney Petersen', False, 82, '4160']
        #            ]
        #    
        #    scrape_id - the id of the scrape that this data is coming from.
    
        insert_list = list()
        change_list = list()
        update_list = list()
        timeseries_list = list()
        mapping = list()
        dts = list()
        translated_headers = list()
        table = 'projection'
        id_index = headers.index("id")

        #Pull into memory any data which may already be in the db to compare/update against
        existing_data = self._get_existing_data(data, table, id_index)

        #Call function to map the incoming data to the order that the db requires
        mapping, dts, translated_headers = self._create_col_ordering(headers, table)
        
        #Create dictionary where the key is the row id and the value is the row of existing dat in the mysql db. This will be used to 
        #check for if any rows need to be updated
        data_dict = dict()
        for row in existing_data:
            data_dict[row[id_index]] = row

        #This loops through each of the incoming data rows to determine what changes need to be made in the db. Any changes that need to be made, the necessary 
        #data to do that is added to the insert, update, or timeseries list as apropriate. These lists are then executed in batches into the db to make it fast
        for incoming_row in data:
            
            #Map the data from the incoming row into a temp row so that it can be compared against whatever is already in the db in the correct order/format
            temp_row = list()
            row_id = incoming_row[id_index]
            num_cols = len(mapping)
            
            #Adds incoming data to the temp row in the correct order
            for i in mapping:
                if i is not None:
                    temp_row.append(incoming_row[i])
                else:
                    temp_row.append(None)

            #Converts any datetimes to datetime objects of the same format so their comparison is valid
            for i in dts:
                if isinstance(temp_row[i], str):
                    my_dt = datetime.fromisoformat(temp_row[i])
                    utc_dt = my_dt.astimezone(timezone.utc)
                    temp_row[i] = utc_dt.replace(tzinfo=None)

            #------Beginning comparison and adding necessary data to correct lists to make updates------

            #If there is nothing already in the DB matching the data id, insert the values straight into the DB
            existing_row = data_dict.get(row_id)
            if existing_row is None:
                insert_list.append(temp_row)
                
            #If the projection is already in the DB, then check to see if anything has changed. If a value has changed, then log it in the 
            #'projection_change_history' table and update the 'projection' table to reflect the new values
            else:
                #Call function to check equality of the incoming vs existing row and return list of any changes
                changes = self._create_changes(num_cols, mapping, translated_headers, existing_row, temp_row, row_id, scrape_id, change_list)

                #If changes are made then add that to the correct data structures to be put in the right places
                if len(changes) > 0:
                    change_list += changes
                    update_list.append(temp_row)

            #Call function to add any timeseries data to the timeseries list if it exists in the incoming row
            timeseries_list += self._add_timeseries(headers, incoming_row, row_id, scrape_id)

        
        #Function which makes batch requests for the 3 tables to be updated
        self._add_new_lines(insert_list, change_list, update_list, table, timeseries_list)
            
    def _add_new_lines(self, my_data_list, data_history_list, update_list, table_name, timeseries_list, row_id_index = 1):
        #Function takes various lists of data all of which needs to be updated in the db, and updates the db with that data

        #Goes through and updates the rows in the target table which have had values changed
        if len(update_list) > 0:
            #To update the existing projection rows in the db, they are first deleted and then replaced by the updated rows

            #Goes through the update list and grabs the ids of the rows that need to be deleted
            delete_ids = [row[row_id_index] for row in update_list]
            
            #add the updated row to my_data_list so that the latest data is inserted into the db
            my_data_list += update_list

            #build SQL query to delete the rows with old data in them
            base_sql = f"DELETE FROM {table_name} "
            where_clause = "" if delete_ids is None else f"WHERE ID in ({','.join([str(x) for x in delete_ids])})"
            delete_query = base_sql + where_clause

            try:
                self._sql_cursor.execute(delete_query)
            except mysql.connector.Error as sql_err:
                self._report_sql_error(sql_err, delete_query, update_list)

        #Goes through and add in all the latest row data to the target table
        if len(my_data_list) > 0:
            #All of the data which needs to be inserted into the projection table is manged here

            #Create the SQL query to format and insert the data into the db
            data_alias_list = str()
            for _ in range(len(my_data_list[0])):
                data_alias_list += "%s,"
            my_data_write_query = f"INSERT INTO {table_name} VALUES ({data_alias_list[:-1]});"
            
            #Execute the SQL query created above
            try:
                self._sql_cursor.executemany(my_data_write_query, my_data_list)
                print(f"Added {len(my_data_list)} rows to {table_name}")
            except mysql.connector.Error as sql_err:
                self._report_sql_error(sql_err, my_data_write_query, my_data_list)

        #All of the changes to the projections are tracked. This block adds the changed attributes and values into the table tracking the history of the changes
        if len(data_history_list) > 0:
            
            #Create the SQL query to format and insert the data into the db
            history_alias_list = str()
            for _ in range(len(data_history_list[0])):
                history_alias_list += "%s,"
            history_write_query = f"INSERT INTO {table_name}_change_history VALUES({history_alias_list[:-1]});"
            
            #Execute the SQL query created above
            try:
                self._sql_cursor.executemany(history_write_query, data_history_list)
                print(f"Added {len(data_history_list)} rows to {table_name}_change_history")
            except mysql.connector.Error as sql_err:
                self._report_sql_error(sql_err, history_write_query, data_history_list)

        #Some of the projection attributes are expected to change all the time. Rather than keep changing the whole projection record every time, these
        #values are tracked/stored in this timeseries table and the latest values are alwyas inserted in here. This does not check if that value has changed
        #at all, it just adds it no matter what
        if len(timeseries_list) > 0:

            #Create the SQL query to format and insert the data into the db
            ts_alias_string = str()
            for _ in range(len(timeseries_list[0])):
                ts_alias_string += "%s,"
            ts_write_query = f"INSERT INTO {table_name}_timeseries VALUES ({ts_alias_string[:-1]});"

            #Execute the SQL query created above
            try:
                self._sql_cursor.executemany(ts_write_query, timeseries_list)
                print(f"Added {len(timeseries_list)} rows to {table_name}_timeseries")
            except mysql.connector.Error as sql_err:
                self._report_sql_error(sql_err, ts_write_query, timeseries_list)

        return True
    
    def _report_sql_error(self, error, query, rows):
        print(f"Query: {query}")
        print(f"ERROR MESSAGE: {error.msg}")
        for row in rows:
            print(row)
        raise Exception("SQL Error found, please review")

    def read_query(self, query):
        
        try:
            self._sql_cursor.execute(query)
            result = self._sql_cursor.fetchall()
            return result
        
        except Exception as E:
            print(f"Attempting query: {query}\nBut error occured")
            raise E

    def _remove_mysql_prefix(self, name_list):
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

    def post_scrape_error(self, scrape_id, error):
        update_existing = f"UPDATE scrape_data SET my_status = {error} WHERE id = {scrape_id};"
        self._sql_cursor.execute(update_existing)
        self._sql_conn.commit()

    def create_scrape_id( self, status, leaguenum, timestamp):
        #function which takes in the required data to define a scrape entry in the db.
        #this function add that the db and returns the id of that new entry

        self._sql_cursor.execute(f"INSERT INTO scrape_data (id, my_status, league_num, store_time) VALUES ( NULL, {status},{leaguenum}, '{timestamp}');")
        self._sql_conn.commit()
        scrape_id = self.read_query('SELECT LAST_INSERT_ID();')[0][0]
        return scrape_id
    
    def _send_included_data(self, included_data_dict, scrape_id):
        #Function to send the included data to the db. Since included data spans multiple types and tables, this
        #needs to go through each of the items in the included_data_dict and put the data into the correct table.
        #Each key of the dictionary is the table name that the data is going into, and the values are a single 
        #list of dicts where each dict key is the column name and the value is the value for that column in a given 
        #row.
        for table, data in included_data_dict.items():
            #Loop through each of the tables in the included_data_dict and send the data to the db
            insert_list = list()
            change_list = list()
            update_list = list()
            timeseries_list = list()
            dt_indexes = list()
            col_order = list()

            #get order of columns for the given table and keep track of any datetimes (they need special handling)
            self._sql_cursor.execute(f"SHOW COLUMNS FROM {table};")
            col_info = self._sql_cursor.fetchall()
            for i, col in enumerate(col_info):
                col_order.append(col[0])
                if col[1] == "datetime":
                    dt_indexes.append(i)

            id_index = col_order.index('id') #finding this just in case it changes in the future, it should always be at [0] though            

            #pull in existing data for the db into a dict to compare against and see if any changes need to be made to the db
            incoming_ids = [row['id'] for row in data]
            '''if len(incoming_ids) == 1:
                incoming_ids = f"({incoming_ids[0]})"
            else:
                incoming_ids = tuple(incoming_ids)
            existing_data = self.read_query(f"SELECT * FROM {table} WHERE id IN {incoming_ids};")'''

            #build SQL query to delete the rows with old data in them
            base_sql = f"DELETE FROM {table} "
            where_clause = "" if incoming_ids is None else f"WHERE ID in ({','.join([str(x) for x in incoming_ids])})"
            sql_query = base_sql + where_clause
            existing_data = self.read_query(sql_query)
            
            existing_dict = dict()
            for row in existing_data:
                existing_dict[row[id_index]] = row

            #Go through each of the rows in the incoming data and check to see if any changes need to be made
            for incoming_data in data:

                #turn the dict into a list of values in the correct order to be intput to the db
                row_list = [incoming_data[col_name] for col_name in col_order]
                row_list[id_index] = int(row_list[id_index])

                #Convert any datetimes to datetime objects of the same format so their comparison is valid
                for i in dt_indexes:
                    if isinstance(row_list[i], str):
                        my_dt = datetime.fromisoformat(row_list[i])
                        utc_dt = my_dt.astimezone(timezone.utc)
                        row_list[i] = utc_dt.replace(tzinfo=None)

                existing_row = existing_dict.get(row_list[id_index])

                #If the row is new, then it can be added straight into the db insert list
                if existing_row is None:
                    insert_list.append(row_list)
                
                #If row is already in db, then check to see if any changes need to be made
                else:
                    change = False

                    #make any necessary entries to the correlary change_history table
                    for i in range(len(col_order)):
                        if row_list[i] != existing_row[i]:
                            if str(row_list[i]) != str(existing_row[i]):
                                change = True
                                change_list.append([incoming_data['id'], col_order[i], existing_row[i], scrape_id])
                    
                    #Adding the new row to the update list so the old data can be overwritten with the new data for this row
                    if change:
                        update_list.append(row_list)

                #insert timeseries data into correlary timeseries table
                for ts_name in self.INCLUDED_TIME_SERIES[table]:
                    if incoming_data[ts_name] is not None:
                        timeseries_list.append([incoming_data['id'], ts_name, incoming_data[ts_name], scrape_id])   

            self._add_new_lines(insert_list, change_list, update_list, table, timeseries_list, id_index)

    #A way for a caller to check if db cleaning is ongoing
    def is_cleaning(self):
        return self._is_cleaning

    #How caller can manually stop cleaning process of the db
    def stop_clean(self):
        self._is_cleaning = False

    def _build_dict(self, lgnm, nums, start):
        print("Building validation dict")
        id_list = self.read_query(f"SELECT id FROM scrape_data WHERE league_num = {lgnm} AND my_status = 1 AND is_cleaned = 0 AND id > {start} ORDER BY store_time ASC;")
        pre_dict = dict()
        print("\tGetting parse data from the DB")
        for i in range(nums):

            parse_data = self.read_query(f"SELECT * FROM projection_timeseries WHERE parsenum = {id_list[i][0]}")
            for row in parse_data:

                kn = f"{row[0]}_{row[1]}"
                temp_series = pre_dict.get(kn)
                if temp_series is None:
                    pre_dict[kn] = [row[2]]
                else:
                    '''---To make code back to the way it was, remove this if/else satetmtn'''
                    temp_series.append(row[2])

        return pre_dict

    #Function to standardize creation of keys for dict in cleaning db
    def _create_keyword(self, row_data):
        assert len(row_data) > 2
        return f"{row_data[0]}_{row_data[1]}"

    def clean_db(self, leaguenum = None, timer = None, num_ids = None, start_id = None):
        #Function to facilitate cleaning of redundant data in the timeseries tables. Since these data points are added no matter what after parsing, 
        #there is a lot of times where data is stored when it doesnt need to because nothing is changing, so this function is meant to be run 
        #periodically to reduce bloat in the timeseries tables of the database.

        #Since this could eventually become a very time-consuming function, there are a few ways that the caller can bound the function:
        #   Calling the stop_clean() function will set a flag that stops the cleaning loop at the beginning of the next iteration
        #   The 'timer' arguement will limit the function to run only a specificed integer number of 'wall time' seconds have passed
        #   The 'num_ids' argument will limit the function to limit the number of parsenums that are cleaned

        #Define a function to create keywords for the ts_dict, this way in the future if I need to change this logic, I can just apply here and it 
        #will change for everwhere
        
        if leaguenum is None and start_id is None and num_ids is None:
            input("Using default values for dev, if not ok then exit rn!")
            leaguenum = 7
            start_id = 341
            num_ids = 30

        #########Validating arguments############

        #If there is neither a leaguenum nor start_id then the function doesnt know where to look/start
        if leaguenum is None and start_id is None:
            print("Not enough arguments for the function, need either leaguenum or start_id at least!")
            return 0, "000"

        #Validate leaguenum is valid
        if leaguenum is not None:

            valid = False
            existing_leaguenums = self.read_query(f"SELECT DISTINCT league_num FROM scrape_data WHERE my_status = 1;")
            for num in existing_leaguenums:
                if leaguenum == num[0]:
                    valid = True
                    break
            if not valid:
                print(f"ex lgs:\n{existing_leaguenums}")
                print(f"001 - invalid leaguenum: {leaguenum}")
                return 0, "001"

        #Validate start_id and confrim it does not conflict with leaguenum passed in 
        if start_id is not None:
            
            if isinstance(start_id,int) is False:
                print(f"Start_id = {start_id}")
                print("002 - Start_id must be an int")
                return 0, "002"
            
            temp_id = self.read_query(f"SELECT league_num FROM scrape_data WHERE id = {start_id};")

            if len(temp_id) == 0:
                print(f"022 - Start data has no entries in the db: {start_id}")
                return 0, "022"
            
            temp_id = temp_id[0][0]

            if leaguenum is None:
                print("Inferred leaguenum from start_id")
                leaguenum = temp_id

            elif leaguenum != temp_id:
                print(f"{leaguenum}\t{temp_id}")
                print("012 - Leaguenum and start_id are for different leagues")
                return 0, "012"
            
        #If no start id is given to the function then go into the DB and find the oldest uncleaned parse for the given leaguenum
        else:
            temp_id = self.read_query(f"SELECT id FROM scrape_data WHERE league_num = {leaguenum} AND is_cleaned = 0 AND my_status = 1 ORDER BY id ASC LIMIT 1;")
            if len(temp_id) == 0:
                print(f"ids = {temp_id}")
                print("022 - Cannot find parsenum to start cleaning with")
                return 0, "022"
            
            #set start id to the correct one based on this query
            start_id = temp_id[0][0]
        
        #Validate num_ids is expected
        if (num_ids is not None) and (isinstance(num_ids,int) is False or num_ids <= 0) :
            print(f"003 - Num_ids must be an int >= 1: {num_ids}")
            return 0, "003"

        ###############Setting up variables for controling how long the function goes for############

        self._is_cleaning = True

        if timer is not None:
            if isinstance(timer,int) is False:
                '''---Post some error for this?---'''
                print("Value for timer is invalid, must be an int or None")
                return 0, "004"
            timer = datetime.now() + timedelta(seconds=timer)
        else:
            timer = datetime.max

        ############Fill up ts_dict with what the last values were for each projection in the start_id###########

        #get all the projection ids within the initial scope of the cleaning
        ids = self.read_query(f"SELECT DISTINCT projection_id FROM projection_timeseries WHERE parsenum = {start_id};")

        if len(ids) == 0:
            print("Warning - there are no entries for this parsenum. May yield unexpected results...")
            print("Need to add a way to recover from this in the case there is truly data in the db from prior")
            all_ts = []

        #Pull in all the data from the DB for the interested timeseries

        else:
            all_ts = self.read_query(f"""
            SELECT * 
            FROM projection_timeseries 
            WHERE parsenum < {start_id} 
            AND projection_id in ({','.join([str(proj_id[0]) for proj_id in ids])}) 
            ORDER BY parsenum DESC;
            """)

        #create dict to see what the latest value for a given projection is
        '''
        Once dev is complete, I need to add a way to track cases where the projection is not updated for a long time. If the number of scrapes is long
        enough, this dict could get really big and be storing a bunch of data that will never be used/checked again. Either a paralell dict or another
        value in the stored data to count the last parse this projection was seen should do it, but since each entry in the dict is relativley small
        I think this is not a top concern right now
        '''
        ts_dict = dict()
        for data_point in all_ts:
            kw = self._create_keyword(data_point)
            if kw not in ts_dict:
                ts_dict[kw] = data_point
        
        for k,v in list(ts_dict.items())[:min(len(ts_dict),25)]:
            print(f"{k}\t{v[2]}")
        
        print("Stopping before the big loop")
        return

        ##############create list of all the parsenums that I need to check for timeseries data in#############
        prsenm_qury = f"SELECT DISTINCT parsenum FROM scrape_data WHERE id >= {start_id} and league_num = {leaguenum} ORDER BY parsenum ASC"
        add_lmt = ";" if num_ids is None else f"LIMIT {num_ids};"
        parsenums = self.read_query(prsenm_qury+add_lmt)


        #############Loop through each of the parsenums and check if any of the entries need to be removed#############
        for i, parsenum in enumerate(parsenums):
            
            #############Check to see if external caller requested to stop the loop or if allowed time has expired#############
            if self._is_cleaning is False:
                print("Someone asked the loop to stop, exiting...")
                return i, parsenum
            if datetime.now() > timer:
                print("Timer has expired, exiting loop")
                return i, parsenum

            ###########Go through each of the data points in the parsenum and check to see if they are redundant#############
            #create list to store all the data to delete and pull all timeseries data for the current parse
            delete_info = []
            parse_data = self.read_query(f"SELECT * FROM projection_timeseries WHERE parsenum = {parsenum}")

            #loop through all the data points from a given parsenum and check if they need to be deleted or not
            for data_point in parse_data:
                kw = self._create_keyword(data_point)
                ex_data = ts_dict.get(kw)
                #if there is nothing in the dict already, then it cant be duplicate and can safely be added, nothing else to do
                if ex_data is None:
                    ts_dict[kw] = data_point
                #if the existing data is already in the dict then the new data point can safely be deleted as redundant
                elif ts_dict[kw][2] == data_point[2]:
                    delete_info.append(data_point)
                #anything else means the data point has changed, so the dict needs to be updated with the new value
                else:
                    ts_dict[kw] = data_point

            #############Go through all the info marked as redundant and delete it#############
            #This batch size is not scientific, I just picked one that seems to work. I'm not sure what the limitations are of this. Something to 
            #investigate in the future to optimize.
            print(f"Deleting {len(delete_info)} entries")
            batch_size = 50
            delete_query = ""
            if len(delete_info) > 0:
                print("Before...")
                check0 = f"SELECT * FROM projection_timeseries WHERE projection_id = {delete_info[0][0]} AND name = '{delete_info[0][1]}' AND parsenum = {delete_info[0][3]};"
                print(self.read_query(check0))
                check1 = f"SELECT * FROM projection_timeseries WHERE projection_id = {delete_info[-1][0]} AND name = '{delete_info[-1][1]}' AND parsenum = {delete_info[-1][3]};"
                print(self.read_query(check1))
                print()

            row_idfiers = []
            delete_query = f"DELETE FROM projection_timeseries WHERE projection_id = %s AND name = %s AND parsenum = %s;"
            for j in range(len(delete_info)):                
                row_idfiers.append([delete_info[j][0], delete_info[j][1], delete_info[j][3]])

            batch_num = 0
            for batch_num in range( int((len(row_idfiers) / batch_size ))):
                start = batch_num*batch_size
                end = (batch_num+1)*batch_size
                print(f"Deleting batchnum = {batch_num}. s={start} e={end}")
                self._sql_cursor.executemany(delete_query, row_idfiers[start:end])
            
            batch_num+=1
            print(f"Deleteing last batch. Batchnum = {batch_num}")
            self._sql_cursor.executemany(delete_query, row_idfiers[start:-1])

            ##############update that this parsenum has been cleaned and commit all the changes#############
            self._sql_cursor.execute(f"UPDATE scrape_data SET is_cleaned = 1 WHERE id = {parse_id[0]};")
            self._sql_conn.commit()
            if len(delete_info) > 0:
                print("After...")
                print(self.read_query(check0))
                print(self.read_query(check1))
                print()

    
    def new_clean_db(self, timer = None, num_ids = 30, leaguenum = 7, start_id = 341):
        #Function to facilitate cleaning of redundant data in the timeseries tables. Since these data points are added no matter what after parsing, 
        #there is a lot of times where data is stored when it doesnt need to because nothing is changing, so this function is meant to be run 
        #periodically to reduce bloat in the timeseries tables of the database.

        #Since this could eventually become a very time-consuming function, there are a few ways that the caller can bound the function:
        #   Calling the stop_clean() function will set a flag that stops the cleaning loop at the beginning of the next iteration
        #   The 'timer' arguement will limit the function to run only a specificed integer number of 'wall time' seconds have passed
        #   The 'num_ids' argument will limit the function to limit the number of parsenums that are cleaned

        '''
        Functionality should be added to this to make the function more efficient. This function should be able to run just on a specific leaguenum 
        and/or use the fact that the function returns the parsenum it ended off with to make sure that is what the function starts with next time 
        rather than have to query the db to get the id to start with.
        '''
        
        #Setting up variables for bounding the function
        self._is_cleaning = True

        if timer is not None:
            if isinstance(timer,int) is False:
                '''---Post some error for this?---'''
                print("Value for timer is invalid, must be an int or None")
                return 0, None
            timer = datetime.now() + timedelta(seconds=timer)
        else:
            timer = datetime.max
        if num_ids is not None:
            if isinstance(num_ids, int) is False or num_ids < 1:
                print("Value for num_ids is invalid, must be a positive int or None")
                return 0, None

                # Set isolation level to READ UNCOMMITTED for this transaction
        
        '''---DELETE THIS AFTER IMPLEMENTATION IS VALIDATED---'''
        #self._sql_cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        #self._sql_cursor.execute("START TRANSACTION")
        #input("MODIFYING SESSION, IF NOT INTENDED THEN THAT IS A PROBLEM!!!!")

        #getting old data from the db from before the first parsenum so that any comparisons made are valid
        print("Getting old data from the DB")
        #id_list = get a list of all the parse nums which have happened since the last one cleaned - ordered first->last
        id_list = self.read_query(f"SELECT id FROM scrape_data WHERE league_num = {leaguenum} AND my_status = 1 AND is_cleaned = 0 AND id > {start_id} ORDER BY store_time ASC;")
        #print(f"id_list:\n{id_list}")
        
        print("Finding next good parse_id")
        start_id_index = 0
        seed_data = self.read_query(f"SELECT * FROM projection_timeseries WHERE parsenum = {id_list[start_id_index][0]}")        
        while len(seed_data) == 0:
            #If for some reason there was nothing logged on this, then keep increasing the number until the nex one which has entries
            start_id_index += 1
            seed_data = self.read_query(f"SELECT * FROM projection_timeseries WHERE parsenum = {id_list[start_id_index][0]}")

        #Then we need to go through all the entries in the list and find any data that already exists for those projections, this is what we need to 
        #compare against for the first parsenum in the list
        last_entries = dict()
        print("Building last entry from existing db data")

        #Search for all the projection ids in the db and pull all that into memory sorted by parsenum
        pids = set()
        for each in seed_data:
            pids.add(each[0])
        print("Asking for all the data based on pids")
        base_sql = "SELECT * FROM projection_timeseries "
        where_clause = "" if pids is None else f"WHERE parsenum < {seed_data[0][3]} AND projection_id in ({','.join([str(pid) for pid in pids])}) ORDER BY parsenum DESC"
        sql = base_sql + where_clause
        all_ts = self.read_query(sql)
        already_found = dict()

        print("determining latest ts values we are interested in...")
        for data in all_ts:
            #Loop through all of the timeseries data sent from the db. Since it is already sorted, this can just be done lineraly with the assumption 
            #that if nothing is already there, then that must be the most recent data point for that series
            '''
            Perhaps this can be further improved in the future, but for now I'm not worrying about it as long as it is fast enough

            This request assumes that each parsenum will only increase over time which may not always be true, but for now I'm ok assuming this
            '''
            kn = f"{data[0]}_{data[1]}"
            already_found = last_entries.get(kn)

            if already_found is None:
                last_entries[kn] = [data[2]]

        #helper.print_dict(last_entries)

        #################DONE GETTING OLD DATA#################

        #Create dict to eventually compare the before and after
        #pre_dict = self._build_dict(leaguenum, num_ids, start_id)

        id_list = self.read_query(f"SELECT id FROM scrape_data WHERE league_num = {leaguenum} AND my_status = 1 AND is_cleaned = 0 AND id > {start_id} ORDER BY store_time ASC;")
        ts_dict = last_entries
        delete_info = list()
        interested = set()
        
        for i, parse_id in enumerate(id_list[start_id_index:]):
            #Loop through each of the parse ids and compare with whatever the latest is in the DB. If it is the same, then add it to the delete pile 
            #to be removed

            #check if stop condition is met, if so, Return last cleaned parsenum and how many parsenums were cleaned
            if self._is_cleaning is False:
                print("Stopping cleaning loop externally")
                return i, parse_id
            elif datetime.now() > timer:
                print("Cleaning timer expired")
                return  i, parse_id
            elif i == num_ids:
                print("Cleaning id limit reached")
                break
                return i, parse_id

            '''---Improve speed of how this is being queried---'''
            parse_data = self.read_query(f"SELECT * FROM projection_timeseries WHERE parsenum = {parse_id[0]}")
            
            #Check to make sure data was actually parsed before comparing, if not, then that comparison is invalid must be skipped
            if len(parse_data) == 0:
                continue

            delete_info.clear()
            for row in parse_data:

                kn = f"{row[0]}_{row[1]}"
                if kn == "5014468_rank":
                    print(row)
                temp_series = ts_dict.get(kn)
                if temp_series is None:
                    ts_dict[kn] = [row[2]]
                else:
                    if ts_dict[kn][-1] == row[2]:
                        if len(interested) < 30 and kn not in interested:
                            interested.add(kn)
                        delete_info.append(row)
                    else:
                        temp_series.append(row[2])
        
            #This batch size is not scientific, I just picked one that seems to work. I'm not sure what the limitations are of this. Something to 
            #investigate in the future to optimize.
            print(f"Deleting {len(delete_info)} entries")
            batch_size = 50
            delete_query = ""
            if len(delete_info) > 0:
                print("Before...")
                pre_del = f"SELECT * FROM projection_timeseries WHERE projection_id = {delete_info[0][0]} AND name = '{delete_info[0][1]}' AND parsenum = {delete_info[0][3]};"
                print(self.read_query(pre_del))
                pre_del = f"SELECT * FROM projection_timeseries WHERE projection_id = {delete_info[-1][0]} AND name = '{delete_info[-1][1]}' AND parsenum = {delete_info[-1][3]};"
                print(self.read_query(pre_del))
                print()

            row_idfiers = []
            delete_query = f"DELETE FROM projection_timeseries WHERE projection_id = %s AND name = %s AND parsenum = %s;"
            for j in range(len(delete_info)):                
                row_idfiers.append([delete_info[j][0], delete_info[j][1], delete_info[j][3]])

            batch_num = 0
            for batch_num in range( int((len(row_idfiers) / batch_size ))):
                start = batch_num*batch_size
                end = (batch_num+1)*batch_size
                print(f"Deleting batchnum = {batch_num}. s={start} e={end}")
                self._sql_cursor.executemany(delete_query, row_idfiers[start:end])
            
            batch_num+=1
            print(f"Deleteing last batch. Batchnum = {batch_num}")
            self._sql_cursor.executemany(delete_query, row_idfiers[start:-1])

            #update that this parsenum has been cleaned and commit all the changes
            #self._sql_cursor.execute(f"UPDATE scrape_data SET is_cleaned = 1 WHERE id = {parse_id[0]};")
            self._sql_conn.commit()
            
            exit()
        
        #print("Printing full TS dict:")
        #helper.print_dict(ts_dict)
        #input("How does this look?")

        my_series = self.read_query("SELECT * FROM projection_timeseries WHERE projection_id = 5014468 AND name = \"rank\" ORDER BY parsenum ASC")
        print(f"Example series:\n{my_series}\n")
        print("Creating dict after the deletions...")

        '''post_dict = self._build_dict(leaguenum, num_ids, start_id)
        print("Pre example:")
        for key in interested:
            print(f"{key} : {pre_dict[key]}")
        print("\n------Post example---------\n")
        for key in interested:
            print(f"{key} : {post_dict[key]}")
        print("\nActual TS dict:\n")
        for key in interested:
            print(f"{key} : {ts_dict[key]}")'''