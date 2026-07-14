import feedparser
import datetime
import os

# ====================== AITools 全局配置 ======================
# 项目根目录
ROOT_DIR = "aitools"
# 修改输出路径：aitools/docs/posts
OUT_DIR = os.path.join(ROOT_DIR, "docs", "posts")
os.makedirs(OUT_DIR, exist_ok=True)

# 清理失效RSS，保留稳定可用源 + 新增AI工具垂直RSS
RSS_SOURCES = [
    ("量子位", "https://www.qbitai.com/feed"),
    ("爱范儿", "https://www.ifanr.com/feed"),
    ("AI工具集", "https://www.aihuiju.com/feed"),
    ("站酷AI频道", "https://www.zcool.com.cn/rss/ai"),
]

# AI内容自动分类关键词池（扩充绘图/办公关键词）
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

# 测评判定关键词（必须命中才收录）
REVIEW_KEYWORDS = {"测评", "评测", "实测", "横向对比", "深度体验", "横评", "上手体验", "体验", "对比", "实测报告", "深度实测", "工具对比"}
# 广告推广黑名单
BLACK_WORDS = {"赞助", "广告", "推广", "付费体验", "合作推送", "品牌合作"}
# 无关资讯过滤：展会/融资/汽车/手机等无测评价值内容
NO_REVIEW_WORDS = {"融资", "IPO", "WAIC", "世界人工智能大会", "汽车", "iPhone", "手机", "芯片", "上市", "预售", "英伟达发布会", "造车"}

# 抓取时间窗口：近48小时，扩大素材范围
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(hours=48)

# 去重集合
link_set = set()
# 分类存储容器
article_pool = {
    "大模型测评": [],
    "AI绘图工具": [],
    "AI办公工具": [],
    "其他AI工具测评": []
}
# ==============================================================

# 遍历所有RSS源抓取
for source_name, feed_url in RSS_SOURCES:
    print(f"\n===== 正在抓取：{source_name} | {feed_url} =====")
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            print(f"⚠️ 解析警告：{feed.bozo_exception}")
        print(f"该源总文章数：{len(feed.entries)}")

        for entry in feed.entries:
            try:
                # 跳过无发布时间的文章
                if not entry.get("published_parsed"):
                    print(f"跳过无发布时间文章：{entry.title}")
                    continue
                publish_struct = entry.published_parsed[:6]
                publish_time = datetime.datetime(*publish_struct, tzinfo=datetime.timezone.utc)
                # 过滤48小时外旧内容
                if publish_time < cutoff:
                    continue

                link = entry.link.strip()
                # 去重
                if link in link_set:
                    continue
                link_set.add(link)

                title = entry.get("title", "")
                summary = entry.get("summary", "暂无简介")
                full_text = (title + summary).lower()

                # 过滤广告软文
                if any(word in full_text for word in BLACK_WORDS):
                    continue
                # 过滤融资/展会/数码无关资讯
                if any(word in full_text for word in NO_REVIEW_WORDS):
                    continue
                # 仅保留带测评属性文章
                if not any(word in full_text for word in REVIEW_KEYWORDS):
                    continue

                # 组装文章信息
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
                if not matched:
                    article_pool["其他AI工具测评"].append(article_info)
                print(f"✅ 匹配测评文章：{title}")
            except Exception as e:
                print(f"单篇解析异常：{e}")
                continue
    except Exception as e:
        print(f"❌ 抓取{source_name}失败：{e}")
        continue

# 统计总收录文章
total_count = sum(len(lst) for lst in article_pool.values())

if total_count > 0:
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{date_str}_aitools_digest.md"
    file_path = os.path.join(OUT_DIR, filename)

    # 写入Markdown文件，适配静态博客Frontmatter
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

        # 按分类分块输出内容
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

    print(f"\n✅ AITools 采集完成，文件输出路径：{file_path}")
    print("📊 分类统计：")
    for cat, lst in article_pool.items():
        print(f" - {cat}：{len(lst)} 篇")
else:
    print("\nℹ️ 近48小时无符合条件的AI工具测评文章")
    print("调试提示：")
    print("1. 查看上方各源文章总数，0代表RSS链接失效/访问受限")
    print("2. 匹配过少可删减NO_REVIEW_WORDS无关过滤词或扩充REVIEW_KEYWORDS")