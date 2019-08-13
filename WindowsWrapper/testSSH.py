import os
# push it to remote dir
filenameshort = 'data31'
remoteDir = 'caskeylab@caskeylab-HP-Z820-Workstation:Tom/ConvnetCellDetection/data/Try3/' 

#putFile = 'pscp -pw ultrasound main_config.cfg ' + remoteDir

getFiles = 'pscp -r -pw ultrasound ' + remoteDir + filenameshort + '_postprocessed .'
print(getFiles)
os.system(getFiles)