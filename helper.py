import shutil
import os

def print_dict(my_dict):
    for k,v in my_dict.items():
        print(f"{k}\t{v}")

#Function used to get personal info from secret file. Caller passes in a string 'query' and this function
#goes line by line in the fn passed into the function looking for the query. The file is expected to be formatted like
#(description)_(variable name)=(value). Example for mysql database password would be something like: 'mysql_pw=my_password'.
def get_secret(query, fn = "secrets.txt"):
    

    #This function only parses lines if query matches the description. It puts the matched lines into a dictionary where the 
    #variable names are the keys and the values are the values.
    
        #requires that the user have a file called 'secrets.txt' where 3 of the lines in it are:
        #mysql_un=username
        #mysql_pw=password
        #mysql_hn=hostname
        #mysql_db_name=db_name

    dir_path = os.path.dirname(os.path.realpath(__file__))
    fn = os.path.join(dir_path, fn)
    my_dict = {}
    with open(fn, "r") as f:
        '''---Going line by line in file looking for query---'''
        for line in f:
            desc_delim = line.find("_")
            if desc_delim == -1:
                '''---If format is not as expected, then skip that line and print warning to console---'''
                print(f"WARNING: Should have '_' in this line:\n{line}\n")

            if line.find(query) > -1:
                '''---If query is found, parse the line---'''
                key_delim = line.find("=")
                if key_delim == -1:
                    '''---If format is not as expected, then skip that line and print warning to console---'''
                    print(f"WARNING: Should have '=' in this line:\n{line}\n")
                    continue

                key = line[desc_delim+1:key_delim]
                value = line[key_delim+1:].replace("\n","")
                my_dict[key] = value

    return my_dict

def dev_files_check():
    '''
    Rather than wrestle with gitignoring all the dev files, I'm just going to pull them in with this function
    whenever I cant find what I need. All the dev files are stored outside of the repo so that when they are deleted when I rebase,
    I can simply pull them back in and we are all good!
    '''
    raise NotImplementedError
    dest_dir = pathlib.Path(__file__).parent.resolve()
    src_dir = str(pathlib.Path(__file__).parent.resolve())
    src_dir.rfind('\\')
    src_dir = src_dir[:src_dir.rfind('\\')+1]
    src_dir += "dev_files"
    
    if not os.path.exists(src_dir):
        print(f"Source directory '{src_dir}' does not exist.")
        return

    '''---Create the destination directory if it doesn't exist---'''
    os.makedirs(dest_dir, exist_ok=True)

    '''---Iterate over files in the source directory---'''
    for filename in os.listdir(src_dir):
        src_file = os.path.join(src_dir, filename)

        '''---Check if it's a file (not a directory)---'''
        if os.path.isfile(src_file):
            dest_file = os.path.join(dest_dir, filename)
            shutil.copy2(src_file, dest_file)
