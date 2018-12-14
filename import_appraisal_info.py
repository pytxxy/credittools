import argparse
import os
import json
import sqlite3


import creditutils.trivial_util as utility


class Flag:
    src = 'src'
    dst = 'dst'
    func = 'func'

    user = 'user'
    result = 'result'
    feedback = 'feedback'

    name = 'name'
    role = 'role'
    ratio = 'ratio'
    score = 'score'
    result = 'result'
    adjust = 'adjust'
    comment = 'comment'
    dimension = 'dimension'


class GradeType:
    none = 0
    excellent = 1
    good = 2
    qualified = 3
    fail = 4


class GradeTypeStr:
    none = ''
    excellent = '优秀'
    good = '良好'
    qualified = '合格'
    fail = '待改进'


GRADE_TYPE_NAME_MAP = {
    GradeType.none: GradeTypeStr.none,
    GradeType.excellent: GradeTypeStr.excellent,
    GradeType.good: GradeTypeStr.good,
    GradeType.qualified: GradeTypeStr.qualified,
    GradeType.fail: GradeTypeStr.fail,
}


GRADE_NAME_TYPE_MAP = {
    GradeTypeStr.none: GradeType.none,
    GradeTypeStr.excellent: GradeType.excellent,
    GradeTypeStr.good: GradeType.good,
    GradeTypeStr.qualified: GradeType.qualified,
    GradeTypeStr.fail: GradeType.fail,
}


# 最终考核成绩类
class Grade:
    NAME_FLAG = 'name'
    INDEX_FLAG = 'index'

    def __init__(self):
        pass

    def get_grade_by_score(score):
        grade = GradeType.none

        if score >= 90:
            grade = GradeType.excellent
        elif score >= 80:
            grade = GradeType.good
        elif score >= 60:
            grade = GradeType.qualified
        elif score >= 40:
            grade = GradeType.fail

        return grade

    # 根据grade类型获取grade名称
    def get_grade_name(grade):
        if isinstance(grade, str):
            grade = int(grade)

        return GRADE_TYPE_NAME_MAP[grade]

    # 根据grade名称获取grade类型
    def get_grade_type(name):
        return GRADE_NAME_TYPE_MAP[name]

    def get_grade_view_info():
        results = []
        for k in GRADE_TYPE_NAME_MAP:
            item = dict()
            item[Grade.NAME_FLAG] = GRADE_TYPE_NAME_MAP[k]
            item[Grade.INDEX_FLAG] = str(k)
            results.append(item)

        return results

    get_grade_by_score = staticmethod(get_grade_by_score)
    get_grade_name = staticmethod(get_grade_name)
    get_grade_type = staticmethod(get_grade_type)
    get_grade_view_info = staticmethod(get_grade_view_info)


# 打开数据库
def db_open(file_path):
    conn = sqlite3.connect(file_path)

    # 解决sqlite3中读取中文报错的问题
    # conn.text_factory = str

    cur = conn.cursor()

    return cur, conn


# 关闭数据库
def db_close(cur, conn):
    cur.close()
    conn.close()


