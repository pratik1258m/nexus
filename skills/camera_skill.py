from core.skill import Skill
import cv2
import os
import time


class CameraSkill(Skill):

    @property
    def name(self):
        return 'camera_skill'

    def get_tools(self):
        return [{'type': 'function', 'function': {'name': 'take_photo',
            'description': 'Take a photo using the webcam.', 'parameters':
            {'type': 'object', 'properties': {}, 'required': []}}}]

    def get_functions(self):
        return {'take_photo': self.take_photo}

    def take_photo(self, **kwargs):
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return 'Error: Could not open camera.'
            print('Taking photo in 3...')
            time.sleep(1)
            print('2...')
            time.sleep(1)
            print('1...')
            time.sleep(1)
            print('CHEESE!')
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return 'Error: Failed to capture image.'
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(
                __file__)), 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            timestamp = int(time.time())
            filename = f'photo_{timestamp}.jpg'
            filepath = os.path.join(assets_dir, filename)
            cv2.imwrite(filepath, frame)
            return f'Photo taken and saved to {filepath}'
        except Exception as e:
            return f'Error taking photo: {str(e)}'
