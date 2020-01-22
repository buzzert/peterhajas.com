#!/usr/local/bin/python3

import os, sys
import markdown
from datetime import datetime
from pathlib import Path
import shutil

# Where to save contents
output_path_string = "out"
# Files to ignore for the site
# If a file matches these or contains any components that match these, then it
# is skipped. Additionally, all hidden files are skipped
ignore_files = ["before.html", "after.html", "build", "build.py", "deploy", "out", "readme.md", "repo_tools", "repo_setup", "rss_before.xml", "rss_after.xml", "tags"]
# The markdown extensions to use
# - tables gives MMD-style tables
# - smarty gives smartypants-style quotes
markdown_extensions = ["tables", "smarty"]

# The before.html / after.html files
before_html = Path("before.html").read_text()
after_html = Path("after.html").read_text()

# The rss_before.xml and rss_after.xml files
rss_before_xml = Path("rss_before.xml").read_text()
rss_after_xml = Path("rss_after.xml").read_text()

# Command line arguments
extra_head_marker = "<!--EXTRA_HEAD_CONTENT_HERE-->"
# live - turns on live-reloading
live_reloading = "live" in sys.argv
if live_reloading:
    print("Turning on live reloading...")
    live_js_head = '<script type="text/javascript" src="http://livejs.com/live.js"></script>' + '\n' + extra_head_marker
    before_html = before_html.replace(extra_head_marker, live_js_head)

output_path = Path(output_path_string)
index_output_path = output_path.joinpath("index.html")
rss_output_path = output_path.joinpath("rss.xml")

class MarkdownFile:
    # The title associated with this file, or None if it has none
    title = None
    # The date associated with this file, or None if it has none
    date = None
    # The contents associated with this file
    contents = ""
    # The path to export this file to, or None if it has none
    export_path = None

    def metadata(self):
        lines = self.contents.split("\n")
        # If this markdown file doesn't have 5 or more lines, it is missing its
        # metadata
        if len(lines) < 5:
            return None
        # If the second line isn't an HTML comment, this has no metadata
        if lines[1] != "<!--":
            return None
        # If the fifth line isn't an ending comment, this has no metadata
        if lines[4] != "-->":
            return None
        # OK, so now lines[2] has our title and lines[3] has our date string
        title = lines[2]
        date_string = lines[3]
        date = datetime.strptime(date_string, "%Y%m%d %H:%M")
        return { "date" : date, "title" : title }

    # contents_path: Path or None
    # export_path: Path or None
    # contents: String or None
    # Pass contents_path and then export_path and contents will be inferred
    # Pass contents and export_path to be able to save
    def __init__(self, contents_path=None, export_path=None, contents=None):
        self.contents = contents
        self.export_path = export_path
        if contents_path != None:
            self.contents = contents_path.read_text()
            self.export_path = output_path.joinpath(contents_path).with_suffix(".html")
        metadata = self.metadata()
        if metadata != None:
            self.title = metadata["title"]
            self.date = metadata["date"]

    # A pretty-formatted date for self
    def pretty_date(self):
        return self.date.strftime("%B %e, %Y") 

    # Returns whether or not we are an article
    def is_article(self):
        return self.title != None and self.date != None

    # An RSS-formatted date for self
    def rss_date(self):
        # Always PST :-/
        # From python:
        # "For a naive object, the %z and %Z format codes are replaced by empty strings."
        return self.date.strftime("%a, %d %b %Y %H:%M:%S PST")

    # The page title, with prequel, for self
    def page_title(self):
        if self.title != None:
            return self.title
        else:
            return self.export_path.stem.capitalize()

    # Just the HTML for this entry
    def html(self):
        return markdown.markdown(self.contents, extensions=markdown_extensions)

    # The decorated HTML for this entry, wrapped in <article> and with title /
    # date if appropriate
    def decorated_html(self):
        # The decorated html is:
        # - the <article> entry if we are an article
        # - the title and date if we are an article
        # - the html
        # - the </article> entry if we are an article

        is_article = self.is_article()
        decorated = ""
        if is_article:
            decorated += "<article>\n"
            decorated += "<div class='title'><a href='{}'>{}</a></div>\n".format(self.rendered_path(), self.title)
            decorated += "<div class='date'>{}</div>\n".format(self.pretty_date())
        decorated += self.html() + "\n"
        if is_article:
            decorated += "</article>\n"
        return decorated

    # HTML that is its own document
    def page_html(self):
        # The page html is:
        # - before.html
        # - the decorated html
        # - after.html

        page_html = before_html + "\n"
        page_html += self.decorated_html()
        page_html += after_html

        # replace the title
        page_html = page_html.replace("TITLE_FOR_PAGE_HERE", self.page_title())

        return page_html

    # The path this file is rendered to in the site
    # For example, /about.html, /blog/some_post.html, etc.
    def rendered_path(self):
        relative = self.export_path.relative_to(output_path)
        return Path("/").joinpath(relative)

    # The RSS item for this page
    def rss_item(self):
        return """<item>
<title>{}</title>
<guid>{}</guid>
<pubDate>{}</pubDate>
<description><![CDATA[
{}
]]></description>
        </item>""".format(self.title, self.rendered_path(), self.rss_date(), self.html())

    # Renders the file to its output location
    def render(self):
        output_path = self.export_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.page_html())

# Delete the current path
# pathlib will only delete empty directories, so we use shutil
shutil.rmtree(output_path_string, ignore_errors=True)

# Make the new path
output_path.mkdir(parents=True, exist_ok=True)

dated_markdown_files = [ ]

# Process the site. We'll look for all the files in our tree
all_file_paths = sorted(Path().rglob("*"))
for path in all_file_paths:
    # If the path is ignored, then we can skip it
    if path.is_dir():
        continue
    is_ignored = False
    parts = path.parts
    for part in parts:
        if part[0] == ".":
            is_ignored = True
            break
        if part in ignore_files:
            is_ignored = True
            break
    if is_ignored:
        continue

    path_outpath = output_path.joinpath(path)
    
    # If the path is markdown, process it
    if path.suffix == ".md":
        markdownFile = MarkdownFile(contents_path=path)
        markdownFile.render()
        # If the file has a date, add it to our list for the index / RSS
        if markdownFile.date != None:
            dated_markdown_files.append(markdownFile)
    # Otherwise, just copy it over
    else:
        file_bytes = path.read_bytes()
        path_outpath.parent.mkdir(parents=True, exist_ok=True)
        path_outpath.write_bytes(file_bytes)

# Sort dated markdown files by date
sorted_dated_markdown_files = sorted(dated_markdown_files, key=lambda entry: entry.date)
# Reverse the list (so it is newest first)
sorted_dated_markdown_files.reverse()

index_markdown_contents = ""
rss_contents = rss_before_xml
# Build the index and rss files
for entry in sorted_dated_markdown_files:
    # Index: add in contents
    index_markdown_contents += entry.decorated_html()
    index_markdown_contents += "\n"

    # RSS: add in item RSS contents
    rss_contents += entry.rss_item()

index_markdown = MarkdownFile(export_path=index_output_path, contents=index_markdown_contents)
index_markdown.render()

rss_contents += rss_after_xml
rss_output_path.write_text(rss_contents)
