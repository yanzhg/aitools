import feedparser
import datetime
import os

# ====================== AITools 全局配置 ======================
# 独立项目根目录，不和原windlisten混用
ROOT_DIR = "aitools"
OUT_DIR = os.path.join(ROOT_DIR, "posts")
os.makedirs(OUT_DIR, exist_ok=True)

# 仅保留垂直AI媒体RSS，无通用科技新闻源
RSS_SOURCES = [
    ("机器之心", "https://www.jiqizhixin.com/feed"),
    ("量子位", "https://www.qbitai.com/feed"),
    ("少数派", "https://sspai.com/feed"),
    ("新智元", "https://www.aiyuangroup.com/feed"),
    ("爱范儿", "https://www.ifanr.com/feed"),
]

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

# 时间范围：近24小时
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(hours=24)

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
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            try:
                # 解析发布时间
                publish_struct = entry.published_parsed[:6]
                publish_time = datetime.datetime(*publish_struct, tzinfo=datetime.timezone.utc)
                # 过滤24小时外旧闻
                if publish_time < cutoff:
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
            except Exception:
                continue
    except Exception:
        continue

# 统计总文章数量
total_count = sum(len(lst) for lst in article_pool.values())

if total_count > 0:
    date_str = now.strftime("%Y-%m-%d")
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
采集时间：{now.strftime('%Y-%m-%d %H:%M:%S')}
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

    print(f"✅ AITools 采集完成，文件输出：{file_path}")
    print("📊 分类统计：")
    for cat, lst in article_pool.items():
        print(f" - {cat}：{len(lst)} 篇")
else:
    print("ℹ️ 过去24小时无符合条件的AI工具测评文章")