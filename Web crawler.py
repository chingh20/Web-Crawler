import requests
import logging
import random
import time
from lxml import html 
from queue import PriorityQueue
from langdetect import detect
from urllib.parse import urlparse, urljoin, urlunparse
from urllib import robotparser

from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

from googlesearch import search

disable_warnings(InsecureRequestWarning)

def fetch_page(url):
    '''
    Peforms a get request on the url and returns the response.
    '''
    try:
        time.sleep(0.01)
        response = requests.get(url, timeout=2.50)
        # check if url is of type text/html
        content_type = response.headers.get("content-type", '')
        if "text/html" not in content_type and content_type != '':    
            return None
        return response
    except Exception as e:
        logger.debug(f"fetch_url {url} : URL cannot be fetched. Error: {e}")
        return None

def parse_response(response):
    '''
    Parses the HTTP response and returns a html tree.
    '''
    response_content = response.content
    try:
        root = html.fromstring(response_content)
        return root
    except Exception as e:
        logger.debug(f"parse_response {response.url}: Content cannot be parsed. Error: {e}")
        return None

def get_attribute(tree, attribute):
    '''
    Returns the value of the target attribute given an html tree.
    '''
    if attribute == 'language':
       
        lang_attribute = tree.get('lang')

        if lang_attribute is None:
            print("Cannot find lang attribute using html tag")

            # Extract text content using XPath
            text_content = tree.xpath('//text()')
            
            if text_content is not None:
                # Join the extracted text into a single string
                extracted_text = ' '.join(text_content)
                try:
                    # Detect the language of the extracted_text
                    lang_attribute = detect(extracted_text)
                except Exception as e:
                    print(f"Cannot detect lang. Exception: {e}")
                    return None
            
        if lang_attribute is not None and 'zh' in lang_attribute:
            return 'chinese' 
        if lang_attribute is not None and 'es' in lang_attribute:
            return 'spanish'
        if lang_attribute is not None and 'pl' in lang_attribute:
            return 'polish'
        
        return lang_attribute

def get_links(tree, num_links):
    '''
    Returns hyperlinks given a html tree. 
    If there are more than num_links hyperlinks in the page, 
    randomly shuffle the hyperlinks and keep the first num_links.
    Check if the hyperlinks are of the correct type before returning them.
    '''

    black_list = ['jpeg', 'png', 'pdf', 'mp4', 'gif', 'mov', 'webm', 'webp']
    final_links = []
    links = tree.xpath('//a/@href') 
    if links is not None and len(links) > num_links:
        random.shuffle(links)
        links = links[:num_links]
    
    #Remove invalid file types
    for link in links:
        in_black_list = False
        for extension in black_list:
            if link.endswith(extension):
                in_black_list = True
                break
        if not in_black_list:
            final_links.append(link)
    
    return final_links

def cal_link_priority(url, base_url, num_links, priority, added_domain):
    '''
    Returns the priority of the url. 

    url: target url
    base_url: the base url or the parent url of the target url
    num_links: a number signifying the lowest priority
    priority: the default priority given to this url
    added_domain: a dictionary of domains that have been added in the past
    '''
    # give links in the same/likely related domain a lower priority
    base_domain = urlparse(base_url).hostname
    if base_domain in url:
        return num_links
    parsed_url = urlparse(url)
    domain = parsed_url.hostname
    if domain in added_domain.keys():
        return num_links
    added_domain[domain] = True
    return priority

def get_base_url(url, tree):
    '''
    Returns the base url of a page given the page's url and html parsed tree.
    '''
    base_element  = tree.find(".//base")
    if base_element is not None and 'href' in base_element.attrib:
        base_url = base_element.get('href')
    elif tree.find(".//base_url") is not None:
        base_url = tree.find(".//base_url")
    else:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    #check if base_url is correct and correct it if it's not
    parsed_url = urlparse(base_url)
    if parsed_url.scheme == '' or parsed_url.netloc =='':
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return base_url

def normalize_url(link, base_url):
    '''
    Returns the normalized url. 
    This converts a relative url to an absolute url. 
    '''
    if link.startswith(('http:', 'https:')):
        absolute_url = link
    elif link.startswith('//'):
        absolute_url = 'https:' + link
    else:
        absolute_url = urljoin(base_url, link)
    parsed_url = urlparse(absolute_url)
    
    scheme = parsed_url.scheme.lower()
    netloc = parsed_url.netloc.lower()
    path = parsed_url.path
    param = parsed_url.params
    query = parsed_url.query

    normalized_url = urlunparse((scheme, netloc, path, param, query, None))
    return normalized_url

