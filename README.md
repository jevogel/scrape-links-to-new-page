# scrapy-linky
Scrapes a collection of source pages for a set of possible URL paths, tests all possible URLs, and creates HTML documents to organize the valid links.

## Motivation
This application was created to find and organize links to as many MIT course websites as possible. MIT course websites often have lecture materials and notes available without authentication, so they can be a great source of information.

## Usage
Run the main Python application (requires Python 3). The first time it runs it will take a while to scrape and test all of the URLs, but once those are saved to file it will only take a second to regenerate the HTML pages.

## Configuration
As this application was created for the specific purpose of organizing MIT course website links, it won't work for any other purposes without modifying the code. Perhaps in the future this could be made more general purpose.
