import mysql.connector
import helper
from datetime import datetime, timezone
from parsed_data import parsed_data, debug_exc
from my_logs import log_perf
import os
import logging
from logging.handlers import RotatingFileHandler
import traceback

#Helper class to help with holding data for many to many relationships. To compare and decide what needs to be updated
class one_to_many:
    
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
    _external_data_names = dict()
    _log = None

    def __init__(self):
        self._create_log()
        self._sql_conn = self._create_db_connection()
        self._sql_cursor = self._sql_conn.cursor()
        self._set_external_data_names()

    #Create a log for this class
    def _create_log(self):
        log_path = f"{str(os.path.dirname(__file__))}\\logs"
        if not os.path.isdir(log_path): 
            os.mkdir(log_path)

        #Set up stats logger
        stats_logname = f"{__name__}_stats"
        self._log = logging.getLogger(stats_logname)
        self._log.setLevel("INFO")
        stats_file_handler = RotatingFileHandler(f"{log_path}\\{stats_logname}.log", maxBytes=5000000, backupCount=5)
        stats_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(funcName)s - %(message)s'))
        self._log.addHandler(stats_file_handler)

    #function to get
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
            ts_list = self.read_query(f"SELECT DISTINCT name FROM {table_name}_timeseries;")
            ts_names = [each[0] for each in ts_list]

            #Add the names of both the target table and the timeseries tables to save
            self._external_data_names[table_name] = data_names + ts_names

    def get_data_to_parse(self):
        #Don't want caller messing with the member variable directly, so this fuctions allows a caller to a
        #copy of those names
        return self._external_data_names.copy()

    def _create_db_connection(self, db_name="pp dev", host_name= None, user_name = None, user_password = None):      
        #Function to create a connection to the local mySQL database. Credentials can be passed in or they default to None and if host_name is left as None
        #then the root_login() function will get the root login data form a file somewhere on the computer

        #If this is is in a file indicating that this is running prod, then make sure it points to prod db, not dev db
        if 'pp_prod' in os.path.abspath("."):
            db_name = "prizepicks"
            print("Connecting to PROD DB")
            self._log.info(f"PROD")
        else:
            print("Connecting to DEV DB")
            self._log.info(f"DEV")

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

        #MySQL Database connection successful
        self._log.info(f"0")
        return connection
    
    '''Long term, this should not need to be root user'''
    #This function is used to retrive the username, host name, and password to gain access to the local mySQL database. 
    def _root_login(self):
        
        #requires that the user have a file called 'secrets.txt' where 3 of the lines in it are:
        #mysql_un=username
        #mysql_pw=password
        #mysql_hn=hostname
        
        #So, to access this, that file must be setup beforehand and then this function will work properly as it
        #is simply reading those 3 items from the file. It muse have *accurate* user info of the 3
        #fields above to get into the SQL DB
        
        my_dict = helper.get_secret("mysql")
        #Checking to make sure all the necessary parts were read from file
        not_found_list = []
        if my_dict.get('un') is None: 
            not_found_list.append('un')

        if my_dict.get('pw') is None: 
            not_found_list.append('pw')

        if my_dict.get('hn') is None: 
            not_found_list.append('hn')

        if len(not_found_list) > 0:
            #Missing values in dict, will probably cause errors later...
            self._log.warning(f"01: ntfnd={not_found_list}")
            return None

        return my_dict

    #Function called by app manager to send the parsed data to the local mySQL database
    def send_to_sql(self, parsed_data_obj, scrape_id):
        
        if not isinstance(parsed_data_obj, parsed_data):
            self._log.warning(f"1: type={type(parsed_data_obj)}")
            return 1
        
        #Sends values parsed into the projection table
        
        #No data to send to the DB, returning since there is nothing to do")
        if len(parsed_data_obj.data_values) == 0:
            self._log.info(f"0000")
            return True
        
        self._send_to_projection_table(parsed_data_obj.data_order, parsed_data_obj.data_values, scrape_id)
        self._send_included_data(parsed_data_obj.included_tag_values, scrape_id)
        #Commits changes made during above functions
        self._sql_conn.commit()
        return True
    
    #Function takes in the headers of the incoming data and maps them to the order which they appear in the mysql table 
    '''
    For this section, I wonder if rather than just sending everything in in the prerfectly correct order it would be easier to just tell the db
    the column name order that the info will come in. May clean up the code a bit here.
    '''
    @log_perf
    def _create_col_ordering(self, headers, table): 
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
            #ignore anything that is a timeseries since that will not show up in the projections table
            if header in self.PROJECTION_TIME_SERIES:
                continue
            
            #Add 'my_' to the front of the mysql reserved words so that all column names
            if header in self.SQL_RESERVED_WORDS: 
                header = f"my_{header}"
            translated_headers.append(header)
            
            #Align the incoming headers with how they appear in the db
            try:
                col_num = mysql_cols.index(header)
                mysql_map[col_num] = i
            except ValueError:
                self._log.warning(f"01: unexhdr={header}")
                continue
        
        return (mysql_map, dt_indexes, translated_headers)

    #Function to get existing data from the given table name and all the data which is from the passed in ids
    @log_perf
    def _get_existing_data(self, table, id_list):
        
        #Pull in all incoming row ids so db can be queried for existing rows
        my_len = len(id_list)
        if my_len == 0:
            #No data to add for {table}. Returning empty list
            self._log.info(f"0000")
            return []
    
        #build SQL query to get existing data from the db for the ids to compare with
        base_sql = f"SELECT * FROM {table} "
        where_clause = "" if id_list is None else f"WHERE ID in ({','.join([str(data_id) for data_id in id_list])})"
        sql_query = base_sql + where_clause
        return self.read_query(sql_query)

    #Function to create timeseries entires for each entry in the incoming row if it exists

    def _add_timeseries(self, hdr_order, incoming_row, row_id, scrape_id, last_values):
    #If timeseries data does exist in the incoming row, then the row which must be added to the
    #mysql is returned

        timeseries_list = list()
        for timeseries in self.PROJECTION_TIME_SERIES:
            #Not all timeseries data is always guarunteed, so this check to make sure that the timeseries data actually exists before trying to add anything. 
            #If it does not exist then just skip it, that's ok.
            '''Probably faster way to do this somehow rather than look for the same indexes each time'''
            ts_ind = hdr_order.index(timeseries)
            kw = self._create_keyword([row_id,timeseries])

            if incoming_row[ts_ind] is not None:
                last_value = last_values.get(kw)
                new_value = incoming_row[ts_ind]

                if last_value is None:
                    #If there is not data for last value in the DB then it can be added in there
                    last_values[kw] = new_value
                    timeseries_list.append([row_id, timeseries, incoming_row[ts_ind], scrape_id])

                elif last_value[2] != new_value:
                    #if value has changed then add it to the timeseries list
                    timeseries_list.append([row_id, timeseries, incoming_row[ts_ind], scrape_id])
                else:
                    #If the data already exists then no need to add it again
                    pass

            else:
                #if timeseries data does not exist in the incoming row, then just skip it
                pass
        
        return timeseries_list

    #This fucntion goes through each of the items of two existing and incoming data rows and compares them. If any differences then
    #They are added to the change list in the formate I want to store in the db and returned to the caller
    def _create_changes(self, num_cols, mapping, translated_headers, existing_row, temp_row, row_id, scrape_id, change_list):
        change_list = list()
        for i in range(num_cols):
            #If a value has changed, then add it to the change list and mark that a change has been made. This change will be logged in the appropriate change_history table
            if existing_row[i] != temp_row[i]:
                change_list.append([row_id, translated_headers[mapping[i]], existing_row[i], scrape_id])
        
        return change_list
    
    #function to pull in all the last timeseries values for the passed in projection ids
    @log_perf
    def _get_last_values(self, proj_ids):

        #Pull in all the data from the DB for the interested timeseries and turn it into a dict
        my_q =f"""
        SELECT * 
        FROM projection_timeseries 
        WHERE projection_id in ({','.join([str(proj_id) for proj_id in proj_ids])}) 
        ORDER BY parsenum DESC;
        """
        self._log.debug(my_q)
        all_ts = self.read_query(my_q)
        #create dict to see what the latest value for a given projection is
        ts_dict = dict()
        for data_point in all_ts:
            kw = self._create_keyword([data_point[0],data_point[1]])

            if kw not in ts_dict:
                ts_dict[kw] = data_point

        return ts_dict

    @log_perf
    def _send_to_projection_table( self, headers, data, scrape_id):
        #Function which will send passed in data into the 'data' table of the local mySQL database
        #Argumetns are:
        #    headers - a list of names of the columns of the target table in order for how they apprear in the data
         
        #    data - a list of lists where each sub-list is the list of data that is going into the database. The data point at each index is
        #        described by that same index of 'headers' list

        #    scrape_id - the id of the scrape that this data is coming from.
    
        mapping = list()
        dts = list()
        translated_headers = list()
        table = 'projection'
        id_index = headers.index("id")

        #tuple of all the projection ids of the incoming data
        new_proj_ids = tuple(values[id_index] for values in data)
        #Pull into memory any data already be in the db to compare/update against
        existing_data = self._get_existing_data(table, new_proj_ids)

        #Call function to map the incoming data to the order that the db requires
        mapping, dts, translated_headers = self._create_col_ordering(headers, table)
        
        #Create dictionary where the key is the row id and the value is the row of existing data in the mysql db. This will be used to 
        #check for if any rows need to be updated
        data_dict = dict()
        for row in existing_data:
            data_dict[row[id_index]] = row

        #Create dict to keep track of the latest values of the timeseries parsed from the projection data. This will dictate whether a new data point 
        # hould be added to a timeseries or not
        last_values = self._get_last_values(new_proj_ids)

        #loop through each of the headers and determine which are timeseries so that they can be handled separatley from the items which are not 
        # expected to change
        ts_hdr_inds = dict()
        for ts in self.PROJECTION_TIME_SERIES:
            try:
                ts_hdr_inds[ts] = headers.index(ts)
            except ValueError:
                #Cant find index of {ts}, unexpected, but not critical
                self._log.warning(f"01: tsntfnd={ts}")
                ts_hdr_inds[ts] = None

        #Call function that loops through each of the incoming data rows to determine what changes need to be made in the db. Any changes that need to be made, the 
        #necessary data to do that is added to the insert, update, or timeseries list as apropriate. These lists are then executed in batches into the
        #db to make it fast Rather than calculate the index for each of the timeseries iteration of loop, do it once before we get into the loop. Also
        #including stat_type index as well since I need that too
        insert_list, change_list, update_list, timeseries_list = self._loop_data(data, id_index, mapping, dts, data_dict, translated_headers, scrape_id, headers, last_values)

        #Function which makes batch requests for the 3 tables to be updated
        self._add_new_lines(insert_list, change_list, update_list, table, timeseries_list)
            
    #This loops through each of the incoming data rows to determine what changes need to be made in the db. Any changes that need to be made, the 
    #necessary data to do that is added to the insert, update, or timeseries list as apropriate. These lists are then executed in batches into the
    #db to make it fast Rather than calculate the index for each of the timeseries iteration of loop, do it once before we get into the loop. Also
    #including stat_type index as well since I need that too
    @log_perf
    def _loop_data(self, data, id_index, mapping, dts, data_dict, translated_headers, scrape_id, headers, last_values):
        
        insert_list = list()
        update_list = list()
        change_list = list()
        timeseries_list = list()
        
        for i,incoming_row in enumerate(data):
            #Map the data from the incoming row into a temp row so that it can be compared against whatever is already in the db in the correct 
            # order/format
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

            ###Beginning comparison and adding necessary data to correct lists to make updates
            
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
            timeseries_list += self._add_timeseries(headers, incoming_row, row_id, scrape_id, last_values)

        return insert_list, change_list, update_list, timeseries_list

    @log_perf
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
                #If something goes wrong with delete query, then that is really bad. Stop the program...
                self._log.critical(f"1: qry={delete_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
                raise debug_exc(sql_err, "1", {"qry":delete_query}, "PPDB")

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

            except mysql.connector.Error as sql_err:
                #If something goes wrong with delete query, then that is really bad. Stop the program...
                self._log.critical(f"2: qry={my_data_write_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
                raise debug_exc(sql_err, "2", {"qry":my_data_write_query, "dta_lst":my_data_list}, "PPDB")

            #log however many rows were added to which table
            self._log.info(f"0: add={len(my_data_list)} - tbl={table_name}")

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

            except mysql.connector.Error as sql_err:
                self._log.critical(f"3: qry={history_write_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
                raise debug_exc(sql_err, "3", {"qry":history_write_query, "dta_lst":data_history_list}, "PPDB")

            #log however many rows were added to which table
            self._log.info(f"0: add={len(data_history_list)} - tbl={table_name}")
            
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

            except mysql.connector.Error as sql_err:
                self._log.critical(f"4: qry={ts_write_query} - err={sql_err.__class__.__name__} - msg={sql_err.msg}")
                raise debug_exc(sql_err, "4", {"qry":ts_write_query, "dta_lst":timeseries_list}, "PPDB")

            #log however many rows were added to which table
            self._log.info(f"0: add={len(timeseries_list)} - tbl={table_name}")

        return True
    
    def _report_sql_error(self, error, query, rows):
        raise NotImplementedError
        print(f"Query: {query}")
        print(f"ERROR MESSAGE: {error.msg}")
        for row in rows:
            print(row)
        raise Exception("SQL Error found, please review")

    #Function within the class to handle all the reads to the DB
    def read_query(self, query):
        
        try:
            self._sql_cursor.execute(query)
            result = self._sql_cursor.fetchall()
        
        except Exception as e:
            self._log.warning(f"9999: qry={query} - err={e.__class__.__name__} - msg={e.msg} - tb={traceback.format_exc()}")
            raise e
            
        return result

    #Function to remove the prefixes added when data is put into the mysql to avoid reserved words
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

    #Function to post to the db that there was an error parsing the data from a specific api scrape
    def post_scrape_error(self, scrape_id, error):
        update_existing = f"UPDATE scrape_data SET my_status = {error} WHERE id = {scrape_id};"
        self._sql_cursor.execute(update_existing)
        self._sql_conn.commit()

    #function which takes in the required data to define a scrape entry in the db.
    #this function add that the db and returns the id of that new entry
    def create_scrape_id( self, status, leaguenum, timestamp):

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

    def _build_dict(self, lgnm, nums, start):
        raise NotImplementedError
        self._log.debug(f"0")
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

    #Function to standardize creation of keys for dict in cleaning db with proj_id and ts_name
    def _create_keyword(self, row_data):
        if len(row_data) < 2:
            #need to make sure there are tuple long enough to make the keyword before doing it
            self._log.critical(f"1111: invrow={row_data}")
            raise debug_exc(IndexError, "1111", {"invrow":row_data}, "PPDB")
        return f"{row_data[0]}_{row_data[1]}"

    #This is the function which will be called periodically to retrieve stats for the size of the db to be logged over time
    def get_stats(self):
        
        size_query = """
        SELECT 
            TABLE_NAME AS `Table`,
            ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS `Size (MB)`
        FROM 
            information_schema.TABLES
        WHERE 
            TABLE_SCHEMA = 'prizepicks'
        ORDER BY 
            (DATA_LENGTH + INDEX_LENGTH) DESC;
        """
        self._sql_cursor.execute(size_query)
        result = self._sql_cursor.fetchall()
        return result
