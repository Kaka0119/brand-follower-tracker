# 💎 珠宝品牌社交平台粉丝数追踪器

自动采集 15 个珠宝品牌的 **TikTok / Instagram / Facebook** 实时粉丝数。

## 品牌列表

| 等级 | 品牌 |
|:---|:---|
| 🏆 传统奢侈品牌 | Tiffany & Co., Cartier, Bulgari, Van Cleef & Arpels |
| 💎 轻奢珠宝 | David Yurman, Monica Vinader, Pandora, Kendra Scott |
| 🆕 DTC 原生品牌 | Mejuri, Stone and Strand, Ana Luisa, Catbird, Jeulia |
| 🌏 新锐/中国品牌 | Mindjewel, HEFANG |

## 数据采集

| 平台 | 方式 | 频率 |
|:---|:---|:---|
| TikTok | StealthyFetcher 实时爬取 | 每次运行 |
| Instagram | StealthyFetcher 实时爬取 | 每次运行 |
| Facebook | StealthyFetcher 实时爬取 | 每次运行 |

## 文件结构

```
├── .github/workflows/scrape-followers.yml  # GitHub Action 配置
├── scrape_all.py                            # 采集脚本
├── data/
│   ├── brand_followers.json                 # 最新数据
│   └── history/                            # 历史存档
│       └── brand_followers_YYYYMMDD_HHMMSS.json
└── README.md
```

## 使用方式

1. 把此仓库 push 到 GitHub
2. 进入仓库 → Actions → 手动触发 `🏷️ 珠宝品牌社交平台粉丝数采集`
3. 或者设置每周一早8点自动运行
4. 采集结果自动提交到 `data/` 目录
