# -*- coding: utf-8 -*-
"""
Creates a CSV file of facilities data for a SOAP request to the FMSS web service.

File paths are hard coded in the script and relative to the current working directory.

Written for Python 2.7; it may with Python 3.x.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import json

try:
    import urllib2
except ImportError:
    # Python 3 replacement
    import urllib.request as urllib2

try:
    from urllib2 import HTTPError
except ImportError:
    # Python 3 replacement
    from urllib.error import HTTPError

import csv23

# These URLs return JSON
location_url = "http://inpniscvnpunit2/fmss/api/locations?siteid={0}&page={1}"
asset_url = "http://inpniscvnpunit2/fmss/api/assets?siteid={0}&page={1}"

# Response is JSON, converted to Python it looks like (as of July 20115):
response = {
    "TotalItems": 2,
    "TotalPages": 1,
    "PagedList": ["item1", "item2", "..."],
    "Page": 1,
    "PageSize": 25,
}

# example item in PagedList
example = {
    "LOCATIONSID": 5128917331,
    "STATUS": {"maxvalue": "OPERATING", "Value": "OPERATING"},
    "SOURCESYSID": "",
    "DESCRIPTION": "ANM Alaska Packers Historic Site & Access Area",
    "LO11": "AC",
    "LO6": 37978.81,
    "CHANGEBY": "RSHERMAN",
    "LO2": "3100",
    "LOCHIERARCHY": {
        "ORGID": "NPS",
        "LOCHIERARCHYID": 1517752492,
        "SYSTEMID": "PRIMARY",
        "PARENT": "ANIA",
    },
    "SITEID": "P117",
    "LOCATION": "95774",
    "SITE": {"SITEUID": "1005", "PARKALPHA": "ANIA"},
    "LO5": 58,
    "ORGID": "NPS",
    "LO14": "",
    "LO9": 3123.6,
    "LOCOPER": {
        "FLO3": "4",
        "SHIFTNUM": "",
        "LOCOPERID": 3059260311,
        "WARRANTYEXPDATE": None,
    },
    "CHANGEDATE": "2014-02-14T12:24:44-07:00",
    "LO7": 0.082,
}

# Map of common names for keys in example
location_fields = {
    "LO2": "Asset Code",
    "LO5": "API",
    "LO6": "CRV",
    "LO7": "FCI",
    "LO9": "DM",
    "LO11": "Unit of Measure",
    # No Unit of Measure QTY
    # No Aquisition Date
    "LO14": "unknown",  # empty on all records
    "LOCOPER.FL03": "Optimizer Band",
}  # usually blank, occassionally "{UNITCODE}001"

# The Status.maxvalue does not vary for a given status.value
status = {
    "EXCESS": "OPERATING",  # value:maxvalue
    "INACTIVE": "OPERATING",
    "NOTREADY": "NOTREADY",
    "OPERATING": "OPERATING",
    "PLANNED": "NOTREADY",
    "REMOVED": "DECOMMISSIONED",
    "SITE": "OPERATING",
}

# Site Id by Park Unit Code (Site ID is used in URL Query)
sites = {
    "AKRO": "P115",
    "ANCH": "P166",
    "FAIR": "P120",
    "ALEU": "P165",  # empty
    "ALAG": "P116",
    "ANIA": "P117",
    "BELA": "P118",
    "CAKR": "P119",  # empty
    "DENA": "P167",
    "GAAR": "P121",
    "GLBA": "P003",
    "KATM": "P122",
    "KEFJ": "P123",
    "KLGO": "P168",
    "LACL": "P169",
    "KOVA": "P124",  # empty
    "NOAT": "P125",  # empty
    "SITK": "P126",
    "WEAR": "P127",
    "WRST": "P128",
    "YUCH": "P170",
}

# List of Asset Codes seen in All Alaska Sites
assetCodes = {
    0000: "Site",
    1100: "Road",
    1300: "Parking Area",
    1700: "Road Bridge",
    1800: "Road Tunnel",  # not used
    2100: "Trail",
    2200: "Trail Bridge",
    2300: "Trail Tunnel",
    3100: "Grounds",
    3800: "Fence",
    4100: "Building",
    5100: "Utility-Water",
    5200: "Utility-Sewer",
    5300: "Utility-Heat",
    5400: "Utility-Elec",
    5500: "Utility-Comm",
    5700: "Utility-Fuel",
    5800: "Utility-Waste",
    6200: "Constructed Waterway",
    6300: "Marina/Waterfront System",
    6400: "Aviation System",
    7100: "Monument",
    7200: "Maintained Archeological Sites",
    7400: "Towers/Missile Silos",
    7500: "Intepretive Media",
    7900: "Amphitheater",
}


def my_str(s):
    if s:
        return "{0}".format(s)
    else:
        return ""


def locations(park):
    page = 1
    done, data = locations_page(park, page)
    while not done:
        page += 1
        done, moredata = locations_page(park, page)
        data += moredata
    return data


def locations_page(park, page):
    try:
        f = urllib2.urlopen(location_url.format(sites[park], page))
    except HTTPError:
        print("Unable to retrieve Location page {0} for {1}.".format(page, park))
        return False, []

    data = json.load(f)
    # print(data)
    total_pages = data["TotalPages"]  # maybe 0 if there is no data
    current_page = data["Page"]  # will always be 1 or greater
    done = current_page >= total_pages
    data = location_data(data["PagedList"], park)
    return done, data


def location_data(page, park):
    data = []
    for item in page:
        try:
            parent_org = item["LOCHIERARCHY"]["ORGID"]
        except KeyError:
            parent_org = None
        try:
            parent_location = item["LOCHIERARCHY"]["PARENT"]
        except KeyError:
            parent_location = None
        try:
            opt = item["LOCOPER"]["FL03"]
        except KeyError:
            opt = None
        values = [
            park,
            item["LO2"],
            item["LOCATION"],
            item["DESCRIPTION"],
            item["STATUS"]["Value"],
            parent_location,
            item["LO5"],
            item["LO6"],
            item["LO7"],
            item["LO9"],
            item["LO11"],
            item["STATUS"]["maxvalue"],
            item["ORGID"],
            parent_org,
            item["LO14"],
            opt,
            item["LOCATIONSID"],
        ]
        data.append(values)
    return data


loc_header = [
    "Park",
    "Asset_Code",
    "Location",
    "Description",
    "Status",
    "Parent_Location",
    "API",
    "CRV",
    "FCI",
    "DM",
    "Unit_of_Measure",
    "StatusMax",
    "Organization",
    "Parent_Organization",
    "Unknown",
    "Optimizer_Band",
    "LocationsId",
]


def lshowone(park, csv_path=None):
    if csv_path:
        with csv23.open(csv_path, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv23.write(csv_writer, loc_header)
            for row in locations(park):
                csv23.write(csv_writer, row)
    else:
        print(",".join(loc_header))
        for item in locations(park):
            print(",".join([my_str(x) for x in item]))


def lshowall(csv_path=None):
    if csv_path:
        with csv23.open(csv_path, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv23.write(csv_writer, loc_header)
            for park in sites:
                for row in locations(park):
                    csv23.write(csv_writer, row)
    else:
        print(",".join(loc_header))
        for park in sites:
            for item in locations(park):
                print(",".join([my_str(x) for x in item]))


def assets(park):
    page = 1
    done, data = assets_page(park, page)
    while not done:
        page += 1
        done, moredata = assets_page(park, page)
        data += moredata
    return data


def assets_page(park, page):
    try:
        f = urllib2.urlopen(asset_url.format(sites[park], page))
    except HTTPError:
        print("Unable to retrieve Asset page {0} for {1}.".format(page, park))
        return False, []

    data = json.load(f)
    f.close()
    # print(data)
    total_pages = data["TotalPages"]
    current_page = data["Page"]
    print(park, current_page, total_pages)
    done = current_page >= total_pages
    data = asset_data(data["PagedList"], park)
    return done, data


def asset_data(page, park):
    data = []
    for page in page:
        try:
            parent_org = page["LOCHIERARCHY"]["ORGID"]
        except KeyError:
            parent_org = None
        try:
            parent_location = page["LOCHIERARCHY"]["PARENT"]
        except KeyError:
            parent_location = None
        try:
            opt = page["LOCOPER"]["FL03"]
        except KeyError:
            opt = None
        values = [
            park,
            page["ASSETTYPE"],
            page["EQ4"],
            page["ASSETID"],
            page["ASSETNUM"],
            page["ASSETUID"],
            page["LOCATION"],
            page["DESCRIPTION"],
            page["EQ19"],
            page["EQ20"],
            page["EQ21"],
            page["EQ5"],
            page["EQ6"],
            page["EQ7"],
            page["EQ8"],
            page["EQ9"],
            page["INSTALLDATE"],
            page["REPLACECOST"],
            page["ORGID"],
            parent_org,
            parent_location,
            opt,
        ]
        data.append(values)
    return data


asset_header = [
    "Park",
    "Asset_Type",
    "Asset_Code",
    "Asset_ID",
    "Asset_UID",
    "Asset_Num",
    "Location",
    "Description",
    "unk19",
    "unk20",
    "unk21",
    "unk5",
    "unk6",
    "Quantity",
    "Unit_of_Measure",
    "Expiration_Date",
    "Install_Date",
    "Replacement_Cost",
    "Organization",
    "Parent_Org",
    "Parent_Loc",
    "Opt",
]


def ashowone(park, csv_path=None):
    if csv_path:
        with csv23.open(csv_path, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv23.write(csv_writer, asset_header)
            for row in assets(park):
                csv23.write(csv_writer, row)
    else:
        print(",".join(asset_header))
        for item in assets(park):
            print(",".join([my_str(x) for x in item]))


def ashowall(csv_path=None):
    if csv_path:
        with csv23.open(csv_path, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv23.write(csv_writer, asset_header)
            for park in sites:
                for row in assets(park):
                    csv23.write(csv_writer, row)
    else:
        print(",".join(asset_header))
        for park in sites:
            for item in assets(park):
                print(",".join([my_str(x) for x in item]))


# lshowall('fmss.csv')
# lshowone('AKRO')
ashowall("assets.csv")
# ashowone('KLGO','klgo.csv')
# ashowone('LACL','lacl.csv')
