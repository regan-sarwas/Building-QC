import csv
import os.path

i = 0
items = []
with open(r'T:\PROJECTS\AKR\FMSS\PHOTOS\PROCESSING\PhotoCSVLoader.csv') as f:
    csv_reader = csv.reader(f)
    for row in csv_reader:
        i += 1
        if i == 1:
            continue
        name = row[1]
        folder = row[6]
        if not name or not folder:
            print "Bad record at line", i
            continue
        # path = os.path.join(r'T:\PROJECTS\AKR\FMSS\PHOTOS\ORIGINAL', name)
        path = os.path.join(folder, name)
        # if not folder.upper().startswith(r'T:\PROJECTS\AKR\FMSS\PHOTOS\ORIGINAL'):
        if not os.path.exists(path):
            items.append((path, i))

for path, i in sorted(items):
    print "Path not found at line", i, path