# coding=utf-8
import os
import csv
import heapq
from tokenstream import TokenStream
from singlestringcomp import Singlestringcomp
from gamma import Gamma
from find import Find

class indexer:
    def __init__(self, data_path, max_block=10000):
        self.dir_path = os.path.dirname(data_path)
        self.block_dir = os.path.join(self.dir_path, 'indexer_block')
        self.block_path_repo = []
        self.max_block = max_block
        """ 判断词项流是否为空 """
        self.empty_stream = False
        """分词"""
        self.tokenstream = TokenStream(data_path)
        """ 搜索 """
        self.find = None
    
    # 获得docID和文档名的字典
    def get_document_num(self):
        return self.tokenstream.get_document_num()

    # 做统计
    def do_statistic(self):
        term_cnt,doc_cnt = self.tokenstream.cal_term_doc()
        print "语料库词项数量:", term_cnt
        print "语料库文档数量:", doc_cnt
        print "文档的平均长度:", ('%.2f')%(term_cnt*1.0/doc_cnt)

    # SPIMI算法构建索引块
    def spimi_invert(self):
        term_dic = {}
        """ 倒排索引 """
        inverted_index = []
        """ 记录词项在倒排记录表位置，不排序 """
        term_cnt = 0
        block_size = 0
        """ 每一个block维护一个字典和倒排记录表 """
        while block_size < self.max_block:
            tmp_term_pos_docid = self.tokenstream.get_next_term_pos_docid()
            if tmp_term_pos_docid is None:
                self.empty_stream = True
                break

            """ 返回不是None """
            term,term_pos,docid = tmp_term_pos_docid
            """ 不在词典中，加入并返回在词典中的位置 """
            if term not in term_dic:
                term_dic[term] = term_cnt
                inverted_index.append([docid])
                term_cnt += 1
            else:
                """ 返回在词典中位置 """
                pos = term_dic[term]
                """ 词项所在文档ID不在倒排记录表里 """
                if docid != inverted_index[pos][-1]:
                    inverted_index[pos].append(docid)
            block_size += 1
        return term_dic, term_cnt, inverted_index

    # 索引块持久化
    def write_index_block(self, block_path, term_dic, inverted_index):
        """ 对字典排序 """
        term_dic_sorted = [(k, term_dic[k]) for k in sorted(term_dic.keys())]
        temp_lst = [0]*len(term_dic_sorted)
        for i,(k, v) in enumerate(term_dic_sorted):
            """ 将排序后的字典元素放到新list里 """
            temp_lst[i] = inverted_index[v]
        """ 对字典进行单一字符串压缩 和 持久化 """
        Singlestringcomp.write_dic([k for k,v in term_dic_sorted], block_path + '_sscompdic')
        """ 先把未Gamma压缩的倒排记录表写入磁盘, 与压缩的排序的字典对应 """
        Gamma.write_invert_index_noencode(temp_lst, block_path + '_invindex')

    # 构建索引块
    def build_index_block(self):
        index_block = 0
        while True:
            """ 用SPIMI算法构建索引块 """
            """ 拿到了一个索引块 """
            term_dic, term_cnt, inverted_index = self.spimi_invert()
            index_block += 1
            """ ../../indexer_block_1/2/3... """
            self.block_path_repo.append(os.path.join(self.block_dir, 
                'indexer_block_' + str(index_block)))
            """ 索引块持久化 """
            self.write_index_block(self.block_path_repo[-1], term_dic, inverted_index)

            if self.empty_stream:
                break
            
    # 合并索引块    
    def merge_index_block(self):
        """
        从原来持久化的索引块取出倒排索引和词项
        block_dic: 放每个索引块的词典
        block_invindex_csv: 放每个索引块的倒排索引
        all_term_dic: 合并的总词典
        all_invindex: 合并的总倒排索引
        """
        block_dic = []
        block_invindex_csv = []
        all_term_dic = []
        all_invindex = []
        for path_i in self.block_path_repo:
            with open(path_i + '_sscompdic', 'r') as f:
                datalines = f.readlines()
                block_dic.append(Singlestringcomp.ssdecompress(datalines))
            block_invindex_csv.append(csv.reader(open(path_i + '_invindex', 'r'), delimiter=' '))
        
        """ 
        用来记录每一个词典里有多少词已经加入到总词典all_term_dic [0,0,0] for example
        其docID 也已经加入到all_invindex
        """
        block_dic_pt = [0] * len(block_dic)
        """ 维护一个堆队列，只子节点和父节点排序，存词典，为了pop有序 """
        dic_heap = []
        heapq.heapify(dic_heap)

        while True:
            flag = True
            for i in range(len(block_dic)):
                if block_dic_pt[i] >= len(block_dic[i]):
                    continue
                flag = False
                """ 按序依次把每个文档词典加入到优先级队列 """
                tmp_term = block_dic[i][block_dic_pt[i]]
                if tmp_term in dic_heap:
                    continue
                else:
                    heapq.heappush(dic_heap, tmp_term)
            """ 如果词典合并完毕，结束合并 """
            if flag:
                break
            """ 输出 最小 词项 """
            top_term = heapq.heappop(dic_heap)
            all_term_dic.append(top_term)
            tmp_merge_docid = []
            for i in range(len(block_dic)):
                if block_dic_pt[i] >= len(block_dic[i]):
                    continue
                """ 找到与堆队列里最高优先级词项对应的倒排记录表,合并相同词项的文档ID """
                if block_dic[i][block_dic_pt[i]] != top_term:
                    continue
                """ 取出对应的倒排记录表中对应词项的docID列表 """
                i_docid = block_invindex_csv[i].next()
                for id_i in i_docid:
                    if int(id_i) not in tmp_merge_docid:
                        tmp_merge_docid.append(int(id_i))
                block_dic_pt[i] += 1
            all_invindex.append(tmp_merge_docid)
        return all_term_dic,all_invindex


    # 构建倒排记录表和词典
    def build_indexer(self):
        """
        1.用spimi-invert对每个块产生独立的词典和倒排索引,建索引块,写入磁盘
        2.合并索引块,写入磁盘过程中压缩
        """
        """ 构建索引块 """
        self.build_index_block()
        """ 合并索引块, """
        all_term_dic, all_invindex = self.merge_index_block()
        """ 持久化单字符串压缩的全局词典 """
        Singlestringcomp.write_dic(all_term_dic, os.path.join(self.dir_path, 'global_index/glo_dic'))
        """ 持久化gamma编码的全局倒排记录表 """
        Gamma.write_invert_index_encode(all_invindex, os.path.join(self.dir_path, 'global_index/glo_index_encode'))
        return 

