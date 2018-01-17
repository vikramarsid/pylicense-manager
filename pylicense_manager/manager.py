# coding=utf-8
import base64
import datetime
import logging
import urlparse
from email import message_from_string

import os
import pip
import pip.req
import pkg_resources
import re
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader, StrictUndefined
from pip.download import PipSession

import utils

logging.basicConfig()
logger = logging.getLogger(__name__)
meta_files_to_check = ['PKG-INFO', 'METADATA']


class Manager(object):
    def __init__(self, requirements_path, output_path, gh_token=None):
        self.reqs_path = requirements_path
        self.output_path = output_path
        self.gh_token = gh_token
        self.custom_header = {"Authorization": "token {}".format(self.gh_token)} if self.gh_token else None
        self.session = PipSession()
        self.created_dirs = None

    def parse_requirements(self):
        # parse requirements.txt file
        package_details = []
        requirement_file_list = pip.req.parse_requirements(self.reqs_path, session=self.session)
        for item in requirement_file_list:
            if isinstance(item, pip.req.InstallRequirement):
                comes_from = str(item.comes_from)
                line_str = (comes_from.index("(line") + 6, comes_from.index(")"))
                line_no = str(comes_from[line_str[0]:line_str[1]]).strip()
                package_info = {
                    "name": item.name,
                    "as_egg": item.as_egg,
                    "line_no": line_no,
                    "editable": item.editable,
                    "installed_version": item.installed_version,
                    "is_wheel": item.is_wheel,
                    "link": item.link,
                    "update": item.update,
                    "nothing_to_uninstall": item.nothing_to_uninstall,

                }
                logger.info("required package: {}".format(item.name))

                if len(str(item.req.specifier)) > 0:
                    package_info["version_specific"] = str(item.req.specifier)

                if item.link is not None:
                    package_info["link_url"] = item.link.url
                    package_info["link_filename"] = item.link.filename
                    package_info["link_egg_file"] = item.link.egg_fragment

                package_details.append(package_info)

        # add license details
        package_details = self._get_license_details(package_details)
        self.search_router(package_details)
        return package_details

    @staticmethod
    def _get_license_details(package_details):
        """
        Get package license details
        :param package_details:
        :return:
        """
        for package in package_details:
            pkg_name = package["name"]
            pkg_version = package["version_specific"][2:] if "version_specific" in package else None
            if package["installed_version"]:
                installed_packages = pkg_resources.require(pkg_name)
                installed_pkg = installed_packages[0]
                for meta_file in meta_files_to_check:
                    if not installed_pkg.has_metadata(meta_file):
                        continue
                    pkg_meta_data = installed_pkg.get_metadata(meta_file)
                    meta_data = {k.lower(): v for k, v in dict(message_from_string(pkg_meta_data)).iteritems()}
                    package.update(meta_data)
                if "home-page" in package:
                    logger.info("{}: Cannot find link to license home page.\n".format(pkg_name))
            else:
                # Fetch details from PyPI server
                if pkg_name and pkg_version:
                    pyp_request_url = "https://pypi.python.org/pypi/{}/{}/json".format(pkg_name, pkg_version)
                    package_online_info = utils.request("GET", pyp_request_url)
                    if "info" in package_online_info:
                        info = package_online_info["info"]
                        package["author"] = info["author"]
                        package["version"] = info["version"]
                        package["author_email"] = info["author_email"]
                        package["license"] = info["license"]
                        package["home-page"] = info["home_page"]
                else:
                    logger.error("Missing package name/version: {} - {}".format(pkg_name, pkg_version))
        return package_details

    def search_router(self, package_details):
        """
        Parse home-page of python package to determine the version control server and fetch license file
        :param package_details:
        :return:
        """
        for package in package_details:
            home_url = package["home-page"] if "home-page" in package else None
            if not home_url or str(home_url).lower() == "unknown":
                continue
            name = package["name"]
            author = package["author"]
            license_name = package["license"] if "license" in package else None
            domain_name = utils.parse_url(home_url).lower()
            found = False
            # Get license from github repo
            if "github.com" in domain_name:
                license_content = self._get_github_license(home_url)
                if license_content:
                    self._create_license_file(name, license_content)
                    found = True

            # Get license from bitbucket repo
            if "bitbucket.org" in domain_name:
                license_content = self.bitbucket_repo_search(home_url)
                if license_content:
                    self._create_license_file(name, license_content)
                    found = True

            # check if the homepage is on readthedocs and then parse for repo url
            if not found:
                extracted_url = self.extract_home_page_urls(home_url)
                if extracted_url and name in extracted_url:

                    if "github.com" in extracted_url:
                        license_content = self._get_github_license(extracted_url)
                        if license_content:
                            found = True
                            self._create_license_file(name, license_content)
                    elif "bitbucket.org" in extracted_url:
                        license_content = self.bitbucket_repo_search(extracted_url)
                        if license_content:
                            found = True
                            self._create_license_file(name, license_content)
                    else:
                        found = False

            # Again open search in github
            if not found:
                search_result = self.github_repo_search(name)
                if search_result:
                    license_content = self._get_github_license(search_result["url"])
                    if license_content:
                        found = True
                        self._create_license_file(name, license_content)

            # Still, if not found generate license file
            if not found:
                if license_name:
                    license_content = self.generate_license(license_name, name, author, "2018")
                    if license_content:
                        self._create_license_file(name, license_content)

    def github_repo_search(self, repo_name):
        """
        Search for github repos
        :param repo_name: search string
        :return:
        """
        try:
            search_url = "https://api.github.com/search/repositories"
            query_params = {"q": str(repo_name)}
            search_results = utils.request("GET", search_url, params=query_params, custom_headers=self.custom_header)
            if "total_count" in search_results and search_results["total_count"] > 0:
                # select search result with highest score. Default sorted based on score.
                item = search_results["items"][0]
                package = {
                    "name": item["name"],
                    "url": item["url"]
                }
                return package
            else:
                logger.info("No search results found")
                return None
        except Exception as exp:
            logger.error("Failed to search Github repository: %s" % exp)
            return None

    def bitbucket_repo_search(self, repo_url):
        """
        Search Bitbucket repositories
        :param repo_url:
        :return:
        """
        try:
            if "https://bitbucket.org/" in repo_url:
                repo_uri = str(repo_url).replace("https://bitbucket.org/", "").strip()
                search_url = "https://api.bitbucket.org/2.0/repositories/{}/src".format(repo_uri)
                query_params = {"pagelen": 100}
                search_results = utils.request("GET", search_url, params=query_params)
                if "values" in search_results:
                    repo_files = search_results["values"]
                    license_file = [lice["links"]["self"]["href"] for lice in repo_files
                                    if "license" in str(lice["path"]).lower()]
                    if license_file:
                        license_file_url = license_file[0]
                        license_content = self._get_bitbucket_license(license_file_url)
                        return license_content
                    else:
                        return None
                else:
                    logger.info("No search results found")
                    return None
        except Exception as exp:
            logger.error("Failed to search Bitbucket repository for [%s]: %s" % (repo_url, exp))
            return None

    def _get_github_license(self, home_url):
        logger.info("Downloading license file from Github")
        if "api.github.com/repos" not in home_url:
            url_path = utils.parse_url(home_url, only_domain=False, only_path=True).lower()
            license_url = "https://api.github.com/repos{}/license".format(url_path)
        else:
            url_path = home_url
            license_url = "{}/license".format(url_path)

        license_response = utils.request("GET", license_url, custom_headers=self.custom_header)
        if "content" in license_response:
            license_content = license_response["content"]
            decode_license_txt = base64.b64decode(license_content)
            return decode_license_txt
        else:
            return False

    @staticmethod
    def _get_bitbucket_license(license_url):
        logger.info("Downloading license file from Bitbucket")
        license_content = utils.request("GET", license_url, json_output=False, stream=True)
        return license_content

    def _create_directory_structure(self):
        if not self.created_dirs:
            logger.info("creating output directory structure")
            now = datetime.datetime.now().time().isoformat().replace(":", "").replace(".", "")
            output_dir_name = "pylicense_{}".format(now)
            license_files = os.path.join(output_dir_name, "license_files")
            output_path = os.path.join(self.output_path, license_files)
            create_dirs = utils.create_path(output_path)
            if create_dirs:
                logger.info("Successfully created output directory structure")
                self.created_dirs = output_path
                return output_path
            else:
                return False
        else:
            return self.created_dirs

    def _create_license_file(self, package_name, license_content):
        """
        Create license file with specified package name
        :param package_name:
        :return:
        """
        self._create_directory_structure()
        license_file_path = os.path.join(self.created_dirs, "{}_license.txt".format(package_name))
        utils.write_to_file(license_file_path, license_content)

    @staticmethod
    def extract_home_page_urls(home_page_url):
        """
        Extract urls from home page and then filter urls for Github and Bitbucket
        :param home_page_url:
        :return: repo url
        """
        # Fetch html content from home page url
        try:
            html_page = utils.request("GET", home_page_url, json_output=False, stream=True)
        except Exception as exp:
            logger.error("Error in extracting urls from %s\n%s" % (home_page_url, exp))
            return None

        # parse html content
        try:
            soup = BeautifulSoup(html_page, 'html.parser')
        except Exception as exp:
            logger.error("Error in parsing HTML for urls from %s\n%s" % (home_page_url, exp))
            return None

        host_name_list = list()
        url_path_list = list()

        # loop through all extracted urls
        for link in soup.findAll('a', attrs={'href': re.compile("^(http|https)://(github.com|bitbucket.org)/")}):
            href = link.get('href')
            if href != "https://github.com/snide/sphinx_rtd_theme":
                parsed_url = urlparse.urlparse(href)
                url_path_list.append(parsed_url.path)
                host_name_list.append("{}://{}".format(parsed_url.scheme, parsed_url.netloc))

        if url_path_list and host_name_list:

            # retain common url paths
            common_path_list = list(set([x for x in url_path_list if url_path_list.count(x) > 1]))
            if common_path_list:
                url_path_list = common_path_list
            else:
                url_path_list = ["/".join(utils.longest_prefix(url_path_list).strip("/").split("/")[:2])]

            # get common prefix from common elements
            url_path_list = [path.strip("/") for path in url_path_list if len(path.strip("/").split("/")) <= 2]
            valid_path = utils.longest_prefix(url_path_list)
            # valid_path = "/".join(common_path.strip("/").split("/")[:2])
            if valid_path:
                valid_path = "/" + valid_path

            # retain common host names
            host_names = [max(host_name_list)]
            if host_names:
                host_name_list = host_names

            # get common prefix from common elements
            hostname = utils.longest_prefix(host_name_list)

            # join path
            if hostname and valid_path:
                full_path = hostname + valid_path
                return full_path
            else:
                return None
        else:
            return None

    @staticmethod
    def generate_license(license_name, project_name, organization, year):
        if all((license_name, project_name, organization, year)):
            templates = ['agpl3', 'apache', 'bsd', 'bsd3', 'cc0', 'cc_by', 'cc_by_nc', 'cc_by_nc_nd',
                         'cc_by_nc_sa', 'cc_by_nd', 'cc_by_sa', 'cddl', 'epl', 'gpl2', 'gpl3', 'isc', 'lgpl',
                         'mit', 'mpl', 'unlicense', 'wtfpl', 'x11', 'zlib']
            license_name = str(license_name).lower().replace("-", "_")
            try:
                template_name = next(license for license in templates if license in license_name)
            except StopIteration:
                template_name = None

            if template_name:
                tmpl_env = Environment(
                    loader=PackageLoader('pylicense_manager', 'templates'),
                    undefined=StrictUndefined)
                license_template = tmpl_env.get_template(str(template_name) + ".txt")
                license_content = license_template.render(project=project_name, organization=organization, year=year)
                return license_content
            else:
                return None
        else:
            return None
