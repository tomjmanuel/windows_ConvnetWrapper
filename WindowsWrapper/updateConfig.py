#update main config
with open('main_config.cfg', 'r') as file:
    # read a list of lines into data
    data = file.readlines()

# now change the 2nd line, note that you have to add a newline
newFolder = 'heyo \n'
data[1] = 'data_dir = ..\data\Try3\\' + newFolder

# and write everything back
with open('main_config.cfg', 'w') as file:
    file.writelines( data )