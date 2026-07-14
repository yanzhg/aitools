import feedparser
import datetime
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ====================== AITools 全局配置 ======================
# 输出文件夹
OUT_DIR = "docs/posts"
os.makedirs(OUT_DIR, exist_ok=True)

# 稳定可用RSS源，移除所有失效链接
RSS_SOURCES = [
    ("量子位", "https://www.qbitai.com/feed"),
    ("爱范儿", "https://www.ifanr.com/feed"),
]

# 请求头模拟浏览器，解决反爬拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8"
}

# 请求重试配置：失败自动重试3次，超时8秒
retry_strategy = Retry(
    total=3,
    backoff_factor=0.8,
    status_forcelist=[403, 429, 500, 502, 503, 504]
)
session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
session.mount("http://", HTTPAdapter(max_retries=retry_strategy))

# AI分类关键词池
CATEGORY_MAP = {
    "大模型测评": {
        "GPT", "Claude", "通义千问", "文心一言", "豆包", "Kimi", "DeepSeek",
        "大模型", "LLM", "本地模型", "推理", "对话模型", "Agent"
    },
    "AI绘图工具": {
        "AI绘图", "Midjourney", "Stable Diffusion", "DALL·E", "图生图", "文生图",
        "绘画", "生图", "海报AI", "插画生成", "AI修图", "Flux", "即梦", "可灵"
    },
    "AI办公工具": {
        "AI写作", "PPT生成", "AI表格", "文档总结", "录音转写", "飞书AI", "WPS AI",
        "办公AI", "思维导图", "AI剪辑", "字幕生成", "效率工具", "智谱清言办公"
    }
}

# 测评必备关键词
REVIEW_KEYWORDS = {"测评", "评测", "实测", "横向对比", "深度体验", "横评", "上手体验", "体验", "对比", "实测报告", "深度实测", "工具对比"}
# 广告软文黑名单
BLACK_WORDS = {"赞助", "广告", "推广", "付费体验", "合作推送", "品牌合作"}
# 低价值资讯过滤（精简，减少误杀测评）
NO_REVIEW_WORDS = {"融资", "IPO", "世界人工智能大会", "造车"}

# 抓取时间范围：近48小时
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(hours=48)

link_set = set()
article_pool = {
    "大模型测评": [],
    "AI绘图工具": [],
    "AI办公工具": [],
    "其他AI工具测评": []
}
# ==============================================================

# 循环抓取RSS
for source_name, feed_url in RSS_SOURCES:
    print(f"\n===== 正在抓取：{source_name} | {feed_url} =====")
    try:
        # 使用带重试、UA的session请求
        resp = session.get(feed_url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        if feed.bozo:
            print(f"⚠️ RSS解析警告：{feed.bozo_exception}")
        print(f"该源原始文章总数：{len(feed.entries)}")

        for entry in feed.entries:
            try:
                if not hasattr(entry, "published_parsed") or not entry.published_parsed:
                    print(f"跳过无发布时间条目：{entry.title}")
                    continue
                publish_struct = entry.published_parsed[:6]
                publish_time = datetime.datetime(*publish_struct, tzinfo=datetime.timezone.utc)
                if publish_time < cutoff:
                    continue

                link = entry.link.strip()
                if link in link_set:
                    continue
                link_set.add(link)

                title = entry.get("title", "")
                summary = entry.get("summary", "暂无简介")
                full_text = (title + summary).lower()

                # 过滤广告
                if any(word in full_text for word in BLACK_WORDS):
                    continue
                # 过滤纯行业资讯
                if any(word in full_text for word in NO_REVIEW_WORDS):
                    continue
                # 只保留测评类文章
                if not any(word in full_text for word in REVIEW_KEYWORDS):
                    continue

                article_info = {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": source_name,
                    "time": publish_time.strftime("%Y-%m-%d %H:%M")
                }

                # 自动分类
                matched = False
                for cat_name, kw_set in CATEGORY_MAP.items():
                    if any(kw.lower() in full_text for kw in kw_set):
                        article_pool[cat_name].append(article_info)
                        matched = True
                        break
                if not matched:
                    article_pool["其他AI工具测评"].append(article_info)
                print(f"✅ 成功收录测评：{title}")
            except Exception as e:
                print(f"单篇文章解析异常：{str(e)}")
                continue
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求{source_name}失败：{str(e)}")
        continue
    except Exception as e:
        print(f"❌ 处理{source_name}未知错误：{str(e)}")
        continue

total_count = sum(len(lst) for lst in article_pool.values())

if total_count > 0:
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{date_str}_aitools_digest.md"
    file_path = os.path.join(OUT_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        header = f"""---
title: {date_str} AI工具测评汇总 | AITools
date: {date_str}
tags: [AI测评,大模型,AI绘图,AI办公,工具实测]
categories: AI工具测评
---
# {date_str} AI工具测评文摘 · AITools
采集时间：{now.strftime('%Y-%m-%d %H:%M:%S')}
项目定位：全网AI工具实测、横向对比专属汇总
抓取范围：近48小时AI测评内容
今日收录总量：{total_count} 篇测评
自动分类：大模型测评 / AI绘图工具 / AI办公工具 / 其他AI工具测评
---
"""
        f.write(header)

        # 分区块写入各分类
        for category, article_list in article_pool.items():
            if not article_list:
                continue
            f.write(f"\n## 📌 {category}（共{len(article_list)}篇）\n\n")
            for item in article_list:
                block = f"""### {item['title']}
- 媒体来源：{item['source']}
- 发布时间：{item['time']}
- 原文链接：[{item['link']}]({item['link']})
{item['summary']}
---
"""
                f.write(block)

    print(f"\n✅ AITools 采集完成，输出文件：{file_path}")
    print("📊 分类统计结果：")
    for cat, lst in article_pool.items():
        print(f" - {cat}：{len(lst)} 篇")
else:
    print("\nℹ️ 近48小时无符合筛选条件的AI工具测评文章")
    print("调试提示：")
    print("1. 收录过少可扩充 REVIEW_KEYWORDS 测评关键词")
    print("2. 资讯过滤严格可删减 NO_REVIEW_WORDS 内词汇")