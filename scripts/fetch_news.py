import feedparser
import datetime
import os
import requests

# ====================== AITools 全局配置 ======================
# 独立项目根目录，不和原windlisten混用
ROOT_DIR = "aitools"
OUT_DIR = os.path.join(ROOT_DIR, "posts")
os.makedirs(OUT_DIR, exist_ok=True)

# 修复可用RSS源（替换失效少数派链接）
RSS_SOURCES = [
    ("机器之心", "https://www.jiqizhixin.com/feed"),
    ("量子位", "https://www.qbitai.com/feed"),
    ("少数派", "https://client.sspai.com/feed"),
    ("新智元", "https://www.aiyuangroup.com/feed"),
    ("爱范儿", "https://www.ifanr.com/feed"),
]

# 请求头模拟浏览器，解决被拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 文章自动分类关键词池
CATEGORY_MAP = {
    "大模型测评": {
        "GPT", "Claude", "通义千问", "文心一言", "豆包", "Kimi", "DeepSeek",
        "大模型", "LLM", "本地模型", "推理", "对话模型", "Agent"
    },
    "AI绘图工具": {
        "AI绘图", "Midjourney", "Stable Diffusion", "DALL·E", "图生图",
        "绘画", "生图", "海报AI", "插画生成", "AI修图"
    },
    "AI办公工具": {
        "AI写作", "PPT生成", "AI表格", "文档总结", "录音转写",
        "办公AI", "思维导图", "AI剪辑", "字幕生成", "效率工具"
    }
}

# 必须包含以下词汇才判定为测评文章
REVIEW_KEYWORDS = {"测评", "评测", "实测", "横向对比", "深度体验", "横评", "上手体验"}
# 广告、推广软文黑名单，命中直接丢弃
BLACK_WORDS = {"赞助", "广告", "推广", "付费体验", "合作推送", "品牌合作"}

# 时间范围：近24小时（改为本地时间兼容，避免UTC时区误伤）
now_local = datetime.datetime.now()
cutoff_local = now_local - datetime.timedelta(hours=24)

# 去重容器
link_set = set()
# 分类存储容器
article_pool = {
    "大模型测评": [],
    "AI绘图工具": [],
    "AI办公工具": [],
    "其他AI工具测评": []
}
# ==============================================================

# 循环抓取所有RSS源
for source_name, feed_url in RSS_SOURCES:
    print(f"\n===== 正在抓取：{source_name} | {feed_url} =====")
    try:
        # 先用requests带UA获取内容，解决反爬拦截
        resp = requests.get(feed_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        # 打印解析状态，调试用
        if feed.bozo:
            print(f"⚠️ 解析警告：{feed.bozo_exception}")
        print(f"该源总文章数：{len(feed.entries)}")

        for entry in feed.entries:
            try:
                # 兼容两种时间格式，优先published_parsed，失败则跳过时间过滤调试
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    publish_struct = entry.published_parsed[:6]
                    publish_time = datetime.datetime(*publish_struct)
                else:
                    print(f"跳过无发布时间文章：{entry.title}")
                    continue

                # 本地时间过滤，不再强制UTC，避免时差误删
                if publish_time < cutoff_local:
                    continue

                link = entry.link.strip()
                # 去重，重复链接跳过
                if link in link_set:
                    continue
                link_set.add(link)

                title = entry.get("title", "")
                summary = entry.get("summary", "暂无简介")
                full_text = (title + summary).lower()

                # 过滤广告软文
                if any(word in full_text for word in BLACK_WORDS):
                    continue
                # 只保留测评类文章
                if not any(word in full_text for word in REVIEW_KEYWORDS):
                    continue

                # 组装文章基础信息
                article_info = {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": source_name,
                    "time": publish_time.strftime("%Y-%m-%d %H:%M")
                }

                # 自动匹配分类
                matched = False
                for cat_name, kw_set in CATEGORY_MAP.items():
                    if any(kw.lower() in full_text for kw in kw_set):
                        article_pool[cat_name].append(article_info)
                        matched = True
                        break
                # 未匹配三类则归入其他
                if not matched:
                    article_pool["其他AI工具测评"].append(article_info)
                print(f"✅ 匹配测评：{title}")
            except Exception as e:
                print(f"单篇文章解析异常：{e}")
                continue
    except Exception as e:
        print(f"❌ 抓取{source_name}失败：{e}")
        continue

# 统计总文章数量
total_count = sum(len(lst) for lst in article_pool.values())

if total_count > 0:
    date_str = now_local.strftime("%Y-%m-%d")
    filename = f"{date_str}_aitools_digest.md"
    file_path = os.path.join(OUT_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        # Markdown 头部 Frontmatter（适配静态博客）
        header = f"""---
title: {date_str} AI工具测评汇总 | AITools
date: {date_str}
tags: [AI测评,大模型,AI绘图,AI办公,工具实测]
categories: AI工具测评
---
# {date_str} AI工具测评文摘 · AITools
采集时间：{now_local.strftime('%Y-%m-%d %H:%M:%S')}
项目定位：每日全网AI工具实测分类汇总
今日收录总量：{total_count} 篇测评
自动分类：大模型测评 / AI绘图工具 / AI办公工具 / 其他AI工具
---
"""
        f.write(header)

        # 按分类分块写入内容
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

    print(f"\n✅ AITools 采集完成，文件输出：{file_path}")
    print("📊 分类统计：")
    for cat, lst in article_pool.items():
        print(f" - {cat}：{len(lst)} 篇")
else:
    print("\nℹ️ 过去24小时无符合条件的AI工具测评文章")
    print("调试提示：")
    print("1. 看上方每个源的总文章数，如果为0说明RSS链接失效/被拦截")
    print("2. 若有文章但无匹配，说明近期没有带「测评/评测/实测」关键词的AI工具内容")