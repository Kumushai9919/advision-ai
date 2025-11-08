#!/usr/bin/env python3
"""
Face Recognition Accuracy Test
Tests face recognition system with realistic company/user distribution
"""

import os
import sys

# Add project root to path so we can import broker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

import base64
import random
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass
import json

from broker import MessageProducer
from broker.message_producer import get_config_from_env


@dataclass
class TestConfig:
    """Configuration for accuracy testing"""
    data_dir: str = 'data'
    registered_ratio: float = 0.7  # 70% of IDs will be registered
    
    # Company size distribution (percentage of companies)
    small_company_ratio: float = 0.4   # 1-3 users
    medium_company_ratio: float = 0.4  # 4-8 users
    large_company_ratio: float = 0.2   # 9-15 users
    
    # Size ranges
    small_company_size: Tuple[int, int] = (1, 3)
    medium_company_size: Tuple[int, int] = (4, 8)
    large_company_size: Tuple[int, int] = (9, 15)
    
    # Random seed for reproducibility
    random_seed: int = 42
    
    # Cross-company testing
    test_cross_company: bool = True  # Test registered users against wrong companies


@dataclass
class TestMetrics:
    """Metrics tracking for accuracy testing"""
    total_tests: int = 0
    correct_matches: int = 0
    incorrect_matches: int = 0
    false_positives: int = 0  # Unregistered face matched
    false_negatives: int = 0  # Registered face not matched
    no_face_detected: int = 0
    
    # Per-scenario metrics
    registered_correct: int = 0
    registered_total: int = 0
    unregistered_correct: int = 0  # Correctly rejected
    unregistered_total: int = 0
    cross_company_correct: int = 0  # Correctly rejected
    cross_company_total: int = 0
    
    def accuracy(self) -> float:
        """Overall accuracy"""
        if self.total_tests == 0:
            return 0.0
        return self.correct_matches / self.total_tests
    
    def precision(self) -> float:
        """Precision (of positive predictions, how many were correct)"""
        total_positive = self.correct_matches + self.incorrect_matches + self.false_positives
        if total_positive == 0:
            return 0.0
        return self.correct_matches / total_positive
    
    def recall(self) -> float:
        """Recall (of actual positives, how many were detected)"""
        total_actual_positive = self.correct_matches + self.false_negatives
        if total_actual_positive == 0:
            return 0.0
        return self.correct_matches / total_actual_positive
    
    def f1_score(self) -> float:
        """F1 Score (harmonic mean of precision and recall)"""
        p = self.precision()
        r = self.recall()
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)


