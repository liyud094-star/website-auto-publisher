from __future__ import annotations

import hashlib
import json
import os
import random
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
DOMAIN_FILE = ROOT / "domains.txt"
CONFIG_FILE = ROOT / "config.json"
POSTS_DIR = ROOT / "posts"
DAILY_LINKS_DIR = ROOT / "daily-links"
LATEST_LINKS_FILE = ROOT / "latest-links.txt"
README_FILE = ROOT / "README.md"


TITLE_BASES = [
    "公开网站入口整理",
    "第三方链接维护记录",
    "网站访问核验清单",
    "域名资源分批归档",
    "公开链接更新日志",
    "网站巡检任务记录",
    "第三方站点导航目录",
    "网站链接整理档案",
    "域名入口检查计划",
    "公开网站索引记录",
    "链接维护工作清单",
    "网站地址分组目录",
    "第三方链接归档记录",
    "站点入口复核任务",
    "网站资源维护日志",
    "公开域名整理清单",
    "链接状态检查档案",
    "网站入口维护计划",
    "第三方地址核验记录",
    "站点资源归档目录",
    "网络资源访问记录",
    "网站入口分组记录",
    "域名访问核验记录",
    "公开站点维护索引",
    "网站资源检查记录",
    "网络地址整理记录",
    "公开入口更新记录",
    "站点地址维护清单",
    "第三方域名整理记录",
    "网站资源复核目录",
]

TITLE_QUALIFIERS = [
    "访问说明",
    "整理与核验",
    "分批记录",
    "维护参考",
    "公开索引",
    "访问检查",
    "资源汇总",
    "更新记录",
    "分类整理",
    "安全访问提示",
    "日常维护",
    "入口复核",
]

INTRODUCTIONS = [
    "本页用于整理一批第三方网站入口，方便后续访问、核验和维护。",
    "以下链接仅作为网站地址索引，不代表推荐、合作或内容来源关系。",
    "本页记录待复核的网站地址，实际状态应以人工访问结果为准。",
    "以下内容属于第三方链接归档，不对网站内容和安全性作保证。",
    "本页面用于分批维护公开网站入口，不构成认证或内容背书。",
    "本页用于记录一组公开可访问的网站地址，并提供基础访问检查提示。",
    "本批内容以域名整理和入口核验为目的，便于后续维护与人工复查。",
    "以下网站地址来自当前维护列表，页面仅承担导航、分类和记录功能。",
]

DISCLAIMERS = [
    "第三方网站内容可能随时变化，请访问者自行判断。",
    "未经实际核验，不应将这些网站描述为官方、权威或安全站点。",
    "遇到异常跳转、自动下载或信息提交要求时，请谨慎操作。",
    "网站被收录仅表示地址已进入整理列表，不代表内容得到认可。",
    "如需提交账号、联系方式或支付信息，请先确认网站真实性和连接安全性。",
]

CONTEXT_BLOCKS = [
    (
        "访问前可以检查什么",
        "打开陌生网站前，可以先确认浏览器地址栏中的域名是否与预期一致，并留意 HTTPS 连接、异常跳转和浏览器安全提示。域名能够访问并不等于其内容已经经过核验，因此本页仍保留人工复查状态。",
    ),
    (
        "域名记录为什么需要定期复核",
        "域名的解析、页面内容和跳转目标都可能发生变化。定期复核可以帮助维护者发现失效地址、跳转变化或内容变更，并及时更新后续记录。",
    ),
    (
        "如何使用本页的链接",
        "本页中的链接主要用于导航和检查。访问后如果页面与预期不一致，应以实际页面为准，不要仅依据域名名称判断网站用途，也不要把未核验的网站标注为合作方或权威来源。",
    ),
    (
        "访问陌生站点时的基本原则",
        "对于首次访问的站点，建议避免直接下载未知文件，也不要在尚未确认网站真实性时提交敏感信息。若浏览器出现证书、重定向或下载提醒，应先停止操作并重新核对地址。",
    ),
    (
        "链接记录的维护方式",
        "为了便于持续维护，链接可以按日期、域名后缀和批次进行记录。后续复核时，只需要针对状态发生变化的地址更新备注，不必重新整理全部历史页面。",
    ),
    (
        "为什么保留原始域名作为锚文本",
        "本页大多数链接直接使用域名作为显示文字，便于访问者在点击前识别目标地址，也便于维护者核对是否出现拼写差异或跳转异常。",
    ),
    (
        "页面状态说明",
        "“待复核”表示该地址已经进入整理列表，但尚未对当前内容、运营主体或安全性做进一步判断。这个状态只用于内部维护，不代表网站存在问题。",
    ),
    (
        "后续检查建议",
        "如果需要进一步检查，可以依次确认域名是否解析、HTTPS 是否正常、首页是否可访问以及页面是否存在异常跳转。检查结果应记录事实，不对无法确认的信息作推断。",
    ),
]


