# ROS 2仿真机器人课程

版本：v1.0

## 1. 课程定位

本目录保存《ROS2仿真机器人学习计划》对应的正式教材。课程基于项目已经完成的`S1-1-M0`至`S1-1-M6`工程成果，按PU1至PU9组织，不改变`S1-1-G1`验收要求。

## 2. 目录

```text
ROS2仿真机器人/
├── README.md
├── source/       # Markdown教材源稿
│   └── PU*/
├── assets/       # 图片与其他阅读资源
│   └── PU*/
├── html/         # 由Markdown生成的HTML阅读版
│   └── PU*/
└── bks/          # 被替代的历史教材与规则
```

Markdown源稿是教材内容基准。HTML用于学员阅读，应由同名、同版本Markdown生成；图片通过相对路径同时供两种格式使用。

## 3. PU1教材

PU1“项目总体架构与工程资源”由五个章节组成：

| 章节 | Markdown源稿 | HTML阅读版 | 状态 |
|---|---|---|---|
| PU1-01 项目总体架构 | `source/PU1/PU1-01_项目总体架构_v1.1.md` | `html/PU1/PU1-01_项目总体架构_v1.1.html` | 已建立 |
| PU1-02 工作空间与目录 | `source/PU1/PU1-02_工作空间与目录_v1.0.md` | `html/PU1/PU1-02_工作空间与目录_v1.0.html` | 待编写 |
| PU1-03 程序包与工程资源 | `source/PU1/PU1-03_程序包与工程资源_v1.0.md` | `html/PU1/PU1-03_程序包与工程资源_v1.0.html` | 待编写 |
| PU1-04 对象与链路概览 | `source/PU1/PU1-04_对象与链路概览_v1.0.md` | `html/PU1/PU1-04_对象与链路概览_v1.0.html` | 待编写 |
| PU1-05 实体迁移概览 | `source/PU1/PU1-05_实体迁移概览_v1.0.md` | `html/PU1/PU1-05_实体迁移概览_v1.0.html` | 待编写 |

原合集`PU1_项目总体架构与工程资源_v1.0.md`已归档到`bks/PU1/`，不再作为当前有效教材。

PU1-05负责建立实体迁移的总体认识；PU3至PU9分别结合模型、底盘、传感器、建图、定位、导航和接口复用主题深化，二者不互相替代。

## 4. 阅读与生成

学员优先打开`html/`中的阅读版。维护教材时编辑`source/`中的Markdown，然后使用：

```bash
/usr/bin/python3 scripts/render_learning_html.py \
  learning/ROS2仿真机器人/source/PU1/PU1-01_项目总体架构_v1.1.md \
  learning/ROS2仿真机器人/html/PU1/PU1-01_项目总体架构_v1.1.html
```

生成后必须检查链接、图片、目录、桌面与移动排版，并确认HTML与Markdown版本一致。
