# NCHhsStaff

Up to date info on stuff going on at NCH high school in Cincinnati, Ohio.  Go trojans

Live at **https://nchstaff.com** — an unofficial staff resource, not a district site.

## How it is built

Plain static HTML, one file per page, CSS inlined in each page. No framework, no
build step for the pages themselves — edit the HTML and push.

## Search

The search box on every page reads `search-index.json`, which holds the text of
every page section **and every page of every hosted PDF**. That file is generated,
not hand-edited.

**After adding, replacing or removing anything in `docs/`, regenerate it:**

```bash
python3 tools/build-search-index.py
```

Then commit the updated `search-index.json`. If you skip this, the new document
simply will not appear in search results — nothing breaks, it is just invisible.

Requires `pdfminer.six` (`pip install pdfminer.six`).

`tools/add-search-ui.py` injects the search box, styles and script into every
page. It is idempotent — re-run it after adding a new page.

### Known limits

- **Scanned PDFs are not searchable.** A PDF with no text layer has nothing to
  index. The script prints a warning naming any it finds. `district-calendar-2024-25.pdf`
  and `ms-extension-list-2026-27.pdf` are currently the two. The middle school list is
  transcribed into `directory.html`, so its names and extensions are still searchable.
- **Deep links into PDFs** use `#page=N`. Desktop browsers and most mobile ones
  honour it; a few third-party mobile PDF viewers ignore it and open page 1.

## Privacy

The repository is **public**. Anything committed here can be read by anyone with
the URL — `noindex` only keeps pages out of search engines.

Student-identifying data must not be committed: no IEP or 504 content, no
language plans, no rosters tying names to attendance, discipline, risk tiers or
assessment scores. Those are protected under FERPA and IDEA. Building-level
aggregates are fine; anything naming a student is not. Route staff to SameGoal
or the district dashboard instead, both of which are permission-controlled.
