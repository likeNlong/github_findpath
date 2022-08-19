import time
import argparse
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading
from requests.adapters import HTTPAdapter
from termcolor import cprint

github_url=None

#常量
giturl = 'https://github.com'
files = []
dirs = []
#代理
proxies = None
#线程池
pool = None
lock = threading.RLock()     #创建可重入锁
parser = argparse.ArgumentParser(description='Extract the github open source project path to blast')
futures = []


#添加参数
parser.add_argument('-u','--url',type=str,help='github project path',required=True)
parser.add_argument('-v','--vv',action='store_true',help='Show all issued request')
parser.add_argument('-f','--file',type=str,default=r'D:/github.txt',help='File storage path,default:D:/github.txt')
parser.add_argument('-t','--threads',type=int,default=20,help='thread numbers')
parser.add_argument('-p','--proxy',type=str,help='Set Proxy example:http://127.0.0.1:8080')
#获取参数
args = parser.parse_args()

#请求完整检测开关
requests_all = True

#改变url
github_url = args.url
# 默认url是github的主分支
branches = '/tree/master/'
# 整理url格式为主分支
if github_url[-1] == '/':
    github_url = github_url + branches[1:]
else:
    github_url = github_url + branches

pool = ThreadPoolExecutor(max_workers=args.threads)
if args.proxy == None:
    proxies = {}
else:
    proxies = {'https':args.proxy,'http':args.proxy}


def out(x,color):
    lock.acquire()
    cprint(x,color=color)
    lock.release()


def send(url):

    time.sleep(0.5)
    if args.vv:
        out(f'[+] request: {url}','green')
    #超时重发，最多三次
    s = requests.session()
    s.mount('http://', HTTPAdapter(max_retries=2))
    s.mount('https://', HTTPAdapter(max_retries=2))
    try:
        response = s.get(url=url,proxies=proxies,timeout=5)
    except requests.exceptions.RequestException:
        out(f'[Error] request failed suggest set proxy: {url} ','red')
        global  requests_all
        requests_all = False
        return


    #创建BeautifulSoup对象
    soup =BeautifulSoup(response.text,"html.parser")
    links = soup.find_all("a")
    path_link = []
    #整理出文件或文件夹的a标签
    for link in links:
        if 'class' in link.attrs:
            if 'js-navigation-open' in link['class'] and 'Link--primary' in link['class']:
                path_link.append(link)
    #调优释放内存
    del links

    files_url = []

    for link in path_link:
        if 'href' in link.attrs:
            raw_href = str(link['href']).split('/')
            if 'tree' in raw_href:
                files_url.append(giturl+link['href'])
                dirs.append('/'+'/'.join(raw_href[5:]))
            elif 'blob' in raw_href:
                files.append('/'+'/'.join(raw_href[5:]))


    if len(files_url) != 0:
        for x in files_url:
            f = pool.submit(send,x)
            futures.append(f)

#线程控制
def twaite():
    old = len(futures)
    time.sleep(5)
    new = len(futures)
    while old != new:
        old = new
        new = len(futures)
        time.sleep(5)

    #检测有多少卡住的线程
    while True:
        num = 0
        for i in futures:
            if not i.done():
                num+=1
        if num==0:
            break
        else:
            time.sleep(2)




def out_file():
    cprint('[*] Writing to file...','cyan')
    filepath = args.file
    #写文件
    with open(filepath,'w')as f:
        f.write('\n'.join(dirs))
        f.write('\n'.join(files))

    if requests_all:
        cprint(f'[*] write success,file in {filepath}','cyan')
    else:
        cprint(f'[x] write success,file in {filepath} , but check request has failed so result may not be accurate', 'red')


if __name__ == '__main__':

    print('''
        
         ___    ___ ___    ___ ________  _________   
        |\  \  /  /|\  \  /  /|\   ____\|\___   ___\ 
        \ \  \/  / | \  \/  / | \  \___|\|___ \  \_| 
         \ \    / / \ \    / / \ \_____  \   \ \  \  
          /     \/   /     \/   \|____|\  \   \ \  \ 
         /  /\   \  /  /\   \     ____\_\  \   \ \  \ 
        /__/ /\ __\/__/ /\ __\   |\_________\   \|__|
        |__|/ \|__||__|/ \|__|   \|_________|        
            
            
        微信公众号：小惜渗透，欢迎师傅们关注（回复：`彩蛋`有惊喜）                                 
    ''')
    print('Crawling for data,Please wait for......')
    send(github_url)
    twaite()
    out_file()
    pool.shutdown()
