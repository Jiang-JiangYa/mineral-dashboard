"""公开网页采集与授权行情导入；不绕过 robots、登录墙或验证码。"""

import csv
import hashlib
import io
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date

from .models import MINERALS, Record, identify, utcnow
from .settings import csv_env
from .text import canonical_url, clean_text


class Fetcher:
    def __init__(self, settings):
        self.settings = settings
        self.agent = os.getenv("USER_AGENT", "MineralDashboard/0.3")
        self.client = httpx.Client(
            timeout=settings.request_timeout,
            follow_redirects=True,
            headers={"User-Agent": self.agent},
        )
        self.last, self.robots = {}, {}

    def close(self):
        self.client.close()

    def _request(self, url, headers=None):
        host = urlsplit(url).netloc
        for attempt in range(self.settings.http_retries + 1):
            time.sleep(
                max(0, self.settings.request_interval - (time.monotonic() - self.last.get(host, 0)))
            )
            self.last[host] = time.monotonic()
            try:
                response = self.client.get(url, headers=headers)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.settings.http_retries:
                        delay = response.headers.get("Retry-After", "")
                        time.sleep(min(30, float(delay) if delay.isdigit() else 2**attempt))
                        continue
                response.raise_for_status()
                return response
            except httpx.TransportError:
                if attempt == self.settings.http_retries:
                    raise
                time.sleep(2**attempt)

    def get(self, url, headers=None, authorized=False):
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("采集地址必须为 HTTP(S)")
        origin = f"{parts.scheme}://{parts.netloc}"
        if not authorized:
            if origin not in self.robots:
                parser = RobotFileParser()
                try:
                    robot_response = self._request(origin + "/robots.txt")
                    parser.parse(robot_response.text.splitlines())
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in (404, 410):
                        raise
                    # RFC 9309: robots missing (404/410) is not a crawl prohibition.
                    parser.parse([])
                self.robots[origin] = parser
            if not self.robots[origin].can_fetch(self.agent, url):
                raise PermissionError("robots.txt 禁止访问此路径")
        response = self._request(url, headers)
        raw_dir = self.settings.data_dir / "raw"
        raw_dir.mkdir(exist_ok=True)
        raw = raw_dir / (hashlib.sha256(response.content).hexdigest() + ".raw")
        raw.write_bytes(response.content)
        return response, str(raw.relative_to(self.settings.data_dir))


def article(html, url, source, kind, fallback_date=None, raw_path=""):
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one("h1") or soup.find("title")
    if not title_node:
        raise ValueError("缺少标题")
    date = None
    for selector in [
        'meta[property="article:published_time"]',
        'meta[name="pubdate"]',
        'meta[name="publishdate"]',
        'meta[name="PubDate"]',
        "time[datetime]",
        'meta[name="DC.date.issued"]',
    ]:
        node = soup.select_one(selector)
        if node:
            date = node.get("content") or node.get("datetime")
            break
    if not date:
        for script in soup.select('script[type="application/ld+json"]'):
            match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', script.get_text())
            if match:
                date = match[1]
                break
    if not date:
        # Only use labelled publication dates, never an arbitrary date in article prose.
        match = re.search(
            r"(?:发布时间|发布日期|Published|Date published)\s*[:：]?\s*(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})",
            soup.get_text(" ", strip=True),
            re.I,
        )
        if match:
            date = match[1].replace("年", "-").replace("月", "-")
    if not date and not fallback_date:
        raise ValueError("缺少可核验的发布日期")
    published = parse_date(date) if date else fallback_date
    if published.tzinfo is None:
        # Source sites: Chinese sites use UTC+8; Australian dateless zone is documented UTC baseline.
        published = published.replace(
            tzinfo=timezone(timedelta(hours=8)) if "regcc.cn" in url else timezone.utc
        )
    for node in soup.select(
        "script,style,nav,footer,header,aside,form,.related-posts,.advertisement"
    ):
        node.decompose()
    body = soup.select_one(
        ".article-content,.entry-content,.field--name-body,.view.TRScode,.TRS_Editor,.content-article,article"
    ) or soup.select_one("main")
    if not body:
        raise ValueError("未识别正文容器")
    text = clean_text(body.get_text("\n", strip=True))
    if len(text) < 200:
        raise ValueError("正文不足 200 字符，可能为摘要或登录墙")
    if kind == "policy" and (
        not identify(text + title_node.get_text(), MINERALS)
        or not re.search(
            r"政策|战略|条例|通知|办法|规定|strategy|policy|regulation|legislation|framework",
            title_node.get_text(),
            re.I,
        )
    ):
        raise ValueError("不属于可识别的矿产政策文件")
    return Record(
        kind=kind,
        source=source,
        url=url,
        title=title_node.get_text(" ", strip=True),
        text=text,
        published_at=published,
        raw_path=raw_path,
        publisher=source,
        document_type="web_article",
    )


