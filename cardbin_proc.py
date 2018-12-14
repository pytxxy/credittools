# -*- coding:UTF-8 -*-

'''
Created on 2016年5月16日

@author: caifh
'''
import json
import re
import creditutils.file_util as myfile
import pprint
import argparse
import creditutils.trivial_util as utility
import os
# import xlrd
import creditutils.excel_util as excel
import operator


def generate_test_card_info(rec_file_name, target_file_name):
    lines = myfile.read_file_lines(rec_file_name)
    recs = []
    rec_split_str = ','
    for line in lines:
        if line and not line.isspace():
            items = line.strip().split(rec_split_str)
            if items and len(items) > 2:
                rec_item = '  {{card="{}", name="{}", code={}}}'.format(items[1], items[0], items[2])
                recs.append(rec_item)
            else:
                print('error: ' + items)
        else:
            print('error: ' + line)

    str_recs = ',\r\n'.join(recs)
    str_info = '{{\r\n{}\r\n}}'.format(str_recs)
    myfile.write_to_file(target_file_name, str_info, 'utf-8')


def generate_prefix_map_from_info(name_map_file, rec_file_name, target_file_name):
    map_lines = myfile.read_file_lines(name_map_file)
    name_map = {}
    for line in map_lines:
        if line and not line.isspace():
            items = line.split(',')
            if items and len(items) > 1:
                name_map[items[0].strip()] = items[1].strip()
            else:
                print('error: ' + items)
        else:
            print('error: ' + line)

    lines = myfile.read_file_lines(rec_file_name)

    recs = []
    for line in lines:
        if line and not line.isspace():
            ptn_str = '^\s*{\s*prefix\s*=\s*"(\d+)",\s*name\s*=\s*"([\u2e80-\ua4cf]+)",'
            ptn = re.compile(ptn_str)
            match_rlt = ptn.match(line)
            if match_rlt:
                k = match_rlt.group(1)
                name = match_rlt.group(2)

                rec_item = '  {{prefix = "{}", index = {}}}'.format(k, name_map[name])
                recs.append(rec_item)
            else:
                print('error: ' + items)
        else:
            print('error: ' + line)

    str_info = ',\r\n'.join(recs)
    myfile.write_to_file(target_file_name, str_info, 'utf-8')


def add_prefix_map_to_info(name_map_file, rec_file_name, target_file_name):
    map_lines = myfile.read_file_lines(name_map_file)
    name_map = {}
    for line in map_lines:
        if line and not line.isspace():
            items = line.split(',')
            if items and len(items) > 1:
                name_map[items[0].strip()] = items[1].strip()
            else:
                print('error: ' + items)
        else:
            print('error: ' + line)

    lines = myfile.read_file_lines(rec_file_name)

    recs = []
    for line in lines:
        if line and not line.isspace():
            ptn_str = '^\s*{\s*prefix\s*=\s*"(\d+)",\s*name\s*=\s*"([\u2e80-\ua4cf]+)",'
            ptn = re.compile(ptn_str)
            match_rlt = ptn.match(line)
            if match_rlt:
                k = match_rlt.group(1)
                name = match_rlt.group(2)

                rec_reserved = line.strip()
                if rec_reserved.endswith(','):
                    rec_reserved = rec_reserved[:-1]

                rec_reserved = rec_reserved[:-1]

                rec_item = '  {}, index={}}}'.format(rec_reserved, name_map[name])
                recs.append(rec_item)
            else:
                print('error: ' + items)
        else:
            print('error: ' + line)

    str_info = ',\r\n'.join(recs)
    myfile.write_to_file(target_file_name, str_info, 'utf-8')


class Label:
    cardbin = 'CARDBIN'
    samecarddiff = 'SAMECARDDIFF'
    headoffice = 'HEADOFFICE'
    nature = 'NATURE'
    cardnolen = 'CARDNOLEN'
    bankcode = 'BANKCODE'

    type_map = {
        cardbin: excel.Ctype.string,
        samecarddiff: excel.Ctype.string,
        headoffice: excel.Ctype.string,
        nature: excel.Ctype.string,
        cardnolen: excel.Ctype.number,
        bankcode: excel.Ctype.string
    }


