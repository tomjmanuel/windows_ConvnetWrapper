##########################################################
#
# Module to run ZNN commands in a Docker container
#
# Author: Alex Riordan
#
# Description: Python interface to ZNN running in Docker
#
##########################################################

import subprocess
import ConfigParser
import os
import signal
from create_znn_files import dockerize_path
from preprocess import remove_ds_store, add_pathsep


def start_docker_machine(memory, machine_name):
    '''Input: memory allocates memory (in MB) to docker-machine'''
    cmd = ''
    cmd += 'docker-machine create -d virtualbox --virtualbox-memory ' + memory + ' ' + machine_name + '; ' 
    cmd += 'docker-machine start ' + machine_name + '; ' 
    cmd += 'eval $(docker-machine env ' + machine_name + ')' 
    # cmd += ' ;docker run hello-world' #for testing
    return cmd


def start_znn_container(dir_to_mount, container_name):
    cmd = ''
    cmd += 'docker run -v ' + dir_to_mount + ':/opt/znn-release/ConvnetCellDetection '
    cmd += '--name ' + container_name + ' -it jpwu/znn:v0.1.4 ' + '/bin/bash -c '
    return cmd


def train_network(output_dir):
    output_dir = dockerize_path(output_dir)
    cmd = ''
    cmd += '"cd opt/znn-release/python; sudo ldconfig; python train.py -c ' + output_dir + 'znn_config.cfg"'
    return cmd


def forward_pass(output_dir):
    output_dir = dockerize_path(output_dir)
    cmd = ''
    cmd += '"cd opt/znn-release/python; sudo ldconfig; python forward.py -c ' + output_dir + 'znn_config.cfg"'
    return cmd


def remove_znn_container(container_name, machine_name, stop_machine):
    cmd = ''
    cmd += '; docker stop ' + container_name + '; docker rm ' + container_name + '; '
    if stop_machine:
        cmd += 'docker-machine stop ' + machine_name
    return cmd


def rename_output_files(cfg_parser, main_config_fpath, forward_output_dir):
    '''Maps ZNN output fnames back to user-given fnames'''
    dict_list = cfg_parser.items('fnames')
    for item in dict_list:
        number = item[0]
        fname = item[1]
        old_fname = forward_output_dir + '/_sample' + str(number)
        new_fname = forward_output_dir + '/' + fname.split('/')[-1]
        os.rename(old_fname + '_output.h5', new_fname + '_output.h5')
        os.rename(old_fname + '_output_0.tif', new_fname + '_output_0.tif')
        os.rename(old_fname + '_output_1.tif', new_fname + '_output_1.tif')

        
def main(main_config_fpath='../data/example/main_config.cfg', run_type='forward'):
    cfg_parser = ConfigParser.SafeConfigParser()
    cfg_parser.readfp(open(main_config_fpath, 'r'))
    memory = cfg_parser.get('docker', 'memory')
    use_docker_machine = cfg_parser.getboolean('docker', 'use_docker_machine')
    container_name = cfg_parser.get('docker', 'container_name')
    machine_name_prefix = cfg_parser.get('docker', 'machine_name')
    machine_name = machine_name_prefix + "-" + memory.strip()
    training_output_dir = add_pathsep(cfg_parser.get('training', 'training_output_dir'))
    data_dir = add_pathsep(cfg_parser.get('general', 'data_dir'))[0:-1]
    forward_output_dir = add_pathsep(data_dir + "_training_output")
   
    dir_to_mount = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Mounts ConvnetCellDetection directory
    print dir_to_mount

    cmd = ''
    if use_docker_machine:
        cmd += start_docker_machine(memory, machine_name)
        cmd += '; '
    cmd += start_znn_container(dir_to_mount, container_name)

    if run_type == 'training':
        cmd += train_network(training_output_dir) + remove_znn_container(container_name, machine_name, use_docker_machine)
    elif run_type == 'forward':
        cmd += forward_pass(forward_output_dir) + remove_znn_container(container_name, machine_name, use_docker_machine)
    else:
        cmd += remove_znn_container(container_name, machine_name, use_docker_machine)
        raise ValueError('run_type variable should be one of "forward" or "training"', run_type)

    print cmd
    process = subprocess.Popen(cmd, shell=True)
    process.communicate()

    if run_type == 'forward':
        rename_output_files(cfg_parser, main_config_fpath, forward_output_dir)
        cfg_parser.remove_section('fnames')
        with open(main_config_fpath, 'w') as main_config_file:
            cfg_parser.write(main_config_file)


if __name__ == "__main__":
    main()
