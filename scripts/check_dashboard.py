"""Exercise all five pages in a running local Streamlit app using Chrome."""

import argparse
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


PAGES = (
    ("", "经营与履约概览", ("99,441", "97.02%", "96,470", "6.77%", "6,534", "14.69%")),
    ("delivery", "履约异常诊断", ("96,281 笔订单", "延误高峰月回顾")),
    ("experience", "客户体验分析", ("62.42%", "9.27%", "53.15 个百分点", "调整后 OR 为 15.44")),
    ("sellers", "商家排查优先级", ("415", "75.34%", "21 家", "0.371", "2 / 10 家")),
    ("scenarios", "改善情景测算", ("1,522", "24.05%", "366", "36.6", "329.4")),
)


def expect_text(page, phrase):
    expect(page.locator("main")).to_contain_text(phrase)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1500, "height": 1100}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for route, title, anchors in PAGES:
            page.goto(f"{args.url.rstrip('/')}/{route}", wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible(timeout=15000)
            for anchor in anchors:
                expect_text(page, anchor)
            expect(page.locator('[data-testid="stException"]')).to_have_count(0)
            expect(page.locator('[data-testid="stError"]')).to_have_count(0)
            chart_count = {"": 2, "delivery": 4, "experience": 2, "sellers": 1, "scenarios": 0}[route]
            if chart_count:
                expect(page.locator('[data-testid="stVegaLiteChart"]')).to_have_count(chart_count)
                expect(page.locator('[data-testid="stVegaLiteChart"] canvas, [data-testid="stVegaLiteChart"] svg').first).to_be_visible()
            assert page.locator("main").evaluate("(el) => el.scrollWidth <= el.clientWidth + 1"), title
            if route == "delivery":
                page.get_by_role("tab", name="订单主品类").click()
                expect_text(page, "床品、桌布与浴室用品")
                page.get_by_role("tab", name="收货州").click()
            if route == "experience":
                page.get_by_text("模型估计与敏感性分析").click()
                expect(page.locator('[data-testid="stDataFrame"]')).to_have_count(2)
                page.get_by_text("模型估计与敏感性分析").click()
            if route == "sellers":
                page.get_by_text("全量样本的平滑延误率与超额延误").click()
                page.get_by_text("高峰期收货州 × 订单主品类同行对比").click()
                expect(page.locator('[data-testid="stDataFrame"]')).to_have_count(3)
                page.get_by_text("高峰期收货州 × 订单主品类同行对比").click()
                page.get_by_text("全量样本的平滑延误率与超额延误").click()
            if args.screenshots:
                page.locator("h1").scroll_into_view_if_needed()
                page.screenshot(path=args.screenshots / f"{route or 'overview'}.png", animations="disabled")
            print(f"PASS {title}: expected values and {chart_count} chart containers", flush=True)
        slider = page.get_by_role("slider").first
        slider.press("Home")
        expect_text(page, "0.0")
        slider.press("End")
        expect_text(page, "109.8")
        for _ in range(10):
            slider.press("ArrowLeft")
        expect(page.locator('[data-testid="stMetricValue"]').nth(1)).to_have_text("73.2")
        expect(page.locator('[data-testid="stMetricValue"]').nth(2)).to_have_text("292.8")
        print("PASS scenario slider: zero, 30%, 20%, and remaining orders", flush=True)

        page.get_by_role("link", name="经营与履约概览").click()
        expect_text(page, "6.77%")
        state = page.locator('[data-testid="stMultiSelect"]').nth(0)
        state.get_by_role("combobox").fill("RJ")
        page.get_by_role("option", name="RJ", exact=True).click()
        expect_text(page, "12.11%")
        expect_text(page, "1,495")
        page.keyboard.press("Escape")
        category = page.locator('[data-testid="stMultiSelect"]').nth(1)
        category.get_by_role("combobox").fill("床品")
        page.get_by_role("option", name="床品、桌布与浴室用品", exact=True).click()
        expect_text(page, "已选 1 个州 · 已选 1 个主品类")
        expect(page.locator('[data-testid="stMetricValue"]').nth(0)).to_have_text("1,388")
        expect(page.locator('[data-testid="stMetricValue"]').nth(2)).to_have_text("1,352")
        expect(page.locator('[data-testid="stMetricValue"]').nth(4)).to_have_text("202")
        expect(page.locator('[data-testid="stException"]')).to_have_count(0)
        page.keyboard.press("Escape")
        page.get_by_role("link", name="履约异常诊断").click()
        expect(page.get_by_role("heading", name="履约异常诊断", exact=True)).to_be_visible()
        expect_text(page, "已选 1 个州 · 已选 1 个主品类")
        month = page.get_by_role("slider").first
        month.press("ArrowRight")
        expect_text(page, "下单月份：2016-10")
        print("PASS state, category and purchase-month filters; scope persists across delivery pages", flush=True)
        page.get_by_role("link", name="客户体验分析").click()
        expect_text(page, "62.42%")
        expect(page.locator('[data-testid="stMultiSelect"]')).to_have_count(0)
        print("PASS fixed model sample and unavailable geographic controls", flush=True)

        page.get_by_role("link", name="商家排查优先级").click()
        page.get_by_role("combobox").last.click()
        page.get_by_role("option", name=re.compile(r"^02")).click()
        expect_text(page, "71/591")
        expect_text(page, "27.92 天")
        print("PASS seller selector and matched-peer detail", flush=True)
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    main()
