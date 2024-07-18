from lsy_interfaces.srv import VLService
import hello_helpers.hello_misc as hm
from sound_play.libsoundplay import SoundClient

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
import sys
import math
from enum import Enum

from sensor_msgs.msg import Image
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
from speech_recognition_msgs.msg import SpeechRecognitionCandidates
from std_msgs.msg import Int32

class Prompt(Enum):
    DESCRIBE = 0
    MOVE = 1

class GetVoiceCommands:
    def __init__(self, node):
        self.node = node

        # Initialize the voice command
        self.voice_command = ' '

        # Initialize the sound direction
        self.sound_direction = 0

        # Initialize subscribers
        self.speech_to_text_sub = self.node.create_subscription(SpeechRecognitionCandidates, "/speech_to_text", self.callback_speech, 1)
        self.sound_direction_sub = self.node.create_subscription(Int32, "/sound_direction", self.callback_direction, 1)

    def callback_direction(self, msg):
        #self.sound_direction = msg.data * -self.rad_per_deg
        self.sound_direction = None

    def callback_speech(self,msg):
        self.voice_command = ' '.join(map(str,msg.transcript))
        if self.voice_command != None:
            self.node.get_logger().info(f'Voice Command: {self.voice_command}')


    def get_inc(self):
        inc = {'rad': self.rotate, 'translate': self.translate}
        return inc

    def print_commands(self):
        """
        A function that prints the voice teleoperation menu.
        :param self: The self reference.
        """
        print('                                           ')
        print('------------ VLM TELEOP MENU ------------')
        print('                                           ')
        print('               VOICE COMMANDS              ')
        print(' "stretch describe": DESCRIBE SCENE        ')
        print(' "stretch move [object]": MOVE TO OBJECT   ')
        print('                                           ')
        print('                                           ')
        print(' "quit"   : QUIT AND CLOSE NODE            ')
        print('                                           ')
        print('-------------------------------------------')

    def get_prompt(self):
        type = Prompt.DESCRIBE
        prompt = None
        # Move base forward command
        if 'describe' in self.voice_command:
            type = Prompt.MOVE
            prompt = 'Describe what you see in the image in a short sentence.'

        # Move base back command
        if 'move' in self.voice_command:
            desired_obj = self.voice_command.split(' ')[-1]
            prompt = f'Describe how to move from your current location to the {desired_obj}. Please answer by providing a comma separated array using only a combination of the words in the following list [forward, backward, turn left, turn right].'

        # Rotate base right command
        if self.voice_command == 'right':
            prompt = 'Please say potato'
            #command = {'joint': 'rotate_mobile_base', 'inc': -self.get_inc()['rad']}

        # Move base to sound direction command
        if self.voice_command == 'left':
            prompt = 'Please say potato'
            #command = {'joint': 'translate_mobile_base', 'inc': self.get_inc['translate']}

        if self.voice_command == 'quit':
            # Sends a signal to ros to shutdown the ROS interfaces
            self.node.get_logger().info("done")

            # Exit the Python interpreter
            sys.exit(0)

        # Reset voice command to None
        self.voice_command = ' '

        # return the updated command
        return (type, prompt)
    

class VLClient(Node):
    def __init__(self, node):
        self.node = node

        self.cli = self.node.create_client(VLService, 'vision_language_client')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            print('service not available, waiting again')
            #self.get_logger().info('service not available, waiting again...')
        self.req = VLService.Request()

        self.image_sub = self.node.create_subscription(Image, 'camera/color/image_raw', self.image_callback, 1)
        self.image = None
        self.prompt = None
        self.result = None

    def image_callback(self, msg):
        self.image = msg.data

    def send_request(self, prompt):
        self.req.image = self.image
        self.req.prompt = prompt
        return self.cli.call_async(self.req)
    
    def read_message(self):
        self.get_logger().info(self.result)


class VLMTeleop(hm.HelloNode):

    def __init__(self):
        hm.HelloNode.__init__(self)
        hm.HelloNode.main(self, 'vlm_teleop', 'vlm_teleop', wait_for_first_pointcloud=False)

        self.rate = 10.0
        self.joint_state = None
        self.sleeper = self.create_timer(3, self._dummy)

        self.rad_per_deg = math.pi/180.0
        self.rotate = 90 * self.rad_per_deg # radians
        self.translate = 0.05 # meters

        self.speech = GetVoiceCommands(self)
        self.VLM = VLClient(self)
        self.speaker = SoundClient(self, blocking=False)
        self.voice = 'voice_kal_diphone'
        self.volume = 2.0

        self.last_prompt = None

    def _dummy(self):
        pass

    def joint_states_callback(self, msg):
        self.joint_state = msg

    def timer_get_prompt(self):
        # Get voice command
        type, prompt = self.speech.get_prompt()

        if prompt != None:
            self.get_logger().info(f'Prompt: {prompt}')
            self.speaker.say('Hi, my name is stretch')
        # Send voice command for joint trajectory goals
        self.last_prompt = prompt
        self.process_prompt(type, prompt)

    def process_prompt(self, type, prompt):
        if prompt is None:
            return

        future = self.VLM.send_request(prompt)
        rclpy.spin_until_future_complete(self.VLM, future)
        result = future.result()
        
        joint_state = self.joint_state

        if type == Prompt.DESCRIBE:
            pass
        elif type == Prompt.MOVE and joint_state is not None:
            for command in result:
                # Assign point as a JointTrajectoryPoint message type
                point = JointTrajectoryPoint()
                point.time_from_start = Duration(seconds=0).to_msg()

                # Assign trajectory_goal as a FollowJointTrajectoryGoal message type
                trajectory_goal = FollowJointTrajectory.Goal()
                trajectory_goal.goal_time_tolerance = Duration(seconds=0).to_msg()

                # Extract the joint name from the command dictionary
                if command == 'forward':
                    joint_name = 'translate_mobile_base'
                    inc = self.translate
                elif command == 'backward':
                    joint_name = 'translate_mobile_base'
                    inc = -self.translate
                elif command == 'turn left':
                    joint_name = 'rotate_mobile_base'
                    inc = self.rotate
                elif command == 'turn right':
                    joint_name = 'rotate_mobile_base'
                    inc = -self.rotate

                trajectory_goal.trajectory.joint_names = [joint_name]
                new_value = inc

                # Assign the new_value position to the trajectory goal message type
                point.positions = [new_value]
                trajectory_goal.trajectory.points = [point]
                trajectory_goal.trajectory.header.stamp = self.get_clock().now().to_msg()
                self.get_logger().info('joint_name = {0}, trajectory_goal = {1}'.format(joint_name, trajectory_goal))

                # Make the action call and send goal of the new joint position
                self.trajectory_client.send_goal(trajectory_goal)
                self.get_logger().info('Done sending command.')
                self.sleeper.sleep()
            self.get_logger().info('Finished Moving to Desired Object')
            ### Ask if at object
            ### Yes, good
            ### No, rerun prompt

    def main(self):
        self.create_subscription(JointState, '/stretch/joint_states', self.joint_states_callback, 1)
        rate = self.create_rate(self.rate)   
        #self.speech.peint_commands() 
        self.sleep = self.create_timer(1/self.rate, self.timer_get_prompt)        

def main(args=None):
    try:
        #rclpy.init()
        node = VLMTeleop()
        node.main()
        node.new_thread.join()
    except:
        node.get_logger().info('Error. Shutting Down Node...')
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()