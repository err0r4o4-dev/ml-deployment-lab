import json
from pathlib import Path
import sys
import threading

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import app


def check_browser():
    screenshots = ROOT / "docs"
    screenshots.mkdir(exist_ok=True)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    summary = {"viewport_widths": [], "checks": []}
    try:
        with sync_playwright() as playwright:
            with playwright.chromium.launch(channel="msedge", headless=True) as browser:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                response = page.goto(f"http://127.0.0.1:{server.server_port}/")
                assert response.status == 200
                expect(page.locator("#output")).to_be_hidden()
                page.keyboard.press("Tab")
                expect(page.locator("#MedInc")).to_be_focused()
                summary["checks"].append("keyboard focus and empty state")

                page.get_by_role("button", name="Use sample values").click()
                with page.expect_response("**/predict") as prediction_response:
                    page.get_by_role("button", name="Predict", exact=True).click()
                result = prediction_response.value.json()
                prediction = result["prediction"]
                expect(page.locator("#output")).to_have_attribute("data-state", "success")
                expect(page.locator("#output")).to_contain_text(f"Prediction: {prediction:.3f}")
                expect(page.locator("#output")).to_contain_text(f"${prediction * 100000:,.0f}")
                summary["prediction"] = prediction
                summary["checks"].append("real API prediction and USD conversion")

                for width in (320, 768, 1024, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    for field in page.locator('input[type="number"]').all():
                        expect(field).to_be_visible()
                    summary["viewport_widths"].append(width)
                page.screenshot(path=str(screenshots / "prediction-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 375, "height": 900})
                page.screenshot(path=str(screenshots / "prediction-mobile.png"), full_page=True)

                page.get_by_role("button", name="Reset", exact=True).click()
                expect(page.locator("#output")).to_be_hidden()
                expect(page.locator("#MedInc")).to_have_value("")
                page.get_by_role("button", name="Predict", exact=True).click()
                expect(page.locator("#MedInc")).to_be_focused()
                expect(page.locator("#output")).to_be_hidden()
                summary["checks"].append("reset and missing-input validation")

                page.get_by_role("button", name="Use sample values").click()
                page.route("**/predict", lambda route: route.abort())
                page.get_by_role("button", name="Predict", exact=True).click()
                expect(page.locator("#output")).to_have_attribute("data-state", "error")
                expect(page.locator("#output")).to_contain_text("Cannot reach the server")
                expect(page.get_by_role("button", name="Predict", exact=True)).to_be_enabled()
                page.unroute("**/predict")
                page.get_by_role("button", name="Predict", exact=True).click()
                expect(page.locator("#output")).to_have_attribute("data-state", "success")
                summary["checks"].append("network error and retry recovery")

                page.route("**/predict", lambda route: route.fulfill(
                    status=400, content_type="application/json",
                    body=json.dumps({"error": "Invalid feature values."}),
                ))
                page.get_by_role("button", name="Predict", exact=True).click()
                expect(page.locator("#output")).to_have_attribute("data-state", "error")
                expect(page.locator("#output")).to_contain_text("Invalid feature values.")
                page.unroute("**/predict")
                summary["checks"].append("server validation error display (injected response)")

                page.route("**/predict", lambda route: route.fulfill(
                    status=200, content_type="application/json", body='{"prediction":"bad"}',
                ))
                page.get_by_role("button", name="Predict", exact=True).click()
                expect(page.locator("#output")).to_contain_text("invalid prediction")
                page.unroute("**/predict")
                summary["checks"].append("invalid server prediction recovery (injected response)")

                def delayed_prediction(route):
                    expect(page.locator("#predict")).to_be_disabled()
                    expect(page.locator("#form")).to_have_attribute("aria-busy", "true")
                    expect(page.locator("#output")).to_have_attribute("data-state", "loading")
                    page.get_by_role("button", name="Reset", exact=True).click()
                    route.continue_()

                page.route("**/predict", delayed_prediction)
                page.get_by_role("button", name="Predict", exact=True).click()
                expect(page.locator("#output")).to_be_hidden()
                expect(page.get_by_role("button", name="Predict", exact=True)).to_be_enabled()
                page.unroute("**/predict")
                summary["checks"].append("loading state and reset cancels in-flight prediction")
                assert not errors, errors
                summary["checks"].append("no JavaScript runtime errors")

                with browser.new_context(java_script_enabled=False) as context:
                    fallback = context.new_page()
                    fallback.goto(f"http://127.0.0.1:{server.server_port}/")
                    for name, value in zip(
                        ["MedInc", "HouseAge", "AveRooms", "AveBedrms", "Population", "AveOccup", "Latitude", "Longitude"],
                        [8.3, 25, 6, 1, 1200, 3, 34.2, -118.3],
                    ):
                        fallback.locator(f"#{name}").fill(str(value))
                    fallback.get_by_role("button", name="Predict", exact=True).click()
                    expect(fallback.locator("#output")).to_contain_text("Prediction:")
                    fallback.locator("#MedInc").fill("9")
                    fallback.get_by_role("button", name="Reset", exact=True).click()
                    expect(fallback.locator("#MedInc")).to_have_value("8.3")
                summary["checks"].append("no-JavaScript form prediction and native reset")
        print(json.dumps(summary, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


if __name__ == "__main__":
    check_browser()
