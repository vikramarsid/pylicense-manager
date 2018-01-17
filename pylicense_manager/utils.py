# coding=utf-8
import errno
import logging
import shutil
from StringIO import StringIO
from urlparse import urlparse

import os
import re
import requests
from bs4 import BeautifulSoup
from requests import ConnectionError, HTTPError
from requests.adapters import HTTPAdapter
from urllib3 import Retry

logging.basicConfig()
logger = logging.getLogger(__name__)


def request(method, request_url, params=None, data=None, custom_headers=None, stream=False,
            json_output=True, verify_ssl=True, timeout=60):
    logger.info("Sending request to {}".format(request_url))
    response = None
    try:
        session = requests.Session()
        session.params = {} if not params else params
        session.stream = stream
        session.verify = verify_ssl
        session.proxies = None  # Future extension to proxy implementation
        session.headers.update({
            'Content-Type': "application/json",
            'Cache-Control': "no-cache"
        })

        session.mount('https://', HTTPAdapter(
            max_retries=Retry(
                total=2,
                status_forcelist=[429, 500, 502, 503],
                backoff_factor=5,
            )
        ))

        with session:
            # Request headers
            if custom_headers:
                session.headers.update(custom_headers)
            response = session.request(method=method, url=request_url, data=data, timeout=timeout)
            logger.info("[%s] Response status: %s" % (response.status_code, response.reason))
            if response.status_code == 400:
                raise Exception("Bad request")
            elif response.status_code == 404:
                return {}
            elif response.status_code == 403:
                logger.info(response.text)
                return {}
            else:
                response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        logger.error(error)
        raise HTTPError(response.text)

    except Exception as exp:
        logger.info("REQUEST ERROR: %s" % exp)
        raise ConnectionError(exp)

    if stream:
        content_string = StringIO()
        for content in response.iter_content(decode_unicode=True, chunk_size=1024 * 16):
            try:
                if content:
                    content_string.write(content)
            except StopIteration:
                break
        response = content_string.getvalue()
        content_string.flush()

    if json_output:
        try:
            response = response.json()
        except Exception as exp:
            raise Exception("Internal Error: Unable to decode response json: {}".format(exp))

    return response


def write_to_file(file_path, content):
    logger.info("Writing content to file at %s" % file_path)
    try:
        with open(file_path, "w+") as license_file:
            license_file.write(content.encode('utf8'))
    except Exception as exp:
        logger.error("Error in writing contents to file at %s - %s" % (file_path, exp))
        return None


def create_path(path):
    try:
        paths_to_create = []
        while not os.path.exists(path):
            paths_to_create.insert(0, path)
            head, tail = os.path.split(path)
            # Just in case path ends with a / or \
            if len(tail.strip()) == 0:
                path = head
                head, tail = os.path.split(path)
            path = head
        for path in paths_to_create:
            os.mkdir(path)
        return True
    except OSError as exp:
        logger.error("Error occurred while creating directories - %s" % exp)
        if exp.errno not in [errno.EEXIST, errno.ENOENT]:
            raise


def delete_directories(directory_path):
    try:
        shutil.rmtree(directory_path)
    except OSError as exp:
        logger.error("Error occurred while delete directories - %s" % exp)
        if exp.errno not in [errno.EEXIST, errno.ENOENT]:
            raise


def parse_url(url, only_domain=True, only_path=False):
    parsed_url = urlparse(url)
    if only_path:
        return parsed_url.path
    if only_domain:
        return parsed_url.netloc


def extract_urls(url):
    """
    Extract urls from HTML page
    :param url:
    :return: Extracted url list
    """
    html_page = request("GET", url, json_output=False, stream=True)
    html_content = html_page.content
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []

    for link in soup.findAll('a', attrs={'href': re.compile("^(http|https)://github")}):
        links.append(link.get('href'))

    return links


def common_prefix_size(s1, s2):
    res, i = 0, 0
    while i < min(len(s1), len(s2)):
        if s1[i] == s2[i]:
            res += 1
            i += 1
        else:
            break
    return res


def longest_prefix(lst):
    if len(lst) == 1:
        return lst[0]
    res = ''
    maxsize = 0
    for i in range(len(lst) - 1):
        for j in range(i + 1, len(lst)):
            t = common_prefix_size(lst[i], lst[j])
            maxsize = max(maxsize, t)
            if maxsize == t:
                res = lst[i][:maxsize]
    return res
