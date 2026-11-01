# 温室静态资源（设计v1.4）

World：`../worlds/greenhouse_env.world`。生成：项目根执行`python3 scripts/generate_greenhouse_env.py`。观察：`bash scripts/view_greenhouse_env.sh`。

60个种植单元，58个轨道单元。内部63×44.15 m，两段30 m，中间通道3 m；所有布局由生成器统一定义。局部轨道+X端朝通道，连接短管中心x=15.230 m；外端管面x=-15 m，保持在基座范围内。第二段旋转π。墙体高2 m、厚0.115 m，入口x=30..33 m。

土壤为中深棕、干燥哑光；种植面深棕；通道/基座为中浅灰哑光混凝土；番茄行中深绿并有少量红果；轨道为工业黄半哑光涂漆。纹理由固定种子程序生成，完全本地资源，不依赖下载。纹理仅表示视觉粗糙度，不改变碰撞表面。

轨道采用闭合管网格：每90°圆弧32段、截面32段，圆弧中心线与直线相切，共用连接顶点，视觉/碰撞共用网格。曲线方向弦误差<0.019 mm，截面<0.121 mm；不把三角网格称为数学光滑面。管半径0.025 m、弯曲中心线半径0.060 m。

入轨要求：内轮经过U端头平顺进入直轨，不沿U形端头转弯。实际轮型、速度、角度和位置偏差条件待机器人模型确定，届时验证卡滞、跳动、穿透及脱轨。本资源自测不包含轮轨动态验收。摩擦mu=mu2=0.8为待标定候选值，不代表黄色漆钢管实测参数。

安装：`ai_robot_sim/setup.py`保留模型子目录。安装World加载时须将`share/ai_robot_sim/models`加入GAZEBO_MODEL_PATH；源码观察入口自动设置源码模型路径，使用独立Gazebo端口11365，无机器人或运动插件。

开发自测：`src/ai_robot_sim/test/test_greenhouse_env.py`与`scripts/test_greenhouse_env_runtime.py`。用户验收：`tests/scenario/greenhouse_env_验收说明.md`。证据：`tests/evidence/greenhouse_env/`。设计原文在本地`docs/温室环境建模_v1.4.md`，按用户既有要求不上传docs。

Gazebo显示坐标：X_world=X_design−31.5、Y_world=Y_design−22.075，温室中心对齐栅格原点；设计尺寸和局部坐标不变。默认相机(0,0,85)，垂直俯视。
