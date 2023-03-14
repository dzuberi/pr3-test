import numpy as np
import subprocess
from subprocess import DEVNULL
import signal
import time
import shutil
import json

#https://stackoverflow.com/questions/5228158/cartesian-product-of-a-dictionary-of-lists
import itertools

import os
import filecmp
import os.path

def are_dir_trees_equal(dir1, dir2):
    """
    Compare two directories recursively. Files in each directory are
    assumed to be equal if their names and contents are equal.

    @param dir1: First directory path
    @param dir2: Second directory path

    @return: True if the directory trees are the same and 
        there were no errors while accessing the directories or files, 
        False otherwise.
   """

    dirs_cmp = filecmp.dircmp(dir1, dir2)
    if len(dirs_cmp.left_only)>0 or len(dirs_cmp.right_only)>0 or \
        len(dirs_cmp.funny_files)>0:
        return False
    (_, mismatch, errors) =  filecmp.cmpfiles(
        dir1, dir2, dirs_cmp.common_files, shallow=False)
    if len(mismatch)>0 or len(errors)>0:
        return False
    for common_dir in dirs_cmp.common_dirs:
        new_dir1 = os.path.join(dir1, common_dir)
        new_dir2 = os.path.join(dir2, common_dir)
        if not are_dir_trees_equal(new_dir1, new_dir2):
            return False
    return True

def check_diffs():
    client_path = 'courses/ud923/filecorpus/'
    server_path = 'cached_files/'
    return are_dir_trees_equal(client_path, server_path)

    file_list = os.listdir(client_path)

    passed = True;

    for f in file_list:
        comp = filecmp.cmp(client_path+f, server_path+f, shallow=False)
        if (not comp) or (not os.path.exists(server_path+f)):
            print(client_path+f, 'failed')
            passed = False
    # passed = filecmp.dircmp(client_path, server_path)

    return passed
    #     split_at = ".jpg"
    #     index = f.find(split_at)
    #     name = f[0:index+len(split_at)]
    #     comp = filecmp.cmp(client_path+f, server_path+name, shallow=False)
    #     if not comp:
    #         print(client_path+f,'failed')
    #         failed = True
    # if not failed:
    #     print('diff passed :)')
    # else:
    #     print('diff failed')

def create_cross(d):
    keys, values = zip(*d.items())
    args_list = [dict(zip(keys, bundle)) for bundle in itertools.product(*values)]
    # print(args_list)
    args_list_list = []
    for a in args_list:
        new_list_list = []
        for k in a.keys():
            new_list_list.append(k)
            new_list_list.append(str(int(a[k])))
        args_list_list.append(new_list_list)
    return args_list_list

def clean_ipc():
    paths = ["/dev/shm/","/dev/mqueue"]
    for path in paths:
        dir_list = os.listdir(path)
        for file in dir_list:
            os.remove(path,file)

server_exe = './webproxy'
cache_exe = './simplecached'
download_exe = './gfclient_download'

num_each = 2
server_args_dict = {
    '-p' : [6200],
    '-t' : np.linspace(1, 100, num=num_each),
    '-z' : np.linspace(824, 2**20-1, num=num_each),
    '-n' : np.linspace(1, 100, num=num_each),
}

cache_args_dict = {
    '-t' : np.linspace(1, 420, num=num_each),
    '-d' : np.linspace(0, 2500000, num=num_each),
}

downloader_args_dict = {
    '-t' : np.linspace(1,10, num_each)
}

# passed = True

server_args_list = create_cross(server_args_dict)
cache_args_list = create_cross(cache_args_dict)
downloader_args_list = create_cross(downloader_args_dict)
server_args_list.reverse()
# cache_args_list.reverse()

failed_args = []

test_num = 0
num_tests = len(server_args_list) * len(cache_args_list) * len(downloader_args_list)

for server_args in server_args_list:
    for cache_args in cache_args_list:
        for downloader_args in downloader_args_list:
            clean_ipc()
            print('test num', test_num, 'of', num_tests ,server_args, cache_args, downloader_args)
            print('failed tests:', len(failed_args), 'of', num_tests, "|", len(failed_args)/num_tests*100,"%")

            status_dict = {}


            server_process = subprocess.Popen([server_exe, *server_args])#, stdout=DEVNULL)
            status_dict['server'] = ' '.join([server_exe, *server_args])
            cache_process = subprocess.Popen([cache_exe, *cache_args])#, stdout=DEVNULL)
            status_dict['cache'] = ' '.join([cache_exe, *cache_args])
            download_process = subprocess.Popen([download_exe, *downloader_args])
            status_dict['download'] = ' '.join([download_exe, *downloader_args])

            passed  = True
            # try:
            #     download_process.wait(timeout=120)
            # except subprocess.TimeoutExpired:
            #     download_process.send_signal(signal.SIGINT)
            #     passed = False
            #     print('test failed')
            #     failed_args.append(status_dict)
            seconds_passed = 0
            done = False
            while not done:
                if server_process.poll() is not None:
                    status_dict['status'] = "server exited"
                    passed = False
                    done = True
                if cache_process.poll() is not None:
                    passed = False
                    status_dict['status'] = "cache exited"
                    done = True
                if download_process.poll() is not None:
                    done = True
                time.sleep(1)
                seconds_passed += 1
                if seconds_passed > 300:
                    # download_process.send_signal(signal.SIGINT)
                    download_process.kill()
                    print('download timed out, killing')
                    passed = False
                    status_dict['status'] = "download timed out"
                    done = True
                    
            download_process.send_signal(signal.SIGINT)
            server_process.send_signal(signal.SIGINT)
            cache_process.send_signal(signal.SIGINT)
            server_process.wait()
            cache_process.wait()
            download_process.wait()

            if passed and not check_diffs():
                passed = False
                print('test failed')
                status_dict['status'] = "diff failed"
                # failed_args.append(status_dict)
                # print('test failed','server_args',server_args,'cache_args',cache_args)
            if not passed:
                print('test failed with status',status_dict['status'])
                failed_args.append(status_dict)
            time.sleep(1)
            shutil.rmtree('courses', ignore_errors=True)
            time.sleep(.1)
            test_num += 1
pass_rate = (num_tests - len(failed_args)) / num_tests*100
# if len(failed_args) == 0:
#     print("All tests passed :)")
# else:
#     print()
print(failed_args)
print("pass rate:", pass_rate)
with open("failed_args.json","w") as fp:
    json.dump(failed_args, fp)