def get_robot_text(url):
    '''
    Returns the content of the robots.txt in list of strings if the file exists. 
    '''
    parsed_url = urlparse(url)
    robots_txt_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    try:
        response = requests.get(robots_txt_url, verify=False)
        if response.status_code == 200:   
            return response.text.splitlines()
    except Exception as e:
        return None

def allowed_to_fetch(url, robot_text):
    '''
    Returns whether a url is allowed to be fetch by a crawler given the robots text. 
    '''
    # if robots.txt cannot be fetched, return true
    if robot_text is None:
        return True
   
    rp = robotparser.RobotFileParser()
    try:
        rp.parse(robot_text)
        if rp.can_fetch("*", url):
            return True
        else: 
            return False
    except Exception as e:
        print(e)
        return True


def should_sample():
    '''
    Returns true with a probability of 1/3 and false with a probability of 2/3.
    '''
    #sample with a probability of 1/3
    x = random.randint(0,8)
    if x < 3:
        return True
    return False 

def get_ggl_results(query, num_res):
    '''
    Returns the first num_res results of a query in Google. 
    '''
    results = search(query, num_results=num_res)
    return results

######### main logic starts here ############

start_time = time.time()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
 # create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler('file_run4.log')
ef_handler = logging.FileHandler('error.log')
c_handler.setLevel(logging.INFO)
f_handler.setLevel(logging.INFO)
ef_handler.setLevel(logging.WARNING)

# create formatters and add it to handlers
c_format = logging.Formatter('%(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(message)s')
ef_format = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)
ef_handler.setFormatter(ef_format)

# add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)
logger.addHandler(ef_handler)


added_domain = dict()
traversed_url = dict()
can_fetch = dict()
pq = PriorityQueue()
crawled = 0
sampled = 0
num_links = 50
rank = list(range(0, num_links)) # this is for assigning the default priorities of hyperlinks

##keep track of the number of pages in each language
chinese = 0
polish = 0
spanish = 0


query = input("Type your query: ")
ggl_results = get_ggl_results(query, 10)
for result in ggl_results:
    pq.put((0, result))

while not pq.empty() and crawled < 10000:
    url = pq.get()[1]
    if url in traversed_url.keys():
        continue
    traversed_url[url] = True
    response = fetch_page(url)
    if response is None:
        continue
    parsed_tree = parse_response(response)
    if parsed_tree is None:
        continue

    crawled = crawled + 1
    
    sampled_curr = should_sample()
    lang = None
    if sampled_curr:
        lang = get_attribute(parsed_tree, 'language')
        if lang is not None:
            if lang == 'chinese':
                chinese = chinese + 1
            elif lang == 'polish':
                polish = polish + 1
            elif lang == 'spanish':
                spanish = spanish + 1
            sampled = sampled + 1

    links = get_links(parsed_tree, num_links)
    if links is None:
        logger.info(f"crawled: {crawled}, sampled: {sampled}, URL: {url}, Size: {len(response.content)}, Status: {response.status_code}, Sampled: {sampled_curr}, Lan: {lang}")
        continue
  
    random.shuffle(rank)
    base_url = get_base_url(url, parsed_tree)
    robot_text = get_robot_text(base_url)
    for index, link in enumerate(links):
        link = normalize_url(link, base_url)
        if link in traversed_url.keys():
            continue
        if not allowed_to_fetch(link, robot_text):
           traversed_url[url] = False
           continue 
        priority = cal_link_priority(link, base_url, num_links, rank[index], added_domain)
        pq.put((priority, link))

    logger.info(f"crawled: {crawled}, sampled: {sampled}, URL: {url}, Size: {len(response.content)}, Status: {response.status_code}, Sampled: {sampled_curr}, Lan: {lang}")


logger.info(f'crawled: {crawled}, sampled: {sampled}, chinese: {chinese}, spanish: {spanish}, polish: {polish}')
logger.info(f'crawled: {crawled}, sampled: {sampled}, chinese: {chinese/sampled}, spanish: {spanish/sampled}, polish: {polish/sampled}')

print("program ended")
end_time = time.time()
logger.info(f'program took {end_time - start_time}')