def load_config() -> dict:
    # 保留原有三个配置项，同时新增可选增强项。
    # 旧 config.json 不需要修改也可以直接继续运行。
    default = {
        "posts_per_day": 2000,
        "domains_per_post": 54,
        "timezone": "Asia/Shanghai",
        "content_mode": "mixed",
        "content_ratio": 0.20,
        "add_internal_links": True,
        "context_sections": 2,
    }

    if not CONFIG_FILE.exists():
        return default

    loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    default.update(loaded)
    return default


def normalize_domain(value: str) -> str:
    value = value.strip()

    if not value or value.startswith("#"):
        return ""

    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)
    domain = parsed.netloc or parsed.path
    domain = domain.strip().strip("/").lower()

    if "@" in domain:
        domain = domain.rsplit("@", 1)[-1]

    if ":" in domain:
        domain = domain.split(":", 1)[0]

    if not re.fullmatch(r"[a-z0-9.-]+", domain):
        return ""

    return domain


def load_domains() -> list[str]:
    if not DOMAIN_FILE.exists():
        raise FileNotFoundError("找不到 domains.txt")

    domains: list[str] = []

    for line in DOMAIN_FILE.read_text(encoding="utf-8").splitlines():
        domain = normalize_domain(line)

        if domain:
            domains.append(domain)

    return list(dict.fromkeys(domains))


def make_seed(*parts: object) -> int:
    source = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def numbered_template(domains: list[str]) -> str:
    lines = ["## 网站入口", ""]

    for index, domain in enumerate(domains, start=1):
        lines.append(f"{index}. [{domain}](https://{domain})")

    return "\n".join(lines)


def checklist_template(domains: list[str]) -> str:
    lines = ["## 待核验网站", ""]

    for domain in domains:
        lines.append(f"- [ ] [{domain}](https://{domain})")

    return "\n".join(lines)


def table_template(domains: list[str]) -> str:
    lines = [
        "## 网站检查表",
        "",
        "| 序号 | 网站 | 当前状态 |",
        "|---:|---|---|",
    ]

    for index, domain in enumerate(domains, start=1):
        lines.append(
            f"| {index} | [{domain}](https://{domain}) | 待核验 |"
        )

    return "\n".join(lines)


def suffix_template(domains: list[str]) -> str:
    groups: dict[str, list[str]] = {}

    for domain in domains:
        suffix = "." + domain.rsplit(".", 1)[-1]
        groups.setdefault(suffix, []).append(domain)

    lines = ["## 按域名后缀分类", ""]

    for suffix in sorted(groups):
        lines.extend([f"### `{suffix}`", ""])

        for domain in groups[suffix]:
            lines.append(f"- [{domain}](https://{domain})")

        lines.append("")

    return "\n".join(lines).rstrip()


