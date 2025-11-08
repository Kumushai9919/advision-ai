#!/usr/bin/env python3
"""
Test Management Operations
Tests: create_company, create_user, add_face, delete_user, delete_company
"""

import base64
import sys
import os

# Add project root to path so we can import broker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from broker import MessageProducer
from broker.message_producer import get_config_from_env

def encode_image_file(filepath):
    """Read and encode image file to base64"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_management_operations():
    """Test all management operations"""
    
    print("=" * 60)
    print("MANAGEMENT OPERATIONS TEST")
    print("=" * 60)
    
    # Initialize producer
    print("\n[1] Initializing message producer...")
    producer = MessageProducer(get_config_from_env())
    print("✓ Producer initialized")
    
    # Test data
    company_id = "test_company_001"
    user_id = "user_001"
    face_id_1 = "face_001"
    face_id_2 = "face_002"

    # Get the directory where this test file is located
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # Path to test images in fixtures directory
    face_image_1 = os.path.join(test_dir, "fixtures", "test_face_1.jpg")
    face_image_2 = os.path.join(test_dir, "fixtures", "test_face_2.jpg")
    
    try:
        # Load images
        print("\n[2] Loading test images...")
        image_base64_1 = encode_image_file(face_image_1)
        image_base64_2 = encode_image_file(face_image_2)
        print(f"✓ Loaded {face_image_1}")
        print(f"✓ Loaded {face_image_2}")
        
        # Test 1: Create Company
        print("\n[3] Creating company...")
        result = producer.create_company(company_id)
        print(f"✓ Company created: {company_id}")
        print(f"   Result: {result}")
        
        # Test 2: Create User with first face
        print("\n[4] Creating user with first face...")
        embedding = producer.create_user(company_id, user_id, face_id_1, image_base64_1)
        print(f"✓ User created: {user_id}")
        print(f"   Face ID: {face_id_1}")
        print(f"   Embedding dimensions: {len(embedding)}")
        
        # Test 3: Add second face to user
        print("\n[5] Adding second face to user...")
        embedding2 = producer.add_face(company_id, user_id, face_id_2, image_base64_2)
        print(f"✓ Face added: {face_id_2}")
        print(f"   Embedding dimensions: {len(embedding2)}")
        
        # Test 4: Get user faces
        print("\n[6] Getting user faces...")
        face_ids = producer.get_user_faces(company_id, user_id)
        print(f"✓ User has {len(face_ids)} faces: {face_ids}")
        
        # Test 5: Face Recognition
        print("\n[7] Testing face recognition...")
        recognized_user, confidence, bbox = producer.recognize_face(company_id, image_base64_1)
        print(f"✓ Recognition result:")
        print(f"   User ID: {recognized_user}")
        print(f"   Confidence: {confidence:.3f}")
        print(f"   Bounding box: {bbox}")
        
        # Test 6: Delete User
        print("\n[8] Deleting user...")
        result = producer.delete_user(company_id, user_id)
        print(f"✓ User deleted: {result}")
        
        # Test 7: Delete Company
        print("\n[9] Deleting company...")
        result = producer.delete_company(company_id)
        print(f"✓ Company deleted: {result}")
        
        print("\n" + "=" * 60)
        print("ALL MANAGEMENT TESTS PASSED ✓")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\n✗ ERROR: Image file not found: {e}")
        print("Please provide face image files:")
        print(f"  - {face_image_1}")
        print(f"  - {face_image_2}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        producer.close()
        print("\n[10] Producer connection closed")

if __name__ == "__main__":
    test_management_operations()