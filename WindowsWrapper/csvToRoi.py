#libs for csv reading
import csv
import os
#libs nec for ROI handling
from ij.plugin.frame import RoiManager
from ij.gui import OvalRoi
RoiManager()
b = RoiManager.getInstance()
#x = OvalRoi(322, 144, 108, 104)
#b.addRoi(x)
print(os.getcwd())

fn = 'C:/Users/tomjm/Documents/CellDetect/src/data31_postprocessed/data31_ROIsManual.csv'
# set radius
r=5

with open(fn) as csvfile:
	readCSV = csv.reader(csvfile,delimiter=',')
	for row in readCSV:
		xc = int(row[0])+10
		yc = int(row[1])+10
		
		x = OvalRoi(xc-r, yc-r, 2*r, 2*r)
		b.addRoi(x)