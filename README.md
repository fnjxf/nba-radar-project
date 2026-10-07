# 🏀 NBA 季后赛球员雷达图对比

一个基于 Streamlit + Pyecharts 的交互式 NBA 球员数据可视化工具，支持多赛季切换、10 维能力雷达图、球队主色渲染、冠军荣誉展示，以及深色/浅色主题切换。

**🔗 在线体验**：[点击访问](https://nba-playoffs-radar.streamlit.app/)

## ✨ 功能特性

- **10 维雷达图**：得分、篮板、助攻、抢断、盖帽、三分、命中率、罚球、失误、上场时间
- **多赛季支持**：一键切换 2022-23 / 2023-24 赛季季后赛数据
- **球队主色**：每位球员的雷达图线条使用其所在球队主色
- **冠军荣誉**：右侧展示球员总冠军星星（⭐ 总冠军 / 🌟 FMVP）
- **深色/浅色主题**：侧边栏一键切换
- **智能排序**：球员列表支持原始数据排序和按姓名排序
- **状态保持**：切换主题、排序、赛季时，已生成的雷达图不丢失
- **移动端适配**：手机浏览器访问自动调整布局


## 🚀 使用说明

无需安装任何软件，直接打开在线链接即可：

1. 点击左上角 **`>`** 打开侧边栏
2. 选择赛季（2022-23 / 2023-24）
3. 可打开「🔤 按姓名排序」方便查找
4. 从下拉框选择 2-3 名球员（最多 3 人，超过会导致图形密集）
5. 点击「生成雷达图」
6. 左侧查看雷达图，右侧查看球员照片和冠军荣誉

## 📁 项目结构

```
nba_radar_project/
├── app.py                              # Streamlit 主程序
├── charts/
│   └── radar_chart.py                  # 雷达图生成逻辑
├── utils/
│   └── data_fetcher.py                 # 从 CSV 读取球员数据
├── data/
│   ├── player_stats_playoffs_2022-23.csv
│   └── player_stats_playoffs_2023-24.csv
├── photos/
│   ├── 2022-23/                        # 2022-23 赛季球员定妆照
│   └── 2023-24/                        # 2023-24 赛季球员定妆照
├── tools/
│   └── fetch_data_api.py               # 从第三方 API 拉取数据生成 CSV
├── requirements.txt
└── README.md
```

## 🛠️ 本地运行

### 环境要求

- Python 3.10+
- pip

### 安装步骤

1. 克隆仓库
   ```bash
   git clone https://github.com/fnjxf/nba-radar-project.git
   cd nba-radar-project
   ```

2. 创建虚拟环境
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. 启动应用
   ```bash
   python -m streamlit run app.py
   ```

5. 浏览器自动打开 `http://localhost:8501`

## 📊 数据来源

- **球员统计数据**：通过 [nbaapi.com](https://api.server.nbaapi.com/) 获取，数据交叉验证自 Basketball-Reference 和 NBA.com
- **冠军数据**：手动补充（含 FMVP 标记）

## ⚠️ 注意事项

- 雷达图最多同时对比 3 名球员，超过会导致图形过于密集

## 📝 更新日志

### v0.1.0（2026.10.06）
- 初始版本
- 支持 2022-23 / 2023-24 赛季季后赛数据
- 深色/浅色主题切换
- 移动端适配

### v0.1.1（2026.10.07）
- 深色主题优化
- 主页更新，现在在不生成雷达图的情况下会自动生成本赛季季后赛出战的球员列表
- 球员搜索现在支持按球队分类
- 支持部分球员图片
- 雷达图现在只会按顺序出现红、蓝、绿三种颜色，不再依据球队颜色

## 🤝 如果你想协助更新（为 ❤️ 发 ⚡）……？

发现 Bug，或者有好点子？欢迎通过以下方式联系：

- **B站主页**：[点击进入](https://space.bilibili.com/390941856)
- **GitHub Issues**：[提交 Issue](https://github.com/fnjxf/nba-radar-project/issues)

如果你也想为这个项目添加你的创意，欢迎私信！

## 📄 License

MIT License

## 🙏 致谢

- 数据来源：[nbaapi.com](https://api.server.nbaapi.com/)，[项目链接](https://github.com/nprasad2077/nbaStats)
- 数据验证：[Basketball-Reference](https://www.basketball-reference.com/)、[NBA.com](https://www.nba.com/stats)
- 灵感来源：NBA 官方数据可视化 & 我的个人创意（灵感来自B站的CS2赛事数据雷达图）
- 部署平台：[Streamlit Community Cloud](https://share.streamlit.io/)