class AccuracyTester:
    """Face Recognition Accuracy Tester"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.logger = logging.getLogger('accuracy_tester')
        self.producer = None
        self.metrics = TestMetrics()
        
        # Data structures
        self.all_ids: List[str] = []
        self.registered_ids: Set[str] = set()
        self.unregistered_ids: Set[str] = set()
        self.companies: Dict[str, List[str]] = {}  # company_id -> list of user_ids
        self.user_images: Dict[str, Dict[str, List[str]]] = {}  # user_id -> {train: [], test: []}
        
        # Set random seed
        random.seed(config.random_seed)
    
    def setup(self):
        """Setup test environment"""
        self.logger.info("Setting up accuracy test...")
        
        # Load data
        self._load_data()
        
        # Split IDs into registered/unregistered
        self._split_ids()
        
        # Create company distribution
        self._create_companies()
        
        # Split images into train/test
        self._split_images()
        
        # Connect to producer
        self.producer = MessageProducer(get_config_from_env())
        
        self.logger.info("Setup completed")
        self._log_test_config()
    
    def _load_data(self):
        """Load all person IDs from data directory"""
        self.logger.info(f"Loading data from {self.config.data_dir}")
        
        data_path = Path(self.config.data_dir)
        if not data_path.exists():
            raise ValueError(f"Data directory not found: {self.config.data_dir}")
        
        for person_dir in data_path.iterdir():
            if person_dir.is_dir():
                images = list(person_dir.glob('*.jpg')) + list(person_dir.glob('*.png')) + \
                         list(person_dir.glob('*.jpeg')) + list(person_dir.glob('*.JPG'))
                
                if len(images) >= 2:
                    self.all_ids.append(person_dir.name)
                else:
                    self.logger.warning(f"Skipping {person_dir.name}: only {len(images)} images (need at least 2)")
        
        self.logger.info(f"Loaded {len(self.all_ids)} person IDs")
    
    def _split_ids(self):
        """Split IDs into registered and unregistered"""
        random.shuffle(self.all_ids)
        
        n_registered = int(len(self.all_ids) * self.config.registered_ratio)
        self.registered_ids = set(self.all_ids[:n_registered])
        self.unregistered_ids = set(self.all_ids[n_registered:])
        
        self.logger.info(f"Registered IDs: {len(self.registered_ids)}")
        self.logger.info(f"Unregistered IDs: {len(self.unregistered_ids)}")
    
    def _create_companies(self):
        """Create companies with realistic user distribution"""
        registered_list = list(self.registered_ids)
        random.shuffle(registered_list)
        
        company_sizes = []
        idx = 0
        company_num = 1
        
        while idx < len(registered_list):
            # Determine company size based on distribution
            rand = random.random()
            if rand < self.config.small_company_ratio:
                size = random.randint(*self.config.small_company_size)
            elif rand < self.config.small_company_ratio + self.config.medium_company_ratio:
                size = random.randint(*self.config.medium_company_size)
            else:
                size = random.randint(*self.config.large_company_size)
            
            # Get users for this company
            company_users = registered_list[idx:idx + size]
            if company_users:
                company_id = f"company_{company_num}"
                self.companies[company_id] = company_users
                company_sizes.append(len(company_users))
                company_num += 1
            
            idx += size
        
        self.logger.info(f"Created {len(self.companies)} companies")
        self.logger.info(f"Company sizes - Min: {min(company_sizes)}, Max: {max(company_sizes)}, Avg: {sum(company_sizes)/len(company_sizes):.1f}")
    
    def _split_images(self):
        """Split each person's images into train and test sets"""
        for person_id in self.all_ids:
            person_dir = Path(self.config.data_dir) / person_id
            images = list(person_dir.glob('*.jpg')) + list(person_dir.glob('*.png')) + \
                     list(person_dir.glob('*.jpeg')) + list(person_dir.glob('*.JPG'))
            
            # Shuffle images
            random.shuffle(images)
            
            # Split 50/50 (round up for training)
            split_idx = (len(images) + 1) // 2
            train_images = [str(img) for img in images[:split_idx]]
            test_images = [str(img) for img in images[split_idx:]]
            
            self.user_images[person_id] = {
                'train': train_images,
                'test': test_images
            }
    
    def _log_test_config(self):
        """Log test configuration"""
        self.logger.info("=" * 60)
        self.logger.info("TEST CONFIGURATION")
        self.logger.info("=" * 60)
        self.logger.info(f"Total IDs: {len(self.all_ids)}")
        self.logger.info(f"Registered IDs: {len(self.registered_ids)}")
        self.logger.info(f"Unregistered IDs: {len(self.unregistered_ids)}")
        self.logger.info(f"Companies: {len(self.companies)}")
        
        total_train = sum(len(imgs['train']) for imgs in self.user_images.values())
        total_test = sum(len(imgs['test']) for imgs in self.user_images.values())
        self.logger.info(f"Training images: {total_train}")
        self.logger.info(f"Test images: {total_test}")
        self.logger.info("=" * 60)
    
    def _image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 string"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def register_users(self):
        """Register all users in their respective companies"""
        self.logger.info("Starting user registration...")
        
        for company_id, user_ids in self.companies.items():
            self.logger.info(f"Registering company {company_id} with {len(user_ids)} users")
            
            # Create company
            self.producer.create_company(company_id)
            
            # Register each user
            for user_id in user_ids:
                train_images = self.user_images[user_id]['train']
                
                # Create user with first training image
                first_image = self._image_to_base64(train_images[0])
                face_id = f"{user_id}_face_0"
                
                try:
                    embedding = self.producer.create_user(
                        company_id=company_id,
                        user_id=user_id,
                        face_id=face_id,
                        image_base64=first_image
                    )
                    self.logger.debug(f"Created user {user_id} with face {face_id}")
                    
                    # Add additional training images
                    for idx, image_path in enumerate(train_images[1:], start=1):
                        image_base64 = self._image_to_base64(image_path)
                        face_id = f"{user_id}_face_{idx}"
                        
                        embedding = self.producer.add_face(
                            company_id=company_id,
                            user_id=user_id,
                            face_id=face_id,
                            image_base64=image_base64
                        )
                        self.logger.debug(f"Added face {face_id} to user {user_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to register user {user_id}: {e}")
        
        self.logger.info("User registration completed")
    
    def run_tests(self):
        """Run all accuracy tests"""
        self.logger.info("Starting accuracy tests...")
        
        # Test 1: Registered users (should match)
        self._test_registered_users()
        
        # Test 2: Unregistered users (should not match)
        self._test_unregistered_users()
        
        # Test 3: Cross-company (should not match)
        if self.config.test_cross_company:
            self._test_cross_company()
        
        self.logger.info("All tests completed")
    
    def _test_registered_users(self):
        """Test registered users against their own company"""
        self.logger.info("Testing registered users (expected: match)")
        
        for company_id, user_ids in self.companies.items():
            for user_id in user_ids:
                test_images = self.user_images[user_id]['test']
                
                for image_path in test_images:
                    try:
                        image_base64 = self._image_to_base64(image_path)
                        recognized_id, confidence, bbox = self.producer.recognize_face(
                            company_id=company_id,
                            image_base64=image_base64
                        )
                        
                        self.metrics.total_tests += 1
                        self.metrics.registered_total += 1
                        
                        if recognized_id == user_id:
                            self.metrics.correct_matches += 1
                            self.metrics.registered_correct += 1
                            self.logger.debug(f"✓ Correct match: {user_id} (confidence: {confidence:.3f})")
                        elif recognized_id is None:
                            self.metrics.false_negatives += 1
                            self.logger.warning(f"✗ False negative: {user_id} not recognized (confidence: {confidence:.3f})")
                        else:
                            self.metrics.incorrect_matches += 1
                            self.logger.warning(f"✗ Incorrect match: expected {user_id}, got {recognized_id} (confidence: {confidence:.3f})")
                        
                    except Exception as e:
                        self.metrics.no_face_detected += 1
                        self.logger.error(f"Error testing {user_id}: {e}")
    
    def _test_unregistered_users(self):
        """Test unregistered users (should return None)"""
        self.logger.info("Testing unregistered users (expected: no match)")
        
        # Test against random companies
        if not self.companies:
            return
        
        for user_id in self.unregistered_ids:
            test_images = self.user_images[user_id]['test']
            company_id = random.choice(list(self.companies.keys()))
            
            for image_path in test_images:
                try:
                    image_base64 = self._image_to_base64(image_path)
                    recognized_id, confidence, bbox = self.producer.recognize_face(
                        company_id=company_id,
                        image_base64=image_base64
                    )
                    
                    self.metrics.total_tests += 1
                    self.metrics.unregistered_total += 1
                    
                    if recognized_id is None:
                        self.metrics.correct_matches += 1
                        self.metrics.unregistered_correct += 1
                        self.logger.debug(f"✓ Correctly rejected unregistered user {user_id}")
                    else:
                        self.metrics.false_positives += 1
                        self.logger.warning(f"✗ False positive: unregistered {user_id} matched as {recognized_id} (confidence: {confidence:.3f})")
                    
                except Exception as e:
                    self.metrics.no_face_detected += 1
                    self.logger.error(f"Error testing unregistered {user_id}: {e}")
    
    def _test_cross_company(self):
        """Test registered users against wrong companies"""
        self.logger.info("Testing cross-company (expected: no match)")
        
        if len(self.companies) < 2:
            self.logger.warning("Not enough companies for cross-company testing")
            return
        
        company_list = list(self.companies.items())
        
        for company_id, user_ids in company_list:
            # Pick a different company
            other_companies = [c for c in self.companies.keys() if c != company_id]
            if not other_companies:
                continue
            
            wrong_company = random.choice(other_companies)
            
            # Test a subset of users (1-2 per company to avoid too many tests)
            test_users = random.sample(user_ids, min(2, len(user_ids)))
            
            for user_id in test_users:
                test_images = self.user_images[user_id]['test']
                
                # Test first image only to limit test count
                if test_images:
                    try:
                        image_base64 = self._image_to_base64(test_images[0])
                        recognized_id, confidence, bbox = self.producer.recognize_face(
                            company_id=wrong_company,
                            image_base64=image_base64
                        )
                        
                        self.metrics.total_tests += 1
                        self.metrics.cross_company_total += 1
                        
                        if recognized_id is None:
                            self.metrics.correct_matches += 1
                            self.metrics.cross_company_correct += 1
                            self.logger.debug(f"✓ Correctly rejected {user_id} in wrong company")
                        else:
                            self.metrics.incorrect_matches += 1
                            self.logger.warning(f"✗ Wrong company match: {user_id} matched as {recognized_id} in {wrong_company}")
                        
                    except Exception as e:
                        self.metrics.no_face_detected += 1
                        self.logger.error(f"Error testing cross-company {user_id}: {e}")
    
    def print_results(self):
        """Print detailed test results"""
        m = self.metrics
        
        print("\n" + "=" * 80)
        print("FACE RECOGNITION ACCURACY TEST RESULTS")
        print("=" * 80)
        
        print(f"\nOVERALL METRICS:")
        print(f"  Total Tests:        {m.total_tests}")
        print(f"  Correct:            {m.correct_matches} ({m.accuracy()*100:.2f}%)")
        print(f"  Incorrect:          {m.incorrect_matches}")
        print(f"  No Face Detected:   {m.no_face_detected}")
        
        print(f"\nCLASSIFICATION METRICS:")
        print(f"  Accuracy:           {m.accuracy()*100:.2f}%")
        print(f"  Precision:          {m.precision()*100:.2f}%")
        print(f"  Recall:             {m.recall()*100:.2f}%")
        print(f"  F1 Score:           {m.f1_score()*100:.2f}%")
        
        print(f"\nERROR ANALYSIS:")
        print(f"  False Positives:    {m.false_positives} (unregistered matched)")
        print(f"  False Negatives:    {m.false_negatives} (registered not matched)")
        
        if m.registered_total > 0:
            print(f"\nREGISTERED USERS TEST:")
            print(f"  Total:              {m.registered_total}")
            print(f"  Correct:            {m.registered_correct} ({m.registered_correct/m.registered_total*100:.2f}%)")
        
        if m.unregistered_total > 0:
            print(f"\nUNREGISTERED USERS TEST:")
            print(f"  Total:              {m.unregistered_total}")
            print(f"  Correct Rejections: {m.unregistered_correct} ({m.unregistered_correct/m.unregistered_total*100:.2f}%)")
        
        if m.cross_company_total > 0:
            print(f"\nCROSS-COMPANY TEST:")
            print(f"  Total:              {m.cross_company_total}")
            print(f"  Correct Rejections: {m.cross_company_correct} ({m.cross_company_correct/m.cross_company_total*100:.2f}%)")
        
        print("\n" + "=" * 80)
    
    def save_results(self, output_file: str = 'accuracy_results.json'):
        """Save results to JSON file"""
        results = {
            'config': {
                'data_dir': self.config.data_dir,
                'registered_ratio': self.config.registered_ratio,
                'random_seed': self.config.random_seed,
                'total_ids': len(self.all_ids),
                'registered_ids': len(self.registered_ids),
                'unregistered_ids': len(self.unregistered_ids),
                'companies': len(self.companies)
            },
            'metrics': {
                'total_tests': self.metrics.total_tests,
                'correct_matches': self.metrics.correct_matches,
                'incorrect_matches': self.metrics.incorrect_matches,
                'false_positives': self.metrics.false_positives,
                'false_negatives': self.metrics.false_negatives,
                'no_face_detected': self.metrics.no_face_detected,
                'accuracy': self.metrics.accuracy(),
                'precision': self.metrics.precision(),
                'recall': self.metrics.recall(),
                'f1_score': self.metrics.f1_score()
            },
            'per_scenario': {
                'registered': {
                    'total': self.metrics.registered_total,
                    'correct': self.metrics.registered_correct,
                    'accuracy': self.metrics.registered_correct / self.metrics.registered_total if self.metrics.registered_total > 0 else 0
                },
                'unregistered': {
                    'total': self.metrics.unregistered_total,
                    'correct': self.metrics.unregistered_correct,
                    'accuracy': self.metrics.unregistered_correct / self.metrics.unregistered_total if self.metrics.unregistered_total > 0 else 0
                },
                'cross_company': {
                    'total': self.metrics.cross_company_total,
                    'correct': self.metrics.cross_company_correct,
                    'accuracy': self.metrics.cross_company_correct / self.metrics.cross_company_total if self.metrics.cross_company_total > 0 else 0
                }
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to {output_file}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.producer:
            self.producer.close()


def setup_logging(log_level: str = 'INFO'):
    """Setup logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('accuracy_test.log')
        ]
    )
    
    # Reduce noise from pika
    logging.getLogger('pika').setLevel(logging.WARNING)


def main():
    """Main entry point"""
    import argparse

    # Get default data directory relative to this test file
    test_dir = os.path.dirname(os.path.abspath(__file__))
    default_data_dir = os.path.join(test_dir, 'fixtures', 'test_data')

    parser = argparse.ArgumentParser(description='Face Recognition Accuracy Test')
    parser.add_argument('--data-dir', default=default_data_dir, help='Data directory path')
    parser.add_argument('--registered-ratio', type=float, default=0.7,
                        help='Ratio of IDs to register (default: 0.7)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--no-cross-company', action='store_true',
                        help='Disable cross-company testing')
    parser.add_argument('--output', default='accuracy_results.json',
                        help='Output file for results')

    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger('main')
    
    try:
        # Create config
        config = TestConfig(
            data_dir=args.data_dir,
            registered_ratio=args.registered_ratio,
            random_seed=args.seed,
            test_cross_company=not args.no_cross_company
        )
        
        # Create tester
        tester = AccuracyTester(config)
        
        # Run test workflow
        tester.setup()
        tester.register_users()
        tester.run_tests()
        
        # Show and save results
        tester.print_results()
        tester.save_results(args.output)
        
        # Cleanup
        tester.cleanup()
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()