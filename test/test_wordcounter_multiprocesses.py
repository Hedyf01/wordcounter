#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
import sys, re, time, os
import operator, chardet
from collections import Counter
from functools import reduce
from multiprocessing import Pool, cpu_count
from datetime import datetime
from functools import partial
from utils import humansize, humantime, processbar

WORKERS = min(cpu_count() * 8, 20)  #要启动的进程数,cpu数量的8倍，不超过20
CODING = 'utf8'    #'gbk'
                                
def word_count(fn, p1, p2, f_size):  
    """分段读取大文件并统计词频    
    Args:
        fn:所读文件名称
        p1:文件段的起始位置
        p2:文件段的结尾位置
        f_size:所读文件的大小，单位为B    
    ret:
        该进程所负责的文件段的词频统计结果
        type == collections.Counter
    """
    c = Counter()
    with open(fn, 'rb') as f:    
        if p1:  # 为防止字被截断的，分段处所在行不处理，从下一行开始正式处理
            f.seek(p1-1)
            while b'\n' not in f.read(1):
                pass
        start = time.time()
        while 1:    
            pos = f.tell()          
            line = f.readline().decode(CODING)
            c.update(Counter(re.sub(r'\s+','',line)))   #空格不统计   
            if p1 == 0: #显示进度
                processbar(pos, p2, fn, f_size, start)
            if pos >= p2:               
                return c  

def counter_single(from_file, f_size):
    '''单进程读取文件并统计词频'''
    c = Counter()
    start = time.time()
    with open(from_file, 'rb') as f:
        for line in f:
            c.update(Counter(re.sub(r'\s+','',line.decode(CODING))))
            processbar(f.tell(), f_size, from_file, f_size, start)
    return c            
       
def write_result(counter, to_file):   
    '''将Counter类型的统计结果，按设定编码，写入文件to_file中'''       
    ss = ['{}: {}'.format(i, j) for i, j in counter.most_common()]
    s = ('\n'.join(ss)).encode(CODING)
    with open(to_file, 'wb') as f:
        f.write(s)
    ''' 打印统计结果的前几项
    with open(to_file, 'rb') as f:
        s = f.read()
    print()            
    print(s.decode(CODING)[:50], '\n', '...')
    '''        

def countwords(from_file, to_file, workers = WORKERS):
    start = time.time()
    f_size = os.path.getsize(from_file)
    if workers == 1:
        c = counter_single(from_file, f_size)
    else:
        pool = Pool(workers)
        res_list = []
        for i in range(workers):
            p1, p2 = f_size // workers * i,  f_size // workers * (i+1)
            args = [from_file,p1,p2,f_size]
            res = pool.apply_async(func=word_count, args=args)
            res_list.append(res)
        pool.close()
        pool.join()
        c = reduce(operator.add, [res.get() for res in res_list])
    write_result(c, to_file)
    cost = '{:.1f}'.format(time.time()-start)
    size = humansize(f_size)
    tip = '\nFile size: {}. Workers: {}. Cost time: {} seconds'     
    print(tip.format(size, workers, cost))
    return cost + 's'
    
def main():
    if len(sys.argv) > 2:
        from_file, to_file = sys.argv[1:3]
    # 在上一级目录的var文件夹中，生成测试用大文件
    if os.path.dirname(__file__) in ['test']:
        dir_of_bigfile = os.path.join('..', 'var')    
    else:
        dir_of_bigfile = 'var' 
    if not os.path.exists(dir_of_bigfile):
        os.mkdir(dir_of_bigfile)
    from_file, to_file = '100lines.txt', 'count_result.txt'    
    with open(from_file, 'rb') as f:
        global CODING
        CODING = chardet.detect(f.read(1000))['encoding']
    with open(from_file, 'rb') as f:
        s = f.read()
    files = []
    for i in [2000]:#, 10000, 20000, 100000, 200000]:
        fn = '{}thousandlines.txt'.format(i//10)  
        ffn = os.path.join(dir_of_bigfile, fn)
        files.append(ffn)
        if not os.path.exists(ffn):
            with open(ffn, 'wb') as f:
                f.write(s*i)
                
    count_it = partial(countwords, to_file=to_file)
    ps = [1, 2, 4]#, 8, 16, 32, 64, 128, 256, 512] #待测试的进程数
    pre = '{:8}' * (len(ps) + 1)
    title = ['size'] + ['{}ps'.format(i) for i in ps]
    L = [pre.format(*title)]
    for i in files:
        size = os.path.getsize(i)
        title = [humansize(size)] + [count_it(i, workers=p) for p in ps]
        L.append(pre.format(*title))
        print('-'*40)
    t =  'cpu_count = {}, now = {}'.format(cpu_count(), datetime.now())
    result = '\n'.join([sys.version, t] + L +['-'*75, ''])
    print(result) 
    with open('test_result.txt', 'ab') as f:
        f.write(result.encode('utf-8'))  
    
if __name__ == '__main__':
    main()
        