if __name__ == '__main__':
    """ 程序安装路径，根据自己情况修改 """
    install_dir = '/home/superhui/Informationretrieval/IR'
    dir_path = os.path.join(install_dir,'BigHW_IR/data')
    idx = indexer(os.path.join(dir_path, 'doc'))
    idx.build_indexer()
    dic = Singlestringcomp.read_dic(os.path.join(dir_path, 'global_index/glo_dic'))
    inverted_index = Gamma.read_invert_index_decode(os.path.join(dir_path, 'global_index/glo_index_encode'))

    document_num = idx.get_document_num()
    fd = Find(dic, inverted_index, document_num)
    """ 查询方法为布尔，顺序为从左到右 """
    helpinfo = "\
                \t-q: quit the program!\n \
                \t-s: statistic information!\n \
                \t-c: clear screen!\n \
                \t-x: \n \
                \t    for example:\n \
                \t\t-x an & name | be  =>  (an & name) | be\n \
                \t-h: get help!\n \
               "
    print helpinfo
    while True:
        user_input = raw_input('input key words>>')
        if user_input[:2] == '-q':
            break
        if user_input[:2] == '-s':
            idx.do_statistic()
        if user_input[:2] == '-c':
            os.system('clear')
        if user_input[:2] == '-h':
            print helpinfo
            continue
        if user_input[:2] == '-x':
            qinfo = user_input[2:]
            res = fd.find(qinfo)
            fd.show_result(res)
            print '\n'








