from glob import glob
from setuptools import setup

package_name = "ai_robot_sim"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/ai_robot_sim"]),
        ("share/ai_robot_sim", ["package.xml"]),
        (
            "share/ai_robot_sim/config",
            [
                "../../config/sim_base.yaml",
                "../../config/ekf_sim.yaml",
                "../../config/amcl_sim.yaml",
                "../../config/s1_m4_dependency_status.yaml",
                "../../config/slam_sim.yaml",
                "../../config/sim_sensor_diagnostics.yaml",
                "../../config/sim_sensors.yaml",
            ],
        ),
        ("share/ai_robot_sim/worlds", glob("worlds/*.world")),
        ("share/ai_robot_sim/maps", glob("maps/*")),
        ("share/ai_robot_sim/launch", glob("launch/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="lxq-12345",
    maintainer_email="167375205+lxq-12345@users.noreply.github.com",
    description="S1-M2 Gazebo Classic simulation and command guard.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "capability_task_manager = ai_robot_sim.capability_task_manager:main",
            "camera_image_monitor = ai_robot_sim.camera_image_monitor:main",
            "cmd_vel_guard = ai_robot_sim.cmd_vel_guard:main",
            "manual_motion_demo = ai_robot_sim.manual_motion_demo:main",
            "scan_obstacle_monitor = ai_robot_sim.scan_obstacle_monitor:main",
        ],
    },
)
