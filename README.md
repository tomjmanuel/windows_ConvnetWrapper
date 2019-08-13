# windows_ConvnetWrapper
A python wrapper for using NoahApthorpe/ConvnetCellDetection from a windows machine. 
Due to incompatability between Docker for Windows and Virtualbox, ConvnetCellDetection is incompatible with Windows. There may be a work around using the older "docker tools", but docker tools does not allow mounting a virtual machine to a container in Windows, which made the process complicated.

Rather than set up the software on windows, this implementation sends data to a linux machine with ConvnetCellDetection installed, which gets around the incompatibility of the Convnet with Windows.

<h4>Setup</h4>

-install python 2.7

-clone the repository to a local directory

-setup a virtual environment with the packages listed in requirements.txt

change Hostnames, IP addresses, and passwords in ConnApp.py to match your linux server

run ConnApp.py from within virtualEnv

Open a file, it will get sent to the linux machine for cell detection. The machine will send back cells that the neural net found!
You can then adjust roi thresholder and save the outputs. The output of these is compatible with imageJ.