class DataLabel:
    cardbin = 'cardbin'
    bank = 'bank'  # 银行卡所属银行名称
    type = 'type'  # 银行卡类型
    length = 'length'  # 银行卡号码长度


class CardType:
    name_type_map = {
        '借记卡': 1,
        '贷记卡': 2,
        '借记卡贷记卡': 3,
        '贷记卡(借贷合一卡)': 4,
        '预付费卡': 5,
        '准贷记卡': 6
    }


NAME_MAP = {
    '中国农业银行': '中国农业银行',
    '光大银行': '中国光大银行',
    '中国光大银行': '中国光大银行',
    '工商银行': '中国工商银行',
    '中国工商银行': '中国工商银行',
    '上海银行': '上海银行',
    '中国建设银行': '中国建设银行',
    '华夏银行': '华夏银行',
    '浦发银行': '上海浦东发展银行',
    '浦东发展银行': '上海浦东发展银行',
    '上海浦东发展银行': '上海浦东发展银行',
    '招商银行': '招商银行',
    '中国招商银行': '招商银行',
    '平安银行': '平安银行',
    '民生银行': '中国民生银行',
    '中国民生银行': '中国民生银行',
    '中国银行': '中国银行',
    '中信银行': '中信银行',
    '中信银行信用卡中心': '中信银行',
    '交通银行': '交通银行',
    '中国交通银行': '交通银行',
    '兴业银行': '兴业银行',
    '北京银行': '北京银行',
    '邮储银行': '中国邮政储蓄银行',
    '邮政储蓄银行': '中国邮政储蓄银行',
    '中国邮政储蓄银行': '中国邮政储蓄银行',
    '广发银行': '广发银行',
    '广发银行股份有限公司': '广发银行'
}


class DataProcess:
    def __init__(self, file_path, sheet_index=0):
        self.file_path = file_path
        self.label_table = excel.LabelTable(self.file_path)
        self.sheet_index = sheet_index
        self.data = None

    def process(self):
        if not self.data:
            self.data = []
            table = self.label_table.get_table(self.sheet_index)
            row_cnt = table.nrows
            for i in range(1, row_cnt):
                item = {}
                for label in [Label.cardbin, Label.samecarddiff, Label.headoffice, Label.nature, Label.cardnolen,
                              Label.bankcode]:
                    label_index = self.label_table.get_label_index(label)
                    cell = table.cell(i, label_index)
                    if cell.ctype == Label.type_map[label]:
                        item[label] = cell.value
                    else:
                        item[label] = None
                        print('row {} label {} ctype {} is invalid!'.format(i, label, cell.ctype))

                self.data.append(item)

            # 将cardbin长度统一转换成整型
            for item in self.data:
                value = item[Label.cardnolen]
                sub_item_type = type(value)
                if sub_item_type != int:
                    if sub_item_type == float or sub_item_type == str:
                        item[Label.cardnolen] = int(value)
                    else:
                        raise Exception('invalid value type {}!'.format(sub_item_type))

            # 验证银行名称和编号是否一致，不一致才需要进行映射
            is_consistent = self._verify_bankcode_consistency(self.data)
            if not is_consistent:
                raise Exception('{} and {} is not consistency!'.format(Label.bankcode, Label.headoffice))

            # 校验银行名称映射一致性
            is_consistent = self._verify_bankname_consistency(self.data)
            if not is_consistent:
                raise Exception('{} and target name is not consistency!'.format(Label.headoffice))

            # 只保留必要的数据，其他数据直接滤除
            self.data = self._filter_necessary_data(self.data)

        return self.data

    # 将银行卡信息进行归类，分为需要的银行和非需要的银行的
    def _classify_data(self, items):
        need_data = []
        other_data = []
        for item in items:
            if item[Label.headoffice] in NAME_MAP:
                need_data.append(item)
            else:
                other_data.append(item)

        return need_data, other_data

    # 将必要的银行卡信息过滤出来
    def _filter_necessary_data(self, items):
        set_key_sep = '#'
        set_key_format = '{{}}{}{{}}'.format(set_key_sep)

        need_data, other_data = self._classify_data(items)
        keys = set()
        for i in need_data:
            cardbin = i[Label.cardbin]
            cardnolen = i[Label.cardnolen]
            map_key = set_key_format.format(cardbin, cardnolen)
            keys.add(map_key)

        data = []
        data.extend(need_data)
        for i in other_data:
            cardbin = i[Label.cardbin]
            cardnolen = i[Label.cardnolen]
            map_key = set_key_format.format(cardbin, cardnolen)
            if map_key in keys:
                data.append(i)

        return data

    # 验证银行名称和编号是否一致，不一致才需要进行映射
    def _verify_bankcode_consistency(self, items):
        classify_items = {}
        no_bankcode_items = []

        for item in items:
            bankcode = item[Label.bankcode]
            if bankcode:
                if bankcode not in classify_items:
                    sub_set = set()
                else:
                    sub_set = classify_items[bankcode]

                sub_set.add(item[Label.headoffice])
                classify_items[bankcode] = sub_set
            else:
                bank_name = item[Label.headoffice]
                no_bankcode_items.append(bank_name)
                #                 print('{} has no {}!'.format(bank_name, Label.bankcode))

        is_consistent = True
        for k in classify_items:
            if len(classify_items[k]) > 1:
                is_consistent = False
                print('{} has more than one name: {}'.format(k, classify_items[k]))

                #         print(classify_items)
                #         for item in no_bankcode_items:
                #             print(item)

        return is_consistent

    # 校验从excel表中获取的银行名称和最终实际使用的名称是否一致
    def _verify_bankname_consistency(self, items):
        is_consistent = True
        for item in items:
            bank_name = item[Label.headoffice]
            if bank_name in NAME_MAP:
                target_name = NAME_MAP[bank_name]
                if bank_name != target_name:
                    is_consistent = False
                    print('source {} and target {} is not consistency!'.format(bank_name, target_name))

        return is_consistent


