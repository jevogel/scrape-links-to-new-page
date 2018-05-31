#!/usr/bin/env python3
from bs4 import BeautifulSoup
import requests
import re
import os
import json
import webbrowser


headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0'}
timeout = 5
parser = 'html5lib'
session = requests.session()


def follow_redirects(url):
    try:
        response = session.get(url, headers=headers, timeout=timeout)
    except Exception as e:
        print(f'Request for {url} return error: {e}')
        return None

    content = BeautifulSoup(response.content, parser)
    meta_refresh = content.find('meta', attrs={'http-equiv': lambda x: x and x.lower()=='refresh'})

    status = response.status_code
    if meta_refresh:
        m = re.search(r'(?:url=+)(?:(?P<url>http.+)|(?P<rel>.+))', meta_refresh["content"], re.I)
        if m and m.group('url'):
            next_url = m.group('url')
            print(f'Absolute redirect: {next_url}')
            return follow_redirects(next_url)
        elif m and m.group('rel'):
            next_url = response.url + m.group('rel')
            print(f'Relative redirect: {next_url}')
            return follow_redirects(next_url)
        else:
            print(f'No match in {meta_refresh["content"]}')
    elif status == 301:
        return follow_redirects(url)
    elif status == 200:
        return response.url
    else:
        return None


def get_class_paths(url):
    tag = 'h3'
    path_map = lambda x: re.findall(r'\d+\.\d+', x)
    response = session.get(url, headers=headers)
    content = BeautifulSoup(response.content, parser)
    tags = content.find_all(tag)
    titles = [x.contents[0] for x in tags if isinstance(x.contents[0], str)]
    paths = [path_map(x) for x in titles]
    linklets = []
    for i, path in enumerate(paths):
        if path != []:
            linklet = {
                'href': path[0],
                'content': titles[i].rstrip('\n')
            }
            linklets.append(linklet)
    return linklets


def get_valid_links(url, linklets):
    links = []
    for link in linklets:
        test_url = f'{url}/{link["href"]}'
        print(f'Trying {test_url}... ', end='')
        good_url = follow_redirects(test_url)
        if good_url:
            print(f'Good url: {good_url}')
            link = {
                'href': good_url,
                'content': link["content"]
            }
            links.append(link)
        else:
            print('Invalid')
    return links


def print_link(link):
    print(f'\t{link["content"]}\t<{link["href"]}>')


def save_links(links, link_file):
    print('Saving links:')
    [print_link(link) for link in links]
    with open(link_file, 'w') as f:
        json.dump(links, f)


def gen_course_page(links, course, index_url, template_file, output_file):
    print(f'Generating course page {course["number"]}')

    with open(template_file, 'r') as f:
        doc = BeautifulSoup(f, parser)

    heading = doc.new_tag('h1')
    heading.string = f'{course["course"]}'

    home_link = doc.new_tag('a', href='index.html')
    home_link.string = '⬉ Course Index'

    cat_link = doc.new_tag('a', href=course["course_url"], target='_blank')
    cat_link.string = f'MIT {course["course"]} Course Catalog ➜'

    subject_link = doc.new_tag('a', href=index_url, target='_blank')
    subject_link.string = 'MIT Subject Listing ➜'

    home = doc.new_tag('p')
    cat = doc.new_tag('p')
    subject = doc.new_tag('p')
    subject.string = 'via '
    home.append(home_link)
    cat.append(cat_link)
    subject.append(subject_link)

    doc.body.header.append(heading)
    doc.body.header.append(home)
    doc.body.header.append(cat)
    doc.body.header.append(subject)

    ul = doc.new_tag('ul')
    doc.body.main.append(ul)
    doc.head.title.string = f'{course["course"]}'

    for link in links:
        li = doc.new_tag('li')
        a = doc.new_tag('a', href=link["href"], target='_blank', rel='noopener noreferrer')
        clnum = doc.new_tag('span')
        clnum["class"] = 'clnum'
        course_parts = list(filter(None, re.split(r'([\d\.,\s\[\]A-Z]+) (.+)', link["content"])))
        clnum.string = course_parts[0]
        a.append(clnum)
        cname = doc.new_tag('span')
        cname.string = course_parts[1]
        a.append(cname)
        li.append(a)
        doc.body.main.ul.append(li)

    with open(output_file, 'w') as f:
        f.write(doc.prettify())