def details_template(domains: list[str]) -> str:
    split_point = max(1, len(domains) // 2)
    groups = [domains[:split_point], domains[split_point:]]
    lines = ["## 折叠式网站目录", ""]

    for index, group in enumerate(groups, start=1):
        if not group:
            continue

        lines.extend(
            [
                "<details>",
                f"<summary>第 {index} 组网站</summary>",
                "",
            ]
        )

        for domain in group:
            lines.append(f"- [{domain}](https://{domain})")

        lines.extend(["", "</details>", ""])

    return "\n".join(lines).rstrip()


def cards_template(domains: list[str]) -> str:
    lines = ["## 域名记录卡", ""]

    for domain in domains:
        suffix = "." + domain.rsplit(".", 1)[-1]

        lines.extend(
            [
                f"### {domain}",
                "",
                f"- 访问地址：[{domain}](https://{domain})",
                f"- 域名后缀：`{suffix}`",
                "- 当前状态：待核验",
                "- 检查日期：待填写",
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines).rstrip()


TEMPLATES = [
    numbered_template,
    checklist_template,
    table_template,
    suffix_template,
    details_template,
    cards_template,
]


def repository_context() -> tuple[str, str, str]:
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get(
        "GITHUB_REPOSITORY",
        "YOUR_ACCOUNT/YOUR_REPOSITORY",
    )

    ref_name = os.environ.get("GITHUB_REF_NAME", "main")

    return server_url.rstrip("/"), repository, ref_name


def build_post_url(post_path: str) -> str:
    server_url, repository, ref_name = repository_context()
    return (
        f"{server_url}/{repository}/blob/"
        f"{ref_name}/{post_path}"
    )


def update_readme(entries: list[str], date_text: str) -> None:
    marker_start = "<!-- AUTO-POSTS-START -->"
    marker_end = "<!-- AUTO-POSTS-END -->"

    if README_FILE.exists():
        current = README_FILE.read_text(encoding="utf-8")
    else:
        current = "# 网站链接整理记录\n"

    if marker_start not in current or marker_end not in current:
        current = (
            current.rstrip()
            + "\n\n## 自动发布记录\n\n"
            + marker_start
            + "\n"
            + marker_end
            + "\n"
        )

    before, remaining = current.split(marker_start, 1)
    old_section, after = remaining.split(marker_end, 1)

    old_lines = [
        line
        for line in old_section.strip().splitlines()
        if line.strip()
    ]

    date_heading = f"### {date_text}"

    filtered_lines: list[str] = []
    skip_date_section = False

    for line in old_lines:
        if line.startswith("### "):
            skip_date_section = line == date_heading

            if skip_date_section:
                continue

        if skip_date_section:
            continue

        filtered_lines.append(line)

    new_section_lines = [date_heading, "", *entries, ""]

    if filtered_lines:
        new_section_lines.extend(filtered_lines)

    updated = (
        before.rstrip()
        + "\n\n"
        + marker_start
        + "\n"
        + "\n".join(new_section_lines).rstrip()
        + "\n"
        + marker_end
        + after
    )

    README_FILE.write_text(updated, encoding="utf-8")


def write_link_collections(
    date_text: str,
    post_records: list[dict[str, str]],
) -> None:
    DAILY_LINKS_DIR.mkdir(parents=True, exist_ok=True)

    urls = [record["url"] for record in post_records]
    plain_text = "\n".join(urls) + "\n"

    daily_txt = DAILY_LINKS_DIR / f"{date_text}.txt"
    daily_txt.write_text(plain_text, encoding="utf-8")

    LATEST_LINKS_FILE.write_text(plain_text, encoding="utf-8")

    markdown_lines = [
        f"# {date_text} 自动发布链接汇总",
        "",
        f"> 当天共生成 {len(post_records)} 篇。",
        "",
        "## 一键复制",
        "",
        "```text",
        *urls,
        "```",
        "",
        "## 可点击链接",
        "",
    ]

    for index, record in enumerate(post_records, start=1):
        markdown_lines.append(
            f"{index}. [{record['title']}]({record['url']})"
        )

    markdown_lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 本页由 GitHub Actions 自动生成。",
            "- `latest-links.txt` 始终保存最近一次生成的链接。",
            "",
        ]
    )

    daily_md = DAILY_LINKS_DIR / f"{date_text}.md"
    daily_md.write_text(
        "\n".join(markdown_lines),
        encoding="utf-8",
    )


def select_post_domains(
    all_domains: list[str],
    date_text: str,
    post_number: int,
    count: int,
) -> list[str]:
    seed = make_seed(date_text, post_number, "domains")
    rng = random.Random(seed)
    copied = all_domains.copy()
    rng.shuffle(copied)

    return copied[:count]


