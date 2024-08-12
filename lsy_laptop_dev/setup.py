from setuptools import find_packages, setup

package_name = 'lsy_laptop_dev'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orrin',
    maintainer_email='orrin.dahanaggamaarachchi@mail.utoronto.com',
    description='Learning systems Lab Stretch Laptop Development',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vision_language_server = lsy_laptop_dev.vision_language_server_copy:main',
            #'stretch_speech_client = lsy_laptop_dev.vlm_teleop_openai_tts_LAPTOP_PORT:main'
			'talker = lsy_laptop_dev.vlm_teleop_openai_tts_LAPTOP_PORT:main',
            'odom_listener = lsy_laptop_dev.odom_subscriber:main',
            'ok_robot_node = lsy_laptop_dev.ok_robot_node:main'
        ],
    },
)