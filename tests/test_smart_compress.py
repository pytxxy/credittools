'''
Created on 2016年10月22日

@author: caifh
'''
import unittest
import smart_compress as comp
import format_json_file as jsonfile
import json


# 两数相加返回对应的数组下标
# def twoSum(nums, target):
#     new_dict = {}
#     nums_len = len(nums)
#     for i in range(len(nums)):
#         if target - nums[i] in new_dict:
#             return [i, new_dict[target - nums[i]]]
#         if nums[i] not in new_dict:
#             new_dict[nums[i]] = i

def twoSum(nums, target):
    new_dict = {}
    for index in range(len(nums)):
        if target - nums[index] in new_dict:
            return [index, new_dict[target - nums[index]]]
        new_dict[nums[index]] = index

# 最长回文子串
def manacher(s):
    #预处理 111abcbcba456
    s='#'+'#'.join(s)+'#'

    RL=[0]*len(s)
    MaxRight=0
    pos=0
    MaxLen=0
    MaxIndex = 0
    for i in range(len(s)):
        if i<MaxRight:
            RL[i]=min(RL[2*pos-i], MaxRight-i)
        else:
            RL[i]=1
        #尝试扩展，注意处理边界
        while i-RL[i]>=0 and i+RL[i]<len(s) and s[i-RL[i]]==s[i+RL[i]]:
            RL[i]+=1
        #更新MaxRight,pos
        if RL[i]+i-1>MaxRight:
            MaxRight=RL[i]+i-1
            pos=i
        #更新最长回文串的长度
        MaxLen=max(MaxLen, RL[i])
        print('i = '+ str(i), 'RL[i] = '+ str(RL[i]), pos, MaxLen, 'MaxRight=' + str(MaxRight))

    for index in RL:
        if (index == MaxLen):
            left_index = RL.index(MaxLen) - MaxLen + 1
            right_index = RL.index(MaxLen) + MaxLen
            last_str = s[left_index:right_index]
            last_str = last_str.replace('#','')
            return last_str
    return ''

def lengthOfLongestSubstring(s):
    start = maxLength = 0
    usedChar = {}

    for i in range(len(s)):
        if s[i] in usedChar and start <= usedChar[s[i]]:
            start = usedChar[s[i]] + 1
        else:
            maxLength = max(maxLength, i - start + 1)
        usedChar[s[i]] = i
        print('maxLength: ', maxLength)
        print('start: ', start)
        print(usedChar)

    return maxLength

def findMedianSortedArrays(nums1, nums2):
    nums1_length = len(nums1)
    nums2_length = len(nums2)

    if (nums1_length > nums2_length):
        return findMedianSortedArrays(nums2, nums1)
    if nums1_length == 0:
        if nums2_length % 2 == 0:
            first = nums2[int(nums2_length / 2) - 1]
            second = nums2[int(nums2_length / 2)]
            return (first + second) / 2
        else:
            return nums2[(nums2_length / 2)]
    c1 = c2 = l1 = l2 = r1 = r2 = lo = 0
    hi = 2 * nums1_length
    while (lo <= hi):
        c1 = (lo + hi) / 2
        c2 = nums1_length + nums2_length - c1

        if (c1 == 0):
            l1 = 0
        else:
            l1 = nums1[int((c1 - 1) / 2)]

        if (c1 == 2 * nums1_length):
            r1 = 0
        else:
            r1 = nums1[int(c1 / 2)]

        if (c2 == 0):
            l2 = 0
        else:
            l2 = nums2[int((c2 - 1) / 2)]

        if (c2 == 2 * nums2_length):
            r2 = 0
        else:
            r2 = nums2[int(c2 / 2)]
        print('lo = ', lo, 'hi = ', hi, 'c1 = ', c1, 'c2 = ', c2, 'l1 = ', l1, 'r1 = ', r1, 'l2 = ', l2, 'r2 = ', r2)
        if (l1 > r2):
            hi = c1 - 1
        elif (l2 > r1):
            lo = c1 + 1
        else:
            break


    return (max(l1, l2) + min(r1, r2)) / 2.0

if __name__ == "__main__":
    print(twoSum([2,7,11,15], 9))
