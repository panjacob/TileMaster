import threading
import time
import os
from typing import List


def relative_to_absolute_path(current_file, target):
    return os.path.join(os.path.dirname(os.path.abspath(current_file)), target)


def threaded_map(data_list: list, callback, worker_count: int) -> None:
    initial_length = len(data_list)
    result = []

    start_time = time.time()

    def thread_worker():
        while data_list:
            popped = data_list.pop()
            try:
                result.append(callback(popped))
            except Exception as e:
                print(f"ERROR IN THREADED MAP WHILE WORKING ON {popped}", e)

    workers = list()
    for i in range(worker_count):
        x = threading.Thread(target=thread_worker)
        x.start()
        workers.append(x)

    while data_list:
        print('\r\n%.2f' % ((1 - len(data_list) / initial_length) * 100) + '%')
        time.sleep(1)

    for i in workers:
        i.join()

    print('Done in', time.time() - start_time, 'seconds')
    if len(result) != initial_length:
        print(f'WARNING! Initial length was {initial_length}, now it\'s {len(result)}')

    data_list.__iadd__(result)


def sum_list(data: List[list]) -> list:
    result = []
    for i in data:
        result += i
    return result
