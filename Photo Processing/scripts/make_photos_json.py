# -*- coding: utf-8 -*-

"""
Create a photos.json file which lists each photo in the database with a URL and foreign key.

File paths are hard coded in the script relative to the scipt's location.
The database connection string and schema are also hardcoded in the script.

Written for Python 2.7; may work with Python 3.x.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os.path
import sys


try:
    import pyodbc
except ImportError:
    pyodbc = None
    pydir = os.path.dirname(sys.executable)
    print("pyodbc module not found, make sure it is installed with")
    print(pydir + r"\Scripts\pip.exe install pyodbc")
    print("Don" "t have pip?")
    print(
        "Download <https://bootstrap.pypa.io/get-pip.py> to "
        + pydir
        + r"\Scripts\get-pip.py"
    )
    print("Then run")
    print(sys.executable + " " + pydir + r"\Scripts\get-pip.py")
    sys.exit()


def get_connection_or_die():
    conn_string = (
        "DRIVER={{SQL Server Native Client 11.0}};"
        "SERVER={0};DATABASE={1};Trusted_Connection=Yes;"
    )
    conn_string = conn_string.format("inpakrovmais", "akr_facility2")
    try:
        connection = pyodbc.connect(conn_string)
        return connection
    except pyodbc.Error:
        # Try to alternative connection string for 2008
        conn_string2 = conn_string.replace(
            "SQL Server Native Client 11.0", "SQL Server Native Client 10.0"
        )
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


def get_photo_data(connection):
    photos = {}
    try:
        # FIXME - This only returns one ID for each photo
        #   some photos have multiple IDs (some buildings and building assets have FMSS ID(s) and a FEATUREID)
        rows = (
            connection.cursor()
            .execute(
                """
             SELECT COALESCE(FACLOCID, COALESCE(FEATUREID, COALESCE(FACASSETID, GEOMETRYID))) AS id,
			        REPLACE(ATCHLINK, 'https://akrgis.nps.gov/fmss/photos/web/', '') AS photo
               FROM gis.AKR_ATTACH_evw
              WHERE ATCHALTNAME IS NOT NULL AND (FACLOCID IS NOT NULL OR FACASSETID IS NOT NULL OR FEATUREID IS NOT NULL OR GEOMETRYID IS NOT NULL)
           ORDER BY id, ATCHDATE DESC
                """
            )
            .fetchall()
        )
    except pyodbc.Error as de:
        print("Database error ocurred", de)
        rows = None
    if rows:
        for row in rows:
            if row.id in photos:
                photos[row.id].append(row.photo)
            else:
                photos[row.id] = [row.photo]
    return photos


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outfile = os.path.join(script_dir, "photos.json")
    conn = get_connection_or_die()
    data = get_photo_data(conn)
    with open(outfile, "w") as fh:
        fh.write(json.dumps(data, indent=2, separators=(",", ": ")))
