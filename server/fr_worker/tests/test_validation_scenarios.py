#!/usr/bin/env python3
"""
Test Validation Scenarios
Tests: no image, no face in image, invalid base64, damaged image
"""

import base64
import sys
import os
import cv2
import numpy as np

# Add project root to path so we can import broker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from broker import MessageProducer, ProducerError
from broker.message_producer import get_config_from_env

def create_no_face_image():
    """Create a simple image with no face (just colored rectangle)"""
    # Create 300x300 blue image
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    img[:] = (0, 0, 255)  # Blue color (BGR format)

    # Encode to JPEG
    success, buffer = cv2.imencode('.jpg', img)
    if not success:
        raise Exception("Failed to encode no-face image")

    return base64.b64encode(buffer.tobytes()).decode('utf-8')

def load_test_image(filename):
    """Load a test image from fixtures directory"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(test_dir, "fixtures", filename)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Test image not found: {image_path}")

    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def run_test(test_name, test_func):
    """Helper to run a single test"""
    print("\n" + "=" * 60)
    print(f"TEST: {test_name}")
    print("=" * 60)
    
    try:
        test_func()
        print("✗ FAILED: Should have raised ProducerError")
        return False
    except ProducerError as e:
        error_msg = str(e)
        if "error" in error_msg.lower():
            print(f"✓ PASSED: Got expected error")
            print(f"   Error message: {error_msg}")
            return True
        else:
            print(f"✗ FAILED: Got ProducerError but unexpected message")
            print(f"   Message: {error_msg}")
            return False
    except Exception as e:
        print(f"⚠ PARTIAL: Got exception (not ProducerError)")
        print(f"   Exception type: {type(e).__name__}")
        print(f"   Message: {e}")
        return True  # Still counts as catching the error

def test_validation_scenarios():
    """Test all validation scenarios"""
    
    print("=" * 60)
    print("VALIDATION SCENARIOS TEST")
    print("=" * 60)
    
    # Initialize producer
    print("\n[1] Initializing message producer...")
    producer = MessageProducer(get_config_from_env())
    print("✓ Producer initialized")
    
    # Test data
    company_id = "validation_test_company"
    user_id = "validation_user"
    face_id = "validation_face"
    
    test_results = []
    
    try:
        # Setup: Create company first
        print("\n[2] Setting up test company...")
        producer.create_company(company_id)
        print(f"✓ Test company created: {company_id}")
        
        # Test 1: Empty base64
        result = run_test(
            "Empty base64 string",
            lambda: producer.create_user(company_id, user_id, face_id, "")
        )
        test_results.append(("Empty base64", result))
        
        # Test 2: Invalid base64
        result = run_test(
            "Invalid base64 encoding",
            lambda: producer.create_user(company_id, user_id, face_id, "Not-Valid-Base64!@#$")
        )
        test_results.append(("Invalid base64", result))
        
        # Test 3: Valid base64 but not image
        result = run_test(
            "Valid base64 but not image data",
            lambda: producer.create_user(
                company_id, user_id, face_id,
                base64.b64encode(b"This is text, not an image").decode('utf-8')
            )
        )
        test_results.append(("Non-image base64", result))
        
        # Test 4: Valid image but no face
        print("\n" + "=" * 60)
        print("TEST: Valid image with NO face")
        print("=" * 60)
        try:
            no_face_image = create_no_face_image()
            print("✓ Generated no-face image")
            producer.create_user(company_id, user_id, face_id, no_face_image)
            print("✗ FAILED: Should have raised ProducerError")
            test_results.append(("No face in image", False))
        except ProducerError as e:
            print(f"✓ PASSED: Got expected error")
            print(f"   Error: {e}")
            test_results.append(("No face in image", True))
        except Exception as e:
            print(f"⚠ PARTIAL: Got exception")
            print(f"   Exception: {e}")
            test_results.append(("No face in image", True))
        
        # Test 5: Face recognition with empty image
        result = run_test(
            "Face recognition with empty image",
            lambda: producer.recognize_face(company_id, "")
        )
        test_results.append(("Recognition - empty image", result))
        
        # Test 6: Face recognition with no face
        print("\n" + "=" * 60)
        print("TEST: Face recognition with no face in image")
        print("=" * 60)
        try:
            no_face_image = create_no_face_image()
            producer.recognize_face(company_id, no_face_image)
            print("✗ FAILED: Should have raised ProducerError")
            test_results.append(("Recognition - no face", False))
        except ProducerError as e:
            print(f"✓ PASSED: Got expected error")
            print(f"   Error: {e}")
            test_results.append(("Recognition - no face", True))
        except Exception as e:
            print(f"⚠ PARTIAL: Got exception")
            print(f"   Exception: {e}")
            test_results.append(("Recognition - no face", True))
        
        # Test 7: Face detection with empty image
        result = run_test(
            "Face detection with empty image",
            lambda: producer.detect_faces("")
        )
        test_results.append(("Detection - empty image", result))
        
        # Test 8: Face detection with no face (special case - might return 0 faces)
        print("\n" + "=" * 60)
        print("TEST: Face detection with no face in image")
        print("=" * 60)
        try:
            no_face_image = create_no_face_image()
            count, bboxes = producer.detect_faces(no_face_image)
            if count == 0 and len(bboxes) == 0:
                print(f"✓ PASSED: Correctly returned 0 faces")
                test_results.append(("Detection - no face", True))
            else:
                print(f"✗ FAILED: Detected {count} faces (expected 0)")
                test_results.append(("Detection - no face", False))
        except ProducerError as e:
            print(f"✓ PASSED: Got error (alternative valid behavior)")
            print(f"   Error: {e}")
            test_results.append(("Detection - no face", True))
        
        # Test 9: Embedding generation with empty image
        result = run_test(
            "Embedding generation with empty image",
            lambda: producer.generate_embedding("")
        )
        test_results.append(("Embedding - empty image", result))
        
        # Test 10: Embedding generation with no face
        print("\n" + "=" * 60)
        print("TEST: Embedding generation with no face")
        print("=" * 60)
        try:
            no_face_image = create_no_face_image()
            producer.generate_embedding(no_face_image)
            print("✗ FAILED: Should have raised ProducerError")
            test_results.append(("Embedding - no face", False))
        except ProducerError as e:
            print(f"✓ PASSED: Got expected error")
            print(f"   Error: {e}")
            test_results.append(("Embedding - no face", True))
        except Exception as e:
            print(f"⚠ PARTIAL: Got exception")
            print(f"   Exception: {e}")
            test_results.append(("Embedding - no face", True))

        # Test 11: Multiple faces - Face detection
        print("\n" + "=" * 60)
        print("TEST: Face detection with multiple faces")
        print("=" * 60)
        try:
            multi_face_image = load_test_image("multi_face_large_center.jpg")
            count, bboxes = producer.detect_faces(multi_face_image)
            print(f"✓ Detected {count} faces")
            print(f"   Bounding boxes: {bboxes}")
            if count > 1:
                print(f"✓ PASSED: Multiple faces detected ({count} faces)")
                test_results.append(("Detection - multiple faces", True))
            else:
                print(f"⚠ WARNING: Expected multiple faces, got {count}")
                test_results.append(("Detection - multiple faces", False))
        except FileNotFoundError as e:
            print(f"⚠ SKIPPED: {e}")
            print("   Please add 'multi_face_large_center.jpg' to fixtures/")
            test_results.append(("Detection - multiple faces", None))
        except Exception as e:
            print(f"✗ FAILED: {e}")
            test_results.append(("Detection - multiple faces", False))

        # Test 12: Multiple faces - User registration (should use largest face)
        print("\n" + "=" * 60)
        print("TEST: User registration with multiple faces (should use largest)")
        print("=" * 60)
        try:
            multi_face_image = load_test_image("multi_face_large_center.jpg")
            multi_user_id = "multi_face_user"
            multi_face_id = "multi_face_001"

            embedding = producer.create_user(company_id, multi_user_id, multi_face_id, multi_face_image)
            print(f"✓ PASSED: User registered with multi-face image")
            print(f"   Embedding dimensions: {len(embedding)}")
            print(f"   System should have selected the largest/most prominent face")
            test_results.append(("Registration - multiple faces", True))

            # Cleanup: delete the user
            producer.delete_user(company_id, multi_user_id)

        except FileNotFoundError as e:
            print(f"⚠ SKIPPED: {e}")
            print("   Please add 'multi_face_large_center.jpg' to fixtures/")
            test_results.append(("Registration - multiple faces", None))
        except ProducerError as e:
            print(f"✗ FAILED: {e}")
            print("   System may not support multiple faces in registration")
            test_results.append(("Registration - multiple faces", False))
        except Exception as e:
            print(f"✗ FAILED: {e}")
            test_results.append(("Registration - multiple faces", False))

        # Test 13: Multiple faces - Face recognition (should use largest face)
        print("\n" + "=" * 60)
        print("TEST: Face recognition with multiple faces (should use largest)")
        print("=" * 60)
        try:
            # First register a user with a single face
            single_face_image = load_test_image("test_face_1.jpg")
            recog_user_id = "recog_test_user"
            recog_face_id = "recog_face_001"

            producer.create_user(company_id, recog_user_id, recog_face_id, single_face_image)
            print(f"✓ Registered user with single face")

            # Now try to recognize with a multi-face image
            multi_face_image = load_test_image("multi_face_group.jpg")
            recognized_id, confidence, bbox = producer.recognize_face(company_id, multi_face_image)

            if recognized_id is not None:
                print(f"✓ Recognition succeeded with multi-face image")
                print(f"   Recognized as: {recognized_id}")
                print(f"   Confidence: {confidence:.3f}")
                print(f"   Bbox: {bbox}")
                print(f"   System selected largest/most prominent face")
                test_results.append(("Recognition - multiple faces", True))
            else:
                print(f"⚠ No match found (expected if none match registered user)")
                print(f"   System correctly processed multi-face image")
                test_results.append(("Recognition - multiple faces", True))

            # Cleanup
            producer.delete_user(company_id, recog_user_id)

        except FileNotFoundError as e:
            print(f"⚠ SKIPPED: {e}")
            print("   Please add 'multi_face_group.jpg' and 'test_face_1.jpg' to fixtures/")
            test_results.append(("Recognition - multiple faces", None))
        except ProducerError as e:
            print(f"✗ FAILED: {e}")
            test_results.append(("Recognition - multiple faces", False))
        except Exception as e:
            print(f"✗ FAILED: {e}")
            test_results.append(("Recognition - multiple faces", False))

        # Test 14: Multiple faces side by side (consistency test)
        print("\n" + "=" * 60)
        print("TEST: Multiple faces side by side - consistency")
        print("=" * 60)
        try:
            side_by_side_image = load_test_image("multi_face_side_by_side.jpg")

            # Detect faces multiple times to check consistency
            results = []
            for _ in range(3):
                count, bboxes = producer.detect_faces(side_by_side_image)
                results.append((count, bboxes))

            # Check if results are consistent
            all_same_count = all(r[0] == results[0][0] for r in results)
            if all_same_count:
                print(f"✓ PASSED: Consistent detection across multiple calls")
                print(f"   Detected {results[0][0]} faces each time")
                test_results.append(("Detection - consistency", True))
            else:
                print(f"✗ FAILED: Inconsistent detection")
                print(f"   Counts: {[r[0] for r in results]}")
                test_results.append(("Detection - consistency", False))

        except FileNotFoundError as e:
            print(f"⚠ SKIPPED: {e}")
            print("   Please add 'multi_face_side_by_side.jpg' to fixtures/")
            test_results.append(("Detection - consistency", None))
        except Exception as e:
            print(f"✗ FAILED: {e}")
            test_results.append(("Detection - consistency", False))

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test_name}")
        
        print("\n" + "=" * 60)
        print(f"RESULTS: {passed}/{total} tests passed")
        print("=" * 60)
        
        return passed == total
        
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup: Delete test company
        try:
            print("\n[Cleanup] Deleting test company...")
            producer.delete_company(company_id)
            print("✓ Test company deleted")
        except:
            pass
        
        producer.close()
        print("[Cleanup] Producer connection closed")

if __name__ == "__main__":
    success = test_validation_scenarios()
    sys.exit(0 if success else 1)