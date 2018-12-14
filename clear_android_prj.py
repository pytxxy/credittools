# -*- coding:UTF-8 -*-

#################################################
#环境: win + python 2.7
#作者：马波
#邮箱：mabo02@baidu.com
#部门：hao123-无线
#说明：首次使用时lint分析会耗几分钟，请耐心等待。
#      使用前先clean工程，确保工程bin下重新生成dex，
#      以便lint进行分析。如果要lint重新分析多余
#      资源，需要删掉(2)txt记录文件,(1)(3)(4)需要
#      根据我们的实际工程手动设置。
#      如果清除资源后，工程缺少文件而报错（极少
#      情况），尝试通过svn恢复该文件即可。
#################################################
import subprocess    
import re
import os
import time
import threading  

#(1)工程位置
projectPath="D:\/hao123\/code\/client-android"
#(2)lint输出txt记录文件
txt="D:\/hao123_unused_res.txt"
#(3)正则表达式，清除drawable和layout下多余的jpg/png/xml，
#   并且排除以sailor_|wenku_|zeus_|bdsocialshare_|floating_life_|weather_info_icon_|anthology_开头的文件
regex = re.compile(r"^res\\(drawable(-land)?(-[xn]?[mhlo](dpi))|layout)?\\(?!(sailor_|wenku_|zeus_|bdsocialshare_|floating_life_|weather_info_icon_|anthology_))[0-9a-zA-Z_\.]*\.(jpg|png|xml)", re.IGNORECASE)
#(4)lint.bat的位置
lint="D:\/sdk\/tools\/lint.bat"

isgotTxt=False
def timer(interval):  
    while not isgotTxt:
        print( 'Lint is analyzing: %s'%time.ctime()  )
        time.sleep(interval)

def process(lint_path):
    if not os.path.exists(txt):
        thread = threading.Thread(target=timer, args=(5,))
        cmd=lint+' --check "UnusedResources" "'+ projectPath +'" >'+txt
        p = subprocess.Popen(cmd, shell = True,stdout = subprocess.PIPE,stdin = subprocess.PIPE,stderr = subprocess.PIPE)        
        p.wait()
    
    fobj=open(txt,'r') 
    isgotTxt=True
    i=0
    j=0
    for line in fobj:
        #print( str(i)+":"+line)
        match=regex.match(line)
        if match:
            i=i+1
            filename=projectPath+"\/"+match.group().replace('\\',"\\/")
            try:
                print( filename)
                os.remove(filename)
                j=j+1
                print( "was deleted!")
            except WindowsError:
                print( "is not exists")
                pass
    
    print( "Total Unused Resources = "+str(i))
    print( "Total deleted Resources = "+str(j))
    
    
class ProjectClearer:
    def __init__(self):
        pass
    
    def clear(self):
        pass
        
    def status(_dir='.'):
        # example: "svn: warning: W155007: 'D:\temp' is not a working copy"
        _STATUS_PATTERN = '^svn\:\s+warning.*is\s+not\s+a\s+working\s+copy\s*$'
        
        try:
            args = []
            args.append(_SVN_PATH)
            args.append('status')
            args.append(_dir)
            
            result = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True)
    #         print('result:' + result)
            
            match = re.match(_STATUS_PATTERN, result, re.I|re.S)
            if match:
                return False
            else:
                return True
        except subprocess.CalledProcessError:
            raise