# -*- coding: utf-8 -*-
"""
Add the photos in the CSV list (PhotoCSVLoader.csv) to the facilities database.

Note that database errors are expected.  This is a strange interaction between pyodbc and SDE.
Everything works as expected despite the errors.  Example follows:

Database error:
EXEC sde.create_version 'sde.DEFAULT', 'photo_update_20181211', 1, 2, 'For auto upload of new photos';
('25000', u'[25000] [Microsoft][ODBC Driver 13 for SQL Server][SQL Server]Transaction count after EXECUTE indicates a mismatching number of BEGIN and COMMIT statements. Previous count = 1, current count = 0. (266) (SQLExecDirectW)')
Database error:
EXEC dbo.Calc_Attachments 'DBO.photo_update_20181211';
('25000', u'[25000] [Microsoft][ODBC Driver 13 for SQL Server][SQL Server]Transaction count after EXECUTE indicates a mismatching number of BEGIN and COMMIT statements. Previous count = 1, current count = 0. (266) (SQLExecDirectW); [25000] [Microsoft][ODBC Driver 13 for SQL Server][SQL Server]Transaction count after EXECUTE indicates a mismatching number of BEGIN and COMMIT statements. Previous count = 1, current count = 0. (266)')

File paths are hard coded in the script relative to the scipt's location.
The database connection string and schema are also hardcoded in the script.

Written for Python 2.7; may work with Python 3.x.

Third party requirements:
* pyodbc - https://pypi.python.org/pypi/pyodbc
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import datetime
import os
import sys

import pyodbc

import csv23


def get_connection_or_die(server, database):
    """
    Get a Trusted pyodbc connection to the SQL Server database on server.

    Try several connection strings.
    See https://github.com/mkleehammer/pyodbc/wiki/Connecting-to-SQL-Server-from-Windows

    Exit with an error message if there is no successful connection.
    """
    drivers = [
        "{ODBC Driver 17 for SQL Server}",  # supports SQL Server 2008 through 2017
        "{ODBC Driver 13.1 for SQL Server}",  # supports SQL Server 2008 through 2016
        "{ODBC Driver 13 for SQL Server}",  # supports SQL Server 2005 through 2016
        "{ODBC Driver 11 for SQL Server}",  # supports SQL Server 2005 through 2014
        "{SQL Server Native Client 11.0}",  # DEPRECATED: released with SQL Server 2012
        # '{SQL Server Native Client 10.0}',    # DEPRECATED: released with SQL Server 2008
    ]
    conn_template = "DRIVER={0};SERVER={1};DATABASE={2};Trusted_Connection=Yes;"
    for driver in drivers:
        conn_string = conn_template.format(driver, server, database)
        try:
            connection = pyodbc.connect(conn_string)
            return connection
        except pyodbc.Error:
            pass
    print("Rats!! Unable to connect to the database.")
    print("Make sure you have an ODBC driver installed for SQL Server")
    print("and your AD account has the proper DB permissions.")
    print("Contact akro_gis_helpdesk@nps.gov for assistance.")
    sys.exit()


def read_csv(csv_path):

    rows = []
    with csv23.open(csv_path, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)  # skip the header
        for row in csv_reader:
            row = csv23.fix(row)
            # print(row[4])
            rows.append([i for i in row])
    return rows


def fix_photos(photos):
    today = datetime.date.today().isoformat()
    for photo in photos:
        if not photo[10]:
            photo[10] = "AKRO_GIS"
        if not photo[11]:
            photo[11] = today
    return photos


def make_new_version(conn):
    """Create a new named SDE version in conn.
    SDE will automatically make sure the name is unique (with 1 as the 3rd param)
    need to query the versions to get the owner name as well as the final name."""
    today = datetime.date.today()
    name = "photo_update_{0}{1:02d}{2:02d}".format(today.year, today.month, today.day)
    # 3rd param: 1 for uniquify, 2 to use name as given (may error).
    # 4th param: 0 for private, 1 for public, or 2 for protected.
    sql = "EXEC sde.create_version 'sde.DEFAULT', '{0}', 1, 2, 'For auto upload of new photos';".format(
        name
    )
    execute_sql(conn, sql)
    # Note that the uniquify has been throwing an error but still succeeded.
    # Since the name may have been altered, find the new name
    row = None
    try:
        row = (
            conn.cursor()
            .execute(
                # TODO: test/use where DATEDIFF('sec', creation_time, GETDATE()) < 1
                "select top 1 owner, name from sde.SDE_versions where name like '{0}%' order by creation_time desc".format(
                    name
                )
            )
            .fetchone()
        )
    except pyodbc.Error as de:
        err = "Database error:\n{0}\n{1}".format(sql, de)
        print(err)
    if row and len(row) == 2:
        return "{0}.{1}".format(*row)
    else:
        print("Unexpected database response to query for version name")
        print(row)
    return None


def write_photos(connection, version, photos):
    sql = None
    try:
        with connection.cursor() as wcursor:
            sql = "EXEC sde.set_current_version '{0}';".format(version)
            wcursor.execute(sql)
            sql = "EXEC sde.edit_version '{0}', 1;".format(version)  # Start editing
            wcursor.execute(sql)
            # UNITCODE,FOLDER,FILENAME,TIMESTAMP,FACLOCID,FACASSETID,FEATUREID,GEOMETRYID,DESCRIPTION,ORIGINALPATH,CREATEUSER,CREATEDATE,NOTES
            for photo in photos:
                if photo[1]:
                    link = "https://akrgis.nps.gov/fmss/photos/web/{0}/{1}/{2}".format(
                        photo[0], photo[1], photo[2]
                    )
                else:
                    link = "https://akrgis.nps.gov/fmss/photos/web/{0}/{1}".format(
                        photo[0], photo[2]
                    )
                photo_db = [
                    "'{0}'".format(i) if i else "NULL" for i in photo
                ]  # all attributes are either string or NULL
                sql = (
                    "INSERT gis.AKR_ATTACH_evw "
                    "(ATCHLINK, UNITCODE, ATCHALTNAME, ATCHDATE, FACLOCID, FACASSETID, FEATUREID, GEOMETRYID, ATCHNAME, ATCHSOURCE, CREATEUSER, CREATEDATE, NOTES) "
                    "VALUES ('{0}', {1}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11}, {12}, {13});"
                )
                sql = sql.format(link, *photo_db)
                wcursor.execute(sql)
            # Do automated calcs
            sql = "EXEC dbo.Calc_Attachments '{0}';".format(version)
            wcursor.execute(sql)
            sql = "EXEC sde.edit_version '{0}', 2;".format(version)  # Stop editing
            wcursor.execute(sql)
    except pyodbc.Error as de:
        err = "Database error:\n{0}\n{1}".format(sql, de)
        print(err)
        return err
    return None


def execute_sql(connection, sql):
    try:
        with connection.cursor() as wcursor:
            wcursor.execute(sql)
    except pyodbc.Error as de:
        err = "Database error:\n{0}\n{1}".format(sql, de)
        print(err)
        return err
    return None


if __name__ == "__main__":
    # for editing of SQL Server SDE data without ArcGIS
    # http://desktop.arcgis.com/en/arcmap/10.3/manage-data/using-sql-with-gdbs/edit-versioned-data-using-sql-sqlserver.htm
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assumes script is in the Processing folder which is sub to the photos base folder.
    photo_list_file = os.path.join(script_dir, "PhotoCSVLoader.csv")
    new_photos = read_csv(photo_list_file)
    if not new_photos:
        print("There are no photos to add")
        sys.exit()
    if len(new_photos[0]) != 13:
        print("There are the wrong number of columns in the Photos CSV")
        sys.exit()
    conn = get_connection_or_die("inpakrovmais", "akr_facility2")
    version = make_new_version(conn)
    write_photos(conn, version, fix_photos(new_photos))
