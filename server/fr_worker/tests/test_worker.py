#!/usr/bin/env python3
"""
Face Recognition Worker Test Suite with Real Images
Tests worker functionality using actual face images from data directory
"""

import os
import sys
import time
import base64
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path so we can import broker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from broker import MessageProducer
from broker.message_producer import get_config_from_env


def setup_logging():
    """Setup basic logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_images_from_directory(data_dir: str = "data") -> Dict[str, List[Tuple[str, str]]]:
    """
    Load images from data directory structure.
    
    Args:
        data_dir: Path to data directory
        
    Returns:
        Dictionary mapping person labels to list of (image_path, base64_data) tuples
    """
    data_path = Path(data_dir)
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory '{data_dir}' not found")
    
    images_by_person = {}
    supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    # Iterate through subdirectories (each is a person)
    for person_dir in data_path.iterdir():
        if not person_dir.is_dir():
            continue
            
        person_label = person_dir.name
        images_by_person[person_label] = []
        
        # Load all images for this person
        for image_file in person_dir.iterdir():
            if image_file.suffix.lower() in supported_extensions:
                try:
                    # Read and encode image to base64
                    with open(image_file, 'rb') as f:
                        image_bytes = f.read()
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        images_by_person[person_label].append((str(image_file), image_base64))
                        
                except Exception as e:
                    logging.warning(f"Failed to load {image_file}: {e}")
    
    return images_by_person


def test_enrollment_and_recognition(producer, images_by_person: Dict[str, List[Tuple[str, str]]]):
    """
    Test user enrollment and face recognition with real images
    """
    print("\n=== Testing Enrollment and Recognition ===")
    
    company_id = "test_company_real"
    
    try:
        # Create company
        print(f"1. Creating company: {company_id}")
        success = producer.create_company(company_id)
        print(f"   Result: {success}")
        
        # Enroll users with their first image
        enrolled_users = {}
        print("\n2. Enrolling users with their first images:")
        
        for person_idx, (person_label, images) in enumerate(images_by_person.items()):
            if not images:
                print(f"   Skipping {person_label}: no images found")
                continue
                
            user_id = f"user_{person_idx:03d}"
            face_id = f"face_{person_idx:03d}_00"
            image_path, image_data = images[0]
            
            print(f"   Enrolling: {person_label} (user_id={user_id})")
            print(f"   Image: {Path(image_path).name}")
            
            try:
                embedding = producer.create_user(company_id, user_id, face_id, image_data)
                enrolled_users[person_label] = {
                    'user_id': user_id,
                    'images': images,
                    'embedding_dim': len(embedding)
                }
                print(f"   Success: Embedding dimension = {len(embedding)}")
                
            except Exception as e:
                print(f"   Failed: {e}")
                continue
        
        print(f"\nEnrolled {len(enrolled_users)} users successfully")
        
        # Test recognition with remaining images
        print("\n3. Testing recognition with different images of enrolled users:")
        
        recognition_results = {
            'correct': 0,
            'incorrect': 0,
            'not_recognized': 0,
            'total': 0
        }
        
        for person_label, user_data in enrolled_users.items():
            images = user_data['images']
            expected_user_id = user_data['user_id']
            
            # Test with images beyond the first (enrollment) image
            for img_idx, (image_path, image_data) in enumerate(images[1:], start=2):
                recognition_results['total'] += 1
                
                print(f"\n   Testing: {person_label} - Image #{img_idx} ({Path(image_path).name})")
                
                try:
                    user_id_result, confidence, bbox = producer.recognize_face(company_id, image_data)
                    
                    if user_id_result == expected_user_id:
                        recognition_results['correct'] += 1
                        print(f"   ✓ CORRECT: Recognized as {user_id_result} (confidence: {confidence:.3f})")
                    elif user_id_result is None:
                        recognition_results['not_recognized'] += 1
                        print(f"   ✗ NOT RECOGNIZED: Below threshold (confidence: {confidence:.3f})")
                    else:
                        recognition_results['incorrect'] += 1
                        print(f"   ✗ INCORRECT: Recognized as {user_id_result} instead of {expected_user_id} (confidence: {confidence:.3f})")
                    
                    print(f"   BBox: {bbox}")
                    
                except Exception as e:
                    print(f"   ERROR: {e}")
                    recognition_results['not_recognized'] += 1
        
        # Print recognition statistics
        print("\n" + "=" * 60)
        print("RECOGNITION RESULTS")
        print("=" * 60)
        
        total = recognition_results['total']
        if total > 0:
            accuracy = (recognition_results['correct'] / total) * 100
            print(f"Total Tests: {total}")
            print(f"Correct: {recognition_results['correct']} ({recognition_results['correct']/total*100:.1f}%)")
            print(f"Incorrect: {recognition_results['incorrect']} ({recognition_results['incorrect']/total*100:.1f}%)")
            print(f"Not Recognized: {recognition_results['not_recognized']} ({recognition_results['not_recognized']/total*100:.1f}%)")
            print(f"\nAccuracy: {accuracy:.2f}%")
        else:
            print("No recognition tests performed (need multiple images per person)")
        
        # Cleanup
        print("\n4. Cleaning up...")
        producer.delete_company(company_id)
        print("   Company deleted")
        
        return recognition_results
        
    except Exception as e:
        print(f"Enrollment and recognition test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_multi_face_enrollment(producer, images_by_person: Dict[str, List[Tuple[str, str]]]):
    """
    Test enrolling multiple faces per user and recognition accuracy
    """
    print("\n=== Testing Multi-Face Enrollment ===")
    
    company_id = "test_company_multiface"
    
    try:
        # Create company
        print(f"1. Creating company: {company_id}")
        producer.create_company(company_id)
        
        # Select a person with multiple images
        person_with_most_images = None
        max_images = 0
        
        for person_label, images in images_by_person.items():
            if len(images) > max_images:
                max_images = len(images)
                person_with_most_images = person_label
        
        if not person_with_most_images or max_images < 3:
            print("   Skipping: Need at least one person with 3+ images")
            producer.delete_company(company_id)
            return None
        
        print(f"\n2. Testing with: {person_with_most_images} ({max_images} images)")
        
        user_id = "multiface_user"
        images = images_by_person[person_with_most_images]
        
        # Enroll with first image
        face_id_1 = "multiface_001"
        image_path, image_data = images[0]
        print(f"   Enrolling face 1: {Path(image_path).name}")
        
        try:
            embedding = producer.create_user(company_id, user_id, face_id_1, image_data)
            print(f"   Success: Embedding dimension = {len(embedding)}")
        except Exception as e:
            print(f"   Failed: {e}")
            producer.delete_company(company_id)
            return None
        
        # Test recognition before adding more faces
        print(f"\n3. Testing recognition with 1 enrolled face:")
        test_image_path, test_image_data = images[1]
        
        try:
            user_id_result, confidence_before, bbox = producer.recognize_face(company_id, test_image_data)
            print(f"   Image: {Path(test_image_path).name}")
            print(f"   Result: {user_id_result} (confidence: {confidence_before:.3f})")
        except Exception as e:
            print(f"   Failed: {e}")
            confidence_before = 0.0
        
        # Add second face
        face_id_2 = "multiface_002"
        image_path_2, image_data_2 = images[2] if len(images) > 2 else images[1]
        print(f"\n4. Adding second face: {Path(image_path_2).name}")
        
        try:
            embedding = producer.add_face(company_id, user_id, face_id_2, image_data_2)
            print(f"   Success: Embedding dimension = {len(embedding)}")
        except Exception as e:
            print(f"   Failed: {e}")
        
        # Test recognition after adding more faces
        print(f"\n5. Testing recognition with 2 enrolled faces:")
        
        try:
            user_id_result, confidence_after, bbox = producer.recognize_face(company_id, test_image_data)
            print(f"   Image: {Path(test_image_path).name}")
            print(f"   Result: {user_id_result} (confidence: {confidence_after:.3f})")
            print(f"\n   Confidence improvement: {confidence_after - confidence_before:+.3f}")
        except Exception as e:
            print(f"   Failed: {e}")
        
        # Cleanup
        print("\n6. Cleaning up...")
        producer.delete_company(company_id)
        
        return True
        
    except Exception as e:
        print(f"Multi-face enrollment test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_face_detection(producer, images_by_person: Dict[str, List[Tuple[str, str]]]):
    """
    Test face detection on all images
    """
    print("\n=== Testing Face Detection ===")
    
    detection_stats = {
        'total_images': 0,
        'faces_detected': 0,
        'no_faces': 0,
        'multiple_faces': 0
    }
    
    print("Testing face detection on all images:")
    
    for person_label, images in images_by_person.items():
        print(f"\n{person_label}:")
        
        for image_path, image_data in images:
            detection_stats['total_images'] += 1
            
            try:
                face_count, bboxes = producer.detect_faces(image_data)
                
                if face_count == 0:
                    detection_stats['no_faces'] += 1
                    print(f"   ✗ {Path(image_path).name}: No faces detected")
                elif face_count == 1:
                    detection_stats['faces_detected'] += 1
                    print(f"   ✓ {Path(image_path).name}: 1 face {bboxes[0]}")
                else:
                    detection_stats['multiple_faces'] += 1
                    print(f"   ! {Path(image_path).name}: {face_count} faces detected")
                    
            except Exception as e:
                print(f"   ERROR {Path(image_path).name}: {e}")
    
    # Print statistics
    print("\n" + "=" * 60)
    print("DETECTION STATISTICS")
    print("=" * 60)
    print(f"Total Images: {detection_stats['total_images']}")
    print(f"Single Face Detected: {detection_stats['faces_detected']}")
    print(f"No Faces: {detection_stats['no_faces']}")
    print(f"Multiple Faces: {detection_stats['multiple_faces']}")
    
    if detection_stats['total_images'] > 0:
        success_rate = (detection_stats['faces_detected'] / detection_stats['total_images']) * 100
        print(f"\nSuccess Rate: {success_rate:.2f}%")
    
    return detection_stats


def test_cross_recognition(producer, images_by_person: Dict[str, List[Tuple[str, str]]]):
    """
    Test that enrolled users are not misidentified as each other
    """
    print("\n=== Testing Cross-Recognition (False Positives) ===")
    
    if len(images_by_person) < 2:
        print("Skipping: Need at least 2 different people")
        return None
    
    company_id = "test_company_cross"
    
    try:
        # Create company
        print(f"1. Creating company: {company_id}")
        producer.create_company(company_id)
        
        # Enroll first person
        person1_label = list(images_by_person.keys())[0]
        person1_images = images_by_person[person1_label]
        
        if not person1_images:
            print("Skipping: First person has no images")
            producer.delete_company(company_id)
            return None
        
        user_id_1 = "cross_user_001"
        face_id_1 = "cross_face_001"
        _, image_data_1 = person1_images[0]
        
        print(f"\n2. Enrolling Person 1: {person1_label}")
        producer.create_user(company_id, user_id_1, face_id_1, image_data_1)
        print(f"   Enrolled as {user_id_1}")
        
        # Test with different people
        print(f"\n3. Testing recognition with different people (should NOT match):")
        
        false_positive_count = 0
        true_negative_count = 0
        total_tests = 0
        
        for person_label, images in images_by_person.items():
            if person_label == person1_label or not images:
                continue
            
            total_tests += 1
            image_path, image_data = images[0]
            
            try:
                user_id_result, confidence, bbox = producer.recognize_face(company_id, image_data)
                
                if user_id_result is None:
                    true_negative_count += 1
                    print(f"   ✓ {person_label}: Correctly NOT recognized (confidence: {confidence:.3f})")
                else:
                    false_positive_count += 1
                    print(f"   ✗ {person_label}: FALSE POSITIVE - Recognized as {user_id_result} (confidence: {confidence:.3f})")
                    
            except Exception as e:
                print(f"   ERROR {person_label}: {e}")
        
        # Print results
        print("\n" + "=" * 60)
        print("CROSS-RECOGNITION RESULTS")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"True Negatives: {true_negative_count}")
        print(f"False Positives: {false_positive_count}")
        
        if total_tests > 0:
            specificity = (true_negative_count / total_tests) * 100
            print(f"\nSpecificity: {specificity:.2f}%")
        
        # Cleanup
        print("\n4. Cleaning up...")
        producer.delete_company(company_id)
        
        return {'true_negatives': true_negative_count, 'false_positives': false_positive_count}
        
    except Exception as e:
        print(f"Cross-recognition test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_system_operations(producer):
    """Test system monitoring operations"""
    print("\n=== Testing System Operations ===")
    
    try:
        # Test health check
        print("1. Testing health check")
        health = producer.health_check()
        print(f"   Health status: {health['status']}")
        print(f"   Response time: {health.get('response_time_ms', 'N/A')}ms")
        
        # Test cache stats
        print("2. Testing cache statistics")
        stats = producer.get_cache_stats()
        print(f"   Worker ID: {stats.get('worker_id', 'N/A')}")
        print(f"   Companies: {stats.get('companies', 0)}")
        print(f"   Users: {stats.get('total_users', 0)}")
        print(f"   Faces: {stats.get('total_faces', 0)}")
        
        return True
        
    except Exception as e:
        print(f"System operations failed: {e}")
        return False


def run_comprehensive_test(data_dir: str = "data"):
    """Run comprehensive test with real images"""
    setup_logging()
    logger = logging.getLogger('test_worker')
    
    print("=" * 70)
    print("Face Recognition Worker Test Suite - Real Images")
    print("=" * 70)
    
    # Load images
    print(f"\nLoading images from: {data_dir}")
    try:
        images_by_person = load_images_from_directory(data_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print(f"\nPlease create a '{data_dir}' directory with the following structure:")
        print(f"  {data_dir}/")
        print(f"  ├── person1/")
        print(f"  │   ├── image1.jpg")
        print(f"  │   └── image2.jpg")
        print(f"  ├── person2/")
        print(f"  │   └── image1.jpg")
        print(f"  └── ...")
        return False
    
    if not images_by_person:
        print("ERROR: No images found in data directory")
        return False
    
    # Print dataset summary
    print("\nDataset Summary:")
    total_images = 0
    for person_label, images in images_by_person.items():
        print(f"  {person_label}: {len(images)} images")
        total_images += len(images)
    print(f"Total: {len(images_by_person)} people, {total_images} images")
    
    # Load configuration
    config = get_config_from_env()
    logger.info(f"Connecting to RabbitMQ at {config.host}:{config.port}")
    
    try:
        # Create producer
        with MessageProducer(config) as producer:
            logger.info("Connected to message broker successfully")
            
            # Wait for worker to be ready
            print("\nWaiting for worker to be ready...")
            time.sleep(2)
            
            # Run tests
            tests = [
                ("System Operations", lambda p: test_system_operations(p)),
                ("Face Detection", lambda p: test_face_detection(p, images_by_person)),
                ("Enrollment and Recognition", lambda p: test_enrollment_and_recognition(p, images_by_person)),
                ("Multi-Face Enrollment", lambda p: test_multi_face_enrollment(p, images_by_person)),
                ("Cross-Recognition", lambda p: test_cross_recognition(p, images_by_person))
            ]
            
            results = []
            for test_name, test_func in tests:
                print(f"\n{'=' * 70}")
                try:
                    result = test_func(producer)
                    results.append((test_name, result is not None and result != False))
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Test {test_name} failed with exception: {e}")
                    import traceback
                    traceback.print_exc()
                    results.append((test_name, False))
            
            # Summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            
            for test_name, result in results:
                status = "PASSED" if result else "FAILED"
                symbol = "✓" if result else "✗"
                print(f"{symbol} {test_name:.<50} {status}")
            
            passed = sum(1 for _, result in results if result)
            total = len(results)
            print(f"\nTotal: {passed}/{total} tests passed")
            
            return passed == total
                
    except Exception as e:
        logger.error(f"Failed to connect to message broker: {e}")
        print(f"\nERROR: Connection failed: {e}")
        print("Make sure RabbitMQ is running and worker is started")
        return False


def run_quick_test():
    """Run a quick connectivity test"""
    setup_logging()
    
    print("=" * 50)
    print("Quick Worker Connectivity Test")
    print("=" * 50)
    
    config = get_config_from_env()
    
    try:
        with MessageProducer(config) as producer:
            print("✓ Connected to message broker")
            
            # Simple health check
            health = producer.health_check()
            if health['status'] == 'healthy':
                print("✓ Worker is responding")
                print(f"  Response time: {health.get('response_time_ms', 'N/A')}ms")
                return True
            else:
                print("✗ Worker health check failed")
                return False
                
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Quick test mode
        success = run_quick_test()
    else:
        # Comprehensive test mode with real images
        data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
        success = run_comprehensive_test(data_dir)
    
    sys.exit(0 if success else 1)