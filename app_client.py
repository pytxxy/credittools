import rpyc

def connect_with_name(data):
    conn = rpyc.connect_by_service('central_control')
    result = conn.root.process(data)
    print(f'result: {result}')
    conn.close()


def main():
    connect_with_name()

if __name__ == '__main__':
    main()