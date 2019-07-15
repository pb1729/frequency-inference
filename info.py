import numpy as np
from sys import argv
from util import load_data

MAXSTRLEN = 100

def main():
    data = load_data(argv[1])
    for key in data:
        s = str(data[key])
        if len(s) < MAXSTRLEN or key == 'get_get_strat':
            print(key, ':', s)

if __name__ == '__main__':
    main()
