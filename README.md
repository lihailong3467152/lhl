<div align="center">

# 🚀 Python 综合全栈开发与 AI 转型实践库
**Python Integrated Development Hub**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-05998b?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-Supported-ffee00?logo=chainlink)](https://github.com/langchain-ai/langchain)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-ff4b4b?logo=streamlit)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-important)](LICENSE)

一个集成了 **AI 知识库**、**自动化爬虫**、**企业级后端服务**与**趣味娱乐应用**的综合性 Python 项目仓库。

[快速开始](#🚀-快速开始) · [核心模块](#🌟-核心功能模块) · [技术栈](#🛠-技术栈) · [项目结构](#📁-项目结构)

</div>

---

## 📋 目录
- [🎯 项目简介](#🎯-项目简介)
- [🌟 核心功能模块](#🌟-核心功能模块)
  - [1. AI & 知识库系统 (RAG)](#1-ai--知识库系统)
  - [2. 自动化爬虫系列](#2-自动化爬虫系列)
  - [3. 后端与系统开发](#3-后端与系统开发)
  - [4. 娱乐应用开发](#4-娱乐应用开发)
- [🛠 技术栈](#🛠-技术栈)
- [📁 项目结构](#📁-项目结构)
- [🚀 快速开始](#🚀-快速开始)
- [🤝 贡献指南](#🤝-贡献指南)

---

## <a id="🎯-项目简介"></a>🎯 项目简介
本项目是作者从 **大数据架构** 向 **前沿 AI 应用** 转型过程中的全流程工程实践。它不仅是一个代码仓库，更是一套成熟的 Python 技术链路展示。

### ✨ 项目特色
- **全链路覆盖**：从原始数据爬取、结构化处理到 AI 语义检索。
- **实战导向**：模块均源于政府消费监测、绩效评估等真实业务逻辑。
- **模块化设计**：各组件高度解耦，支持独立部署与复用。
- **持续进化**：紧跟 GLM/DeepSeek 等国产大模型生态及 FastAPI 异步架构。

---

## <a id="🌟-核心功能模块"></a>🌟 核心功能模块

### <a id="1-ai--知识库系统"></a>1. 🧠 AI & 知识库系统
基于 **RAG (Retrieval-Augmented Generation)** 技术的企业级私有文档问答方案。
#### 🛠 技术架构
```
    A[PDF/TXT文档] --> B(LangChain 分割)
    B --> C(M3E 嵌入向量化)
    C --> D[ChromaDB 向量存储]
    D --> E{语义检索}
    E --> F[智谱AI GLM 生成答案]
组件技术选型说明向量数据库ChromaDB高性能本地存储，支持持久化索引嵌入模型moka-ai/m3e-base中文优化的 SOTA 文本向量化模型LLM 服务  
智谱AI (GLM)国产领先大模型，支持长文本理解文本分割LangChain递归字符分割，保留段落语义
```
### <a id="2-自动化爬虫系列"></a>2. 🕷️ 自动化爬虫系列
一套应对复杂网络环境的数据采集引擎，专注于稳定性与自动化。  
网页文章爬取：智能过滤导航栏/页脚，自动处理相对路径。  
PDF 批量工具：PDF网站下载专用：针对特定站点优化的下载逻辑。  
智能重命名：根据 PDF 内部正文内容自动命名文件。  
政务消费监测：针对统计局、商务局等公开数据的专项采集。  
### <a id="3-后端与系统开发"></a>3. ⚡ 后端与系统开发
3.1 FastAPI 高性能服务位于 fapi.py，采用异步 (async/await) 架构。预留 Pydantic 数据模型，支持严格的 API 契约验证。  
3.2 绩效评估管理平台基于 Streamlit 构建的轻量级企业系统：双端闭环：管理端控制项目进度，第三方端提交评估材料。自动化评分：内置 32 项财政预决算公开评估指标，实现“上传即出分”。
### <a id="4-娱乐应用开发"></a>4. 🎮 娱乐应用开发
包含多个经典的交互式应用，展示 Python 在游戏开发领域的趣味性：  
🛸 飞机大战：支持多种敌机类型、Boss 战及道具系统。  
♟️ 五子棋/连连看：基于 HTML5 Canvas 与 Python 交互的轻量级小游戏。
## <a id="🛠-技术栈"></a>🛠 技术栈

| 分类         | 关键技术                                                                 |
| :----------- | :----------------------------------------------------------------------- |
| **核心语言** | Python 3.10+                                                             |
| **AI/ML**    | LangChain, ChromaDB, Sentence Transformers, ZhipuAI SDK                   |
| **Web 框架** | FastAPI, Streamlit, Uvicorn                                               |
| **数据清洗** | Pandas, NumPy, OpenPyXL, pdfplumber                                      |
| **爬虫技术** | Requests, BeautifulSoup, Selenium                                        |
| **游戏开发** | Pygame, HTML5 Canvas                                                      |
## <a id="📁-项目结构"></a>📁 项目结构
```text
vscode-repository/
├── AI/                     # AI 核心逻辑 (RAG 系统)
├── 爬取PDF/                 # PDF 批量采集与重命名脚本
├── 消费数据爬取/             # 政务公开数据专项采集
├── 第三方评估系统/           # Streamlit 评估平台 (管理端/机构端)
├── 自动评估系统系统/         # 财政公开度智能评分引擎
├── 娱乐/                    # 飞机大战、星际猎手等游戏
├── fapi.py                 # FastAPI 服务主入口
├── requirements.txt        # 环境依赖清单
└── README.md               # 项目主说明文档
```
## <a id="🚀-快速开始"></a>🚀 快速开始
 获取代码Bashgit clone [https://github.com/lihailong3467152/lhl.git](https://github.com/lihailong3467152/lhl.git)  
 环境配置Bash
 安装依赖  
pip install -r requirements.txt

# 配置 API Key (RAG 模式必选)
set GLM_API_KEY=your_api_key_here
 运行项目Bash
# 启动 API 服务
uvicorn main:app --reload

# 启动评估管理平台
streamlit run 第三方评估系统/app.py
## <a id="🤝-贡献指南"></a>🤝 贡献指南
我们非常欢迎任何形式的贡献！Fork 本仓库。   
创建你的特性分支 (git checkout -b feature/AmazingFeature)。  
提交你的更改 (git commit -m 'Add some AmazingFeature')。  
推送到分支 (git push origin feature/AmazingFeature)。  
开启一个 Pull Request。📄 许可证本项目基于 MIT License 许可协议。
<div align="center">
⭐ 如果这个项目对你有帮助，请给一个 Star 以示鼓励 ⭐<br>
Made with ❤️ by lihailong3467152
</div>