def get_links(course, link_file):
    links = []
    if os.path.isfile(link_file):
        # already have list of links
        with open(link_file, 'r') as f:
            links = json.load(f)
    else:
        # need to get list of links
        for src_url in course["catalog_urls"]:
            linklets = get_class_paths(src_url)
            base_url = 'http://web.mit.edu'
            links.extend(get_valid_links(base_url, linklets))

        save_links(links, link_file)

    return links


def get_courses(base_url, course_file):
    if os.path.isfile(course_file):
        with open(course_file, 'r') as f:
            courses = json.load(f)
    else:
        courses = []
        for i in range(0, 30):
            j = 'a'
            course = ''
            course_url = base_url.format(i=i, j=j)
            catalog_urls = []
            while j:
                url = base_url.format(i=i, j=j)
                print(f'Trying url {url}... ', end='')
                response = session.get(url, headers=headers)
                if response.status_code == 200:
                    print(f'Succeeded')
                    catalog_urls.append(url)
                    content = BeautifulSoup(response.content, parser)
                    h1 = content.find('h1')
                    course = re.search(r'.+: (?P<course>.+)', h1.contents[0]).group('course')
                    j = chr(ord(j) + 1)
                else:
                    print(f'Failed')
                    j = None
            course = {
                'course': course,
                'number': i,
                'course_url': course_url,
                'catalog_urls': catalog_urls
            }
            courses.append(course)

        with open(course_file, 'w') as f:
            json.dump(courses, f)

    return courses


def gen_course_pages(courses, index_url, template_file, link_file_base, output_file_base):
    for course in courses:
        course_num = course["number"]
        link_file = link_file_base.format(course_num)
        output_file = output_file_base.format(course_num)

        links = get_links(course, link_file)
        gen_course_page(links, course, index_url, template_file, output_file)


def gen_index_page(courses, index_url, template_file, output_file_base):
    print('Generating index page.')

    with open(template_file, 'r') as f:
        doc = BeautifulSoup(f, parser)

    heading = doc.new_tag('h1')
    heading.string = 'MIT Course Websites'

    subject_link = doc.new_tag('a', href=index_url, target='_blank')
    subject_link.string = 'MIT Subject Listing ➜'

    subject = doc.new_tag('p')
    subject.append(subject_link)

    doc.body.header.append(heading)
    doc.body.header.append(subject)

    ul = doc.new_tag('ul')
    doc.body.main.append(ul)
    doc.head.title.string = f'MIT Course Websites'

    for course in courses:
        li = doc.new_tag('li')
        a = doc.new_tag('a', href=output_file_base.format(course["number"]))
        cnum = doc.new_tag('span')
        cnum["class"] = 'cnum'
        cnum.string = f'course {course["number"]}'
        a.append(cnum)
        cname = doc.new_tag('span')
        cname.string = f'{course["course"]}'
        a.append(cname)
        li.append(a)
        doc.body.main.ul.append(li)

    with open('index.html', 'w') as f:
        f.write(doc.prettify())


def main():
    course_file = 'courses.json'
    template_file = 'template.html'
    link_file_base = 'links{}.json'
    output_file_base = 'links{}.html'

    archive = ''
    index_url = 'http://student.mit.edu/catalog/{}index.cgi'.format(archive)
    base_url = 'http://student.mit.edu/catalog/{}m{{i}}{{j}}.html'.format(archive)
    # base_url = 'http://student.mit.edu/catalog/archive/spring/m{}{}.html'
    # base_url = 'http://student.mit.edu/catalog/archive/fall/m{}{}.html'

    all_courses = get_courses(base_url, course_file)
    courses = [x for x in all_courses if x["course"] != '']

    gen_index_page(courses, index_url, template_file, output_file_base)
    gen_course_pages(courses, index_url, template_file, link_file_base, output_file_base)
    webbrowser.open('index.html')


if __name__ == '__main__':
    main()