class BankMapLabel:
    id = 'id'
    name = 'name'
    code = 'code'


class CardInfoLabel:
    prefix = 'prefix'
    samediff = 'samediff'
    code = 'code'
    index = 'index'
    length = 'length'


class CardInfoPattern:
    item_unit = '\w+\s*=\s*(?:(?:"[^"]+")|(?:\d+))'
    item_format = '{{{}(?:,\s*{})+}}'
    #     ptn_format = 'local\s+cardInfo\s*=\s*{{\s*({}(?:,\s*{})+)\s*}}'
    ptn_format = '(local\s+cardInfo\s*=\s*{{\s*)({}(?:,\s*{})+)(\s*}})'
    item_unit_capture = '(\w+)\s*=\s*((?:"[^"]+")|(?:\d+))'


class CardInfoIndexPattern:
    item = '\["\d+"\]\s*=\s*{\d+(?:,\s*\d+)*}'
    ptn_format = '(local\s+cardInfoIndex\s*=\s*{{\s*)({}(?:,\s*{})+)(\s*}})'


SIMPLIFY_MAP = {
    'prefix': 'p',
    'code': 'c',
    'index': 'i',
    'length': 'l',
    'samediff': 's'
}


class LuaProcess:
    def __init__(self, file_path, dst_path=None):
        self.file_path = file_path

        # 没有指定目录，则直接回写原始文件
        if dst_path:
            self.dst_path = dst_path
        else:
            self.dst_path = self.file_path

        self.content = None

    def process(self, new_data):
        if self.content == None:
            # 先将原始lua文件读进来，并存储关键信息便于接下来进处理
            self.content = myfile.read_file_content(self.file_path, encoding_='utf-8')

            # 获取银行信息
            self.bank_map = self._get_bank_map(self.content)
            #             print(self.bank_map)

            # 获取银行卡类型信息
            self.card_type_map = self._get_card_type_map(self.content)
            #             print(self.card_type_map)

            self.card_type_map_revert = self._get_revert_map(self.card_type_map)
            #             print(self.card_type_map_revert)

            # 获取原始cardbin信息
            self.ori_card_info = self._get_card_info(self.content)
            #             print(self.ori_card_info)

            is_consistent = self._verify_cardtype_consistency(new_data)
            if not is_consistent:
                raise Exception('{} and original card type is not consistency!'.format(Label.nature))

            # 将新旧两个表合并成最终的表
            self.card_info = self._combine_card_info(self.ori_card_info, new_data)

            # 计算cardbin最大长度
            min_len = 3
            max_len = 6
            curr_min_len, curr_max_len = self._get_max_cardbin_len_range(self.card_info)

            if curr_min_len < min_len:
                raise Exception('curr_min_len {} is lesser than the expected min_len {}!'.format(curr_max_len, max_len))

            if curr_max_len > max_len:
                raise Exception(
                    'curr_max_len {} is greater than the expected max_len {}!'.format(curr_max_len, max_len))

                # 验证carbin是否存在包含关系，即长的carbin是以短的cardbin开头的(已经验证存在，代码逻辑本身有处理这类情况)
            #             self._check_cardbin_prefix_duplicate(self.card_info)

            # 生成具体的表数据并更新到文件中
            card_info_table_str = self._generate_card_info_table(self.card_info)
            card_info_index_table_str = self._generate_card_info_index_table(self.card_info)
            new_content = self._update_card_info(self.content, card_info_table_str)
            new_content = self._update_card_info_index(new_content, card_info_index_table_str)
            #             for i in self.card_info:
            #                 print(i)
            myfile.write_to_file(self.dst_path, new_content, encoding='utf-8')
            return True

        return True

    def get_cardbin_info_with_json_format(self):
        # 先将原始lua文件读进来，并存储关键信息便于接下来进处理
        self.content = myfile.read_file_content(self.file_path, encoding_='utf-8')

        # 获取原始cardbin信息
        self.ori_card_info = self._get_card_info(self.content)
        # print(self.ori_card_info)

        # 转换成正常的json格式代码，先保留，后续有需要再使用
        # dst_array = []
        # for i in self.ori_card_info:
        #     item = {}
        #     for k in i:
        #         if i[k]:
        #             item[SIMPLIFY_MAP[k]] = i[k]
        #     dst_array.append(item)

        # if with_format:
        #     json_str = json.dumps(dst_array, ensure_ascii=False, sort_keys=True, indent=4)
        # else:
        #     json_str = json.dumps(dst_array, ensure_ascii=False)

        json_str = self._generate_card_info_table_with_js_format(self.ori_card_info)

        myfile.write_to_file(self.dst_path, json_str, encoding='utf-8')

    def _get_bank_map(self, content):
        item_unit_ptn_str = '\w+\s*=\s*"[^"]+"'
        #         item_unit_ptn = re.compile(item_unit_ptn_str, flags=re.M)
        #         match = item_unit_ptn.search(content)
        #         print(match)

        item_ptn_str_format = '{{{}(?:,\s*{})+}}'
        item_ptn_str = item_ptn_str_format.format(item_unit_ptn_str, item_unit_ptn_str)
        item_ptn = re.compile(item_ptn_str, flags=re.M)
        #         match = item_ptn.search(content)
        #         print(match)

        ptn_str_format = 'local\s+bankMap\s*=\s*{{\s*({}(?:,\s*{})+)\s*}}'
        ptn_str = ptn_str_format.format(item_ptn_str, item_ptn_str)
        pnt = re.compile(ptn_str, flags=re.M)
        match = pnt.search(content)
        if match:
            data = match.group(1)
            rtn_list = []

            item_unit_ptn_capture_str = '(\w+)\s*=\s*"([^"]+)"'
            item_unit_ptn = re.compile(item_unit_ptn_capture_str, flags=re.M)

            items = item_ptn.findall(data)
            for item in items:
                item_map = {}
                sub_items = item_unit_ptn.findall(item)
                for sub_item in sub_items:
                    item_map[sub_item[0]] = sub_item[1]

                rtn_list.append(item_map)

            return rtn_list

        return None

    def _get_revert_map(self, ori_map):
        new_map = {}
        for k in ori_map:
            new_map[ori_map[k]] = k

        return new_map

    def _get_card_type_map(self, content):
        item_ptn_str = '\[\d+\]\s*=\s*"[^"]+"'
        #         item_ptn = re.compile(item_ptn_str, flags=re.M)
        #         match = item_ptn.search(content)
        #         print(match)

        ptn_str_format = 'local\s+cardTypeMap\s*=\s*{{\s*({}(?:,\s*{})+)\s*}}'
        ptn_str = ptn_str_format.format(item_ptn_str, item_ptn_str)
        pnt = re.compile(ptn_str, flags=re.M)
        match = pnt.search(content)
        if match:
            data = match.group(1)
            item_map = {}

            item_ptn_capture_str = '\[(\d+)\]\s*=\s*"([^"]+)"'
            item_ptn = re.compile(item_ptn_capture_str, flags=re.M)

            items = item_ptn.findall(data)
            for item in items:
                item_map[int(item[0])] = item[1]

            return item_map

        return None

    def _get_card_info(self, content):
        item_unit_ptn_str = CardInfoPattern.item_unit
        #         item_unit_ptn = re.compile(item_unit_ptn_str, flags=re.M)
        #         match = item_unit_ptn.search(content)
        #         print(match)

        item_ptn_str_format = CardInfoPattern.item_format
        item_ptn_str = item_ptn_str_format.format(item_unit_ptn_str, item_unit_ptn_str)
        item_ptn = re.compile(item_ptn_str, flags=re.M)
        #         match = item_ptn.search(content)
        #         print(match)

        ptn_str_format = CardInfoPattern.ptn_format
        ptn_str = ptn_str_format.format(item_ptn_str, item_ptn_str)
        ptn = re.compile(ptn_str, flags=re.M)
        match = ptn.search(content)
        if match:
            data = match.group(2)
            rtn_list = []

            item_unit_ptn_capture_str = CardInfoPattern.item_unit_capture
            item_unit_ptn = re.compile(item_unit_ptn_capture_str, flags=re.M)

            items = item_ptn.findall(data)
            for item in items:
                item_map = {}
                sub_items = item_unit_ptn.findall(item)
                for sub_item in sub_items:
                    sub_value_1 = sub_item[1]
                    if sub_value_1.startswith('"'):
                        value = sub_value_1[1:-1]
                    else:
                        value = int(sub_value_1)

                    item_map[sub_item[0]] = value

                # 如果不存在samediff配置，则增加该配置
                if CardInfoLabel.samediff not in item_map:
                    item_map[CardInfoLabel.samediff] = None

                rtn_list.append(item_map)

            return rtn_list

        return None

    def _update_card_info(self, content, table_str):
        item_unit_ptn_str = CardInfoPattern.item_unit

        item_ptn_str_format = CardInfoPattern.item_format
        item_ptn_str = item_ptn_str_format.format(item_unit_ptn_str, item_unit_ptn_str)

        ptn_str_format = CardInfoPattern.ptn_format
        ptn_str = ptn_str_format.format(item_ptn_str, item_ptn_str)
        ptn = re.compile(ptn_str, flags=re.M)
        new_content = ptn.sub('\\1{}\\3'.format(table_str), content)
        if new_content != content:
            print('update card_info table success!')
        else:
            print('card_info table has no change!')

        return new_content

    def _update_card_info_index(self, content, table_str):
        item_ptn_str = CardInfoIndexPattern.item

        ptn_str_format = CardInfoIndexPattern.ptn_format
        ptn_str = ptn_str_format.format(item_ptn_str, item_ptn_str)
        ptn = re.compile(ptn_str, flags=re.M)
        new_content = ptn.sub('\\1{}\\3'.format(table_str), content)
        if new_content != content:
            print('update card_info_index table success!')
        else:
            print('card_info_index table has no change!')

        return new_content

    def _get_bank_index(self, bank_name):
        index = 0
        for item in self.bank_map:
            if item[BankMapLabel.name] == bank_name:
                break

            index += 1

        actual_index = 0
        if index < len(self.bank_map):
            actual_index = index + 1

        return actual_index

    def _combine_card_info(self, ori_data, new_data):
        card_map = self._remove_duplicate_card_info_item(ori_data, new_data)
        combine_info = self._simplify_card_info_item(card_map)

        # 对所有数据进行统一排序按照cardbin排序    
        #         combine_info.sort(key=operator.itemgetter(CardInfoLabel.prefix))

        combine_info = self._sort_card_info_item(combine_info)

        return combine_info

    def _remove_duplicate_card_info_item(self, ori_data, new_data):
        card_map = {}
        set_key_sep = '#'
        set_key_format = '{{}}{}{{}}'.format(set_key_sep)

        # 优先处理新数据，以新数据为准
        for item in new_data:
            cardbin = item[Label.cardbin]
            cardnolen = item[Label.cardnolen]
            map_key = set_key_format.format(cardbin, cardnolen)

            # 便于反向解析获取值
            #             infos = map_key.split(set_key_sep)

            if map_key not in card_map:
                card_item = self._get_card_item(item)

                card_items = []
                card_items.append(card_item)
                card_map[map_key] = card_items
            else:
                ori_items = card_map[map_key]
                is_same = self._exists_in_items(item, ori_items)
                if not is_same:
                    card_item = self._get_card_item(item)
                    ori_items.append(card_item)

        # 将老数据合并入新数据    
        for item in ori_data:
            cardbin = item[CardInfoLabel.prefix]
            cardnolen = item[CardInfoLabel.length]
            map_key = set_key_format.format(cardbin, cardnolen)
            if map_key not in card_map:
                card_items = []
                card_items.append(item)
                card_map[map_key] = card_items
            else:
                ori_items = card_map[map_key]
                is_same = self._check_duplicate_item(item, ori_items)
                if not is_same:
                    ori_items.append(item)

        return card_map

    def _simplify_card_info_item(self, card_map):
        combine_info = []
        for k in card_map:
            ori_items = card_map[k]
            is_same = True
            first_item = ori_items[0]
            if len(ori_items) > 1:
                to_compare_items = ori_items[1:]
                for item in to_compare_items:
                    if first_item[CardInfoLabel.index] != item[CardInfoLabel.index]:
                        is_same = False
                        break

                if is_same:
                    to_add_item = first_item.copy()
                    to_add_item[CardInfoLabel.samediff] = None
                    combine_info.append(to_add_item)
                else:
                    combine_info.extend(ori_items)
            else:
                to_add_item = first_item.copy()
                to_add_item[CardInfoLabel.samediff] = None
                combine_info.append(to_add_item)

        return combine_info

    def _sort_card_info_item(self, items):
        rtn_items = []
        item_map = {}
        for item in items:
            key = item[CardInfoLabel.prefix]
            if key not in item_map:
                item_map[key] = []

            item_map[key].append(item)

        sorted_keys = list(item_map.keys())
        sorted_keys.sort()
        for key in sorted_keys:
            sub_items = item_map[key]
            if len(sub_items) > 1:
                sub_items.sort(key=operator.itemgetter(CardInfoLabel.length))

            rtn_items.extend(sub_items)

        return rtn_items

    def _check_cardbin_prefix_duplicate(self, items):
        items_map = {}
        for item in items:
            prefix = item[CardInfoLabel.prefix]
            prefix_len = len(prefix)
            if prefix_len not in items_map:
                items_map[prefix_len] = set()

            items_map[prefix_len].add(prefix)

        for i in items_map:
            top_items = items_map[i]
            for item in top_items:
                for j in items_map:
                    if j > i:
                        sub_items = items_map[j]
                        for sub_item in sub_items:
                            if sub_item.startswith(item):
                                #                                 raise Exception('{} starts with {}!'.format(sub_item, item))
                                print('{} starts with {}!'.format(sub_item, item))

    def _get_card_item(self, ori_item):
        item = {}
        item[CardInfoLabel.prefix] = ori_item[Label.cardbin]
        item[CardInfoLabel.samediff] = ori_item[Label.samecarddiff]
        item[CardInfoLabel.code] = self.card_type_map_revert[ori_item[Label.nature]]
        item[CardInfoLabel.index] = self._get_bank_index(ori_item[Label.headoffice])
        item[CardInfoLabel.length] = ori_item[Label.cardnolen]

        return item

    def _exists_in_items(self, item, ori_items):
        cardbin = item[Label.cardbin]
        cardnolen = item[Label.cardnolen]
        new_index = self._get_bank_index(item[Label.headoffice])
        is_same = False
        for ori_item in ori_items:
            if ori_item[CardInfoLabel.index] != new_index:
                if ori_item[CardInfoLabel.samediff] != item[Label.samecarddiff]:
                    continue
                else:
                    raise Exception(
                        'cardbin {} with samecarddiff {} length {} is not consistency with previous item!'.format(
                            cardbin, item[Label.samecarddiff], cardnolen))
            else:
                if ori_item[CardInfoLabel.samediff] != item[Label.samecarddiff]:
                    continue
                else:
                    is_same = True
                    print('cardbin {} with samecarddiff {} length {} is duplicate!'.format(cardbin,
                                                                                           item[Label.samecarddiff],
                                                                                           cardnolen))
                    break

        return is_same

    def _check_duplicate_item(self, item, ori_items):
        cardbin = item[CardInfoLabel.prefix]
        cardnolen = item[CardInfoLabel.length]
        new_index = item[CardInfoLabel.index]
        is_same = False

        if item[CardInfoLabel.samediff] == None:
            is_same = True
            print('cardbin {} with samediff {} length {} is duplicate!'.format(cardbin, item[CardInfoLabel.samediff],
                                                                               cardnolen))
        else:
            for ori_item in ori_items:
                if ori_item[CardInfoLabel.index] != new_index:
                    if ori_item[CardInfoLabel.samediff] != item[CardInfoLabel.samediff]:
                        continue
                    else:
                        raise Exception(
                            'cardbin {} with samecarddiff {} length {} is not consistency with previous item!'.format(
                                cardbin, item[CardInfoLabel.samediff], cardnolen))
                else:
                    if ori_item[CardInfoLabel.samediff] != item[CardInfoLabel.samediff]:
                        continue
                    else:
                        is_same = True
                        print('cardbin {} with samediff {} length {} is duplicate!'.format(cardbin,
                                                                                           item[CardInfoLabel.samediff],
                                                                                           cardnolen))
                        break

        return is_same

    # 生成cardbin主表
    def _generate_card_info_table(self, card_info):
        unit_sep = ', '
        unit_format = '{}={}'
        unit_str_format = '{}="{}"'
        item_sep = ',\r\n  '
        item_format = '{{{}}}'
        #         table_format = '{{\r\n  {}\r\n}}'

        unit_order = [CardInfoLabel.prefix, CardInfoLabel.code, CardInfoLabel.index, CardInfoLabel.length,
                      CardInfoLabel.samediff]
        formatted_items = []
        for item in card_info:
            formatted_units = []
            for u in unit_order:
                if item[u] != None:
                    if type(item[u]) == str:
                        unit_str = unit_str_format.format(u, item[u])
                    else:
                        unit_str = unit_format.format(u, item[u])
                    formatted_units.append(unit_str)

            item_str = item_format.format(unit_sep.join(formatted_units))
            formatted_items.append(item_str)

        table_str = item_sep.join(formatted_items)

        return table_str

    # 以javasccript的json格式，生成cardbin主表
    def _generate_card_info_table_with_js_format(self, card_info):
        unit_sep = ', '
        unit_format = '{}: {}'
        unit_str_format = "{}: '{}'"
        item_sep = ',\r\n  '
        item_format = '{{{}}}'
        array_format = '[\r\n  {}\r\n]'

        unit_order = [CardInfoLabel.prefix, CardInfoLabel.code, CardInfoLabel.index, CardInfoLabel.length,
                      CardInfoLabel.samediff]
        formatted_items = []
        for item in card_info:
            formatted_units = []
            for u in unit_order:
                if item[u] != None:
                    if type(item[u]) == str:
                        unit_str = unit_str_format.format(SIMPLIFY_MAP[u], item[u])
                    else:
                        unit_str = unit_format.format(SIMPLIFY_MAP[u], item[u])
                    formatted_units.append(unit_str)

            item_str = item_format.format(unit_sep.join(formatted_units))
            formatted_items.append(item_str)

        table_str = array_format.format(item_sep.join(formatted_items))

        return table_str

    # 生成cardbin索引表
    def _generate_card_info_index_table(self, card_info):
        index_map = {}
        for i in range(len(card_info)):
            key = card_info[i][CardInfoLabel.prefix]
            if key not in index_map:
                index_map[key] = []

            index_map[key].append(i + 1)

        key_set = set()
        recs = []
        unit_sep = ', '
        item_format = '["{}"] = {{{}}}'
        item_sep = ',\r\n  '
        #         table_format = '{{\r\n  {}\r\n}}'

        for item in card_info:
            key = item[CardInfoLabel.prefix]
            if key not in key_set:
                key_set.add(key)
                temp_strs = []
                for index_item in index_map[key]:
                    temp_strs.append(str(index_item))
                rec_str = unit_sep.join(temp_strs)
                rec_item = item_format.format(key, rec_str)
                recs.append(rec_item)

        sub_str_info = item_sep.join(recs)
        #         str_info = table_format.format(sub_str_info)

        return sub_str_info

    # 校验从excel表中获取的银行名称和最终实际使用的名称是否一致
    def _verify_cardtype_consistency(self, items):
        is_consistent = True
        for item in items:
            card_type = item[Label.nature]
            if card_type not in self.card_type_map_revert:
                is_consistent = False
                print('new card type {} not in original card type set!'.format(card_type))

        return is_consistent

    def _get_max_cardbin_len_range(self, items):
        max_len = 0
        min_len = 7
        for item in items:
            curr_len = len(item[CardInfoLabel.prefix])
            if curr_len > max_len:
                max_len = curr_len

            if curr_len < min_len:
                min_len = curr_len

        return min_len, max_len


