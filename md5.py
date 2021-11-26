import sys
import hashlib
import os.path

def main():
    filename = sys.argv[1]
    if os.path.isfile(filename):
        fp = open(filename,'rb')
        contents = fp.read()
        fp.close()
        print(hashlib.md5(contents).hexdigest())
    else:
      print('file not exists')

if __name__ == '__main__':
    main()