def price_records(content, source, url, format="csv"):
    rows = (
        json.loads(content)
        if format == "json"
        else list(csv.DictReader(io.StringIO(content.lstrip("\ufeff"))))
    )
    if isinstance(rows, dict):
        rows = rows.get("items", rows.get("data", []))
    for index, row in enumerate(rows, 1):
        try:
            # Authorized feeds are normalized explicitly; unknown vendor schemas fail instead of guessing units.
            date = parse_date(row["published_at"])
            if date.tzinfo is None:
                raise ValueError("行情时间必须包含时区")
            price = str(row["price"])
            instrument = row["instrument"]
            market = row["market"]
            title = f"{market} {instrument} {row.get('contract', '')} {row['quote_type']}"
            text = (
                f"{title}；时间 {date.isoformat()}；价格 {price} {row['currency']}/{row['unit']}。"
            )
            yield Record(
                kind="price",
                source=source,
                url=row.get("url") or url,
                title=title,
                text=text,
                published_at=date,
                market=market,
                instrument=instrument,
                contract=row.get("contract", ""),
                quote_type=row["quote_type"],
                currency=row["currency"],
                unit=row["unit"],
                price=price,
                minerals=identify(instrument, MINERALS),
                document_type="price_observation",
            )
        except Exception as exc:
            raise ValueError(f"行情第 {index} 行无效：{exc}") from exc


SOURCE_SPECS = [
    ("mining", "MINING.COM", "news", "rss", "MINING_RSS_URLS", "https://www.mining.com/feed/"),
    ("spglobal", "S&P Global Mining", "news", "rss", "SPGLOBAL_RSS_URLS", ""),
    (
        "disr",
        "Australia DISR",
        "policy",
        "html",
        "DISR_URLS",
        "https://www.industry.gov.au/news,https://www.industry.gov.au/publications/critical-minerals-strategy-2023-2030",
    ),
    (
        "regcc",
        "中国稀土集团",
        "policy",
        "html",
        "REGCC_URLS",
        "https://www.regcc.cn/zgxtjt/cydt/list.shtml,https://www.regcc.cn/zgxtjt/gsgg/list.shtml",
    ),
    ("lme", "LME", "price", "price", "LME_DATA_URL", ""),
    ("mysteel", "上海钢联", "price", "price", "MYSTEEL_DATA_URL", ""),
    ("gfex", "GFEX（可选替代，非 SHFE）", "price", "price", "GFEX_DATA_URL", ""),
]


