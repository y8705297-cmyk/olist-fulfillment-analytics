"""Print the Markdown business report using Pandoc and the installed Chrome browser."""

import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/business_report.md"


def main():
    html = subprocess.check_output([
        "pandoc", SOURCE.name, "--from=markdown", "--to=html5", "--standalone",
    ], cwd=SOURCE.parent, text=True)
    css = SOURCE.with_name("report_print.css").read_text()
    printable = SOURCE.with_suffix(".print.html")
    printable.write_text(html.replace("</head>", f"<style>{css}</style></head>"))
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome")
            page = browser.new_page()
            page.goto(printable.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            if page.locator("img").evaluate_all("(images) => images.some(i => !i.complete || !i.naturalWidth)"):
                raise RuntimeError("A report chart did not load.")
            page.pdf(
                path=SOURCE.with_suffix(".pdf"), print_background=True, prefer_css_page_size=True,
                display_header_footer=True, header_template="<div></div>",
                footer_template="""<div style="width:100%;padding:0 17mm;font:9px Arial;color:#4d686d;
                  display:flex;justify-content:space-between"><span>OLIST MARKETPLACE FULFILLMENT</span>
                  <span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>""",
            )
            browser.close()
    finally:
        printable.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
