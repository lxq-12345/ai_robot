# 跨包集成测试

本目录保存多程序包、ROS图、第三方组件组合和仿真子系统测试。文件按`test_s1_m<编号>_<能力>.launch.py`命名，由`launch_test`执行，并由`scripts/test.sh`统一编排。

集成测试可以依赖`tests/helpers/`，但不得从包源码目录直接导入未安装模块。需要完整整机任务或Gate条件的测试应放入`tests/system/`。
