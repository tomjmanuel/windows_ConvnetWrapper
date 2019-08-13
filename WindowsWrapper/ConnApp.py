#Tom 8/12/19

from Tkinter import *
from tkFileDialog import askopenfilename
from skimage import io
from skimage import img_as_ubyte as i2u
import numpy as np
import paramiko
import os
from string import find


def runApp():
	
	#This is functioning as my main() sorry...

	filename = askopenfilename(parent=root)
	print('filename: ')
	print(filename)
	image = io.imread(filename)

	#create the deltaF image that the neural net uses
	dF = getdF(image)
	imout = scaleIm(dF)

	#get only short filename
	fnameshort = getShortF(filename)
	filename2 = filename[0:-4] + 'dF.tif'
	io.imsave(filename2,imout)
	print('image saved: ')
	print(filename2)

	#push the new image into a new directory for this data set
	print('Pushing dF image to Linux server for cell detection')
	pushFile(fnameshort,filename2)

	#update the main_config file in the remote directory to point at this data set
	#this edits the local copy of main.config, and pushes it to the remote directory
	print('Updating main_config')
	updateConfig(fnameshort)

	#now runn neural net
	print('Running neural net')
	runZNN()

	#scp the output of the neural net back to a local directory
	print('\nGetting output')
	getOutput(fnameshort)

	#run visualize applet
	print('Running Visualize applet')

def getOutput(fname):

	# pull files from remote dir
	filenameshort = fname
	remoteDir = 'caskeylab@caskeylab-HP-Z820-Workstation:Tom/ConvnetCellDetection/data/Try3/' 
	getFiles = 'pscp -r -pw ultrasound ' + remoteDir + filenameshort + '_postprocessed .'
	os.system(getFiles)
	
	
def getdF(im0):
	#implement dF code
	dim = im0.shape
	ni = np.zeros(dim)
	
	#these make the dF more visible (reset the changes)
	w2 = 20
	inc = 20 #will reset change every 20 frames
	baseFrame = 0
	for i in range (dim[0]):
		if i!=0:	
			ni[i,:,:] = im0[i,:,:] - im0[baseFrame,:,:]
			if i>w2:
				w2 = w2+inc
				if w2>dim[0]-10:
					w2 = dim[0]-10
					baseFrame = w2
	return ni
	
def scaleIm(im0):
	#scale image and convert to int
	im0 = im0 - np.min(im0);
	im0 = np.divide(im0,np.max(im0))
	
	#here im0 is between 0 and 1
	# cast range between -1 and 1
	#im0 = np.multiply(np.subtract(im0,0.5),2)

	#convert to unsigned integer
	im0 = i2u(im0)
	
	return im0
	
def pushFile(fnameshort,filename2):

	#fnameshort is used to make new directory
	#filename2 is the dF file to push over to server

	#mk new directory 
	ssh_client = paramiko.SSHClient()
	ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	username = 'caskeylab'
	hostname = 'caskeylab-HP-Z820-Workstation'
	password = 'ultrasound'
	ssh_client.connect(hostname, 22, username, password)
	mkfol = 'mkdir Tom/ConvnetCellDetection/data/Try3/' + fnameshort[0:-4]
	cmd = mkfol
	#print(cmd)
	#executte the commands mkfol
	stdin, stdout, stderr= ssh_client.exec_command(cmd)
	#print(stderr.readlines())
	ssh_client.close();
	
	#use putty command to push file
	remoteDir = 'caskeylab@caskeylab-HP-Z820-Workstation:Tom/ConvnetCellDetection/data/Try3/' + fnameshort[0:-4] + '/'
	putFile = 'pscp -pw ultrasound ' + filename2 + ' ' + remoteDir
	print(putFile)
	os.system(putFile)
	
def getShortF(filename):
	#reverse
	fRev = filename[::-1] 

	#search for \
	ind = fRev.find('/')
	fShortRev = fRev[0:ind]
	return fShortRev[::-1]
	
def updateConfig(fnameshort):
	#update main config

	#edite the data_dir line
	with open('main_config.cfg', 'r') as file:
		# read a list of lines into data
		data = file.readlines()

	# now change the 2nd line, note that you have to add a newline
	newFolder = fnameshort[0:-4] + '/ \n'
	data[1] = 'data_dir = ../data/Try3/' + newFolder

	# and write everything back
	with open('main_config.cfg', 'w') as file:
		file.writelines( data )

	# push it to remote dir
	remoteDir = 'caskeylab@caskeylab-HP-Z820-Workstation:Tom/ConvnetCellDetection/data/Try3/'
	putFile = 'pscp -pw ultrasound main_config.cfg ' + remoteDir
	os.system(putFile)

def runZNN():
	ssh_client = paramiko.SSHClient()
	ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	username = 'caskeylab'
	hostname = 'caskeylab-HP-Z820-Workstation'
	password = 'ultrasound'
	ssh_client.connect(hostname, 22, username, password)
	move = 'cd Tom/ConvnetCellDetection/src; '
	run = '/home/caskeylab/anaconda3/envs/Conv2/bin/python pipeline.py complete ../data/Try3/main_config.cfg; '
	cmd = move + run;

	stdin, stdout, stderr= ssh_client.exec_command(cmd)
	print(stdout.readlines())
	print(stderr.readlines())
	ssh_client.close();
	
   

root = Tk()
menubar = Menu(root)
filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Open", command=runApp)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

root.config(menu=menubar)
root.mainloop()

