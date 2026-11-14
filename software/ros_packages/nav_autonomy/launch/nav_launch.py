import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, SetParameter
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition

def generate_launch_description():

    use_sim_time = LaunchConfiguration('nav_use_sim_time', default='false') 

    package_name='nav_autonomy'
    pkg_share = get_package_share_directory(package_name)

    nav2_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')

    
    # Jazzy's stock nav2_bringup/navigation_launch.py also manages collision_monitor,
    # docking_server (and route_server on newer releases). We don't configure those,
    # and if any lifecycle node fails to configure the lifecycle manager aborts
    # bringup for ALL nodes (costmaps never activate -> "No map received" in RViz).
    # So we launch only the servers we actually use.
    lifecycle_nodes = [
        'controller_server',
        'smoother_server',
        'planner_server',
        'behavior_server',
        'velocity_smoother',
        'bt_navigator',
        'waypoint_follower',
    ]

    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    def nav2_node(package, executable, extra_remaps=()):
        return Node(
            package=package,
            executable=executable,
            name=executable,
            output='screen',
            respawn=False,
            parameters=[nav2_params],
            remappings=remappings + list(extra_remaps),
        )

    nav2 = GroupAction([
        SetParameter('use_sim_time', use_sim_time),

        # controller/behaviors -> cmd_vel_nav -> velocity_smoother -> /cmd_vel
        # /cmd_vel is picked up by joy_to_drive / drive_can_control and forwarded
        # to /drive_controller/cmd_vel (no collision_monitor in the chain).
        nav2_node('nav2_controller', 'controller_server', [('cmd_vel', 'cmd_vel_nav')]),
        nav2_node('nav2_smoother', 'smoother_server'),
        nav2_node('nav2_planner', 'planner_server'),
        nav2_node('nav2_behaviors', 'behavior_server', [('cmd_vel', 'cmd_vel_nav')]),
        nav2_node('nav2_bt_navigator', 'bt_navigator'),
        nav2_node('nav2_waypoint_follower', 'waypoint_follower'),
        nav2_node('nav2_velocity_smoother', 'velocity_smoother',
                  [('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', '/cmd_vel')]),

        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[{'autostart': True}, {'node_names': lifecycle_nodes}],
        ),
    ])

    mission_manager = Node(
            package='nav_autonomy',
            executable='mission_manager',
    )

    yolo_server = Node(
            package='nav_autonomy',
            executable='yolo_server',
    )

    return LaunchDescription([
        DeclareLaunchArgument('nav_use_sim_time', default_value='false', description='Use simulation (Gazebo) clock if true'),
        nav2,
        mission_manager,
        yolo_server,
    ])
