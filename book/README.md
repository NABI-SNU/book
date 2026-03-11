# Jupyter Book Support

This repo builds a curated session-based Jupyter Book from the checked-in `tutorials/` tree.

The GitHub workflows are defined in:

- `.github/workflows/deploy-cloudflare-book.yml`

To build the student book locally:

1. Install dependencies

`pip install -r requirements.txt`

`pip install jupyter-book==0.14.0 pyyaml beautifulsoup4 jupyter_client==7.3.5`

2. Generate the table of contents and stage the curated notebooks under `book/tutorials/`

`python3 ci/generate_book.py student`

3. Build the book

`jupyter-book build book`

4. Clean rendered HTML for known notebook-output issues

`python3 ci/parse_html_for_errors.py student`

The rendered site will be available under `book/_build/html/index.html`.
