import base64
import sys
import os
import cv2
import numpy as np

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from broker import MessageProducer, ProducerError
from broker.message_producer import get_config_from_env


def load_test_image(filename):
    """Load a test image from fixtures directory"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(test_dir, "fixtures", filename)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Test image not found: {image_path}")

    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')
    
company_id = 'company-1'
user_id = 'user-1'

# Initialize producer
producer = MessageProducer(get_config_from_env())

# Create company first
producer.create_company(company_id)

img1 = load_test_image('reg1.jpg')
img2 = load_test_image('reg2.jpg')

# register faces at company-1
producer.create_user(company_id, user_id, face_id='001', image_base64=img1)
producer.create_user(company_id, user_id, face_id='002', image_base64=img2)

img3 = load_test_image('t1.jpg')
img4 = load_test_image('t2.jpg')
img5 = load_test_image('t3.jpg')

recognized_id, confidence, bbox = producer.recognize_face(company_id, img3)
print(f'user-1 === {recognized_id}, conf = {confidence} bbox = {bbox}')

recognized_id, confidence, bbox = producer.recognize_face(company_id, img4)
print(f'user-1 === {recognized_id}, conf = {confidence} bbox = {bbox}')

recognized_id, confidence, bbox = producer.recognize_face(company_id, img4)
print(f'user-1 === {recognized_id}, conf = {confidence} bbox = {bbox}')