def make_display_title(date_text: str, post_number: int, seed: int) -> str:
    base = TITLE_BASES[seed % len(TITLE_BASES)]
    qualifier = TITLE_QUALIFIERS[
        (seed // len(TITLE_BASES)) % len(TITLE_QUALIFIERS)
    ]
    return f"{base}｜{qualifier}：{date_text} 第 {post_number} 篇"


def build_batch_overview(domains: list[str]) -> str:
    suffixes = ["." + domain.rsplit(".", 1)[-1] for domain in domains]
    counts = Counter(suffixes)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    top_items = ordered[:5]
    suffix_text = "、".join(
        f"`{suffix}` {count} 个" for suffix, count in top_items
    )

    sorted_domains = sorted(domains)
    first_domain = sorted_domains[0]
    last_domain = sorted_domains[-1]

    lines = [
        "## 本批概览",
        "",
        f"本批共整理 **{len(domains)}** 个不同域名，覆盖 **{len(counts)}** 种域名后缀。",
        f"数量较多的后缀包括：{suffix_text}。",
        f"按字母排序后，本批记录范围从 `{first_domain}` 到 `{last_domain}`。",
        "",
    ]

    return "\n".join(lines).rstrip()


def build_context_sections(seed: int, count: int) -> str:
    if count <= 0:
        return ""

    rng = random.Random(make_seed(seed, "context"))
    blocks = CONTEXT_BLOCKS.copy()
    rng.shuffle(blocks)
    selected = blocks[: min(count, len(blocks))]

    lines: list[str] = []
    for heading, paragraph in selected:
        lines.extend([f"## {heading}", "", paragraph, ""])

    return "\n".join(lines).rstrip()


def should_use_enriched_content(
    content_mode: str,
    content_ratio: float,
    seed: int,
) -> bool:
    mode = content_mode.strip().lower()

    if mode == "directory":
        return False

    if mode in {"content", "enriched"}:
        return True

    # mixed 模式：使用确定性随机，保证同一天重复运行结果一致。
    ratio = max(0.0, min(1.0, content_ratio))
    bucket = make_seed(seed, "content-mode") % 10000
    return bucket < int(ratio * 10000)


def build_internal_links(
    date_text: str,
    post_number: int,
    posts_per_day: int,
) -> str:
    links = ["## 相关记录", ""]

    if post_number > 1:
        prev_name = f"{date_text}-{post_number - 1:02d}.md"
        links.append(f"- [上一条记录]({prev_name})")

    if post_number < posts_per_day:
        next_name = f"{date_text}-{post_number + 1:02d}.md"
        links.append(f"- [下一条记录]({next_name})")

    links.append("- [返回自动发布目录](../README.md)")
    links.append(
        f"- [查看 {date_text} 当日汇总](../daily-links/{date_text}.md)"
    )

    return "\n".join(links)


def main() -> None:
    config = load_config()

    posts_per_day = int(config["posts_per_day"])
    domains_per_post = int(config["domains_per_post"])
    timezone_name = str(config["timezone"])
    content_mode = str(config.get("content_mode", "mixed"))
    content_ratio = float(config.get("content_ratio", 0.20))
    add_internal_links = bool(config.get("add_internal_links", True))
    context_sections = int(config.get("context_sections", 2))

    if posts_per_day < 1:
        raise ValueError("posts_per_day 必须大于0")

    if domains_per_post < 1:
        raise ValueError("domains_per_post 必须大于0")

    if context_sections < 0:
        raise ValueError("context_sections 不能小于0")

    all_domains = load_domains()

    if len(all_domains) < domains_per_post:
        raise ValueError(
            f"至少需要 {domains_per_post} 个不同域名，"
            f"当前只有 {len(all_domains)} 个。"
        )

    now = datetime.now(ZoneInfo(timezone_name))
    date_text = now.strftime("%Y-%m-%d")

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    post_records: list[dict[str, str]] = []
    readme_entries: list[str] = []

    for post_number in range(1, posts_per_day + 1):
        seed = make_seed(date_text, post_number)

        introduction = INTRODUCTIONS[
            (seed // len(TITLE_BASES)) % len(INTRODUCTIONS)
        ]
        disclaimer = DISCLAIMERS[
            (seed // len(INTRODUCTIONS)) % len(DISCLAIMERS)
        ]
        template_function = TEMPLATES[seed % len(TEMPLATES)]

        selected = select_post_domains(
            all_domains,
            date_text,
            post_number,
            domains_per_post,
        )

        post_code = f"{post_number:02d}"
        post_name = f"{date_text}-{post_code}.md"
        post_path = f"posts/{post_name}"
        output_file = POSTS_DIR / post_name

        display_title = make_display_title(
            date_text,
            post_number,
            seed,
        )

        body = template_function(selected)
        enriched = should_use_enriched_content(
            content_mode,
            content_ratio,
            seed,
        )

        extra_sections: list[str] = []
        if enriched:
            extra_sections.append(build_batch_overview(selected))
            extra_sections.append(
                build_context_sections(seed, context_sections)
            )

        if add_internal_links:
            extra_sections.append(
                build_internal_links(
                    date_text,
                    post_number,
                    posts_per_day,
                )
            )

        extras = "\n\n".join(
            section for section in extra_sections if section
        )

        content = f"""# {display_title}

> {introduction}  
> {disclaimer}

- 发布日期：{date_text}
- 当日编号：{post_code}
- 本批数量：{len(selected)}
- 页面状态：待复核


{extras}

{body}

## 维护说明

- 所列链接仅用于导航、检查和归档。
- 未完成实际检查前，应保留“待核验”状态。
- 不应把无关网站标注为新闻来源或合作网站。
- 网站状态可能随时间发生变化。

## 免责声明

本页面不构成推荐、认证、内容背书或安全保证。
"""

        output_file.write_text(content, encoding="utf-8")

        post_url = build_post_url(post_path)

        post_records.append(
            {
                "title": display_title,
                "path": post_path,
                "url": post_url,
            }
        )

        readme_entries.append(
            f"- [{display_title}]({post_path})"
        )

        mode_text = "增强型" if enriched else "目录型"
        print(f"已生成：{post_path} [{mode_text}]")

    write_link_collections(date_text, post_records)
    update_readme(readme_entries, date_text)

    print(f"本次共生成 {len(post_records)} 篇。")
    print(f"链接汇总：daily-links/{date_text}.txt")
    print("最近链接：latest-links.txt")


if __name__ == "__main__":
    main()
