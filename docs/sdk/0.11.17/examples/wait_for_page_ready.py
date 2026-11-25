"""Python 3.10+. Run without a URL for a self-contained local demonstration."""
import argparse
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time

from patchright.async_api import Error, async_playwright


# Runs once per document, including child frames, before the page's own scripts.
INSTALL_OBSERVER = """
(() => {
  let lastChange = performance.now();
  new MutationObserver(() => { lastChange = performance.now(); }).observe(document, {
    subtree: true, childList: true, attributes: true, characterData: true
  });
  Object.defineProperty(window, Symbol.for("example.domIdleAge"), {
    value: () => performance.now() - lastChange
  });
})();
"""
READ_AGE = """() => document.readyState === "complete"
  ? (window[Symbol.for("example.domIdleAge")]?.() ?? -1) : -1"""


async def navigate_and_wait(page, url, quiet_ms=500, timeout_ms=15000):
    """Use a fresh Page. Timeout covers navigation AND the shared quiet window."""
    if quiet_ms <= 0 or timeout_ms <= 0:
        raise ValueError("quiet_ms and timeout_ms must be positive")
    loop = asyncio.get_running_loop()
    pending = set()
    last_activity = loop.time()
    failures = 0
    reason = "waiting for load"

    def activity(*_):
        nonlocal last_activity
        last_activity = loop.time()

    def started(request):
        if request.resource_type not in {"eventsource", "websocket"}:
            pending.add(request)
            activity()

    def finished(request):
        if request in pending:
            pending.remove(request)
            activity()

    def failed(request):
        nonlocal failures
        if request in pending:
            failures += 1
        finished(request)

    listeners = {"request": started, "requestfinished": finished, "requestfailed": failed,
                 "frameattached": activity, "framedetached": activity, "framenavigated": activity}
    for event, handler in listeners.items():
        page.on(event, handler)

    async def wait():
        nonlocal reason
        await page.add_init_script(script=INSTALL_OBSERVER)
        response = await page.goto(url, wait_until="load", timeout=0)
        if response and response.status >= 400:
            raise RuntimeError(f"Navigation returned HTTP {response.status}")
        activity()
        while True:
            if pending or (loop.time() - last_activity) * 1000 < quiet_ms:
                reason = "network or frame activity"
            else:
                frames = tuple(page.frames)
                try:
                    ages = await asyncio.gather(*(f.evaluate(READ_AGE) for f in frames))
                except Error as exc:
                    if page.is_closed() or not any(s in str(exc).lower() for s in
                            ("execution context was destroyed", "frame was detached", "frame has been detached",
                             "cannot find context")):
                        raise
                    activity()
                    reason = "frame changed during observation"
                else:
                    reason = "DOM changed or a frame is still loading"
                    if (ages and min(ages) >= quiet_ms and not pending
                            and frames == tuple(page.frames)
                            and (loop.time() - last_activity) * 1000 >= quiet_ms):
                        return {"frames": len(frames), "failed_requests": failures}
            await asyncio.sleep(0.05)

    try:
        return await asyncio.wait_for(wait(), timeout=timeout_ms / 1000)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Readiness timeout after {timeout_ms} ms ({reason}, "
                           f"{len(pending)} requests pending)") from exc
    finally:
        for event, handler in listeners.items():
            page.remove_listener(event, handler)


@contextmanager
def local_demo():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/data":
                time.sleep(0.65)
                body, mime = b"300 products", "text/plain"
            elif self.path == "/":
                body, mime = b"""<!doctype html><h1>Catalog</h1><p id="result">Loading...</p>
                <script>addEventListener('load', () => setTimeout(async () => {
                  const data = await (await fetch('/data')).text();
                  setTimeout(() => document.querySelector('#result').textContent = data, 200);
                }, 150));</script>""", "text/html"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/"
        finally:
            server.shutdown()
            thread.join()


async def run(args, url):
    async with async_playwright() as p:
        async with await p.chromium.launch(executable_path=args.browser) as browser:
            page = await browser.new_page()
            start = time.monotonic()
            status = await navigate_and_wait(page, url, args.quiet_ms, args.timeout_ms)
            elapsed = time.monotonic() - start
            if not args.url:
                result = await page.locator("#result").text_content()
                if result != "300 products":
                    raise RuntimeError(f"Demo content was still {result!r} when marked ready")
                print(result)
            await page.screenshot(path=args.output, timeout=10000)
            print(f"Ready in {elapsed:.2f}s, {status}, screenshot: {Path(args.output).resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?")
    parser.add_argument("--browser", help="YSbrowser executable; defaults to the driver browser")
    parser.add_argument("--quiet-ms", type=int, default=500)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument("--output", default="ready.png")
    args = parser.parse_args()
    if args.url:
        asyncio.run(run(args, args.url))
    else:
        with local_demo() as url:
            asyncio.run(run(args, url))
