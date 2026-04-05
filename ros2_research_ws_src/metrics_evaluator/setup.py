from setuptools import setup

package_name = "metrics_evaluator"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jia",
    maintainer_email="jia@example.com",
    description="Read-only metrics and debug audit nodes for the research layer.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "summary_writer = metrics_evaluator.summary_writer:main",
            "frame_audit = metrics_evaluator.frame_audit_node:main",
            "geometry_consistency = metrics_evaluator.geometry_consistency_node:main",
        ],
    },
)