class ProcessManager:
    def __init__(self, args):
        # 先将输入的控制参数全部存储为成员变量
        for name, value in vars(args).items():
            setattr(self, name, value)

        self.src = os.path.abspath(self.src)
        self.dst = os.path.abspath(self.dst)

        self.new_data = None

    def process(self):
        if self.to_add:
            self.to_add = os.path.abspath(self.to_add)
            # 将新处理的文件关键信息读取过来，便于后续处理
            data_proc = DataProcess(self.to_add, sheet_index=self.sheet_index)
            self.new_data = data_proc.process()

            process = LuaProcess(self.src, self.dst)
            process.process(self.new_data)
        elif self.to_transform:
            process = LuaProcess(self.src, self.dst)
            process.get_cardbin_info_with_json_format()
        else:
            raise Exception('error specify params!')


# 对输入参数进行解析，设置相应参数
def get_args(src_args=None):
    parser = argparse.ArgumentParser(description='update cardbin lua process file.')
    parser.add_argument('src', metavar='src', help='source file to update')
    parser.add_argument('dst', metavar='dst', help='target file')
    parser.add_argument('--sheet', dest='sheet_index', action='store', default=0, type=int,
                        help='when add new data, to specify the sheet index to process, start with 0')

    src_group = parser.add_mutually_exclusive_group()
    src_group.add_argument('--add', dest='to_add', action='store', default=None, help='new data file to process')
    src_group.add_argument('--transform', dest='to_transform', action='store_true', default=False,
                           help='indicate to transform the lua table to json string')

    #     parser.print_help()

    return parser.parse_args(src_args)


def main(args):
    manager = ProcessManager(args)
    manager.process()


if __name__ == '__main__':
    #     test_args = 'a b -i -u'.split()
    test_args = None
    args = get_args(test_args)
    utility.measure_time(main, args)
