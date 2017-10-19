# coding=utf-8
import os

class Singlestringcomp:
    def __init__(self):
        return
    
    # 写入磁盘前先进行单一字符串压缩
    @staticmethod
    def sscompress(sorted_dic):
        """
        sorted_dic: [('an',1), ('you',1), ('me',1) ...]
        dic_sscomp: 2an3you2me...        
        """
        tmp = ''
        for k,v in sorted_dic:
            tmp += str(len(k))
            tmp += k
        return tmp
        
    # 把压缩后的词典写入磁盘
    @staticmethod
    def write_dic(sorted_dic, file_path):
        dic_sscomp = Singlestringcomp.sscompress(sorted_dic)
        with open(file_path, 'w') as f:
            f.writelines(dic_sscomp)


if __name__ == '__main__':
    print 'sscomp'
    #dd = [('an',1), ('you',1), ('me',1)]
        
    #ss.write_dic(dd, './yyy.txt')




    