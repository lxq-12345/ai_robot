from setuptools import setup

package_name = "ai_robot_py_example"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/ai_robot_py_example"]),
        ("share/ai_robot_py_example", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="lxq-12345",
    maintainer_email="167375205+lxq-12345@users.noreply.github.com",
    description="S1-1-M1 minimal Python ROS 2 node example.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "baseline_node = ai_robot_py_example.baseline_node:main",
        ],
    },
)
