## Web Crawler

The goal of this project is to create a web crawler that can estimate the percentage of Polish, Chinese, and German webpages on the internet.

### Project Files

Python program

- Web crawler.py

Log files

- file_run1.log
  - Query used: “food”
  - 11000 pages crawled, 5544 pages sampled
- file_run2.log
  - Query used: “wiki”
  - 10000 pages crawled, 3314 pages sampled

Explain.pdf

- Descriptions of functions, ideas, and limitations of the program.

### Running the program

To run the program, first install the following libraries by using pip:

- googlesearch-python
- requests
- lxml
- langdetect
- urllib3

To execute the program, type the following in the command prompt: python "Web crawler.py"

After the program is executed, an input will be prompted. This input will be used as the query for getting the initial seed pages from Google search. Please type a query and press enter.