class ProcessManager:
    TABLE_MAP = {
        Flag.user: {
            Flag.src: 'appraise_user',
            Flag.dst: 'appraise_user',
            Flag.func: 'import_user_info',
        },
        Flag.result: {
            Flag.src: 'appraise_userinfo',
            Flag.dst: 'appraise_monthrecord',
            Flag.func: 'import_result_info',
        },
        Flag.feedback: {
            Flag.src: 'appraise_userinfo',
            Flag.dst: 'appraise_feedback',
            Flag.func: 'import_feedback_info',
        }
    }

    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.src = os.path.abspath(self.src)
        self.dst = os.path.abspath(self.dst)

    def process(self):
        item_map = ProcessManager.TABLE_MAP[self.import_type]
        src_table = item_map[Flag.src]
        dst_table = item_map[Flag.dst]
        func = getattr(self, item_map[Flag.func])
        func(src_table, dst_table)

    # 将老数据库中的密码导入，保持用户密码不变
    def import_user_info(self, src_table, dst_table):
        src_cur, src_conn = db_open(self.src)
        dst_cur, dst_conn = db_open(self.dst)

        query_sql = 'select email,password from {};'.format(src_table)
        # print(query_sql)
        results = src_cur.execute(query_sql).fetchall()
        for item in results:
            update_sql = 'update {} set password="{}" where email="{}";'.format(dst_table, item[1], item[0])
            # print('item: ' + str(item))
            # print('update_sql: ' + update_sql)
            dst_cur.execute(update_sql)
        dst_conn.commit()
        print('Total update {} items.'.format(len(results)))

        db_close(dst_cur, dst_conn)
        db_close(src_cur, src_conn)

    def _get_result_record_info(cur, uid, score, result, adjust, comment):
        rec_data_map = None
        pos_id = None
        version = 0
        query_sql_format = 'select {user}.username as name, {user}.role as role, {pos_info}.pos_id as pos_id, ' \
                    '{pos}.version as version, {dim_info}.info as dim_info from {pos_info} ' \
                    'inner join {pos} on ({pos_info}.pos_id = {pos}.pos_id) ' \
                    'inner join {user} on ({pos_info}.member_id = {user}.email) ' \
                    'inner join {dim_info} on ({pos_info}.pos_id = {dim_info}.pos_id) where {pos_info}.member_id="{uid}";'
        data_map = dict()
        data_map['user'] = 'appraise_user'
        data_map['pos_info'] = 'appraise_positioninfo'
        data_map['pos'] = 'appraise_position'
        data_map['dim_info'] = 'appraise_positiondimensioninfo'
        data_map['uid'] = uid
        query_sql = query_sql_format.format(**data_map)
        print(query_sql)
        items = cur.execute(query_sql).fetchall()
        if items:
            item = items[0]

            print('results count {}.'.format(len(items)))
            print('item: '+str(item))

            rec_data_map = dict()
            rec_data_map[Flag.name] = item[0]
            rec_data_map[Flag.role] = item[1]
            rec_data_map[Flag.score] = score
            rec_data_map[Flag.result] = result
            rec_data_map[Flag.comment] = comment
            rec_data_map[Flag.adjust] = adjust
            dim_map = json.loads(item[4])
            for k in dim_map:
                dim_map[k][Flag.score] = '0'
            rec_data_map[Flag.dimension] = dim_map

            pos_id = item[2]
            version = int(item[3])

        return pos_id, version, rec_data_map

    def import_result_info(self, src_table, dst_table):
        src_cur, src_conn = db_open(self.src)
        dst_cur, dst_conn = db_open(self.dst)

        query_sql = 'select email,month,score,rank,rank_toHR,comment from {} where month<3;'.format(src_table)
        # print(query_sql)
        results = src_cur.execute(query_sql).fetchall()
        for item in results:
            print('item: '+str(item))
            uid = item[0]
            year = 2018
            month = item[1]
            score = item[2]
            if item[3]:
                result = str(Grade.get_grade_type(item[3]))
            else:
                result = str(GradeType.none)

            if item[4]:
                adjust = str(Grade.get_grade_type(item[4]))
            else:
                adjust = str(GradeType.none)

            comment = item[5]
            pos_id, version, rec_data_map = ProcessManager._get_result_record_info(dst_cur, uid, score, result, adjust, comment)
            rec_data = json.dumps(rec_data_map)
            update_sql_fmt = "insert into {} (member_id, year, month, pos_id, version, record) values ('{}', {}, {}, '{}', {}, '{}');"
            update_sql = update_sql_fmt.format(dst_table, uid, year, month, pos_id, version, rec_data)
            print('item: ' + str(item))
            print('update_sql: ' + update_sql)
            dst_cur.execute(update_sql)
        dst_conn.commit()
        print('Total insert {} items.'.format(len(results)))

        db_close(dst_cur, dst_conn)
        db_close(src_cur, src_conn)

    def import_feedback_info(self, src_table, dst_table):
        src_cur, src_conn = db_open(self.src)
        dst_cur, dst_conn = db_open(self.dst)

        query_sql = 'select email,month,feedback from {} where feedback is not null and feedback!="" ' \
                    'and feedback!="无";'.format(src_table)
        print(query_sql)
        results = src_cur.execute(query_sql).fetchall()
        for item in results:
            update_sql = 'insert into {} (member_id, year, month, feedback) values ("{}", 2018, {}, "{}");'.format(dst_table, item[0], item[1], item[2])
            print('item: ' + str(item))
            print('update_sql: ' + update_sql)
            dst_cur.execute(update_sql)
        dst_conn.commit()
        print('Total insert {} items.'.format(len(results)))

        db_close(dst_cur, dst_conn)
        db_close(src_cur, src_conn)

    def _update_single_user_result_info(self, src_table, dst_table, uid):
        src_cur, src_conn = db_open(self.src)
        dst_cur, dst_conn = db_open(self.dst)

        query_sql = 'select email,month,score,rank,rank_toHR,comment from {} where month<3 and email="{}";'.format(src_table, uid)
        # print(query_sql)
        results = src_cur.execute(query_sql).fetchall()
        for item in results:
            print('item: '+str(item))
            uid = item[0]
            year = 2018
            month = item[1]
            score = item[2]
            if item[3]:
                result = str(Grade.get_grade_type(item[3]))
            else:
                result = str(GradeType.none)

            if item[4]:
                adjust = str(Grade.get_grade_type(item[4]))
            else:
                adjust = str(GradeType.none)

            comment = item[5]
            pos_id, version, rec_data_map = ProcessManager._get_result_record_info(dst_cur, uid, score, result, adjust, comment)
            rec_data = json.dumps(rec_data_map)
            update_sql_fmt = "update {} set pos_id='{}', version={}, record='{}' where member_id='{}' and year={} and month={};"
            update_sql = update_sql_fmt.format(dst_table, pos_id, version, rec_data, uid, year, month)
            print('item: ' + str(item))
            print('update_sql: ' + update_sql)
            dst_cur.execute(update_sql)
        dst_conn.commit()
        print('Total insert {} items.'.format(len(results)))

        db_close(dst_cur, dst_conn)
        db_close(src_cur, src_conn)

    def update_single_user_result_info(self, uid):
        item_map = ProcessManager.TABLE_MAP[Flag.result]
        src_table = item_map[Flag.src]
        dst_table = item_map[Flag.dst]
        self._update_single_user_result_info(src_table, dst_table, uid)

    _get_result_record_info = staticmethod(_get_result_record_info)


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='import old data to new system.')
    parser.add_argument('src', metavar='src', help='source file to import')
    parser.add_argument('dst', metavar='dst', help='target file')
    parser.add_argument('--type', metavar='import_type', dest='import_type', type=str, default='user',
                        choices=['user', 'result', 'feedback'],
                        help='user: user table; result: appraisal result table; feedback: appraisal feedback table;')

    #     parser.print_help()

    return parser.parse_args(src_args)


def main(src_args):
    manager = ProcessManager(src_args)
    manager.process()
    # 可以更新单条数据
    # manager.update_single_user_result_info('liyy@pycredit.cn')


if __name__ == '__main__':
    #     test_args = 'a b -i -u'.split()
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)