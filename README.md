# PrizePicks scraping
---GETTING STARTED---

0) Download and set up mysql database. Keep track of the root username and password
    If you are going to store some tables in an non-default location (like on another drive in system), then you will need to add the below into your mysql options file:
        innodb_directories =/path/to/directory
    *This article here was exactly what I spent many hours trying to figure out: https://moxio.com/blog/moving-individual-mysql-tables-on-disk/
    **On Fedora Linux I had an issue using a different directory while SELinux was enabled, so if that is causing issues, then disable that...


---CREATING SQL DB WITH LATEST SCHEMA---
1) Create mysql connection in terminal with root un and pw
    sudo mysql -u root -p
        cml will prompt you for root pw
    *If you will be using different locations to store different tables, now is the time to add that since moving the tables after there is a bunch of data in them is harder.
    An example of what the table creation functions should look like is as below:
        CREATE TABLE `whatever_table_name` (/* column definitions here*/) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci DATA DIRECTORY='/path/to/directory';

2) Create the database with your desired database name - in my case, it is 'prizepicks_prod'. For a development database perhaps 'prizepicks_dev' is more appropriate
    CREATE DATABASE prizepicks_prod;

3) Tell mysql which database you want to query
    USE prizepicks_prod;

4) Copy the latest sql schema from the repo and pase it into the command line
    At time of writing the file is '20250901sql_schema.sql'

    OPTIONAL HARDWARE MANAGEMENT: When you create all the tables above, some of them end with 'archive'. If you have some slower/larger storage HW then those tables should go on there since those will be the largest and are only written/read in relativley large chunks.
    If you want everything in another location on a different piece of hardware, then just change the datadir of your mysql server. Since I want to keep the smaller tables on my SSD and the larger tables on my HDD then I just move specific table using the steps below:
        *you will need admin access to perform this - permissions make this kind of tricky, I had to use GUI to complete all  this
        a) You will need to find your mysql datadir by using 'SELECT @@datadir;'
        b) Navigate to that datadir, in there you will be able to find all the .ibd files. 
        c) You can configure where any one of the tables are stored by copying the '_archive.ibd' file to the location you would like to store it - perhaps a location that is stored on your other piece of storage hardware
        d) Replace the existing .ibd file with a symbolic link to the copy you just made in in step c. The symbolic link MUST have the same name. So if the .ibd file you moved was called 'projection_archive.ibd' then the symbolic link in the datadir must also be called 'projection_archive.ibd'
        NOTE: These same steps can be used any time as long as the mysql DB is stopped while the files are being changed.

5) Validate that it all worked by checking that all the expected tables are in there and all the tables have the expected columns with the following commands:
    SHOW TABLES;
        This will spit out all the table names, check to make sure they are all there
    DESCRIBE {table name}
        Replace {table name} with the name of the table you want to validate the columns for. This will show not just all the column names for the table but also what type each of those columns is

---Setting up files to read from
6) Create a file called 'secrets.txt' in the same directory as the helper.py file which has the following lines:
    mysql_un={username}
    mysql_pw={password}
    mysql_hn={hostname}
    mysql_db_name={db_name}
        NOTE: username does not have to be root, I just use root because so I don't have to manage permissions.
        For mysql_hn, I use 'localhost' but your system may be different, so make sure that is configured for your system. I'm not a mysql expert so I just Google if I need help
        The mysql_db_name should match your DB's name. I have one for dev and one for prod, so just make sure this is looking for the database you are trying to access

---For creating an 'app' to run the program automatically at launch
7) On my linux system in the /.config/autostart directory I'm created 'prizepicks-scraping.desktop' and included the below info:
	[Desktop Entry]
	Version=1.0
	Type=Application
	Name=Prizepicks Scraping
	Terminal=true
	Comment=Polls prizepicks and save data in sql database
	Exec=/usr/bin/python3 {path to prodcution repo}/scheduler.py
	Categories=Utilities

Then I used the GNOME Tweaks app to auto-launch the 'Prizepicks Scraping' app I created every time the computer boots up. There may be other ways to do this, but this seems to work for my purposes.
