__author__ = 'RESarwas'
import sys
import os

try:
    import pyodbc
except ImportError:
    pyodbc = None
    pydir = os.path.dirname(sys.executable)
    print 'pyodbc module not found, make sure it is installed with'
    print pydir + r'\Scripts\pip.exe install pyodbc'
    print 'Don''t have pip?'
    print 'Download <https://bootstrap.pypa.io/get-pip.py> to ' + pydir + r'\Scripts\get-pip.py'
    print 'Then run'
    print sys.executable + ' ' + pydir + r'\Scripts\get-pip.py'
    sys.exit()


def get_connection_or_die():
    conn_string = ("DRIVER={{SQL Server Native Client 11.0}};"
                   "SERVER={0};DATABASE={1};Trusted_Connection=Yes;")
    conn_string = conn_string.format('inpakrovmais', 'akr_facility2')
    try:
        connection = pyodbc.connect(conn_string)
        return connection
    except pyodbc.Error:
        # Try to alternative connection string for 2008
        conn_string2 = conn_string.replace('SQL Server Native Client 11.0', 'SQL Server Native Client 10.0')
    try:
        connection = pyodbc.connect(conn_string)
        return connection
    except pyodbc.Error as e:
        # Additional alternatives are 'SQL Native Client' (2005) and 'SQL Server' (2000)
        print("Rats!!  Unable to connect to the database.")
        print("Make sure you have the SQL Server Client installed and")
        print("your AD account has the proper DB permissions.")
        print("Contact regan_sarwas@nps.gov for assistance.")
        print("  Connection: " + conn_string)
        print("         and: " + conn_string2)
        print("  Error: " + e[1])
        sys.exit()


def get_database_photos(connection):
    try:
        rows = connection.cursor().execute("""
            SELECT UNITCODE + '/' + ATCHALTNAME AS Name
              FROM gis.AKR_ATTACH_evw
             WHERE ATCHTYPE = 'Photo' 
               AND ATCHLINK LIKE 'http%://akrgis.nps.gov/fmss/photos/%'
        """).fetchall()
    except pyodbc.Error as de:
        print ("Database error ocurred", de)
        rows = None
    return rows


def files_for_folders(root):
    """
    Get the files in the folders below root
    :param root: The full path of the folder to search
    :return: A dictionary of the folders in root with a list of files for each folder.  All paths are relative to root.
    """
    files = {}
    for folder in [f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))]:
        print folder,
        path = os.path.join(root, folder)
        files[folder] = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    return files


def folder_file_tuples(root):
    """
    Get the (folder,file) info below root
    :param root: The full path of the folder to search
    :return: A list of (folder,file) pairs for each file in each folder below root.
    folder and file are names, not paths.
    """
    pairs = []
    folders = files_for_folders(root)
    for folder in folders:
        for name in folders[folder]:
            pairs.append((folder, name))
    return pairs


def files_in_csv(csv_path):
    import csv
    files = set()
    with open(csv_path,'r') as f:
        f.readline() # skip the header
        csv_reader = csv.reader(f)
        for row in csv_reader:
            unit = row[0]
            name = row[1]
            files.add("{0}/{1}".format(unit,name).lower())
    return files


def is_image(name):
    ext = os.path.splitext(name)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.gif']


def is_jpeg(name):
    ext = os.path.splitext(name)[1].lower()
    return ext in ['.jpg', '.jpeg']


if __name__ == '__main__':
    print('Reading database')
    conn = get_connection_or_die()
    # duplicate paths in the database are OK;
    #  two different features could be in the same photo
    # so we want to unique-ify the list of photo links
    db_photo_set = set([row[0].lower() for row in get_database_photos(conn)])
    print('Found {0} unique files in the Database.'.format(len(db_photo_set)))

    csv_file = "PhotoCSVLoader.csv"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assumes script ia adjacent to the CSV list of new photos
    csv_path = os.path.join(script_dir,csv_file)
    print('\nReading {0}'.format(csv_path))
    csv_photo_set = files_in_csv(csv_path)
    print('Found {0} unique files in the {1}.'.format(len(csv_photo_set), csv_file))

    # Assumes script is in the Processing folder which is in the photos base folder.
    #   some/path/PHOTOS/PROCESSING/this_script.py
    #   some/path/PHOTOS/ORIGINAL/{park}/photos_files.jpg
    base_dir = os.path.dirname(script_dir)
    photo_dir = os.path.join(base_dir, "ORIGINAL")
    print('\nReading Folders in ' + photo_dir)
    photo_tuples = [t for t in folder_file_tuples(photo_dir) if is_jpeg(t[1])]
    fs_photo_set = set([(t[0]+'/'+t[1]).lower() for t in photo_tuples])
    print('\nFound {0} unique files in the Filesystem.'.format(len(fs_photo_set)))
    print('')

    fs_not_db = fs_photo_set - db_photo_set - csv_photo_set
    db_not_fs = db_photo_set - fs_photo_set
    csv_not_fs = csv_photo_set - fs_photo_set
    if fs_not_db:
        print('ERROR: The following {0} files are in the Filesystem but not the Database/CSV'.format(len(fs_not_db)))
        for i in sorted(list(fs_not_db)):
            print('  {0}'.format(i))
    if db_not_fs:
        print('ERROR: The following {0} files are in the Database but not the Filesystem'.format(len(db_not_fs)))
        for i in sorted(list(db_not_fs)):
            print('  {0}'.format(i))
    if csv_not_fs:
        print('ERROR: The following {0} files are in the CSV but not the Filesystem'.format(len(csv_not_fs)))
        for i in sorted(list(csv_not_fs)):
            print('  {0}'.format(i))
    if not fs_not_db and not db_not_fs and not csv_not_fs:
        print('Woot, Woot, No issues found.')