def collect_source(store, spec, days=30, limit=200, max_pages=30):
    source_id, name, kind, mode, env, default = spec
    urls = csv_env(env, default)
    report = dict(
        id=source_id,
        name=name,
        kind=kind,
        status="running",
        attempted=0,
        inserted=0,
        updated=0,
        unchanged=0,
        duplicate=0,
        skipped=0,
        excluded={},
        errors=[],
    )
    if not urls:
        message = "需要提供实际 RSS 地址" if mode == "rss" else "需要配置已获授权的标准化行情接口"
        report.update(status="needs_configuration", message=f"{message}（{env}）")
        return report
    cutoff, fetcher = utcnow() - timedelta(days=days), Fetcher(store.settings)
    visited, queue, accepted = set(), [(url, None) for url in urls], 0
    try:
        if mode == "price":
            headers = json.loads(os.getenv(source_id.upper() + "_AUTH_HEADERS", "{}"))
            for url in urls:
                response, raw = fetcher.get(url, headers, authorized=True)
                records = list(
                    price_records(
                        response.text,
                        name,
                        url,
                        "json" if "json" in response.headers.get("content-type", "") else "csv",
                    )
                )
                for record in records:
                    if record.published_at < cutoff or accepted >= limit:
                        report["skipped"] += 1
                        continue
                    record.raw_path = raw
                    result = store.upsert(record)
                    report[result["status"]] += 1
                    accepted += 1
        else:
            while queue and len(visited) < max_pages and accepted < limit:
                url, date_hint = queue.pop(0)
                url = canonical_url(url)
                if url in visited:
                    continue
                visited.add(url)
                report["attempted"] += 1
                try:
                    response, raw = fetcher.get(url)
                    is_feed = mode == "rss" and (
                        "xml" in response.headers.get("content-type", "") or "/feed" in url
                    )
                    if is_feed:
                        feed = feedparser.parse(response.content)
                        for entry in feed.entries:
                            date_parts = entry.get("published_parsed") or entry.get(
                                "updated_parsed"
                            )
                            published = (
                                datetime(*date_parts[:6], tzinfo=timezone.utc)
                                if date_parts
                                else None
                            )
                            if published and published < cutoff:
                                continue
                            if entry.get("link"):
                                queue.append((entry.link, published))
                        for link in feed.feed.get("links", []):
                            if link.get("rel") == "next":
                                queue.append((urljoin(url, link["href"]), None))
                        if (
                            "wordpress" in feed.feed.get("generator", "").lower()
                            and feed.entries
                            and any(
                                (entry.get("published_parsed") or entry.get("updated_parsed"))
                                and datetime(
                                    *(entry.get("published_parsed") or entry.get("updated_parsed"))[
                                        :6
                                    ],
                                    tzinfo=timezone.utc,
                                )
                                >= cutoff
                                for entry in feed.entries
                            )
                        ):
                            parts = urlsplit(url)
                            params = dict(parse_qsl(parts.query))
                            params["paged"] = str(int(params.get("paged", 1)) + 1)
                            queue.append(
                                (
                                    urlunsplit(
                                        (
                                            parts.scheme,
                                            parts.netloc,
                                            parts.path,
                                            urlencode(params),
                                            "",
                                        )
                                    ),
                                    None,
                                )
                            )
                    else:
                        try:
                            record = article(
                                response.text, str(response.url), name, kind, date_hint, raw
                            )
                            if record.published_at >= cutoff:
                                result = store.upsert(record)
                                report[result["status"]] += 1
                                accepted += 1
                            else:
                                report["skipped"] += 1
                                report["excluded"]["outside_window"] = (
                                    report["excluded"].get("outside_window", 0) + 1
                                )
                        except ValueError as exc:
                            report["skipped"] += 1
                            reason = str(exc).split("\n")[0][:120]
                            report["excluded"][reason] = report["excluded"].get(reason, 0) + 1
                        if mode == "html":
                            soup = BeautifulSoup(response.text, "html.parser")
                            for link in soup.select("a[href]"):
                                target = urljoin(url, link["href"])
                                label = link.get_text(" ", strip=True)
                                if urlsplit(target).hostname != urlsplit(
                                    url
                                ).hostname or target.lower().endswith(
                                    (".pdf", ".jpg", ".png", ".zip")
                                ):
                                    continue
                                if re.search(
                                    r"critical|mineral|rare earth|稀土|矿产|下一页|Next",
                                    label,
                                    re.I,
                                ):
                                    queue.append((target, None))
                except Exception as exc:
                    if len(report["errors"]) < 8:
                        report["errors"].append(f"{url}: {type(exc).__name__}: {exc}")
        report["status"] = (
            "completed_with_gaps" if report["errors"] or accepted < limit else "completed"
        )
        report["accepted"] = accepted
        report["message"] = f"本次处理 {accepted} 条有效记录，目标 {limit} 条。"
        if report["errors"]:
            report["message"] += "存在访问限制或网络错误，详见作业详情。"
    except Exception as exc:
        report.update(status="failed", message=f"{type(exc).__name__}: {exc}")
    finally:
        fetcher.close()
    return report
