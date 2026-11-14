from ingestion.load_data import load_data
from ingestion.chunking.cleaner import clean_markdown, remove_tail_sections

raw = load_data("../../data/raw/2005.11401v4.md")
cleaned = clean_markdown(raw)
cut = remove_tail_sections(cleaned)
print(len(raw), len(cleaned), len(cut))
print(cut[-300:])        # phần cuối còn lại: phải là cuối nội dung chính

import re
for m in re.finditer(r"^.*(?:reference|appendix).*$", cleaned, re.I | re.M):
    print(repr(m.group(0)))