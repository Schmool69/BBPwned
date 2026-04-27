# BBPwned

A desktop tool for **bug bounty reconnaissance and testing**, built to streamline the early stages of finding and documenting vulnerabilities.

It combines scope discovery, directory mapping, basic crawling, and testing into a single GUI so you can move from target selection → exploration → testing without juggling multiple tools.

---

## Overview

This tool is designed as a lightweight all-in-one workflow for bug bounty hunting:

* define and explore program scope
* map out target structure
* identify interesting endpoints
* run basic testing
* keep everything organised in one place

---

## Features

### Scope Discovery

* Fetches HackerOne program data
* Filters for bounty-eligible domains and URLs
* Lets you quickly select in-scope targets

### Directory / Endpoint Mapping

* Crawls selected domains
* Builds a visual URL tree
* Tracks visited endpoints
* Handles query parameters and variations

### Crawling Options

* Adjustable depth:

  * Light
  * Medium
  * Deep
* Crawl strategies:

  * Breadth-first (default)
  * Depth-first
* Recrawl from specific nodes

### Basic Testing Workflow

* Identify endpoints with parameters
* Surface forms and input points
* Helps highlight areas worth manual testing

### GUI Interface

* Built with `customtkinter`
* Simple navigation between views
* Interactive tree exploration

---

## Requirements

```bash
pip install requests customtkinter beautifulsoup4 requests-html
```

---

## Setup

Before running, add your HackerOne API credentials.

Find:

```python
login = ('-H1_USERNAME-', '-H1_API_KEY-')
```

Replace with:

```python
login = ('your_username', 'your_api_key')
```

> Tip: avoid hardcoding credentials in real projects — use environment variables instead.

---

## Running

```bash
python BBPwned.py
```

This launches the GUI.

---

## How to use

1. Enter a HackerOne program handle
2. Select a domain from the scope list
3. Choose crawl depth and strategy
4. Start crawling
5. Explore the generated URL tree
6. Click nodes to:

   * recrawl deeper
   * identify interesting endpoints
7. Use findings as a base for manual testing

---

## Typical Workflow

A common way to use the tool:

1. Pull program scope
2. Pick a target domain
3. Run a medium crawl
4. Look for:

   * endpoints with parameters
   * unusual paths
   * forms / inputs
5. Recrawl interesting areas
6. Move into manual testing (XSS, IDOR, etc.)

---

## Limitations

* not a full vulnerability scanner
* limited JS parsing (may miss dynamic routes)
* no built-in exploitation modules
* minimal error handling
* no rate limiting

---

## Possible improvements

* plugin system for vulnerability checks
* request replay / editing
* proxy support (Burp/ZAP integration)
* export results (JSON, markdown)
* better deduplication of URLs
* async crawling for performance
* authentication / header support

---

## Disclaimer

This tool is intended for **legal bug bounty and authorised testing only**.

Only use it on targets where you have permission, and always follow the program’s rules and scope.

---

## Notes

Built as a personal tool to speed up recon and make early-stage bug hunting a bit less manual.

If you’re used to juggling multiple tools during recon, this just pulls a few of those steps into one place.
